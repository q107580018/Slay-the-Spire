from __future__ import annotations

from dataclasses import replace

from slay_the_spire.app.session import MenuState, SessionState, route_menu_choice, start_session


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
                    "boss_relic_offers": ["black_blood", "anchor", "lantern"],
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
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.run_phase == "active"
    assert session.act_state.act_id == "act2"
    assert session.room_state.room_type == "combat"
