from dataclasses import replace

from rich.console import Console

from slay_the_spire.adapters.presentation.renderer import render_room
from slay_the_spire.adapters.presentation.theme import TERMINAL_THEME
from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.content.provider import StarterContentProvider


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
