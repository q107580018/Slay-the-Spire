from __future__ import annotations

from pathlib import Path

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
