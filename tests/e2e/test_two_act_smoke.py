from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from slay_the_spire.app.session import MenuState, SessionState, route_menu_choice, start_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.models.room_state import RoomState


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def _force_act1_boss_reward_complete(session: SessionState) -> SessionState:
    return replace(
        session,
        room_state=replace(
            session.room_state,
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            is_resolved=True,
            rewards=[],
            payload={
                **session.room_state.payload,
                "act_id": "act1",
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
        ),
        menu_state=MenuState(mode="select_boss_reward"),
    )


def test_act1_boss_reward_transitions_into_act2_start_room() -> None:
    session = _force_act1_boss_reward_complete(start_session(seed=5))

    _running, session, _message = route_menu_choice("1", session=session)
    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("2", session=session)

    assert session.run_phase == "active"
    assert session.run_state.relics[-1] == "ectoplasm"
    assert session.act_state.act_id == "act2"
    assert session.room_state.room_type == "combat"


def test_act2_boss_reward_finishes_run_with_victory() -> None:
    base_session = start_session(seed=5)
    provider = _content_provider()
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, current_act_id="act2"),
        act_state=generate_act_state("act2", seed=5, registry=provider),
        room_state=RoomState(
            room_id="act2:boss",
            room_type="boss",
            stage="completed",
            payload={
                "act_id": "act2",
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 120,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
        menu_state=MenuState(mode="select_boss_reward"),
    )

    _running, session, _message = route_menu_choice("1", session=session)
    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.run_phase == "victory"
    assert session.run_state.current_act_id == "act2"
    assert session.room_state.payload["boss_rewards"]["claimed_gold"] is True
    assert session.room_state.payload["boss_rewards"]["claimed_relic_id"] == "black_blood"
