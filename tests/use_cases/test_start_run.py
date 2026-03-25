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

    def potions(self):
        return self._delegate.potions()

    def events(self):
        return self._delegate.events()

    def acts(self):
        return self._delegate.acts()

    def enemy_ids_for_pool(self, pool_id: str):
        return self._delegate.enemy_ids_for_pool(pool_id)

    def event_ids_for_pool(self, pool_id: str):
        return self._delegate.event_ids_for_pool(pool_id)

    def potion_ids_for_pool(self, pool_id: str):
        return self._delegate.potion_ids_for_pool(pool_id)


def _node_id_for_room_type(act_state, room_type: str) -> str:
    for node in act_state.nodes:
        if node.room_type == room_type:
            return node.node_id
    raise AssertionError(f"room_type {room_type} not found")


def test_main_returns_zero_for_stub_argv() -> None:
    assert main(["--help"]) == 0


def test_start_new_run_populates_gold_deck_relics_and_empty_potions() -> None:
    provider = _content_provider()

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert isinstance(run_state, RunState)
    assert run_state.seed == 7
    assert run_state.character_id == "ironclad"
    assert run_state.current_act_id == "act1"
    assert run_state.gold == 99
    assert run_state.deck == [
        "strike#1",
        "strike#2",
        "strike#3",
        "strike#4",
        "strike#5",
        "defend#6",
        "defend#7",
        "defend#8",
        "defend#9",
        "bash#10",
    ]
    assert run_state.relics == ["burning_blood"]
    assert run_state.potions == []


def test_start_new_run_rejects_unknown_character() -> None:
    provider = _content_provider()

    with pytest.raises(KeyError):
        start_new_run("missing", seed=7, registry=provider)


def test_start_new_run_loads_character_definitions_through_provider_contract() -> None:
    provider = _CountingProvider(_content_provider())

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert run_state.current_act_id == "act1"
    assert provider.characters_calls >= 1


def test_enter_room_marks_selected_node_visited_immediately() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)
    target_node_id = act_state.reachable_node_ids[0]

    room_state = enter_room(run_state, act_state, node_id=target_node_id, registry=provider)

    assert isinstance(room_state, RoomState)
    assert act_state.current_node_id == target_node_id
    assert target_node_id in act_state.visited_node_ids


@pytest.mark.parametrize("room_type", ["shop", "rest"])
def test_enter_room_supports_shop_and_rest_room_types(room_type: str) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)
    node_id = _node_id_for_room_type(act_state, room_type)

    room_state = enter_room(run_state, act_state, node_id=node_id, registry=provider)

    assert room_state.room_type == room_type
    assert room_state.stage == "waiting_input"
    assert room_state.payload["node_id"] == node_id
    if room_type == "shop":
        assert "cards" in room_state.payload
        assert "relics" in room_state.payload
        assert "potions" in room_state.payload
        assert room_state.payload["remove_price"] == 75
    else:
        assert room_state.payload["actions"] == ["rest", "smith"]


def test_enter_room_shop_payload_excludes_curse_cards_and_event_only_relics() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)
    node_id = _node_id_for_room_type(act_state, "shop")

    room_state = enter_room(run_state, act_state, node_id=node_id, registry=provider)

    offered_cards = [item["card_id"] for item in room_state.payload["cards"]]
    offered_relics = [item["relic_id"] for item in room_state.payload["relics"]]

    assert "doubt" not in offered_cards
    assert "injury" not in offered_cards
    assert "golden_idol" not in offered_relics


def test_enter_room_builds_playable_combat_state_for_combat_nodes() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.energy == 3
    assert combat_state.round_number == 1
    assert combat_state.hand == [
        "strike#1",
        "strike#2",
        "strike#3",
        "strike#4",
        "strike#5",
    ]
    assert combat_state.draw_pile == [
        "defend#6",
        "defend#7",
        "defend#8",
        "defend#9",
        "bash#10",
    ]
    assert len(combat_state.enemies) == 1
