from __future__ import annotations

from dataclasses import replace

from slay_the_spire.app.session import MenuState, route_menu_choice, start_session
from slay_the_spire.domain.models.room_state import RoomState


def _event_room() -> RoomState:
    return RoomState(
        room_id="act1:event",
        room_type="event",
        stage="waiting_input",
        payload={
            "node_id": "r1c0",
            "room_kind": "event",
            "event_id": "shining_light",
            "next_node_ids": ["r2c0"],
        },
        is_resolved=False,
        rewards=[],
    )


def test_combat_root_menu_can_enter_inspect_root() -> None:
    session = start_session(seed=5)

    running, next_session, message = route_menu_choice("4", session=session)

    assert running is True
    assert next_session.menu_state.mode == "inspect_root"
    assert next_session.menu_state.inspect_parent_mode == "root"
    assert next_session.menu_state.inspect_item_id is None
    assert "资料总览" in message


def test_inspect_root_can_open_deck_and_return() -> None:
    session = replace(start_session(seed=5), menu_state=MenuState(mode="inspect_root"))

    _running, deck_session, deck_message = route_menu_choice("2", session=session)
    _running, back_session, back_message = route_menu_choice(str(len(deck_session.run_state.deck) + 1), session=deck_session)

    assert deck_session.menu_state.mode == "inspect_deck"
    assert deck_session.menu_state.inspect_parent_mode == "root"
    assert deck_session.menu_state.inspect_item_id == "deck"
    assert "牌组列表" in deck_message
    assert back_session.menu_state.mode == "inspect_root"
    assert back_session.menu_state.inspect_parent_mode == "root"
    assert back_session.menu_state.inspect_item_id is None
    assert "资料总览" in back_message


def test_inspect_deck_can_return_to_parent_root_menu() -> None:
    session = start_session(seed=5)

    _running, inspect_session, _message = route_menu_choice("4", session=session)
    _running, deck_session, _message = route_menu_choice("2", session=inspect_session)
    _running, back_session, _message = route_menu_choice(str(len(deck_session.run_state.deck) + 1), session=deck_session)
    _running, root_session, root_message = route_menu_choice("10", session=back_session)

    assert inspect_session.menu_state.mode == "inspect_root"
    assert deck_session.menu_state.mode == "inspect_deck"
    assert deck_session.menu_state.inspect_parent_mode == "root"
    assert deck_session.menu_state.inspect_item_id == "deck"
    assert back_session.menu_state.mode == "inspect_root"
    assert back_session.menu_state.inspect_parent_mode == "root"
    assert root_session.menu_state.mode == "root"
    assert "查看战场" in root_message


def test_inspect_leaf_pages_keep_transition_messages_consistent() -> None:
    session = start_session(seed=5)

    _running, inspect_session, _message = route_menu_choice("4", session=session)
    _running, stats_session, stats_message = route_menu_choice("1", session=inspect_session)
    _running, stats_back_session, stats_back_message = route_menu_choice("1", session=stats_session)
    _running, relic_session, relic_message = route_menu_choice("3", session=stats_back_session)
    _running, relic_back_session, relic_back_message = route_menu_choice("1", session=relic_session)

    assert stats_session.menu_state.mode == "inspect_stats"
    assert stats_session.menu_state.inspect_item_id == "stats"
    assert stats_message.splitlines()[0] == "角色状态"
    assert stats_back_session.menu_state.mode == "inspect_root"
    assert stats_back_message.splitlines()[0] == "资料总览"
    assert relic_session.menu_state.mode == "inspect_relics"
    assert relic_session.menu_state.inspect_item_id == "relics"
    assert relic_message.splitlines()[0] == "遗物列表"
    assert relic_back_session.menu_state.mode == "inspect_root"
    assert relic_back_message.splitlines()[0] == "资料总览"


def test_combat_inspect_root_includes_potions_hand_enemy_pages_and_back() -> None:
    base_session = start_session(seed=5)
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, potions=["fire_potion"]),
        menu_state=MenuState(mode="inspect_root", inspect_parent_mode="root"),
    )

    _running, potion_session, potion_message = route_menu_choice("4", session=session)
    _running, hand_session, hand_message = route_menu_choice("5", session=session)
    _running, enemy_session, enemy_message = route_menu_choice("9", session=session)
    _running, root_session, root_message = route_menu_choice("10", session=session)

    assert potion_session.menu_state.mode == "inspect_potions"
    assert potion_message.splitlines()[0] == "药水列表"
    assert hand_session.menu_state.mode == "inspect_hand"
    assert hand_message.splitlines()[0] == "手牌列表"
    assert enemy_session.menu_state.mode == "inspect_enemy_list"
    assert enemy_message.splitlines()[0] == "敌人列表"
    assert root_session.menu_state.mode == "root"
    assert "查看战场" in root_message


def test_non_combat_root_menu_can_enter_inspect_root() -> None:
    session = replace(start_session(seed=5), room_state=_event_room())

    running, next_session, message = route_menu_choice("3", session=session)

    assert running is True
    assert next_session.menu_state.mode == "inspect_root"
    assert next_session.menu_state.inspect_parent_mode == "root"
    assert next_session.menu_state.inspect_item_id is None
    assert "资料总览" in message


def test_non_combat_inspect_root_can_open_potions_and_return() -> None:
    base_session = replace(start_session(seed=5), room_state=_event_room())
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, potions=["fire_potion"]),
        menu_state=MenuState(mode="inspect_root", inspect_parent_mode="root"),
    )

    _running, potion_session, potion_message = route_menu_choice("4", session=session)
    _running, back_session, back_message = route_menu_choice("1", session=potion_session)
    _running, root_session, root_message = route_menu_choice("5", session=back_session)

    assert potion_session.menu_state.mode == "inspect_potions"
    assert potion_session.menu_state.inspect_parent_mode == "root"
    assert potion_session.menu_state.inspect_item_id == "potions"
    assert potion_message.splitlines()[0] == "药水列表"
    assert back_session.menu_state.mode == "inspect_root"
    assert back_message.splitlines()[0] == "资料总览"
    assert root_session.menu_state.mode == "root"
    assert "查看事件" in root_message
