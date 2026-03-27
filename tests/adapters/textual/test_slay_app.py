from __future__ import annotations

import asyncio
from dataclasses import replace

from io import StringIO

import pytest
from rich.console import Console
from textual.widgets import OptionList, Static

from slay_the_spire.adapters.textual.map_widget import MapWidget
from slay_the_spire.adapters.terminal.theme import TERMINAL_THEME
from slay_the_spire.adapters.textual.slay_app import (
    SlayApp,
    _current_action_menu,
    _hover_preview_renderable,
    _menu_choice_for_action,
    _render_to_rich,
)
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


def test_current_action_menu_marks_disabled_rest_actions() -> None:
    session = replace(
        start_session(seed=5),
        run_state=replace(start_session(seed=5).run_state, relics=["burning_blood", "coffee_dripper", "fusion_hammer"]),
        room_state=replace(start_session(seed=5).room_state, room_type="rest", stage="waiting_input", payload={"actions": ["rest", "smith"]}),
        menu_state=replace(start_session(seed=5).menu_state, mode="rest_root"),
    )

    menu = _current_action_menu(session)

    assert menu is not None
    assert menu.options[0].label == "休息 [已禁用]"
    assert menu.options[1].label == "锻造 [已禁用]"


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


def test_map_widget_uses_compact_node_regions() -> None:
    widget = MapWidget(start_session(seed=5).act_state)

    width_values = {region[2] for region in widget._node_regions.values()}
    height_values = {region[3] for region in widget._node_regions.values()}

    assert max(width_values) <= 7
    assert max(height_values) <= 3


def test_map_widget_centers_view_above_current_node() -> None:
    async def scenario() -> None:
        app = SlayApp(start_session(seed=5))
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            map_widget = app.query_one("#map-widget", MapWidget)
            assert map_widget.scroll_y >= 0
            assert map_widget.max_scroll_y > 0

    asyncio.run(scenario())


def test_display_positions_are_stable_for_same_act_state() -> None:
    act_state = start_session(seed=5).act_state

    left = MapWidget(act_state)
    right = MapWidget(act_state)

    assert left._node_regions == right._node_regions


def test_current_node_region_is_not_centered_exactly() -> None:
    widget = MapWidget(start_session(seed=5).act_state)
    region = widget._current_node_region()

    assert region is not None
    assert region.height <= 3


def test_map_widget_renders_icon_with_label_for_current_floor() -> None:
    widget = MapWidget(start_session(seed=5).act_state)

    canvas = "\n".join(widget._canvas_lines)
    assert "⚔" in canvas or "💀" in canvas or "👑" in canvas
    assert "战斗" in canvas or "精英" in canvas or "商店" in canvas
    assert "┌" not in canvas
    assert "╔" not in canvas


def test_current_and_reachable_nodes_use_distinct_styles() -> None:
    widget = MapWidget(start_session(seed=5).act_state)

    styles = [style for row in widget._style_rows for style in row]
    assert any(style.bold for style in styles)


def test_map_widget_avoids_boxy_edge_glyphs() -> None:
    widget = MapWidget(start_session(seed=5).act_state)

    canvas = "\n".join(widget._canvas_lines)
    assert "│" not in canvas
    assert "─" not in canvas


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


def test_textual_map_panel_css_uses_light_background() -> None:
    assert "#map-panel" in SlayApp.CSS
    map_panel_css = SlayApp.CSS.split("#map-panel", maxsplit=1)[1].split("}", maxsplit=1)[0]
    assert "background:" in map_panel_css


def test_textual_map_panel_declares_light_background_css() -> None:
    assert "#map-panel" in SlayApp.CSS
    assert "background:" in SlayApp.CSS


def test_textual_log_renderable_omits_footer_menu() -> None:
    session = start_session(seed=5)
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None, theme=TERMINAL_THEME)

    console.print(_render_to_rich(session))

    output = buffer.getvalue()
    assert "可选操作" not in output


def test_textual_log_renderable_still_omits_footer_menu_after_map_polish() -> None:
    session = start_session(seed=5)
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None, theme=TERMINAL_THEME)

    console.print(_render_to_rich(session))

    assert "可选操作" not in buffer.getvalue()


def test_textual_log_renderable_omits_duplicate_map_panel() -> None:
    base_session = start_session(seed=5)
    session = replace(
        base_session,
        room_state=replace(
            base_session.room_state,
            room_type="rest",
            stage="waiting_input",
            is_resolved=False,
            payload={"actions": ["rest", "smith"], "node_id": "1"},
        ),
    )
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None, theme=TERMINAL_THEME)

    console.print(_render_to_rich(session))

    output = buffer.getvalue()
    assert "TIP |" not in output
    assert "TYPE |" not in output


def test_hover_preview_panel_is_present_in_reward_menu() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="combat",
            stage="completed",
            is_resolved=True,
            rewards=["card_offer:anger", "gold:15"],
        ),
        menu_state=replace(base.menu_state, mode="select_reward"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#hover-preview", Static).display is True

    asyncio.run(scenario())


def test_hover_preview_panel_shows_guidance_in_reward_menu() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="combat",
            stage="completed",
            is_resolved=True,
            rewards=["card_offer:anger", "gold:15"],
        ),
        menu_state=replace(base.menu_state, mode="select_reward"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            assert "查看说明" in preview.render().plain

    asyncio.run(scenario())


def test_hover_preview_panel_is_present_in_shop_root_menu() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="shop",
            stage="waiting_input",
            is_resolved=False,
            payload={"cards": [], "relics": [], "potions": []},
        ),
        menu_state=replace(base.menu_state, mode="shop_root"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#hover-preview", Static).display is True

    asyncio.run(scenario())


def test_hover_preview_panel_is_hidden_after_leaving_reward_menu() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="combat",
            stage="completed",
            is_resolved=True,
            rewards=["card_offer:anger", "gold:15"],
        ),
        menu_state=replace(base.menu_state, mode="select_reward"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            menu = _current_action_menu(app._session)
            assert menu is not None
            assert app.query_one("#hover-preview", Static).display is True
            back_choice = _menu_choice_for_action(menu, "back")
            assert back_choice is not None
            app._process_command(back_choice)
            await pilot.pause()
            assert app.query_one("#hover-preview", Static).display is False

    asyncio.run(scenario())


def test_hover_preview_shows_card_reward_details_for_highlighted_reward() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="combat",
            stage="completed",
            is_resolved=True,
            rewards=["card_offer:anger", "gold:15"],
        ),
        menu_state=replace(base.menu_state, mode="select_reward"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 0
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            assert "愤怒" in preview.render().plain
            assert "效果" in preview.render().plain

    asyncio.run(scenario())


def test_hover_preview_shows_control_hint_for_claim_all() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="combat",
            stage="completed",
            is_resolved=True,
            rewards=["gold:15", "event:gain_upgrade"],
        ),
        menu_state=replace(base.menu_state, mode="select_reward"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 2
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            assert "全部领取" in preview.render().plain

    asyncio.run(scenario())


def test_hover_preview_shows_boss_relic_details() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="boss",
            stage="completed",
            is_resolved=True,
            payload={
                "boss_rewards": {
                    "gold_reward": 100,
                    "claimed_gold": True,
                    "claimed_relic_id": None,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper"],
                }
            },
        ),
        menu_state=replace(base.menu_state, mode="select_boss_relic"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 0
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            assert "黑色之血" in preview.render().plain
            assert "禁用操作" in preview.render().plain or "替换原遗物" in preview.render().plain

    asyncio.run(scenario())


def test_hover_preview_shows_shop_potion_details() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="shop",
            stage="waiting_input",
            is_resolved=False,
            payload={
                "cards": [],
                "relics": [],
                "potions": [{"offer_id": "potion-1", "potion_id": "fire_potion", "price": 20}],
                "remove_price": 75,
            },
        ),
        menu_state=replace(base.menu_state, mode="shop_root"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 0
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            assert "火焰药水" in preview.render().plain
            assert "药水" in preview.render().plain or "效果" in preview.render().plain
            assert "20" in preview.render().plain

    asyncio.run(scenario())


def test_hover_preview_shows_shop_relic_details() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="shop",
            stage="waiting_input",
            is_resolved=False,
            payload={
                "cards": [],
                "relics": [{"offer_id": "relic-1", "relic_id": "black_blood", "price": 150}],
                "potions": [],
                "remove_price": 75,
            },
        ),
        menu_state=replace(base.menu_state, mode="shop_root"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 0
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            assert "黑色之血" in preview.render().plain
            assert "遗物" in preview.render().plain
            assert (
                "金币规则" in preview.render().plain
                or "禁用操作" in preview.render().plain
                or "替换原遗物" in preview.render().plain
            )

    asyncio.run(scenario())


def test_hover_preview_ignores_unsupported_claim_reward_prefix() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="combat",
            stage="completed",
            is_resolved=True,
            rewards=["gold:15"],
        ),
        menu_state=replace(base.menu_state, mode="select_reward"),
    )

    assert _hover_preview_renderable(session, "claim_reward:potion:fire_potion") is None
