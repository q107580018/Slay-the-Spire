from __future__ import annotations

from dataclasses import replace

from slay_the_spire.app.session import MenuState, route_menu_choice, start_session
from slay_the_spire.domain.models.room_state import RoomState


def _event_session(event_id: str):
    base_session = start_session(seed=7)
    session = replace(
        base_session,
        room_state=RoomState(
            room_id=f"act1:{event_id}",
            room_type="event",
            stage="waiting_input",
            payload={
                "node_id": "r1c1",
                "room_kind": "event",
                "event_id": event_id,
                "next_node_ids": ["r2c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=MenuState(),
    )
    return session


def test_shining_light_accept_enters_upgrade_subflow_and_upgrades_selected_card() -> None:
    session = _event_session("shining_light")

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.menu_state.mode == "event_upgrade_card"
    assert session.room_state.stage == "select_event_upgrade_card"
    assert session.room_state.payload["upgrade_options"] == ["bash#10"]

    _running, session, _message = route_menu_choice("1", session=session)

    assert session.room_state.is_resolved is True
    assert session.room_state.stage == "completed"
    assert "bash_plus#10" in session.run_state.deck
    assert "bash#10" not in session.run_state.deck


def test_living_wall_forget_enters_remove_subflow_and_removes_selected_card() -> None:
    session = _event_session("living_wall")

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.menu_state.mode == "event_remove_card"
    assert session.room_state.stage == "select_event_remove_card"
    assert "strike#1" in session.room_state.payload["remove_candidates"]

    starting_deck_size = len(session.run_state.deck)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.room_state.is_resolved is True
    assert len(session.run_state.deck) == starting_deck_size - 1
    assert "strike#1" not in session.run_state.deck


def test_the_cleric_heal_spends_gold_and_restores_hp() -> None:
    base_session = _event_session("the_cleric")
    session = replace(base_session, run_state=replace(base_session.run_state, current_hp=40, gold=99))

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.room_state.is_resolved is True
    assert session.run_state.gold == 64
    assert session.run_state.current_hp == 60


def test_world_of_goop_gather_gold_costs_hp_and_grants_gold() -> None:
    session = _event_session("world_of_goop")

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.room_state.is_resolved is True
    assert session.run_state.current_hp == 69
    assert session.run_state.gold == 174


def test_big_fish_banana_heals_one_third_max_hp() -> None:
    base_session = _event_session("big_fish")
    session = replace(base_session, run_state=replace(base_session.run_state, current_hp=30))

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.room_state.is_resolved is True
    assert session.run_state.current_hp == 56
    assert session.run_state.max_hp == 80


def test_big_fish_donut_increases_max_hp_and_current_hp() -> None:
    base_session = _event_session("big_fish")
    session = replace(base_session, run_state=replace(base_session.run_state, current_hp=40, max_hp=80))

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("2", session=session)

    assert session.room_state.is_resolved is True
    assert session.run_state.max_hp == 85
    assert session.run_state.current_hp == 45


def test_golden_shrine_pray_grants_gold_without_other_side_effects() -> None:
    session = _event_session("golden_shrine")

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.room_state.is_resolved is True
    assert session.run_state.gold == 199
    assert session.run_state.current_hp == 80


def test_masked_bandits_pay_spends_gold_without_other_side_effects() -> None:
    session = _event_session("masked_bandits")

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.room_state.is_resolved is True
    assert session.run_state.gold == 24
    assert session.run_state.current_hp == 80


def test_ssssserpent_agree_grants_gold_and_adds_doubt_curse() -> None:
    session = _event_session("the_ssssserpent")

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.room_state.is_resolved is True
    assert session.run_state.gold == 274
    assert "doubt#11" in session.run_state.deck


def test_golden_idol_take_hide_grants_relic_and_reduces_max_hp() -> None:
    session = _event_session("golden_idol")

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("1", session=session)

    assert session.room_state.is_resolved is True
    assert "golden_idol" in session.run_state.relics
    assert session.run_state.max_hp == 69
    assert session.run_state.current_hp == 69


def test_golden_idol_take_escape_adds_injury_curse() -> None:
    session = _event_session("golden_idol")

    _running, session, _message = route_menu_choice("2", session=session)
    _running, session, _message = route_menu_choice("3", session=session)

    assert session.room_state.is_resolved is True
    assert "golden_idol" in session.run_state.relics
    assert "injury#11" in session.run_state.deck
