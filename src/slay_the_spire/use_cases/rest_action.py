from __future__ import annotations

from slay_the_spire.domain.models.room_state import RoomState


def rest_action(*, room_state: RoomState, action_id: str) -> RoomState:
    if room_state.room_type != "rest":
        raise ValueError("rest_action requires a rest room")
    if room_state.payload.get("action_id") is not None:
        return room_state
    payload = dict(room_state.payload)
    payload["action_id"] = action_id
    payload["action_committed"] = True
    reward = "rest:heal" if action_id == "rest" else "rest:smith"
    return RoomState(
        schema_version=room_state.schema_version,
        room_id=room_state.room_id,
        room_type=room_state.room_type,
        stage="completed",
        payload=payload,
        is_resolved=True,
        rewards=[reward],
    )
