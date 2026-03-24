from __future__ import annotations

from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState


def _format_next_nodes(room_state: RoomState) -> str:
    next_node_ids = room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list) or not next_node_ids:
        return "-"
    return ", ".join(str(node_id) for node_id in next_node_ids)


def render_room(*, run_state: RunState, act_state: ActState, room_state: RoomState) -> str:
    node_id = room_state.payload.get("node_id", act_state.current_node_id)
    room_kind = room_state.payload.get("room_kind", room_state.room_type)
    return "\n".join(
        [
            f"Run seed: {run_state.seed}",
            f"Character: {run_state.character_id}",
            f"Act: {act_state.act_id}",
            f"Room: {node_id}",
            f"Room type: {room_kind}",
            f"Stage: {room_state.stage}",
            f"Next: {_format_next_nodes(room_state)}",
        ]
    )
