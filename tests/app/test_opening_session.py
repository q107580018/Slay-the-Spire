from __future__ import annotations

from dataclasses import replace
from random import Random

from slay_the_spire.app.session import MenuState, build_opening_action_menu, route_menu_choice, start_new_game_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.use_cases import opening_flow


def _session_with_targeted_offer(*, reward_kind: str):
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer(reward_kind, "tradeoff", reward_kind, provider, Random(0))
    opening_state = replace(session.opening_state, neow_offers=[offer])
    return replace(session, opening_state=opening_state, menu_state=MenuState(mode="opening_neow_offer")), offer


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
    assert next_session.opening_state is None
    assert next_session.room_state.room_type == "combat"


def test_opening_neow_upgrade_offer_routes_into_target_menu_and_back() -> None:
    session, offer = _session_with_targeted_offer(reward_kind="upgrade_card")

    running, target_session, _message = route_menu_choice("1", session=session)

    assert running is True
    assert target_session.run_phase == "opening"
    assert target_session.menu_state.mode == "opening_neow_upgrade_card"
    assert target_session.opening_state.pending_neow_offer_id == offer.offer_id

    back_choice = str(len(build_opening_action_menu(target_session).options))
    running, neow_session, _message = route_menu_choice(back_choice, session=target_session)

    assert running is True
    assert neow_session.run_phase == "opening"
    assert neow_session.menu_state.mode == "opening_neow_offer"
    assert neow_session.opening_state.pending_neow_offer_id is None


def test_opening_neow_target_selection_completes_upgrade_offer() -> None:
    session, _offer = _session_with_targeted_offer(reward_kind="upgrade_card")
    _running, target_session, _message = route_menu_choice("1", session=session)
    provider = StarterContentProvider(target_session.content_root)
    target_action = build_opening_action_menu(target_session).options[0].action_id
    target_card_instance_id = target_action.split(":", 1)[1]
    target_card_id = card_id_from_instance_id(target_card_instance_id)
    upgraded_card_id = provider.cards().get(target_card_id).upgrades_to

    running, next_session, _message = route_menu_choice("1", session=target_session)

    assert running is True
    assert next_session.run_phase == "active"
    assert next_session.opening_state is None
    assert f"{upgraded_card_id}#{target_card_instance_id.split('#', 1)[1]}" in next_session.run_state.deck
    assert target_card_instance_id not in next_session.run_state.deck


def test_opening_neow_target_selection_completes_remove_offer() -> None:
    session, _offer = _session_with_targeted_offer(reward_kind="remove_card")
    _running, target_session, _message = route_menu_choice("1", session=session)
    target_action = build_opening_action_menu(target_session).options[0].action_id
    target_card_instance_id = target_action.split(":", 1)[1]
    before_deck_size = len(target_session.opening_state.run_blueprint.deck)

    running, next_session, _message = route_menu_choice("1", session=target_session)

    assert running is True
    assert next_session.run_phase == "active"
    assert next_session.opening_state is None
    assert len(next_session.run_state.deck) == before_deck_size - 1
    assert target_card_instance_id not in next_session.run_state.deck


def test_opening_neow_target_menu_returns_to_main_menu_when_pending_offer_is_missing() -> None:
    session, _offer = _session_with_targeted_offer(reward_kind="upgrade_card")
    _running, target_session, _message = route_menu_choice("1", session=session)
    broken_session = replace(
        target_session,
        opening_state=replace(target_session.opening_state, pending_neow_offer_id=None),
    )

    running, next_session, message = route_menu_choice("1", session=broken_session)

    assert running is True
    assert next_session.run_phase == "opening"
    assert next_session.menu_state.mode == "opening_neow_offer"
    assert "Neow 选项" in message


def test_opening_neow_target_menu_returns_to_main_menu_when_pending_offer_id_is_invalid() -> None:
    session, _offer = _session_with_targeted_offer(reward_kind="remove_card")
    _running, target_session, _message = route_menu_choice("1", session=session)
    broken_session = replace(
        target_session,
        opening_state=replace(
            target_session.opening_state,
            pending_neow_offer_id="missing-offer",
        ),
    )

    running, next_session, message = route_menu_choice("1", session=broken_session)

    assert running is True
    assert next_session.run_phase == "opening"
    assert next_session.menu_state.mode == "opening_neow_offer"
    assert "Neow 选项" in message
