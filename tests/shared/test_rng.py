from __future__ import annotations

from slay_the_spire.shared.rng import rng_for_room, rng_for_run


def test_rng_for_run_is_deterministic_for_same_seed_and_category() -> None:
    left = rng_for_run(seed=7, category="map:topology")
    right = rng_for_run(seed=7, category="map:topology")

    assert [left.randint(1, 100) for _ in range(5)] == [right.randint(1, 100) for _ in range(5)]


def test_rng_for_room_isolated_by_room_and_category() -> None:
    combat_rng = rng_for_room(seed=7, room_id="act1:r1c0", category="encounter:combat")
    reward_rng = rng_for_room(seed=7, room_id="act1:r1c0", category="reward:card")

    assert [combat_rng.randint(1, 100) for _ in range(3)] != [reward_rng.randint(1, 100) for _ in range(3)]
