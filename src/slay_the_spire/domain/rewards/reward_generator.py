from __future__ import annotations


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
    card_suffix = "reward_strike" if base % 2 == 0 else "reward_defend"
    return [f"gold:{gold_amount}", f"card:{card_suffix}"]
