from __future__ import annotations

from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState


def next_room_options(
    *, act_state: ActState, room_state: RoomState, run_state: RunState
) -> list[str]:
    next_node_ids = room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list):
        return []
    options = [node_id for node_id in next_node_ids if isinstance(node_id, str)]
    if "wing_boots" not in run_state.relics:
        return options
    used_charges = run_state.relic_sequence_positions.get("wing_boots_charges", 0)
    if used_charges >= 3:
        return options
    current_node = room_state.payload.get("node_id")
    if not isinstance(current_node, str):
        return options
    try:
        current = act_state.get_node(current_node)
    except KeyError:
        return options
    detours = [
        node.node_id
        for node in act_state.nodes
        if node.row == current.row + 1 and node.node_id not in options
    ]
    return [*options, *detours]
