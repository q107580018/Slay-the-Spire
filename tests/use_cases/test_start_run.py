from __future__ import annotations

from pathlib import Path

from slay_the_spire.app.cli import main
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.use_cases.enter_room import enter_room
from slay_the_spire.use_cases.start_run import start_new_run


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def test_main_returns_zero_for_stub_argv() -> None:
    assert main(["--help"]) == 0


def test_start_new_run_uses_starter_content() -> None:
    provider = _content_provider()

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert isinstance(run_state, RunState)
    assert run_state.seed == 7
    assert run_state.character_id == "ironclad"
    assert run_state.current_act_id == "act1"


def test_enter_room_returns_room_state_for_node_type() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)

    combat_room = enter_room(run_state, act_state, node_id="hallway", registry=provider)
    event_room = enter_room(run_state, act_state, node_id="event", registry=provider)

    assert isinstance(combat_room, RoomState)
    assert combat_room.room_type == "combat"
    assert combat_room.payload["node_id"] == "hallway"
    assert combat_room.payload["act_id"] == "act1"
    assert combat_room.payload["room_kind"] == "combat"
    assert isinstance(CombatState.from_dict(combat_room.payload["combat_state"]), CombatState)

    assert isinstance(event_room, RoomState)
    assert event_room.room_type == "event"
    assert event_room.payload["node_id"] == "event"
    assert event_room.payload["room_kind"] == "event"
    assert "combat_state" not in event_room.payload
