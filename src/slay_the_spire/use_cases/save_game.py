from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict

from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.save_repository import SaveRepositoryPort
from slay_the_spire.shared.types import JsonDict

SAVE_SCHEMA_VERSION = 1


class SavedGameDocument(TypedDict):
    schema_version: int
    run_state: JsonDict | None
    act_state: JsonDict | None
    room_state: JsonDict | None
    combat_state: JsonDict | None


def _room_combat_state_dict(room_state: RoomState | None) -> JsonDict | None:
    if room_state is None:
        return None
    combat_state = room_state.payload.get("combat_state")
    if combat_state is None:
        return None
    if not isinstance(combat_state, Mapping):
        raise TypeError("room_state.payload.combat_state must be a mapping")
    return CombatState.from_dict(combat_state).to_dict()


def _normalize_combat_sources(
    *,
    room_state_dict: JsonDict | None,
    room_combat_state_dict: JsonDict | None,
    top_level_combat_state_dict: JsonDict | None,
) -> tuple[JsonDict | None, JsonDict | None]:
    if room_combat_state_dict is not None and top_level_combat_state_dict is not None:
        if room_combat_state_dict != top_level_combat_state_dict:
            raise ValueError("combat_state sources do not match")
    resolved_combat_state = top_level_combat_state_dict or room_combat_state_dict
    if room_state_dict is not None and resolved_combat_state is not None:
        payload = dict(room_state_dict["payload"])
        payload["combat_state"] = resolved_combat_state
        room_state_dict = dict(room_state_dict)
        room_state_dict["payload"] = payload
    return room_state_dict, resolved_combat_state


def build_save_document(
    *,
    run_state: RunState | None,
    act_state: ActState | None,
    room_state: RoomState | None,
    combat_state: CombatState | None = None,
) -> SavedGameDocument:
    room_state_dict = None if room_state is None else room_state.to_dict()
    room_combat_state_dict = _room_combat_state_dict(room_state)
    top_level_combat_state_dict = None if combat_state is None else combat_state.to_dict()
    room_state_dict, combat_state_dict = _normalize_combat_sources(
        room_state_dict=room_state_dict,
        room_combat_state_dict=room_combat_state_dict,
        top_level_combat_state_dict=top_level_combat_state_dict,
    )
    return {
        "schema_version": SAVE_SCHEMA_VERSION,
        "run_state": None if run_state is None else run_state.to_dict(),
        "act_state": None if act_state is None else act_state.to_dict(),
        "room_state": room_state_dict,
        "combat_state": combat_state_dict,
    }


def save_game(
    *,
    repository: SaveRepositoryPort[Mapping[str, object]],
    run_state: RunState | None,
    act_state: ActState | None,
    room_state: RoomState | None,
    combat_state: CombatState | None = None,
) -> SavedGameDocument:
    document = build_save_document(
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        combat_state=combat_state,
    )
    repository.save(document)
    return document
