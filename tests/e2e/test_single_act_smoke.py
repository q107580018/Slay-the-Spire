from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from slay_the_spire.app.cli import main
from slay_the_spire.app.session import SessionState, route_menu_choice, start_session
from slay_the_spire.domain.models.room_state import RoomState


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _path_with_shop_and_rest(act_state) -> list[str]:
    found: list[str] | None = None

    def dfs(node_id: str, path: list[str]) -> None:
        nonlocal found
        if found is not None:
            return
        node = act_state.get_node(node_id)
        next_path = [*path, node_id]
        room_types = [act_state.get_node(item).room_type for item in next_path]
        if not node.next_node_ids:
            if "shop" in room_types and "rest" in room_types and room_types[-1] == "boss":
                found = next_path
            return
        for next_node_id in node.next_node_ids:
            dfs(next_node_id, next_path)

    dfs(act_state.current_node_id, [])
    if found is None:
        raise AssertionError("expected a path containing shop, rest, and boss")
    return found


def _complete_current_room(session: SessionState) -> SessionState:
    room_state = replace(session.room_state, stage="completed", is_resolved=True, rewards=[])
    return replace(session, room_state=room_state)


def _advance_to(session: SessionState, target_node_id: str) -> SessionState:
    next_node_ids = session.room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list):
        raise AssertionError("current room is missing next_node_ids")
    if len(next_node_ids) > 1:
        _running, session, _message = route_menu_choice("1", session=session)
        choice = str(next_node_ids.index(target_node_id) + 1)
        _running, session, _message = route_menu_choice(choice, session=session)
        return session
    _running, session, _message = route_menu_choice("1", session=session)
    return session


def _shop_leave_choice(room_state: RoomState) -> str:
    cards = room_state.payload.get("cards", [])
    relics = room_state.payload.get("relics", [])
    potions = room_state.payload.get("potions", [])
    offer_count = sum(len(items) for items in (cards, relics, potions) if isinstance(items, list))
    remove_slot = 1 if room_state.payload.get("remove_used") is not True else 0
    return str(offer_count + remove_slot + 1)


def test_main_new_run_renders_first_room(capsys, monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt="": "6")

    exit_code = main(["new", "--seed", "1"])

    captured = capsys.readouterr()
    output = _strip_ansi(captured.out)

    assert exit_code == 0
    assert "种子: 1" in output
    assert "房间: 起点" in output
    assert "6. 退出游戏" in output


def test_single_act_smoke_covers_map_shop_rest_and_boss_victory() -> None:
    session = start_session(seed=1)
    path = _path_with_shop_and_rest(session.act_state)
    visited_types: list[str] = [session.room_state.room_type]

    for next_node_id in path[1:]:
        if session.room_state.room_type == "shop":
            _running, session, _message = route_menu_choice("1", session=session)
            _running, session, _message = route_menu_choice(_shop_leave_choice(session.room_state), session=session)
        elif session.room_state.room_type == "rest":
            _running, session, _message = route_menu_choice("2", session=session)
            _running, session, _message = route_menu_choice("1", session=session)
        else:
            session = _complete_current_room(session)
        session = _advance_to(session, next_node_id)
        visited_types.append(session.room_state.room_type)

    session = replace(
        session,
        room_state=replace(session.room_state, stage="completed", is_resolved=True, rewards=["gold:99"]),
    )
    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert "shop" in visited_types
    assert "rest" in visited_types
    assert session.run_phase == "victory"
    assert session.run_state.gold < 99
    assert "bash_plus#9" in session.run_state.deck
