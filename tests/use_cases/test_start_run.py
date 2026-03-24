from __future__ import annotations

from pathlib import Path

import pytest

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


class _CountingProvider:
    def __init__(self, delegate: StarterContentProvider) -> None:
        self._delegate = delegate
        self.characters_calls = 0

    def characters(self):
        self.characters_calls += 1
        return self._delegate.characters()

    def cards(self):
        return self._delegate.cards()

    def enemies(self):
        return self._delegate.enemies()

    def relics(self):
        return self._delegate.relics()

    def events(self):
        return self._delegate.events()

    def acts(self):
        return self._delegate.acts()


def test_main_returns_zero_for_stub_argv() -> None:
    assert main(["--help"]) == 0


def test_start_new_run_uses_starter_content() -> None:
    provider = _content_provider()

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert isinstance(run_state, RunState)
    assert run_state.seed == 7
    assert run_state.character_id == "ironclad"
    assert run_state.current_act_id == "act1"


def test_start_new_run_rejects_unknown_character() -> None:
    provider = _content_provider()

    with pytest.raises(KeyError):
        start_new_run("missing", seed=7, registry=provider)


def test_start_new_run_loads_character_definitions_through_provider_contract() -> None:
    provider = _CountingProvider(_content_provider())

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert run_state.current_act_id == "act1"
    assert provider.characters_calls >= 1


@pytest.mark.parametrize(
    ("node_id", "expected_room_type"),
    [
        ("hallway", "combat"),
        ("elite", "elite"),
        ("event", "event"),
        ("boss", "boss"),
    ],
)
def test_enter_room_returns_room_state_for_node_type(node_id: str, expected_room_type: str) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)

    room_state = enter_room(run_state, act_state, node_id=node_id, registry=provider)

    assert isinstance(room_state, RoomState)
    assert room_state.room_type == expected_room_type
    assert room_state.payload["node_id"] == node_id
    assert room_state.payload["act_id"] == "act1"
    assert room_state.payload["room_kind"] == expected_room_type

    if expected_room_type in {"combat", "elite", "boss"}:
        assert isinstance(CombatState.from_dict(room_state.payload["combat_state"]), CombatState)
    else:
        assert "combat_state" not in room_state.payload
