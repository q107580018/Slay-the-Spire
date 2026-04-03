from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from slay_the_spire.app.menu_definitions import (
    build_root_menu,
    build_target_menu,
    format_menu_lines,
)
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


def test_route_menu_choice_rampage_enters_enemy_target_menu_with_multiple_enemies() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["rampage#1"]
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
    assert target_session.menu_state.selected_card_instance_id == "rampage#1"


def test_route_menu_choice_dropkick_enters_enemy_target_menu() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["dropkick#1"]
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
    assert target_session.menu_state.selected_card_instance_id == "dropkick#1"


def test_route_menu_choice_heavy_blade_enters_enemy_target_menu() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["heavy_blade#1"]
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
    assert target_session.menu_state.selected_card_instance_id == "heavy_blade#1"


def test_route_menu_choice_fiend_fire_enters_enemy_target_menu() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["fiend_fire#1"]
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
    assert target_session.menu_state.selected_card_instance_id == "fiend_fire#1"


def _write_saved_run(save_path: Path) -> None:
    from slay_the_spire.adapters.persistence.save_files import JsonFileSaveRepository
    from slay_the_spire.use_cases.save_game import save_game

    saved_session = start_session(seed=5, save_path=save_path)
    combat_state = CombatState.from_dict(saved_session.room_state.payload["combat_state"])
    save_game(
        repository=JsonFileSaveRepository(save_path),
        run_state=saved_session.run_state,
        act_state=saved_session.act_state,
        room_state=saved_session.room_state,
        combat_state=combat_state,
    )


def _choice_for_root_action(session, action_id: str) -> str:
    menu = build_root_menu(
        room_state=session.room_state, run_state=session.run_state, registry=None
    )
    return str(
        next(index for index, option in enumerate(menu.options, start=1) if option.action_id == action_id)
    )


def test_root_load_enters_save_list_menu(tmp_path: Path, monkeypatch) -> None:
    saves_dir = tmp_path / "saves"
    alpha_path = saves_dir / "alpha.json"
    omega_path = saves_dir / "omega.json"
    _write_saved_run(alpha_path)
    _write_saved_run(omega_path)
    monkeypatch.chdir(tmp_path)
    session = start_session(seed=5)

    running, next_session, message = route_menu_choice(
        _choice_for_root_action(session, "load"), session=session
    )

    assert running is True
    assert next_session.menu_state.mode == "load_select"
    assert next_session.menu_state.inspect_parent_mode == "root"
    assert "选择存档" in message
    assert "alpha.json" in message
    assert "omega.json" in message


def test_load_select_can_restore_specific_save_from_root_menu(
    tmp_path: Path, monkeypatch
) -> None:
    saves_dir = tmp_path / "saves"
    alpha_path = saves_dir / "alpha.json"
    omega_path = saves_dir / "omega.json"
    _write_saved_run(alpha_path)
    _write_saved_run(omega_path)
    monkeypatch.chdir(tmp_path)
    session = start_session(seed=5)

    _running, list_session, _message = route_menu_choice(
        _choice_for_root_action(session, "load"), session=session
    )
    running, next_session, message = route_menu_choice("2", session=list_session)

    assert running is True
    assert next_session.menu_state.mode == "root"
    assert next_session.save_path == omega_path
    assert next_session.room_state.room_type == "combat"
    assert f"已从存档恢复。当前存档: {omega_path}" == message
