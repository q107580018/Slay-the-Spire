from __future__ import annotations

from pathlib import Path

from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.act_state import ActNodeState, ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.use_cases.enter_room import enter_room


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def _run_state(*, seed: int, seen_event_ids: list[str] | None = None) -> RunState:
    return RunState(
        seed=seed,
        character_id="ironclad",
        current_act_id="act1",
        current_hp=80,
        max_hp=80,
        gold=99,
        deck=[],
        relics=["burning_blood"],
        potions=[],
        card_removal_count=0,
        seen_event_ids=[] if seen_event_ids is None else seen_event_ids,
    )


def _act_state(*, node_id: str, room_type: str) -> ActState:
    return ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=[node_id]),
            ActNodeState(node_id=node_id, row=1, col=0, room_type=room_type, next_node_ids=[]),
        ],
        visited_node_ids=[],
        enemy_pool_id="act1_basic",
        elite_pool_id="act1_elites",
        boss_pool_id="act1_bosses",
        event_pool_id="act1_events",
    )


def test_enter_combat_room_uses_weighted_enemy_pool_entries() -> None:
    room_state = enter_room(
        _run_state(seed=7),
        _act_state(node_id="r1c0", room_type="combat"),
        "r1c0",
        _content_provider(),
    )

    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.enemies[0].enemy_id == "jaw_worm"


def test_enter_event_room_uses_weighted_event_pool_entries() -> None:
    room_state = enter_room(
        _run_state(seed=37),
        _act_state(node_id="r1c0", room_type="event"),
        "r1c0",
        _content_provider(),
    )

    assert room_state.payload["event_id"] == "shining_light"


def test_enter_event_room_skips_once_per_run_events_already_seen() -> None:
    room_state = enter_room(
        _run_state(seed=37, seen_event_ids=["shining_light"]),
        _act_state(node_id="r1c0", room_type="event"),
        "r1c0",
        _content_provider(),
    )

    assert room_state.payload["event_id"] == "the_cleric"
