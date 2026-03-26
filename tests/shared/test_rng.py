from __future__ import annotations

import pytest

from slay_the_spire.shared.rng import rng_for_room, rng_for_run, weighted_choice


def test_rng_for_run_is_deterministic_for_same_seed_and_category() -> None:
    left = rng_for_run(seed=7, category="map:topology")
    right = rng_for_run(seed=7, category="map:topology")

    assert [left.randint(1, 100) for _ in range(5)] == [right.randint(1, 100) for _ in range(5)]


def test_rng_for_room_isolated_by_room_and_category() -> None:
    combat_rng = rng_for_room(seed=7, room_id="act1:r1c0", category="encounter:combat")
    reward_rng = rng_for_room(seed=7, room_id="act1:r1c0", category="reward:card")

    assert [combat_rng.randint(1, 100) for _ in range(3)] != [reward_rng.randint(1, 100) for _ in range(3)]


def test_weighted_choice_returns_only_configured_member_ids() -> None:
    choice = weighted_choice(
        [
            ("jaw_worm", 3),
            ("slime", 1),
        ],
        rng=rng_for_room(seed=9, room_id="act1:r1c0", category="encounter:combat"),
    )

    assert choice in {"jaw_worm", "slime"}


def test_weighted_choice_rejects_non_positive_total_weight() -> None:
    with pytest.raises(ValueError):
        weighted_choice([("jaw_worm", 0)], rng=rng_for_run(seed=1, category="encounter"))
