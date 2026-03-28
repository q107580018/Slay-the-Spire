from __future__ import annotations

from slay_the_spire.adapters.textual.map_layout import build_vertical_map_layout
from slay_the_spire.domain.models.act_state import ActNodeState, ActState


def _branching_act_state() -> ActState:
    return ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=["r1c0", "r1c1"]),
            ActNodeState(node_id="r1c0", row=1, col=0, room_type="event", next_node_ids=["r2c0"]),
            ActNodeState(node_id="r1c1", row=1, col=1, room_type="shop", next_node_ids=["r2c0"]),
            ActNodeState(node_id="r2c0", row=2, col=0, room_type="boss", next_node_ids=[]),
        ],
        visited_node_ids=["start"],
    )


def test_vertical_map_layout_spreads_branching_routes_and_marks_connections() -> None:
    layout = build_vertical_map_layout(_branching_act_state())

    start_x, start_y = layout.node_positions["start"]
    left_x, left_y = layout.node_positions["r1c0"]
    right_x, right_y = layout.node_positions["r1c1"]
    boss_x, boss_y = layout.node_positions["r2c0"]

    assert start_y > left_y > boss_y
    assert left_x != right_x
    assert abs(boss_x - ((left_x + right_x) // 2)) <= 2
    assert any(char in "\n".join(layout.canvas_lines) for char in ("│", "╱", "╲", "├", "┤", "┼"))
    assert layout.node_regions["start"][2] <= 9
    assert layout.node_regions["start"][3] <= 5
    assert layout.canvas_width > 0
    assert layout.canvas_height > 0


def test_vertical_map_layout_is_stable_for_same_act_state() -> None:
    left = build_vertical_map_layout(_branching_act_state())
    right = build_vertical_map_layout(_branching_act_state())

    assert left.node_positions == right.node_positions
    assert left.node_regions == right.node_regions
    assert left.canvas_lines == right.canvas_lines


def test_vertical_map_layout_is_stable_when_node_input_order_changes() -> None:
    original = _branching_act_state()
    shuffled = ActState(
        act_id=original.act_id,
        current_node_id=original.current_node_id,
        nodes=list(reversed(original.nodes)),
        visited_node_ids=list(original.visited_node_ids),
    )

    left = build_vertical_map_layout(original)
    right = build_vertical_map_layout(shuffled)

    assert left.node_positions == right.node_positions
    assert left.node_regions == right.node_regions
    assert left.canvas_lines == right.canvas_lines
