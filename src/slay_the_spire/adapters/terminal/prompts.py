from __future__ import annotations

from slay_the_spire.domain.models.room_state import RoomState


def prompt_for_room(room_state: RoomState) -> str:
    if room_state.is_resolved:
        return "Command (quit): "
    return "Command (look, next, help, quit): "
