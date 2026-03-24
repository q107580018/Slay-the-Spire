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


def build_save_document(
    *,
    run_state: RunState | None,
    act_state: ActState | None,
    room_state: RoomState | None,
    combat_state: CombatState | None = None,
) -> SavedGameDocument:
    return {
        "schema_version": SAVE_SCHEMA_VERSION,
        "run_state": None if run_state is None else run_state.to_dict(),
        "act_state": None if act_state is None else act_state.to_dict(),
        "room_state": None if room_state is None else room_state.to_dict(),
        "combat_state": None if combat_state is None else combat_state.to_dict(),
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
