from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict

from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.save_repository import SaveRepositoryPort
from slay_the_spire.shared.types import JsonDict

SAVE_SCHEMA_VERSION = 2


class LoadedGame(TypedDict):
    run_state: RunState | None
    act_state: ActState | None
    room_state: RoomState | None
    combat_state: CombatState | None


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _require_schema_version(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("schema_version must be an int")
    return value


def _migrate_document(document: Mapping[str, object]) -> JsonDict:
    schema_version = _require_schema_version(document.get("schema_version"))
    if schema_version != SAVE_SCHEMA_VERSION:
        raise ValueError(f"unsupported save schema_version: {schema_version}")
    return dict(document)


def _combat_state_from_room(room_state: RoomState | None) -> CombatState | None:
    if room_state is None:
        return None
    combat_state = room_state.payload.get("combat_state")
    if combat_state is None:
        return None
    return CombatState.from_dict(_require_mapping(combat_state, "room_state.payload.combat_state"))


def _room_with_restored_combat_state(
    room_state: RoomState | None,
    combat_state: CombatState | None,
) -> RoomState | None:
    if room_state is None or combat_state is None:
        return room_state
    payload = dict(room_state.payload)
    payload["combat_state"] = combat_state.to_dict()
    return RoomState(
        schema_version=room_state.schema_version,
        room_id=room_state.room_id,
        room_type=room_state.room_type,
        stage=room_state.stage,
        payload=payload,
        is_resolved=room_state.is_resolved,
        rewards=list(room_state.rewards),
    )


def _resolve_combat_sources(
    *,
    room_state: RoomState | None,
    top_level_combat_state: CombatState | None,
) -> tuple[RoomState | None, CombatState | None]:
    room_combat_state = _combat_state_from_room(room_state)
    if room_combat_state is not None and top_level_combat_state is not None:
        if room_combat_state.to_dict() != top_level_combat_state.to_dict():
            raise ValueError("combat_state sources do not match")
    resolved_combat_state = top_level_combat_state or room_combat_state
    return _room_with_restored_combat_state(room_state, resolved_combat_state), resolved_combat_state


def load_game(*, repository: SaveRepositoryPort[Mapping[str, object]]) -> LoadedGame:
    document = repository.load()
    if document is None:
        return {
            "run_state": None,
            "act_state": None,
            "room_state": None,
            "combat_state": None,
        }
    migrated = _migrate_document(_require_mapping(document, "document"))
    run_state_raw = migrated.get("run_state")
    act_state_raw = migrated.get("act_state")
    room_state_raw = migrated.get("room_state")
    combat_state_raw = migrated.get("combat_state")
    run_state = None if run_state_raw is None else RunState.from_dict(_require_mapping(run_state_raw, "run_state"))
    act_state = None if act_state_raw is None else ActState.from_dict(_require_mapping(act_state_raw, "act_state"))
    top_level_combat_state = (
        None
        if combat_state_raw is None
        else CombatState.from_dict(_require_mapping(combat_state_raw, "combat_state"))
    )
    room_state = None if room_state_raw is None else RoomState.from_dict(_require_mapping(room_state_raw, "room_state"))
    room_state, combat_state = _resolve_combat_sources(
        room_state=room_state,
        top_level_combat_state=top_level_combat_state,
    )
    return {
        "run_state": run_state,
        "act_state": act_state,
        "room_state": room_state,
        "combat_state": combat_state,
    }
