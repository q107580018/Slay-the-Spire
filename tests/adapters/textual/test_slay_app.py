from __future__ import annotations

import asyncio
from dataclasses import replace

from io import StringIO

import pytest
from rich.console import Console

from slay_the_spire.adapters.textual.map_widget import MapWidget
from slay_the_spire.adapters.terminal.theme import TERMINAL_THEME
from slay_the_spire.adapters.textual.slay_app import SlayApp, _current_action_menu, _menu_choice_for_action, _render_to_rich
from slay_the_spire.app.menu_definitions import build_next_room_menu, build_root_menu
from slay_the_spire.app.session import render_session_renderable, start_session


def test_menu_choice_for_root_next_room_action() -> None:
    resolved_session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, stage="completed", is_resolved=True, rewards=[]),
    )

    menu = build_root_menu(room_state=resolved_session.room_state)

    assert _menu_choice_for_action(menu, "next_room") == "1"


def test_menu_choice_for_next_node_action() -> None:
    session = start_session(seed=5)
    next_node_ids = session.room_state.payload["next_node_ids"]
    menu = build_next_room_menu(options=[(f"next_node:{node_id}", node_id) for node_id in next_node_ids])

    assert _menu_choice_for_action(menu, f"next_node:{next_node_ids[0]}") == "1"


def test_slay_app_console_can_render_existing_rich_theme() -> None:
    session = start_session(seed=5)
    app = SlayApp(session)
    app.console.file = StringIO()

    try:
        app.console.print(render_session_renderable(session))
    except Exception as exc:  # pragma: no cover - current regression path
        pytest.fail(f"unexpected render failure: {exc}")


def test_current_action_menu_matches_root_menu() -> None:
    session = start_session(seed=5)

    menu = _current_action_menu(session)

    assert menu is not None
    assert menu.title == "可选操作"
    assert menu.options[0].action_id == "view_current"


def test_clicking_action_list_drives_menu_choice() -> None:
    async def scenario() -> None:
        app = SlayApp(start_session(seed=5))
        async with app.run_test() as pilot:
            await pilot.click("#action-list", offset=(3, 1))
            await pilot.pause()
            assert app._session.command_history == ["1"]

    asyncio.run(scenario())


def test_map_widget_enables_scrollbars() -> None:
    widget = MapWidget(start_session(seed=5).act_state)

    assert widget.show_horizontal_scrollbar is True
    assert widget.show_vertical_scrollbar is True


def test_map_initially_scrolls_toward_current_node() -> None:
    async def scenario() -> None:
        app = SlayApp(start_session(seed=5))
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            map_widget = app.query_one("#map-widget", MapWidget)
            assert map_widget.scroll_y > 0

    asyncio.run(scenario())


def test_textual_ui_omits_input_and_legend_regions() -> None:
    async def scenario() -> None:
        app = SlayApp(start_session(seed=5))
        async with app.run_test() as pilot:
            await pilot.pause()
            assert list(app.query("#cmd-input")) == []
            assert list(app.query("#legend-bar")) == []

    asyncio.run(scenario())


def test_textual_log_renderable_omits_footer_menu() -> None:
    session = start_session(seed=5)
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None, theme=TERMINAL_THEME)

    console.print(_render_to_rich(session))

    output = buffer.getvalue()
    assert "可选操作" not in output
