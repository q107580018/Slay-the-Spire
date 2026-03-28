from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from slay_the_spire.app.cli import main
from slay_the_spire.app.session import SessionState, route_menu_choice, start_session
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState


def _path_with_shop_rest_and_treasure(act_state) -> list[str]:
    found: list[str] | None = None

    def dfs(node_id: str, path: list[str]) -> None:
        nonlocal found
        if found is not None:
            return
        node = act_state.get_node(node_id)
        next_path = [*path, node_id]
        room_types = [act_state.get_node(item).room_type for item in next_path]
        if not node.next_node_ids:
            if "shop" in room_types and "rest" in room_types and "treasure" in room_types and room_types[-1] == "boss":
                found = next_path
            return
        for next_node_id in node.next_node_ids:
            dfs(next_node_id, next_path)

    dfs(act_state.current_node_id, [])
    if found is None:
        raise AssertionError("expected a path containing shop, rest, treasure, and boss")
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
    return str(offer_count + 2)


def _shop_inspect_choice(room_state: RoomState) -> str:
    return str(int(_shop_leave_choice(room_state)) + 1)


def _inspect_relics_and_return_to_parent(session: SessionState) -> SessionState:
    for choice in ["3", "1", "2", "5"]:
        _running, session, _message = route_menu_choice(choice, session=session)
    return session


def test_main_new_run_dispatches_first_room_to_textual(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def fake_run_textual_session(*, session: SessionState) -> None:
        recorded["seed"] = session.run_state.seed
        recorded["room_type"] = session.room_state.room_type
        recorded["run_phase"] = session.run_phase

    monkeypatch.setattr("slay_the_spire.app.cli.run_textual_session", fake_run_textual_session)

    exit_code = main(["new", "--seed", "1"])

    assert exit_code == 0
    assert recorded == {"seed": 1, "room_type": "combat", "run_phase": "active"}


def test_single_act_smoke_simulates_map_shop_rest_and_boss_reward_transition_into_act2() -> None:
    session = start_session(seed=1)
    _running, session, _message = route_menu_choice("3", session=session)
    _running, session, _message = route_menu_choice("5", session=session)
    _running, session, _message = route_menu_choice("1", session=session)
    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("10", session=session)
    path = _path_with_shop_rest_and_treasure(session.act_state)
    visited_types: list[str] = [session.room_state.room_type]

    for next_node_id in path[1:]:
        if session.room_state.room_type == "event":
            _running, session, _message = route_menu_choice("2", session=session)
            _running, session, _message = route_menu_choice("1", session=session)
            _running, session, _message = route_menu_choice("1", session=session)
            _running, session, _message = route_menu_choice("5", session=session)
        if session.room_state.room_type == "shop":
            _running, session, _message = route_menu_choice(_shop_inspect_choice(session.room_state), session=session)
            _running, session, _message = route_menu_choice("1", session=session)
            _running, session, _message = route_menu_choice("1", session=session)
            _running, session, _message = route_menu_choice("5", session=session)
            _running, session, _message = route_menu_choice(_shop_leave_choice(session.room_state), session=session)
        elif session.room_state.room_type == "rest":
            _running, session, _message = route_menu_choice("3", session=session)
            session = _inspect_relics_and_return_to_parent(session)
            _running, session, _message = route_menu_choice("2", session=session)
            _running, session, _message = route_menu_choice("1", session=session)
        elif session.room_state.room_type == "treasure":
            _running, session, _message = route_menu_choice("1", session=session)
        else:
            session = _complete_current_room(session)
        session = _advance_to(session, next_node_id)
        visited_types.append(session.room_state.room_type)

    # 这里有意直接补齐房间结算结果，用来串起地图/菜单/奖励路径，
    # 不是在验证完整的真实 Boss 战斗胜利流程。
    session = replace(
        session,
        room_state=replace(
            session.room_state,
            stage="completed",
            is_resolved=True,
            rewards=[],
            payload={
                **session.room_state.payload,
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
        ),
    )
    _running, session, _message = route_menu_choice("1", session=session)
    _running, session, _message = route_menu_choice("1", session=session)
    assert session.run_phase == "active"
    assert session.menu_state.mode == "select_boss_reward"
    assert session.room_state.rewards == []
    assert session.room_state.payload["boss_rewards"]["claimed_gold"] is True
    assert "boss_rewards" in session.room_state.payload

    _running, session, _message = route_menu_choice("2", session=session)
    assert session.menu_state.mode == "select_boss_relic"
    _running, session, boss_chest_message = route_menu_choice("1", session=session)

    assert "shop" in visited_types
    assert "rest" in visited_types
    assert "treasure" in visited_types
    assert session.run_phase == "active"
    assert session.run_state.current_act_id == "act1"
    assert session.act_state.act_id == "act1"
    assert session.room_state.room_type == "boss_chest"
    assert session.room_state.payload["next_act_id"] == "act2"
    assert "Boss宝箱" in boss_chest_message
    assert "前往下一幕" in boss_chest_message
    assert session.run_state.gold == 198
    assert "black_blood" in session.run_state.relics
    assert "bash_plus#10" in session.run_state.deck

    _running, session, _message = route_menu_choice("1", session=session)

    assert session.run_phase == "active"
    assert session.run_state.current_act_id == "act2"
    assert session.act_state.act_id == "act2"
    assert session.room_state.payload["act_id"] == "act2"
    assert session.room_state.room_type == "combat"
    assert session.run_state.gold == 198
    assert "black_blood" in session.run_state.relics
    assert "bash_plus#10" in session.run_state.deck


def test_single_act_smoke_boss_room_uses_act1_bosses_and_hexaghost() -> None:
    session = start_session(seed=1)
    _running, session, _message = route_menu_choice("3", session=session)
    _running, session, _message = route_menu_choice("5", session=session)
    _running, session, _message = route_menu_choice("1", session=session)
    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("10", session=session)
    path = _path_with_shop_rest_and_treasure(session.act_state)

    for next_node_id in path[1:]:
        if session.room_state.room_type == "event":
            _running, session, _message = route_menu_choice("2", session=session)
            _running, session, _message = route_menu_choice("1", session=session)
            _running, session, _message = route_menu_choice("1", session=session)
            _running, session, _message = route_menu_choice("5", session=session)
        if session.room_state.room_type == "shop":
            _running, session, _message = route_menu_choice(_shop_inspect_choice(session.room_state), session=session)
            _running, session, _message = route_menu_choice("1", session=session)
            _running, session, _message = route_menu_choice("1", session=session)
            _running, session, _message = route_menu_choice("5", session=session)
            _running, session, _message = route_menu_choice(_shop_leave_choice(session.room_state), session=session)
        elif session.room_state.room_type == "rest":
            _running, session, _message = route_menu_choice("3", session=session)
            session = _inspect_relics_and_return_to_parent(session)
            _running, session, _message = route_menu_choice("2", session=session)
            _running, session, _message = route_menu_choice("1", session=session)
        elif session.room_state.room_type == "treasure":
            _running, session, _message = route_menu_choice("1", session=session)
        else:
            session = _complete_current_room(session)
        session = _advance_to(session, next_node_id)

    assert session.room_state.room_type == "boss"
    assert session.room_state.payload["enemy_pool_id"] == "act1_bosses"
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    assert combat_state.enemies[0].enemy_id == "hexaghost"
