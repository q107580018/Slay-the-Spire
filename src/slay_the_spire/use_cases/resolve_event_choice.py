from __future__ import annotations

from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.ports.content_provider import ContentProviderPort


def resolve_event_choice(*, room_state: RoomState, choice_id: str, registry: ContentProviderPort) -> RoomState:
    if room_state.room_type != "event":
        raise ValueError("resolve_event_choice requires an event room")
    if room_state.payload.get("choice_id") is not None:
        return room_state
    event_id = room_state.payload.get("event_id")
    if not isinstance(event_id, str):
        raise ValueError("event room is missing event_id")
    event_def = registry.events().get(event_id)
    result = None
    for outcome in event_def.outcomes:
        if outcome.get("choice_id") == choice_id:
            result = outcome.get("result")
            break
    if not isinstance(result, str):
        raise ValueError(f"choice_id not found for event {event_id}: {choice_id}")
    payload = dict(room_state.payload)
    payload["choice_id"] = choice_id
    payload["result"] = result
    payload["action_committed"] = True
    return RoomState(
        schema_version=room_state.schema_version,
        room_id=room_state.room_id,
        room_type=room_state.room_type,
        stage="completed",
        payload=payload,
        is_resolved=True,
        rewards=[f"event:{result}"],
    )
