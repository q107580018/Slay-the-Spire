from __future__ import annotations

import json
from pathlib import Path

import pytest

from slay_the_spire.adapters.persistence.save_files import JsonFileSaveRepository
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.use_cases.load_game import load_game
from slay_the_spire.use_cases.save_game import SAVE_SCHEMA_VERSION, save_game
from slay_the_spire.use_cases.start_run import start_new_run


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def _combat_state() -> CombatState:
    return CombatState(
        round_number=2,
        energy=1,
        hand=["strike-1"],
        draw_pile=["defend-1", "bash-1"],
        discard_pile=["strike-2"],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=68,
            max_hp=80,
            block=5,
            statuses=[StatusState(status_id="weak", stacks=1, duration=1)],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="jaw_worm",
                hp=24,
                max_hp=40,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[{"type": "damage", "target": "enemy-1", "amount": 6}],
        log=["player turn starts"],
    )


def test_save_game_persists_json_document_with_schema_version(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=11, registry=provider)
    act_state = generate_act_state("act1", seed=11, registry=provider)
    combat_state = _combat_state()
    room_state = RoomState(
        room_id="act1:hallway",
        room_type="combat",
        stage="waiting_input",
        payload={
            "act_id": "act1",
            "node_id": "hallway",
            "combat_state": combat_state.to_dict(),
        },
        is_resolved=False,
        rewards=[],
    )
    repository = JsonFileSaveRepository(tmp_path / "save.json")

    save_game(
        repository=repository,
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        combat_state=combat_state,
    )

    raw_document = json.loads((tmp_path / "save.json").read_text(encoding="utf-8"))

    assert raw_document["schema_version"] == SAVE_SCHEMA_VERSION
    assert raw_document["run_state"]["schema_version"] == RunState.schema_version
    assert raw_document["act_state"]["schema_version"] == act_state.schema_version
    assert raw_document["room_state"]["schema_version"] == 1
    assert raw_document["combat_state"]["schema_version"] == 1


def test_load_game_restores_map_and_combat_state_from_json_save(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=19, registry=provider)
    act_state = generate_act_state("act1", seed=19, registry=provider)
    combat_state = _combat_state()
    room_state = RoomState(
        room_id="act1:hallway",
        room_type="combat",
        stage="waiting_input",
        payload={
            "act_id": "act1",
            "node_id": "hallway",
            "combat_state": combat_state.to_dict(),
        },
        is_resolved=False,
        rewards=[],
    )
    repository = JsonFileSaveRepository(tmp_path / "save.json")
    save_game(
        repository=repository,
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        combat_state=combat_state,
    )

    restored = load_game(repository=repository)

    assert restored["run_state"].to_dict() == run_state.to_dict()
    assert restored["act_state"].to_dict() == act_state.to_dict()
    assert restored["combat_state"].to_dict() == combat_state.to_dict()
    assert restored["room_state"].payload["combat_state"] == combat_state.to_dict()


def test_save_game_rejects_mismatched_combat_state_sources(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=17, registry=provider)
    act_state = generate_act_state("act1", seed=17, registry=provider)
    combat_state = _combat_state()
    mismatched_combat_state = CombatState(
        round_number=3,
        energy=2,
        hand=["bash-1"],
        draw_pile=["strike-1"],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=60,
            max_hp=80,
            block=0,
            statuses=[],
        ),
        enemies=[],
        effect_queue=[],
        log=["mismatch"],
    )
    room_state = RoomState(
        room_id="act1:hallway",
        room_type="combat",
        stage="waiting_input",
        payload={
            "act_id": "act1",
            "node_id": "hallway",
            "combat_state": combat_state.to_dict(),
        },
        is_resolved=False,
        rewards=[],
    )
    repository = JsonFileSaveRepository(tmp_path / "save.json")

    with pytest.raises(ValueError, match="combat_state sources do not match"):
        save_game(
            repository=repository,
            run_state=run_state,
            act_state=act_state,
            room_state=room_state,
            combat_state=mismatched_combat_state,
        )


def test_load_game_rejects_mismatched_combat_state_sources(tmp_path: Path) -> None:
    combat_state = _combat_state()
    mismatched_combat_state = CombatState(
        round_number=1,
        energy=3,
        hand=["strike-x"],
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
        enemies=[],
        effect_queue=[],
        log=["other"],
    )
    repository = JsonFileSaveRepository(tmp_path / "save.json")
    (tmp_path / "save.json").write_text(
        json.dumps(
            {
                "schema_version": SAVE_SCHEMA_VERSION,
                "run_state": None,
                "act_state": None,
                "room_state": {
                    "schema_version": 1,
                    "room_id": "act1:hallway",
                    "room_type": "combat",
                    "stage": "waiting_input",
                    "payload": {
                        "combat_state": combat_state.to_dict(),
                    },
                    "is_resolved": False,
                    "rewards": [],
                },
                "combat_state": mismatched_combat_state.to_dict(),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="combat_state sources do not match"):
        load_game(repository=repository)


def test_load_game_rejects_unknown_schema_version(tmp_path: Path) -> None:
    repository = JsonFileSaveRepository(tmp_path / "save.json")
    (tmp_path / "save.json").write_text(
        json.dumps({"schema_version": 999, "run_state": None, "act_state": None, "room_state": None, "combat_state": None}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported save schema_version: 999"):
        load_game(repository=repository)
