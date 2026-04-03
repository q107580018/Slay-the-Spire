from __future__ import annotations

from dataclasses import replace

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


def _apply_relic_on_acquire_effects(run_state: RunState, relic_id: str) -> RunState:
    max_hp = run_state.max_hp
    current_hp = run_state.current_hp
    gold = run_state.gold

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
        max_hp == run_state.max_hp
        and current_hp == run_state.current_hp
        and gold == run_state.gold
    ):
        return run_state

    return replace(run_state, max_hp=max_hp, current_hp=current_hp, gold=gold)


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
        return _apply_relic_on_acquire_effects(updated, relic_id)
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
        return replace(run_state, potions=[*run_state.potions, potion_id])
    if reward_id.startswith("card:"):
        card_id = reward_id.split(":", 1)[1]
        registry.cards().get(card_id)
        return _apply_card_reward(run_state, card_id)
    return run_state
