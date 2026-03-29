from dataclasses import replace
from random import Random

from rich.console import Console

from slay_the_spire.adapters.presentation.renderer import render_room
from slay_the_spire.adapters.presentation.theme import TERMINAL_THEME
from slay_the_spire.app.session import MenuState, render_session_renderable, start_new_game_session, start_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.use_cases import opening_flow


def _provider(session):
    return StarterContentProvider(session.content_root)


def test_render_room_from_presentation_package() -> None:
    session = start_session(seed=5)
    room_state = replace(session.room_state, is_resolved=True, rewards=["card_offer:anger"])
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase=session.run_phase,
    )

    console = Console(
        width=100,
        record=True,
        force_terminal=False,
        color_system=None,
        theme=TERMINAL_THEME,
    )
    console.print(output)

    rendered = console.export_text(clear=False)
    assert "卡牌 愤怒" in rendered


def test_render_session_renderable_supports_opening_target_menu() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("remove_card", "tradeoff", "remove_card", provider, Random(0))
    session = replace(
        session,
        opening_state=replace(session.opening_state, neow_offers=[offer], pending_neow_offer_id=offer.offer_id),
        menu_state=MenuState(mode="opening_neow_remove_card"),
    )

    console = Console(
        width=100,
        record=True,
        force_terminal=False,
        color_system=None,
        theme=TERMINAL_THEME,
    )
    console.print(render_session_renderable(session))

    rendered = console.export_text(clear=False)
    assert "选择要移除的卡牌" in rendered
    assert "Neow 赐福:" not in rendered
