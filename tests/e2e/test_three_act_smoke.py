from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from slay_the_spire.app.session import (
    MenuState,
    SessionState,
    route_menu_choice,
    start_session,
)
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.models.room_state import RoomState


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def _force_act_boss_reward_complete(session: SessionState, act_id: str) -> SessionState:
    provider = _content_provider()
    return replace(
        session,
        run_state=replace(session.run_state, current_act_id=act_id),
        act_state=generate_act_state(act_id, seed=session.run_state.seed, registry=provider),
        room_state=RoomState(
            room_id=f"{act_id}:boss",
            room_type="boss",
            stage="completed",
            payload={
                "act_id": act_id,
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=["gold:120"],
        ),
        menu_state=MenuState(mode="root"),
        run_phase="active",
    )


def _claim_boss_reward_to_boss_chest(session: SessionState) -> tuple[SessionState, str]:
    _running, session, _message = route_menu_choice("1", session=session)
    _running, session, _message = route_menu_choice("1", session=session)
    _running, session, _message = route_menu_choice("1", session=session)
    _running, session, boss_chest_message = route_menu_choice("1", session=session)
    return session, boss_chest_message


@pytest.mark.guardrail
def test_three_act_full_run_reaches_victory() -> None:
    session = start_session(seed=5)

    session = _force_act_boss_reward_complete(session, "act1")
    session, _msg = _claim_boss_reward_to_boss_chest(session)
    assert session.room_state.room_type == "boss_chest"
    assert session.room_state.payload["next_act_id"] == "act2"

    _running, session, _message = route_menu_choice("1", session=session)
    assert session.act_state.act_id == "act2"
    assert session.run_state.current_act_id == "act2"

    session = _force_act_boss_reward_complete(session, "act2")
    session, _msg = _claim_boss_reward_to_boss_chest(session)
    assert session.room_state.room_type == "boss_chest"
    assert session.room_state.payload["next_act_id"] == "act3"

    _running, session, _message = route_menu_choice("1", session=session)
    assert session.act_state.act_id == "act3"
    assert session.run_state.current_act_id == "act3"
    assert session.room_state.room_type == "combat"

    session = _force_act_boss_reward_complete(session, "act3")
    session, boss_chest_message = _claim_boss_reward_to_boss_chest(session)
    assert session.room_state.room_type == "boss_chest"
    assert "next_act_id" not in session.room_state.payload
    assert "完成攀登" in boss_chest_message

    _running, session, _message = route_menu_choice("1", session=session)
    assert session.run_phase == "victory"


@pytest.mark.guardrail
def test_act2_boss_transitions_to_act3() -> None:
    session = _force_act_boss_reward_complete(start_session(seed=5), "act2")

    session, boss_chest_message = _claim_boss_reward_to_boss_chest(session)

    assert session.run_phase == "active"
    assert session.room_state.room_type == "boss_chest"
    assert session.room_state.payload["next_act_id"] == "act3"
    assert "前往下一幕" in boss_chest_message

    _running, session, _message = route_menu_choice("1", session=session)
    assert session.run_phase == "active"
    assert session.act_state.act_id == "act3"
    assert session.run_state.current_act_id == "act3"


@pytest.mark.guardrail
def test_act3_boss_transitions_to_victory() -> None:
    session = _force_act_boss_reward_complete(start_session(seed=5), "act3")

    session, boss_chest_message = _claim_boss_reward_to_boss_chest(session)

    assert session.room_state.room_type == "boss_chest"
    assert "next_act_id" not in session.room_state.payload
    assert "完成攀登" in boss_chest_message

    _running, session, _message = route_menu_choice("1", session=session)
    assert session.run_phase == "victory"
