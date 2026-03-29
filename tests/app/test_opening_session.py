from __future__ import annotations

from slay_the_spire.app.session import route_menu_choice, start_new_game_session


def test_character_select_routes_into_neow_offer_menu() -> None:
    session = start_new_game_session(seed=5)

    running, next_session, _message = route_menu_choice("1", session=session)

    assert running is True
    assert next_session.run_phase == "opening"
    assert next_session.menu_state.mode == "opening_neow_offer"


def test_opening_neow_selection_starts_first_room_after_targetless_offer() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    gold_choice = next(
        str(index)
        for index, offer in enumerate(session.opening_state.neow_offers, start=1)
        if offer.reward_kind == "gold" and offer.requires_target is None
    )

    running, next_session, _message = route_menu_choice(gold_choice, session=session)

    assert running is True
    assert next_session.run_phase == "active"
    assert next_session.room_state.room_type == "combat"
