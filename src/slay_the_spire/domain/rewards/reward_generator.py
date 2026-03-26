from __future__ import annotations

from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort

_IRONCLAD_EARLY_REWARD_CARDS = (
    "anger",
    "pommel_strike",
    "shrug_it_off",
)

_BOSS_RELIC_OFFERS = ("black_blood", "anchor", "lantern")


def _room_hash(room_id: str) -> int:
    if not isinstance(room_id, str):
        raise TypeError("room_id must be a string")
    if not room_id:
        raise ValueError("room_id must not be empty")
    return sum(ord(ch) for ch in room_id)


def _require_seed(seed: object) -> int:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an int")
    return seed


def generate_combat_rewards(*, room_id: str, seed: int) -> list[str]:
    normalized_seed = _require_seed(seed)
    base = _room_hash(room_id) + normalized_seed
    gold_amount = 10 + (normalized_seed % 10)
    card_id = _IRONCLAD_EARLY_REWARD_CARDS[base % len(_IRONCLAD_EARLY_REWARD_CARDS)]
    return [f"gold:{gold_amount}", f"card:{card_id}"]


def generate_boss_rewards(
    *,
    room_id: str,
    seed: int,
    run_state: RunState,
    registry: ContentProviderPort,
) -> dict[str, object]:
    _room_hash(room_id)
    normalized_seed = _require_seed(seed)
    available_relic_ids = {relic.id for relic in registry.relics().all()}
    boss_pool = [
        relic_id
        for relic_id in _BOSS_RELIC_OFFERS
        if relic_id in available_relic_ids and relic_id not in run_state.relics
    ]
    return {
        "generated_by": "boss_reward_generator",
        "gold_reward": 90 + (normalized_seed % 21),
        "claimed_gold": False,
        "boss_relic_offers": boss_pool[:3],
        "claimed_relic_id": None,
    }
