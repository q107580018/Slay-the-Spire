from __future__ import annotations

from dataclasses import replace

from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort


def _next_instance_id(deck: list[str], card_id: str) -> str:
    highest_suffix = 0
    for card_instance_id in deck:
        _current_card_id, suffix = card_instance_id.split("#", 1)
        if suffix.isdigit():
            highest_suffix = max(highest_suffix, int(suffix))
    return f"{card_id}#{highest_suffix + 1}"


def _gold_amount(run_state: RunState, amount: int) -> int:
    if "ectoplasm" in run_state.relics:
        return 0
    if "golden_idol" not in run_state.relics:
        return amount
    return amount + (amount // 4)


def _card_acquisition_gold_bonus(run_state: RunState) -> int:
    if "ceramic_fish" not in run_state.relics:
        return 0
    return _gold_amount(run_state, 9)


def _apply_card_reward(run_state: RunState, card_id: str) -> RunState:
    next_card_id = _next_instance_id(run_state.deck, card_id)
    bonus_gold = _card_acquisition_gold_bonus(run_state)
    return replace(
        run_state,
        deck=[*run_state.deck, next_card_id],
        gold=run_state.gold + bonus_gold,
    )


_ON_ACQUIRE_MAX_HP_BONUS: dict[str, int] = {
    "strawberry": 7,
    "pear": 10,
    "mango": 14,
    "leeches_waffle": 7,
}

_ON_ACQUIRE_GOLD_BONUS: dict[str, int] = {
    "old_coin": 300,
}

_HEAL_TO_FULL_ON_ACQUIRE: frozenset[str] = frozenset({"leeches_waffle"})

_ON_ACQUIRE_RELIC_POSITION_FLAGS: dict[str, tuple[str, int]] = {
    "vajra": ("relic:vajra:strength_bonus", 1),
    "oddly_smooth_stone": ("relic:oddly_smooth_stone:dexterity_bonus", 1),
}


def _upgrade_matching_cards(
    run_state: RunState,
    *,
    registry: ContentProviderPort,
    card_type: str,
    limit: int,
    exclude_rarity: str | None = None,
) -> RunState:
    updated_deck = list(run_state.deck)
    upgraded = 0
    for index, instance_id in enumerate(updated_deck):
        card_id = card_id_from_instance_id(instance_id)
        card_def = registry.cards().get(card_id)
        if card_def.card_type != card_type:
            continue
        if not card_def.upgrades_to:
            continue
        if exclude_rarity is not None and card_def.rarity == exclude_rarity:
            continue
        updated_deck[index] = instance_id.replace(card_id, card_def.upgrades_to, 1)
        upgraded += 1
        if upgraded == limit:
            break
    return replace(run_state, deck=updated_deck)


def _apply_relic_on_acquire_effects(
    run_state: RunState, relic_id: str, *, registry: ContentProviderPort
) -> RunState:
    updated = run_state
    max_hp = updated.max_hp
    current_hp = updated.current_hp
    gold = updated.gold

    hp_bonus = _ON_ACQUIRE_MAX_HP_BONUS.get(relic_id, 0)
    if hp_bonus:
        max_hp += hp_bonus
        current_hp += hp_bonus

    if relic_id in _HEAL_TO_FULL_ON_ACQUIRE:
        current_hp = max_hp

    gold_bonus = _ON_ACQUIRE_GOLD_BONUS.get(relic_id, 0)
    if gold_bonus:
        gold += _gold_amount(run_state, gold_bonus)

    if (
        max_hp != updated.max_hp
        or current_hp != updated.current_hp
        or gold != updated.gold
    ):
        updated = replace(updated, max_hp=max_hp, current_hp=current_hp, gold=gold)

    if relic_id == "war_paint":
        updated = _upgrade_matching_cards(
            updated,
            registry=registry,
            card_type="skill",
            limit=2,
        )
    if relic_id == "whetstone":
        updated = _upgrade_matching_cards(
            updated, registry=registry, card_type="attack", limit=2
        )
    if relic_id in _ON_ACQUIRE_RELIC_POSITION_FLAGS:
        key, value = _ON_ACQUIRE_RELIC_POSITION_FLAGS[relic_id]
        positions = dict(updated.relic_sequence_positions)
        positions[key] = value
        updated = replace(updated, relic_sequence_positions=positions)

    return updated


def _apply_relic_acquisition(
    *, run_state: RunState, relic_id: str, registry: ContentProviderPort
) -> tuple[RunState, bool]:
    relic = registry.relics().get(relic_id)
    relics = list(run_state.relics)

    if relic_id == "circlet":
        return replace(run_state, relics=[*relics, relic_id]), True

    if relic.replaces_relic_id is not None:
        relics = [owned for owned in relics if owned != relic.replaces_relic_id]

    if relic_id in relics:
        return replace(run_state, relics=relics), False
    return replace(run_state, relics=[*relics, relic_id]), True


def apply_reward(
    *, run_state: RunState, reward_id: str, registry: ContentProviderPort
) -> RunState:
    if reward_id.startswith("gold:"):
        amount = int(reward_id.split(":", 1)[1])
        return replace(run_state, gold=run_state.gold + _gold_amount(run_state, amount))
    if reward_id.startswith("relic:"):
        relic_id = reward_id.split(":", 1)[1]
        updated, acquired = _apply_relic_acquisition(
            run_state=run_state,
            relic_id=relic_id,
            registry=registry,
        )
        if not acquired:
            return updated
        return _apply_relic_on_acquire_effects(updated, relic_id, registry=registry)
    if reward_id == "card:reward_strike":
        registry.cards().get("strike_plus")
        return _apply_card_reward(run_state, "strike_plus")
    if reward_id == "card:reward_defend":
        registry.cards().get("defend_plus")
        return _apply_card_reward(run_state, "defend_plus")
    if reward_id.startswith("card_offer:"):
        card_id = reward_id.split(":", 1)[1]
        registry.cards().get(card_id)
        return _apply_card_reward(run_state, card_id)
    if reward_id.startswith("potion:"):
        potion_id = reward_id.split(":", 1)[1]
        registry.potions().get(potion_id)
        if "sozu" in run_state.relics:
            return run_state
        return replace(run_state, potions=[*run_state.potions, potion_id])
    if reward_id.startswith("card:"):
        card_id = reward_id.split(":", 1)[1]
        registry.cards().get(card_id)
        return _apply_card_reward(run_state, card_id)
    return run_state
