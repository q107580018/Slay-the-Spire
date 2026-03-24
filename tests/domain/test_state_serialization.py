from __future__ import annotations

from collections.abc import Mapping

import pytest

from slay_the_spire.domain.models.act_state import ActNodeState, ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.models.statuses import StatusState


def assert_primitive_tree(value: object) -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, list):
        for item in value:
            assert_primitive_tree(item)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            assert isinstance(key, str)
            assert_primitive_tree(item)
        return
    pytest.fail(f"non-primitive value found: {value!r}")


def test_run_state_round_trips_to_dict():
    state = RunState.new(character_id="ironclad", seed=7)
    restored = RunState.from_dict(state.to_dict())
    assert restored.to_dict() == state.to_dict()


def test_room_and_combat_state_round_trip_without_python_object_refs():
    player = PlayerCombatState(
        instance_id="player-1",
        hp=72,
        max_hp=72,
        block=3,
        statuses=[StatusState(status_id="weak", stacks=1, duration=2)],
    )
    enemy = EnemyState(
        instance_id="enemy-1",
        hp=18,
        max_hp=18,
        block=0,
        statuses=[],
        enemy_id="jaw_worm",
    )
    combat_state = CombatState(
        schema_version=1,
        round_number=3,
        energy=2,
        hand=["strike-1", "defend-1"],
        draw_pile=["strike-2"],
        discard_pile=["defend-2"],
        exhaust_pile=[],
        player=player,
        enemies=[enemy],
        effect_queue=[],
        log=["combat starts"],
    )
    room_state = RoomState(
        schema_version=1,
        room_id="room-1",
        room_type="combat",
        stage="waiting_input",
        payload={"combat_state_id": "combat-1"},
        is_resolved=False,
        rewards=["gold"],
    )

    restored_room = RoomState.from_dict(room_state.to_dict())
    restored_combat = CombatState.from_dict(combat_state.to_dict())

    assert restored_room.to_dict() == room_state.to_dict()
    assert restored_combat.to_dict() == combat_state.to_dict()
    assert_primitive_tree(room_state.to_dict())
    assert_primitive_tree(combat_state.to_dict())


def test_room_state_to_dict_returns_deep_snapshot():
    payload = {"nested": {"cards": ["strike"]}}
    state = RoomState(
        schema_version=1,
        room_id="room-1",
        room_type="event",
        stage="waiting_input",
        payload=payload,
        is_resolved=False,
        rewards=[],
    )

    data = state.to_dict()
    data["payload"]["nested"]["cards"].append("defend")

    assert state.payload["nested"]["cards"] == ["strike"]
    assert state.to_dict()["payload"]["nested"]["cards"] == ["strike"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("payload", []),
        ("rewards", "gold"),
        ("is_resolved", "false"),
    ],
)
def test_room_state_from_dict_rejects_wrong_container_and_bool_types(field, value):
    payload = {
        "schema_version": 1,
        "room_id": "room-1",
        "room_type": "combat",
        "stage": "waiting_input",
        "payload": {},
        "is_resolved": False,
        "rewards": [],
    }
    payload[field] = value

    with pytest.raises(TypeError):
        RoomState.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("nodes", "node-1"),
        ("visited_node_ids", "node-1"),
    ],
)
def test_act_state_from_dict_rejects_string_lists(field, value):
    payload = {
        "schema_version": 1,
        "act_id": "act-1",
        "current_node_id": "node-1",
        "nodes": [
            {"schema_version": 1, "node_id": "node-1", "next_node_ids": []}
        ],
        "visited_node_ids": [],
        "enemy_pool_id": None,
        "elite_pool_id": None,
        "boss_pool_id": None,
        "event_pool_id": None,
    }
    payload[field] = value

    with pytest.raises(TypeError):
        ActState.from_dict(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("hand", "strike"),
        ("hand", [1]),
        ("draw_pile", "strike"),
        ("draw_pile", [1]),
        ("discard_pile", "strike"),
        ("discard_pile", [1]),
        ("exhaust_pile", "strike"),
        ("exhaust_pile", [1]),
        ("enemies", "enemy-1"),
        ("effect_queue", "effect"),
        ("log", "combat starts"),
        ("log", [True]),
    ],
)
def test_combat_state_from_dict_rejects_string_lists(field, value):
    payload = {
        "schema_version": 1,
        "round_number": 1,
        "energy": 3,
        "hand": [],
        "draw_pile": [],
        "discard_pile": [],
        "exhaust_pile": [],
        "player": {
            "schema_version": 1,
            "instance_id": "player-1",
            "hp": 80,
            "max_hp": 80,
            "block": 0,
            "statuses": [],
            "kind": "player",
        },
        "enemies": [],
        "effect_queue": [],
        "log": [],
    }
    payload[field] = value

    with pytest.raises(TypeError):
        CombatState.from_dict(payload)


def test_status_state_from_dict_rejects_non_mapping():
    with pytest.raises(TypeError):
        StatusState.from_dict(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_schema_version_is_preserved_on_serialization():
    state = RunState.new(character_id="ironclad", seed=7)
    data = state.to_dict()

    assert data["schema_version"] == RunState.schema_version
    assert RunState.from_dict(data).schema_version == RunState.schema_version


def test_unknown_schema_version_is_rejected_or_migrated_explicitly():
    with pytest.raises(ValueError, match="schema_version"):
        RunState.from_dict(
            {
                "schema_version": 999,
                "seed": 7,
                "character_id": "ironclad",
                "current_act_id": None,
            }
        )


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("seed", "7", TypeError),
        ("character_id", 7, TypeError),
        ("current_act_id", 7, TypeError),
    ],
)
def test_run_state_from_dict_rejects_wrong_field_types(field, value, error):
    payload = {
        "schema_version": 1,
        "seed": 7,
        "character_id": "ironclad",
        "current_act_id": None,
    }
    payload[field] = value

    with pytest.raises(error):
        RunState.from_dict(payload)


def test_act_state_rebuilds_derived_node_index_on_load():
    state = ActState(
        schema_version=1,
        act_id="act-1",
        current_node_id="node-2",
        nodes=[
            ActNodeState(node_id="node-1", next_node_ids=["node-2"]),
            ActNodeState(node_id="node-2", next_node_ids=["node-3"]),
            ActNodeState(node_id="node-3", next_node_ids=[]),
        ],
        visited_node_ids=["node-1"],
        enemy_pool_id="basic",
        elite_pool_id="elite",
        boss_pool_id="boss",
        event_pool_id="event",
    )

    restored = ActState.from_dict(state.to_dict())

    assert restored.get_node("node-2").next_node_ids == ["node-3"]
    assert restored.reachable_node_ids == ["node-3"]


def test_combat_state_rebuilds_entity_index_on_load():
    state = CombatState(
        schema_version=1,
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=80,
            max_hp=80,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                hp=10,
                max_hp=10,
                block=0,
                statuses=[],
                enemy_id="slime",
            )
        ],
        effect_queue=[],
        log=[],
    )

    restored = CombatState.from_dict(state.to_dict())

    assert restored.get_entity("player-1").hp == 80
    assert restored.get_entity("enemy-1").enemy_id == "slime"


def test_identity_validation_rejects_duplicate_entity_ids():
    payload = {
        "schema_version": 1,
        "round_number": 1,
        "energy": 3,
        "hand": [],
        "draw_pile": [],
        "discard_pile": [],
        "exhaust_pile": [],
        "player": {
            "schema_version": 1,
            "instance_id": "entity-1",
            "hp": 80,
            "max_hp": 80,
            "block": 0,
            "statuses": [],
            "kind": "player",
        },
        "enemies": [
            {
                "schema_version": 1,
                "instance_id": "entity-1",
                "hp": 10,
                "max_hp": 10,
                "block": 0,
                "statuses": [],
                "kind": "enemy",
                "enemy_id": "slime",
            }
        ],
        "effect_queue": [],
        "log": [],
    }

    with pytest.raises(ValueError, match="instance_id"):
        CombatState.from_dict(payload)
