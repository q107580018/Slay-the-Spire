from __future__ import annotations

from dataclasses import replace

from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.use_cases.reward_actions import RewardAction, parse_reward_action


def _is_placeholder_card(*, registry: ContentProviderPort, card_id: str) -> bool:
    card_def = registry.cards().get(card_id)
    return getattr(card_def, "implementation_status", None) == "placeholder"


def _is_placeholder_relic(*, registry: ContentProviderPort, relic_id: str) -> bool:
    relic_def = registry.relics().get(relic_id)
    return getattr(relic_def, "implementation_status", None) == "placeholder"


def _is_placeholder_potion(*, registry: ContentProviderPort, potion_id: str) -> bool:
    potion_def = registry.potions().get(potion_id)
    return getattr(potion_def, "implementation_status", None) == "placeholder"


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


def _resolve_card_reward_card_id(
    card_id: str, registry: ContentProviderPort
) -> str | None:
    if card_id == "reward_strike":
        if _is_placeholder_card(registry=registry, card_id="strike_plus"):
            return None
        registry.cards().get("strike_plus")
        return "strike_plus"
    if card_id == "reward_defend":
        if _is_placeholder_card(registry=registry, card_id="defend_plus"):
            return None
        registry.cards().get("defend_plus")
        return "defend_plus"
    if _is_placeholder_card(registry=registry, card_id=card_id):
        return None
    registry.cards().get(card_id)
    return card_id


def _upgrade_card_in_deck(
    run_state: RunState, card_instance_id: str, *, registry: ContentProviderPort
) -> RunState:
    if card_instance_id not in run_state.deck:
        return run_state
    card_id = card_id_from_instance_id(card_instance_id)
    upgraded_card_id = registry.cards().get(card_id).upgrades_to
    if upgraded_card_id is None:
        return run_state
    _old_card_id, suffix = card_instance_id.split("#", 1)
    upgraded_instance_id = f"{upgraded_card_id}#{suffix}"
    return replace(
        run_state,
        deck=[
            upgraded_instance_id if card == card_instance_id else card
            for card in run_state.deck
        ],
    )


def _remove_card_from_deck(run_state: RunState, card_instance_id: str) -> RunState:
    if card_instance_id not in run_state.deck:
        return run_state
    return replace(
        run_state,
        deck=[card for card in run_state.deck if card != card_instance_id],
        card_removal_count=run_state.card_removal_count + 1,
    )


def _select_transform_target_card_id(
    run_state: RunState,
    card_instance_id: str,
    *,
    registry: ContentProviderPort,
    target_card_id: str | None,
) -> str | None:
    source_card_id = card_id_from_instance_id(card_instance_id)
    if target_card_id is not None:
        registry.cards().get(target_card_id)
        return target_card_id

    candidate_ids = sorted(
        card.id
        for card in registry.cards().all()
        if card.id != source_card_id and card.card_type not in {"curse", "status"}
    )
    if not candidate_ids:
        return None
    return candidate_ids[0]


def _transform_card_in_deck(
    run_state: RunState,
    card_instance_id: str,
    *,
    registry: ContentProviderPort,
    target_card_id: str | None,
) -> RunState:
    if card_instance_id not in run_state.deck:
        return run_state
    next_card_id = _select_transform_target_card_id(
        run_state,
        card_instance_id,
        registry=registry,
        target_card_id=target_card_id,
    )
    if next_card_id is None:
        return run_state
    _old_card_id, suffix = card_instance_id.split("#", 1)
    transformed_instance_id = f"{next_card_id}#{suffix}"
    return replace(
        run_state,
        deck=[
            transformed_instance_id if card == card_instance_id else card
            for card in run_state.deck
        ],
    )


def _duplicate_card_in_deck(run_state: RunState, card_instance_id: str) -> RunState:
    if card_instance_id not in run_state.deck:
        return run_state
    card_id = card_id_from_instance_id(card_instance_id)
    next_card_id = _next_instance_id(run_state.deck, card_id)
    bonus_gold = _card_acquisition_gold_bonus(run_state)
    return replace(
        run_state,
        deck=[*run_state.deck, next_card_id],
        gold=run_state.gold + bonus_gold,
    )


def _apply_relic_acquisition(
    *, run_state: RunState, relic_id: str, registry: ContentProviderPort
) -> tuple[RunState, bool]:
    relic = registry.relics().get(relic_id)
    if (
        getattr(relic, "implementation_status", None) == "placeholder"
        and relic.replaces_relic_id is None
    ):
        return run_state, False
    relics = list(run_state.relics)

    if relic_id == "circlet":
        return replace(run_state, relics=[*relics, relic_id]), True

    if relic.replaces_relic_id is not None:
        relics = [owned for owned in relics if owned != relic.replaces_relic_id]

    if relic_id in relics:
        return replace(run_state, relics=relics), False
    return replace(run_state, relics=[*relics, relic_id]), True


def apply_reward_action(
    *, run_state: RunState, action: RewardAction, registry: ContentProviderPort
) -> RunState:
    try:
        if action.kind == "gold":
            amount = action.payload.get("amount")
            if not isinstance(amount, int):
                return run_state
            return replace(
                run_state,
                gold=run_state.gold + _gold_amount(run_state, amount),
            )
        if action.kind == "relic":
            relic_id = action.payload.get("relic_id")
            if not isinstance(relic_id, str) or not relic_id:
                return run_state
            updated, acquired = _apply_relic_acquisition(
                run_state=run_state,
                relic_id=relic_id,
                registry=registry,
            )
            if not acquired:
                return updated
            return _apply_relic_on_acquire_effects(updated, relic_id, registry=registry)
        if action.kind == "card":
            card_id = action.payload.get("card_id")
            if not isinstance(card_id, str) or not card_id:
                return run_state
            resolved_card_id = _resolve_card_reward_card_id(card_id, registry)
            if resolved_card_id is None:
                return run_state
            return _apply_card_reward(run_state, resolved_card_id)
        if action.kind == "card_offer":
            card_id = action.payload.get("card_id")
            if not isinstance(card_id, str) or not card_id:
                return run_state
            if _is_placeholder_card(registry=registry, card_id=card_id):
                return run_state
            registry.cards().get(card_id)
            return _apply_card_reward(run_state, card_id)
        if action.kind == "potion":
            potion_id = action.payload.get("potion_id")
            if not isinstance(potion_id, str) or not potion_id:
                return run_state
            if _is_placeholder_potion(registry=registry, potion_id=potion_id):
                return run_state
            registry.potions().get(potion_id)
            if "sozu" in run_state.relics:
                return run_state
            return replace(run_state, potions=[*run_state.potions, potion_id])
        if action.kind == "event":
            return run_state
        if action.kind == "remove":
            card_instance_id = action.payload.get("card_instance_id")
            if not isinstance(card_instance_id, str) or not card_instance_id:
                return run_state
            return _remove_card_from_deck(run_state, card_instance_id)
        if action.kind == "upgrade":
            card_instance_id = action.payload.get("card_instance_id")
            if not isinstance(card_instance_id, str) or not card_instance_id:
                return run_state
            return _upgrade_card_in_deck(
                run_state,
                card_instance_id,
                registry=registry,
            )
        if action.kind == "transform":
            card_instance_id = action.payload.get("card_instance_id")
            target_card_id = action.payload.get("target_card_id")
            if not isinstance(card_instance_id, str) or not card_instance_id:
                return run_state
            if target_card_id is not None and not isinstance(target_card_id, str):
                return run_state
            return _transform_card_in_deck(
                run_state,
                card_instance_id,
                registry=registry,
                target_card_id=target_card_id,
            )
        if action.kind == "duplicate":
            card_instance_id = action.payload.get("card_instance_id")
            if not isinstance(card_instance_id, str) or not card_instance_id:
                return run_state
            return _duplicate_card_in_deck(run_state, card_instance_id)
        if action.kind in {"skip", "noop"}:
            return run_state
        return run_state
    except (KeyError, TypeError, ValueError):
        return run_state


def apply_reward(
    *, run_state: RunState, reward_id: str, registry: ContentProviderPort
) -> RunState:
    action = parse_reward_action(reward_id)
    return apply_reward_action(run_state=run_state, action=action, registry=registry)
