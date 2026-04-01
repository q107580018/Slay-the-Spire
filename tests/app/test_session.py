from __future__ import annotations

from dataclasses import replace

from slay_the_spire.app.menu_definitions import build_target_menu, format_menu_lines
from slay_the_spire.app.session import (
    MenuState,
    route_menu_choice,
    start_session,
)
from slay_the_spire.domain.models.combat_state import CombatState


def test_route_menu_choice_headbutt_uses_enemy_then_discard_target() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["headbutt#1"]
    combat_state.discard_pile = ["bash#9"]
    session = replace(
        session,
        room_state=replace(
            session.room_state,
            payload={
                **session.room_state.payload,
                "combat_state": combat_state.to_dict(),
            },
        ),
        menu_state=MenuState(mode="select_card"),
    )

    running, target_session, _message = route_menu_choice("1", session=session)

    assert running is True
    assert target_session.menu_state.mode == "select_target"
    assert target_session.menu_state.selected_card_instance_id == "headbutt#1"


def test_build_target_menu_groups_enemy_and_discard_targets() -> None:
    menu = build_target_menu(
        target_options=[
            ("target_enemy:1", "敌人 绿史莱姆"),
            ("target_discard:1", "弃牌堆 痛击 (bash#9)"),
        ],
        current_card_name="头槌",
        header_lines=["敌人目标:", "弃牌堆目标:"],
        title="选择目标（敌人或弃牌堆）",
    )

    assert format_menu_lines(menu)[0] == "选择目标（敌人或弃牌堆）:"
