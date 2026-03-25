from __future__ import annotations

from dataclasses import replace

from slay_the_spire.app.session import MenuState, route_menu_choice, start_session


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
    _running, root_session, root_message = route_menu_choice("4", session=back_session)

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
    assert "角色状态" in stats_message
    assert stats_back_session.menu_state.mode == "inspect_root"
    assert "资料总览" in stats_back_message
    assert relic_session.menu_state.mode == "inspect_relics"
    assert relic_session.menu_state.inspect_item_id == "relics"
    assert "遗物列表" in relic_message
    assert relic_back_session.menu_state.mode == "inspect_root"
    assert "遗物列表" in relic_back_message
