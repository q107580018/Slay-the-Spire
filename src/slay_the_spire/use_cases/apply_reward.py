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
    if "golden_idol" not in run_state.relics:
        return amount
    return amount + (amount // 4)


def apply_reward(*, run_state: RunState, reward_id: str, registry: ContentProviderPort) -> RunState:
    if reward_id.startswith("gold:"):
        amount = int(reward_id.split(":", 1)[1])
        return replace(run_state, gold=run_state.gold + _gold_amount(run_state, amount))
    if reward_id == "card:reward_strike":
        registry.cards().get("strike_plus")
        return replace(run_state, deck=[*run_state.deck, _next_instance_id(run_state.deck, "strike_plus")])
    if reward_id == "card:reward_defend":
        registry.cards().get("defend_plus")
        return replace(run_state, deck=[*run_state.deck, _next_instance_id(run_state.deck, "defend_plus")])
    if reward_id.startswith("card:"):
        card_id = reward_id.split(":", 1)[1]
        registry.cards().get(card_id)
        return replace(run_state, deck=[*run_state.deck, _next_instance_id(run_state.deck, card_id)])
    return run_state
