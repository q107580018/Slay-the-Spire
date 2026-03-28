from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.map.map_generator import generate_act_state


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def test_generate_act_state_builds_row_col_room_type_graph() -> None:
    provider = _content_provider()

    act_state = generate_act_state("act1", seed=7, registry=provider)
    start = act_state.get_node(act_state.current_node_id)

    assert act_state.act_id == "act1"
    assert start.node_id == "start"
    assert start.row == 0
    assert start.col == 0
    assert start.room_type == "combat"
    assert start.next_node_ids
    assert all(node.row >= 0 and node.col >= 0 for node in act_state.nodes)
    assert all(node.room_type for node in act_state.nodes)


def test_generate_act_state_guarantees_shop_and_rest() -> None:
    provider = _content_provider()

    act_state = generate_act_state("act1", seed=7, registry=provider)
    room_types = {node.room_type for node in act_state.nodes}
    last_row = max(node.row for node in act_state.nodes)
    boss_nodes = [node for node in act_state.nodes if node.row == last_row]

    assert "shop" in room_types
    assert "rest" in room_types
    assert len(boss_nodes) == 1
    assert boss_nodes[0].room_type == "boss"


def test_generate_act_state_is_deterministic_for_same_seed() -> None:
    provider = _content_provider()

    left = generate_act_state("act1", seed=42, registry=provider)
    right = generate_act_state("act1", seed=42, registry=provider)

    assert left.to_dict() == right.to_dict()


def _longest_special_streak(act_state) -> int:
    best = 0
    special_room_types = {"event", "elite", "shop", "rest"}

    def dfs(node_id: str, streak: int) -> None:
        nonlocal best
        node = act_state.get_node(node_id)
        next_streak = streak + 1 if node.room_type in special_room_types else 0
        best = max(best, next_streak)
        for next_node_id in node.next_node_ids:
            dfs(next_node_id, next_streak)

    dfs(act_state.current_node_id, 0)
    return best


def test_generate_act_state_guarantees_at_least_one_elite_across_sampled_seeds() -> None:
    provider = _content_provider()

    for seed in range(1, 11):
        act_state = generate_act_state("act1", seed=seed, registry=provider)
        room_counts = Counter(node.room_type for node in act_state.nodes)

        assert room_counts["elite"] >= 1


def test_generate_act_state_limits_special_room_streaks_across_sampled_seeds() -> None:
    provider = _content_provider()

    for seed in range(1, 11):
        act_state = generate_act_state("act1", seed=seed, registry=provider)

        assert _longest_special_streak(act_state) <= 2


def test_generate_act2_state_guarantees_two_elites_across_sampled_seeds() -> None:
    provider = _content_provider()

    for seed in range(1, 21):
        act_state = generate_act_state("act2", seed=seed, registry=provider)
        room_counts = Counter(node.room_type for node in act_state.nodes)

        assert room_counts["elite"] >= 2


@pytest.mark.parametrize("act_id", ("act1", "act2"))
def test_generate_act_state_has_fixed_floor_markers_for_floor_9_15_16(act_id: str) -> None:
    provider = _content_provider()

    act_state = generate_act_state(act_id, seed=7, registry=provider)
    # Floor 9, 15, 16 correspond to rows 8, 14, 15 in the current zero-based grid.
    treasure_row = 8
    rest_row = 14
    boss_row = 15

    treasure_nodes = [node for node in act_state.nodes if node.row == treasure_row]
    rest_nodes = [node for node in act_state.nodes if node.row == rest_row]
    boss_nodes = [node for node in act_state.nodes if node.row == boss_row]

    assert treasure_nodes
    assert all(node.room_type == "treasure" for node in treasure_nodes)
    assert rest_nodes
    assert all(node.room_type == "rest" for node in rest_nodes)
    assert len(boss_nodes) == 1
    assert boss_nodes[0].room_type == "boss"


@pytest.mark.parametrize("act_id", ("act1", "act2"))
def test_generate_act_state_keeps_fixed_floor_room_types_across_sampled_seeds(act_id: str) -> None:
    provider = _content_provider()

    for seed in range(1, 21):
        act_state = generate_act_state(act_id, seed=seed, registry=provider)
        row_room_types = {
            row: {node.room_type for node in act_state.nodes if node.row == row}
            for row in (0, 8, 14, 15)
        }

        assert row_room_types[0] == {"combat"}
        assert row_room_types[8] == {"treasure"}
        assert row_room_types[14] == {"rest"}
        assert row_room_types[15] == {"boss"}


@pytest.mark.parametrize("act_id", ("act1", "act2"))
def test_generate_act_state_expands_to_boss_floor(act_id: str) -> None:
    provider = _content_provider()

    act_state = generate_act_state(act_id, seed=7, registry=provider)

    assert max(node.row for node in act_state.nodes) == 15
