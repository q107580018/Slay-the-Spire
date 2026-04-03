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


def _apply_relic_acquisition(
    *, run_state: RunState, relic_id: str, registry: ContentProviderPort
) -> RunState:
    relic = registry.relics().get(relic_id)
    relics = list(run_state.relics)

    if relic_id == "circlet":
        return replace(run_state, relics=[*relics, relic_id])

    if relic.replaces_relic_id is not None:
        relics = [owned for owned in relics if owned != relic.replaces_relic_id]

    if relic_id in relics:
        return replace(run_state, relics=relics)
    return replace(run_state, relics=[*relics, relic_id])


def apply_reward(
    *, run_state: RunState, reward_id: str, registry: ContentProviderPort
) -> RunState:
    if reward_id.startswith("gold:"):
        amount = int(reward_id.split(":", 1)[1])
        return replace(run_state, gold=run_state.gold + _gold_amount(run_state, amount))
    if reward_id.startswith("relic:"):
        relic_id = reward_id.split(":", 1)[1]
        return _apply_relic_acquisition(
            run_state=run_state,
            relic_id=relic_id,
            registry=registry,
        )
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
    if reward_id.startswith("card:"):
        card_id = reward_id.split(":", 1)[1]
        registry.cards().get(card_id)
        return _apply_card_reward(run_state, card_id)
    return run_state
