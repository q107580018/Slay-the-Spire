from __future__ import annotations

import asyncio
from dataclasses import replace

from io import StringIO

import pytest
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from textual.widgets import OptionList, Static

from slay_the_spire.adapters.textual.map_widget import MapWidget
from slay_the_spire.adapters.rich_ui.theme import TERMINAL_THEME
from slay_the_spire.adapters.textual.slay_app import (
    SlayApp,
    _current_action_menu,
    _hover_preview_renderable,
    _menu_choice_for_action,
    _render_to_rich,
)
from slay_the_spire.app.menu_definitions import build_next_room_menu, build_root_menu
from slay_the_spire.app.session import render_session_renderable, start_session
from slay_the_spire.domain.models.act_state import ActNodeState, ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.room_state import RoomState


def _span_styles(text) -> set[str]:
    return {str(span.style) for span in text.spans}


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
    assert menu.options[0].action_id == "play_card"


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


def test_current_action_menu_preserves_card_style_for_hand_targets() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["true_grit_plus#1", "strike_plus#2"]
    session = replace(
        session,
        room_state=replace(session.room_state, payload={**session.room_state.payload, "combat_state": combat_state.to_dict()}),
        menu_state=replace(session.menu_state, mode="select_target", selected_card_instance_id="true_grit_plus#1"),
    )

    menu = _current_action_menu(session)

    assert menu is not None
    label = menu.options[0].label
    assert label.plain == "手牌 打击+ (strike_plus#2)"
    assert "card.rarity.basic" in _span_styles(label)
    assert "card.upgraded" in _span_styles(label)


def test_current_action_menu_preserves_current_card_style_in_target_menu() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["anger_plus#1", "strike_plus#2"]
    session = replace(
        session,
        room_state=replace(session.room_state, payload={**session.room_state.payload, "combat_state": combat_state.to_dict()}),
        menu_state=replace(session.menu_state, mode="select_target", selected_card_instance_id="anger_plus#1"),
    )

    menu = _current_action_menu(session)

    assert menu is not None
    assert isinstance(menu.header_lines[0], Text)
    assert menu.header_lines[0].plain == "当前卡牌: 愤怒+"
    assert "card.rarity.common" in _span_styles(menu.header_lines[0])
    assert "card.upgraded" in _span_styles(menu.header_lines[0])


def test_action_summary_refresh_keeps_current_card_styles_in_target_menu() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["anger_plus#1", "strike_plus#2"]
    session = replace(
        session,
        room_state=replace(session.room_state, payload={**session.room_state.payload, "combat_state": combat_state.to_dict()}),
        menu_state=replace(session.menu_state, mode="select_target", selected_card_instance_id="anger_plus#1"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            summary = app.query_one("#action-summary", Static)
            rendered = summary.render()
            assert rendered.plain.startswith("选择目标")
            assert "当前卡牌: 愤怒+" in rendered.plain
            assert rendered.spans
            card_name_start = rendered.plain.index("愤怒+")
            assert any(span.start <= card_name_start < span.end for span in rendered.spans)

    asyncio.run(scenario())


def test_current_action_menu_preserves_rarity_style_for_event_upgrade_choices() -> None:
    session = replace(
        start_session(seed=5),
        room_state=RoomState(
            room_id="act1:event",
            room_type="event",
            stage="select_event_upgrade_card",
            payload={
                "node_id": "r1c1",
                "room_kind": "event",
                "event_id": "shining_light",
                "upgrade_options": ["anger_plus#1"],
                "next_node_ids": ["r2c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=replace(start_session(seed=5).menu_state, mode="event_upgrade_card"),
    )

    menu = _current_action_menu(session)

    assert menu is not None
    label = menu.options[0].label
    assert isinstance(label, Text)
    assert label.plain == "愤怒+"
    assert "card.rarity.common" in _span_styles(label)
    assert "card.upgraded" in _span_styles(label)


def test_current_action_menu_preserves_rarity_style_for_event_remove_choices() -> None:
    session = replace(
        start_session(seed=5),
        room_state=RoomState(
            room_id="act1:event",
            room_type="event",
            stage="select_event_remove_card",
            payload={
                "node_id": "r1c1",
                "room_kind": "event",
                "event_id": "shining_light",
                "remove_candidates": ["anger_plus#1"],
                "next_node_ids": ["r2c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=replace(start_session(seed=5).menu_state, mode="event_remove_card"),
    )

    menu = _current_action_menu(session)

    assert menu is not None
    label = menu.options[0].label
    assert isinstance(label, Text)
    assert label.plain == "愤怒+"
    assert "card.rarity.common" in _span_styles(label)
    assert "card.upgraded" in _span_styles(label)


def test_current_action_menu_shows_readable_next_room_labels() -> None:
    base_session = start_session(seed=5)
    act_state = ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=["r1c0", "r1c1"]),
            ActNodeState(node_id="r1c0", row=1, col=0, room_type="event", next_node_ids=[]),
            ActNodeState(node_id="r1c1", row=1, col=1, room_type="shop", next_node_ids=[]),
        ],
        visited_node_ids=["start"],
    )
    session = replace(
        base_session,
        act_state=act_state,
        room_state=RoomState(
            room_id="act1:start",
            room_type="combat",
            stage="completed",
            payload={"node_id": "start", "room_kind": "combat", "next_node_ids": ["r1c0", "r1c1"]},
            is_resolved=True,
            rewards=[],
        ),
        menu_state=replace(base_session.menu_state, mode="select_next_room"),
    )

    menu = _current_action_menu(session)

    assert menu is not None
    assert [option.label for option in menu.options[:2]] == ["事件", "商店"]


def test_action_list_refresh_keeps_text_styles_for_hand_targets() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["true_grit_plus#1", "strike_plus#2"]
    session = replace(
        session,
        room_state=replace(session.room_state, payload={**session.room_state.payload, "combat_state": combat_state.to_dict()}),
        menu_state=replace(session.menu_state, mode="select_target", selected_card_instance_id="true_grit_plus#1"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            prompt = action_list.get_option_at_index(0).prompt
            assert isinstance(prompt, Text)
            assert prompt.plain == "1. 手牌 打击+ (strike_plus#2)"
            assert "card.rarity.basic" in _span_styles(prompt)
            assert "card.upgraded" in _span_styles(prompt)

    asyncio.run(scenario())


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


def test_textual_log_renderable_omits_combat_summary_panel() -> None:
    session = start_session(seed=5)
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None, theme=TERMINAL_THEME)

    console.print(_render_to_rich(session))

    output = buffer.getvalue()
    assert "战斗摘要" not in output
    assert "战斗记录" in output


def test_textual_log_renderable_keeps_player_hp_in_player_panel() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.player.hp = 57
    combat_state.player.max_hp = 80
    session = replace(
        session,
        room_state=replace(session.room_state, payload={**session.room_state.payload, "combat_state": combat_state.to_dict()}),
    )
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None, theme=TERMINAL_THEME)

    console.print(_render_to_rich(session))

    output = buffer.getvalue()
    assert "玩家状态" in output
    assert "生命" in output
    assert "57/80" in output


def test_flash_msg_stays_empty_after_render_only_play_flow() -> None:
    async def scenario() -> None:
        app = SlayApp(start_session(seed=5))
        async with app.run_test() as pilot:
            await pilot.pause()
            app._process_command("1")
            await pilot.pause()
            app._process_command("1")
            await pilot.pause()
            flash = app.query_one("#flash-msg", Static)
            assert flash.render().plain == ""

    asyncio.run(scenario())


def test_flash_msg_keeps_short_invalid_option_error() -> None:
    async def scenario() -> None:
        app = SlayApp(start_session(seed=5))
        async with app.run_test() as pilot:
            await pilot.pause()
            app._process_command("99")
            await pilot.pause()
            flash = app.query_one("#flash-msg", Static)
            assert flash.render().plain == "无效选项，请输入菜单编号。"

    asyncio.run(scenario())


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


def test_combat_summary_panel_is_rendered_below_map_when_in_combat() -> None:
    async def scenario() -> None:
        app = SlayApp(start_session(seed=5))
        async with app.run_test() as pilot:
            await pilot.pause()
            summary = app.query_one("#combat-summary", Static)
            rendered = summary.render()
            assert summary.display is True
            assert isinstance(rendered._renderable, Panel)
            assert rendered._renderable.title == "战斗摘要"

    asyncio.run(scenario())


def test_combat_summary_panel_is_hidden_outside_combat() -> None:
    base_session = start_session(seed=5)
    session = replace(
        base_session,
        room_state=replace(
            base_session.room_state,
            room_type="rest",
            stage="waiting_input",
            payload={"actions": ["rest", "smith"], "node_id": "r1c0"},
        ),
        menu_state=replace(base_session.menu_state, mode="rest_root"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            summary = app.query_one("#combat-summary", Static)
            assert summary.display is False

    asyncio.run(scenario())


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


def test_hover_preview_shows_card_reward_details_on_mouse_hover() -> None:
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
            await pilot.hover("#action-list", offset=(3, 1))
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            assert "愤怒" in preview.render().plain
            assert "费用" in preview.render().plain
            assert "效果" in preview.render().plain


def test_hover_preview_shows_card_rarity_and_upgrade_state_for_reward_card() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="combat",
            stage="completed",
            is_resolved=True,
            rewards=["card_offer:anger"],
        ),
        menu_state=replace(base.menu_state, mode="select_reward"),
    )

    preview = _hover_preview_renderable(session, "claim_reward:card_offer:anger")

    assert preview is not None
    assert "稀有度" in preview.plain
    assert "普通" in preview.plain
    assert "状态" in preview.plain
    assert "未升级" in preview.plain
    assert "card.rarity.common" in _span_styles(preview)


def test_hover_preview_shows_power_type_for_combust() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        run_state=replace(base.run_state, deck=["combust#1"]),
        menu_state=replace(base.menu_state, mode="inspect_deck"),
    )

    preview = _hover_preview_renderable(session, "item:1")

    assert preview is not None
    assert "类型" in preview.plain
    assert "能力" in preview.plain


def test_hover_preview_shows_status_type_for_burn() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        run_state=replace(base.run_state, deck=["burn#1"]),
        menu_state=replace(base.menu_state, mode="inspect_deck"),
    )

    preview = _hover_preview_renderable(session, "item:1")

    assert preview is not None
    assert "类型" in preview.plain
    assert "状态" in preview.plain


def test_hover_preview_keeps_rarity_color_for_upgraded_shop_card() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="shop",
            stage="waiting_input",
            payload={
                "cards": [{"offer_id": "offer-1", "card_id": "anger_plus", "price": 99, "sold": False}],
                "relics": [],
                "potions": [],
                "remove_price": 75,
                "remove_used": False,
            },
        ),
        menu_state=replace(base.menu_state, mode="shop_root"),
    )

    preview = _hover_preview_renderable(session, "buy_card:offer-1")

    assert preview is not None
    assert "愤怒+" in preview.plain
    assert "已升级" in preview.plain
    assert "card.rarity.common" in _span_styles(preview)
    assert "card.upgraded" in _span_styles(preview)


def test_hover_preview_shows_event_upgrade_before_and_after_effects() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=RoomState(
            room_id="act1:event",
            room_type="event",
            stage="select_event_upgrade_card",
            payload={
                "node_id": "r1c1",
                "room_kind": "event",
                "event_id": "shining_light",
                "upgrade_options": ["bash#9"],
                "next_node_ids": ["r2c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=replace(base.menu_state, mode="event_upgrade_card"),
    )

    preview = _hover_preview_renderable(session, "upgrade_card:bash#9")

    assert preview is not None
    assert "当前" in preview.plain
    assert "升级后" in preview.plain
    assert "造成 8 伤害" in preview.plain
    assert "施加 2 易伤" in preview.plain
    assert "造成 10 伤害" in preview.plain
    assert "施加 3 易伤" in preview.plain


def test_hover_preview_shows_event_upgrade_before_and_after_effects_on_highlight() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=RoomState(
            room_id="act1:event",
            room_type="event",
            stage="select_event_upgrade_card",
            payload={
                "node_id": "r1c1",
                "room_kind": "event",
                "event_id": "shining_light",
                "upgrade_options": ["bash#9"],
                "next_node_ids": ["r2c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=replace(base.menu_state, mode="event_upgrade_card"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 0
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            rendered = preview.render().plain
            assert "当前" in rendered
            assert "升级后" in rendered
            assert "造成 10 伤害" in rendered
            assert "施加 3 易伤" in rendered

    asyncio.run(scenario())


def test_hover_preview_shows_event_upgrade_before_and_after_effects_on_mouse_hover() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=RoomState(
            room_id="act1:event",
            room_type="event",
            stage="select_event_upgrade_card",
            payload={
                "node_id": "r1c1",
                "room_kind": "event",
                "event_id": "shining_light",
                "upgrade_options": ["bash#9"],
                "next_node_ids": ["r2c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=replace(base.menu_state, mode="event_upgrade_card"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.hover("#action-list", offset=(3, 1))
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            rendered = preview.render().plain
            assert "当前" in rendered
            assert "升级后" in rendered
            assert "造成 10 伤害" in rendered
            assert "施加 3 易伤" in rendered

    asyncio.run(scenario())


def test_hover_preview_keeps_event_upgrade_after_section_visible_at_default_size() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=RoomState(
            room_id="act1:event",
            room_type="event",
            stage="select_event_upgrade_card",
            payload={
                "node_id": "r1c1",
                "room_kind": "event",
                "event_id": "shining_light",
                "upgrade_options": ["bash#9"],
                "next_node_ids": ["r2c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=replace(base.menu_state, mode="event_upgrade_card"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 0
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            visible_lines = preview.render().plain.splitlines()[: preview.size.height]
            assert any("升级后" in line for line in visible_lines)
            assert any("造成 10 伤害" in line for line in visible_lines)
            assert any("施加 3 易伤" in line for line in visible_lines)

    asyncio.run(scenario())


def test_hover_preview_shows_rest_upgrade_before_and_after_effects() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=RoomState(
            room_id="act1:rest",
            room_type="rest",
            stage="select_upgrade_card",
            payload={
                "node_id": "r5c0",
                "room_kind": "rest",
                "upgrade_options": ["bash#3"],
                "next_node_ids": ["r6c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=replace(base.menu_state, mode="rest_upgrade_card"),
    )

    preview = _hover_preview_renderable(session, "upgrade_card:bash#3")

    assert preview is not None
    assert "当前" in preview.plain
    assert "升级后" in preview.plain
    assert "造成 8 伤害" in preview.plain
    assert "施加 2 易伤" in preview.plain
    assert "造成 10 伤害" in preview.plain
    assert "施加 3 易伤" in preview.plain


def test_hover_preview_shows_selected_hand_card_effects_in_combat_menu() -> None:
    base = start_session(seed=5)
    combat_state = CombatState(
        round_number=1,
        energy=3,
        hand=["anger#1", "defend#1"],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=80,
            max_hp=80,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="slime",
                hp=12,
                max_hp=12,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="combat",
            stage="waiting_input",
            is_resolved=False,
            payload={
                "node_id": "r1c0",
                "room_kind": "hallway",
                "enemy_pool_id": "act1_basic",
                "next_node_ids": ["r2c0"],
                "combat_state": combat_state.to_dict(),
            },
        ),
        menu_state=replace(base.menu_state, mode="select_card"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 0
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            rendered = preview.render().plain
            assert "愤怒" in rendered
            assert "费用" in rendered
            assert "效果" in rendered
            assert "造成 6 伤害" in rendered

    asyncio.run(scenario())


def test_hover_preview_keeps_card_effect_visible_at_default_size() -> None:
    base = start_session(seed=5)
    combat_state = CombatState(
        round_number=1,
        energy=3,
        hand=["anger#1", "defend#1"],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=80,
            max_hp=80,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="slime",
                hp=12,
                max_hp=12,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="combat",
            stage="waiting_input",
            is_resolved=False,
            payload={
                "node_id": "r1c0",
                "room_kind": "hallway",
                "enemy_pool_id": "act1_basic",
                "next_node_ids": ["r2c0"],
                "combat_state": combat_state.to_dict(),
            },
        ),
        menu_state=replace(base.menu_state, mode="select_card"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 0
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            visible_lines = preview.render().plain.splitlines()[: preview.size.height]
            assert any("效果" in line for line in visible_lines)
            assert any("造成 6 伤害" in line for line in visible_lines)

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
            assert "费用" in preview.render().plain
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


def test_hover_preview_shows_shop_card_details() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="shop",
            stage="waiting_input",
            is_resolved=False,
            payload={
                "cards": [{"offer_id": "card-1", "card_id": "anger", "price": 65}],
                "relics": [],
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
            rendered = preview.render().plain
            assert "愤怒" in rendered
            assert "费用" in rendered
            assert "效果" in rendered
            assert "查看说明" not in rendered

    asyncio.run(scenario())


def test_hover_preview_shows_shop_remove_service_hint() -> None:
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
                "potions": [{"offer_id": "potion-1", "potion_id": "fire_potion", "price": 20}],
                "remove_price": 75,
            },
        ),
        menu_state=replace(base.menu_state, mode="shop_root"),
    )

    preview = _hover_preview_renderable(session, "remove")
    assert preview is not None
    assert "删牌服务" in preview.plain
    assert "黑色之血" not in preview.plain
    assert "火焰药水" not in preview.plain


def test_hover_preview_shows_inspect_relic_details_for_selected_item() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        menu_state=replace(base.menu_state, mode="inspect_relics", inspect_parent_mode="root", inspect_item_id="relics"),
    )

    preview = _hover_preview_renderable(session, "item:1")

    assert preview is not None
    assert "燃烧之血" in preview.plain
    assert "效果" in preview.plain


def test_hover_preview_shows_inspect_relic_details_on_highlight() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        menu_state=replace(base.menu_state, mode="inspect_relics", inspect_parent_mode="root", inspect_item_id="relics"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 0
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            rendered = preview.render().plain
            assert "燃烧之血" in rendered
            assert "效果" in rendered

    asyncio.run(scenario())


def test_hover_preview_shows_boss_reward_entry_hint() -> None:
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
                    "claimed_gold": False,
                    "claimed_relic_id": None,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper"],
                }
            },
        ),
        menu_state=replace(base.menu_state, mode="select_boss_reward"),
    )

    preview = _hover_preview_renderable(session, "choose_boss_relic")
    assert preview is not None
    assert "进入首领遗物选择" in preview.plain


def test_hover_preview_maps_task5_control_actions() -> None:
    base = start_session(seed=5)
    shop_session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="shop",
            stage="waiting_input",
            is_resolved=False,
            payload={
                "cards": [],
                "relics": [],
                "potions": [],
                "remove_price": 75,
            },
        ),
        menu_state=replace(base.menu_state, mode="shop_root"),
    )
    boss_reward_session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="boss",
            stage="completed",
            is_resolved=True,
            payload={
                "boss_rewards": {
                    "gold_reward": 100,
                    "claimed_gold": False,
                    "claimed_relic_id": None,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper"],
                }
            },
        ),
        menu_state=replace(base.menu_state, mode="select_boss_reward"),
    )

    cases = [
        (shop_session, "remove", "删牌服务"),
        (shop_session, "leave", "离开商店"),
        (shop_session, "inspect", "查看资料"),
        (shop_session, "save", "保存游戏"),
        (shop_session, "load", "读取存档"),
        (shop_session, "quit", "退出游戏"),
        (boss_reward_session, "claim_boss_gold", "领取首领金币"),
        (boss_reward_session, "claimed_boss_gold", "首领金币已领取"),
        (boss_reward_session, "choose_boss_relic", "进入首领遗物选择"),
        (boss_reward_session, "claimed_boss_relic", "首领遗物已选择"),
        (boss_reward_session, "back", "返回上一步"),
    ]

    for session, action_id, expected in cases:
        preview = _hover_preview_renderable(session, action_id)
        assert preview is not None
        assert expected in preview.plain
        assert "Boss" not in preview.plain


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


def test_hover_preview_has_usable_height_for_boss_relic_details_at_default_size() -> None:
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
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            action_list = app.query_one("#action-list", OptionList)
            action_list.highlighted = 0
            await pilot.pause()
            preview = app.query_one("#hover-preview", Static)
            rendered = preview.render().plain
            assert "黑色之血" in rendered
            assert preview.size.height > 3

    asyncio.run(scenario())
