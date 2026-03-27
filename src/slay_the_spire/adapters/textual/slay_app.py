"""SlayApp - 主 Textual 应用，整合地图、日志和输入。"""
from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, OptionList, RichLog, Static

from slay_the_spire.adapters.rich_ui.theme import TERMINAL_THEME
from slay_the_spire.adapters.textual.map_widget import MapWidget
from slay_the_spire.app.inspect_registry import COMBAT_INSPECT_CARD_LIST_MODES, inspect_leaf_title
from slay_the_spire.app.menu_definitions import (
    MenuDefinition,
    build_boss_relic_menu,
    build_boss_reward_menu,
    build_card_detail_menu,
    build_enemy_detail_menu,
    build_event_choice_menu,
    build_event_remove_menu,
    build_event_upgrade_menu,
    build_inspect_root_menu,
    build_leaf_menu,
    build_menu,
    build_next_room_menu,
    build_rest_root_menu,
    build_rest_upgrade_menu,
    build_reward_menu,
    build_root_menu,
    build_select_card_menu,
    build_shop_remove_menu,
    build_shop_root_menu,
    build_target_menu,
    build_terminal_phase_menu,
)
from slay_the_spire.app.session import (
    SessionState,
    _content_provider,
    render_session,
    render_session_renderable,
    route_menu_choice,
)
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.adapters.rich_ui.inspect import (
    format_card_detail_lines,
    format_potion_detail_lines,
    format_relic_detail_lines,
    format_reward_detail_lines,
)
from slay_the_spire.adapters.rich_ui.widgets import render_card_name

_ROOM_LABELS: dict[str, str] = {
    "combat": "战斗房",
    "elite": "精英房",
    "boss": "Boss 房",
    "event": "事件房",
    "shop": "商店",
    "rest": "休息点",
}

_CARD_PREVIEW_MENU_MODES = frozenset(
    {
        "select_card",
        "shop_remove_card",
        "rest_upgrade_card",
        "event_upgrade_card",
        "event_remove_card",
        "inspect_deck",
        *COMBAT_INSPECT_CARD_LIST_MODES,
    }
)


def _is_full_map_panel(renderable: object) -> bool:
    return isinstance(renderable, Panel) and _plain_label(renderable.title) == "完整地图"


def _strip_full_map_panel(renderable: Any) -> Any:
    if _is_full_map_panel(renderable):
        return None
    if isinstance(renderable, Group):
        filtered = [_strip_full_map_panel(item) for item in renderable.renderables]
        kept = [item for item in filtered if item is not None]
        return Group(*kept)
    return renderable


def _render_to_rich(session: SessionState) -> Any:
    """把 session 转成 Rich renderable，供 RichLog 显示。"""
    renderable = render_session_renderable(session)
    if isinstance(renderable, Group):
        renderables = list(renderable.renderables)
        if len(renderables) >= 3:
            renderable = Group(*renderables[:-1])
    stripped = _strip_full_map_panel(renderable)
    return renderable if stripped is None else stripped


def _menu_choice_for_action(menu: MenuDefinition, action_id: str) -> str | None:
    for index, option in enumerate(menu.options, start=1):
        if option.action_id == action_id:
            return str(index)
    return None


def _plain_label(label: object) -> str:
    return getattr(label, "plain", str(label))


def _combat_state_from_session(session: SessionState) -> CombatState | None:
    combat_state = session.room_state.payload.get("combat_state")
    if not isinstance(combat_state, dict):
        return None
    return CombatState.from_dict(combat_state)


def _boss_rewards(session: SessionState) -> dict[str, object] | None:
    rewards = session.room_state.payload.get("boss_rewards")
    if not isinstance(rewards, dict):
        return None
    return rewards


def _supports_hover_preview(menu_mode: str) -> bool:
    return menu_mode in {"select_reward", "select_boss_reward", "select_boss_relic", "shop_root"} or menu_mode in _CARD_PREVIEW_MENU_MODES


def _hover_preview_guidance(menu_mode: str) -> Text | None:
    if menu_mode in _CARD_PREVIEW_MENU_MODES:
        return Text("查看说明：将鼠标悬停在卡牌上查看详情。")
    if menu_mode in {"select_reward", "select_boss_reward", "select_boss_relic", "shop_root"}:
        return Text("查看说明：将鼠标悬停在奖励或商品上查看详情。")
    return None


def _action_index(action_id: str, *, prefix: str) -> int | None:
    if not action_id.startswith(prefix):
        return None
    raw_index = action_id[len(prefix) :]
    if not raw_index.isdigit():
        return None
    index = int(raw_index) - 1
    if index < 0:
        return None
    return index


def _card_instance_from_indexed_action(action_id: str, *, prefix: str, card_instance_ids: list[str]) -> str | None:
    index = _action_index(action_id, prefix=prefix)
    if index is None or index >= len(card_instance_ids):
        return None
    return card_instance_ids[index]


def _card_preview_instance_id(session: SessionState, action_id: str) -> str | None:
    menu_mode = session.menu_state.mode
    if menu_mode == "select_card":
        combat_state = _combat_state_from_session(session)
        if combat_state is None:
            return None
        return _card_instance_from_indexed_action(action_id, prefix="play_card:", card_instance_ids=combat_state.hand)
    if menu_mode in {"shop_remove_card", "event_remove_card"} and action_id.startswith("remove_card:"):
        return action_id.split(":", 1)[1]
    if menu_mode in {"rest_upgrade_card", "event_upgrade_card"} and action_id.startswith("upgrade_card:"):
        return action_id.split(":", 1)[1]
    if menu_mode == "inspect_deck":
        return _card_instance_from_indexed_action(action_id, prefix="item:", card_instance_ids=session.run_state.deck)
    if menu_mode in COMBAT_INSPECT_CARD_LIST_MODES:
        combat_state = _combat_state_from_session(session)
        if combat_state is None:
            return None
        pile_map = {
            "inspect_hand": combat_state.hand,
            "inspect_draw_pile": combat_state.draw_pile,
            "inspect_discard_pile": combat_state.discard_pile,
            "inspect_exhaust_pile": combat_state.exhaust_pile,
        }
        return _card_instance_from_indexed_action(action_id, prefix="item:", card_instance_ids=pile_map.get(menu_mode, []))
    return None


def _reward_card_instance_id(reward_id: str) -> str | None:
    if reward_id.startswith("card_offer:") or reward_id.startswith("card:"):
        reward_name = reward_id.split(":", 1)[1]
        if reward_name == "reward_strike":
            return "strike_plus#reward"
        if reward_name == "reward_defend":
            return "defend_plus#reward"
        return f"{reward_name}#reward"
    return None


def _supports_reward_preview(reward_id: str) -> bool:
    return reward_id.startswith(("card_offer:", "card:", "gold:", "event:", "relic:"))


def _text_from_lines(lines: list[str | Text]) -> Text:
    rendered = Text()
    for index, line in enumerate(lines):
        if index > 0:
            rendered.append("\n")
        if isinstance(line, Text):
            rendered.append_text(line)
        else:
            rendered.append(line)
    return rendered


def _reward_preview_renderable(session: SessionState, action_id: str) -> Text | None:
    if action_id.startswith("claim_reward:"):
        reward_id = action_id.split(":", 1)[1]
        if not _supports_reward_preview(reward_id):
            return None
        card_instance_id = _reward_card_instance_id(reward_id)
        if card_instance_id is not None:
            return _text_from_lines(format_card_detail_lines(card_instance_id, _content_provider(session)))
        return _text_from_lines(format_reward_detail_lines(reward_id, _content_provider(session)))
    if action_id == "claim_all":
        return Text("控制项：全部领取")
    if action_id == "back":
        return Text("控制项：返回上一步")
    if action_id == "skip_card_rewards":
        return Text("控制项：跳过卡牌奖励")
    return None


def _shop_offer_by_action_id(session: SessionState, action_id: str, *, offer_type: str, item_key: str) -> str | None:
    if not action_id.startswith(f"{offer_type}:"):
        return None
    offer_id = action_id.split(":", 1)[1]
    offers = session.room_state.payload.get(f"{item_key}s")
    if not isinstance(offers, list):
        return None
    for offer in offers:
        if not isinstance(offer, dict) or offer.get("offer_id") != offer_id:
            continue
        item_id = offer.get(f"{item_key}_id")
        if isinstance(item_id, str):
            return item_id
    return None


def _hover_preview_renderable(session: SessionState, action_id: str) -> Text | None:
    if session.menu_state.mode == "select_reward":
        return _reward_preview_renderable(session, action_id)
    card_instance_id = _card_preview_instance_id(session, action_id)
    if card_instance_id is not None:
        return _text_from_lines(format_card_detail_lines(card_instance_id, _content_provider(session)))
    if session.menu_state.mode == "select_boss_reward":
        if action_id == "claim_boss_gold":
            return Text("控制项：领取首领金币")
        if action_id == "claimed_boss_gold":
            return Text("控制项：首领金币已领取")
        if action_id == "choose_boss_relic":
            return Text("控制项：进入首领遗物选择")
        if action_id == "claimed_boss_relic":
            return Text("控制项：首领遗物已选择")
        if action_id == "back":
            return Text("控制项：返回上一步")
        return None
    if session.menu_state.mode == "select_boss_relic" and action_id.startswith("claim_boss_relic:"):
        relic_id = action_id.split(":", 1)[1]
        return _text_from_lines(format_relic_detail_lines(relic_id, _content_provider(session)))
    if session.menu_state.mode == "shop_root":
        if action_id == "remove":
            remove_price = session.room_state.payload.get("remove_price", 75)
            return Text(f"控制项：删牌服务 - {remove_price} 金币")
        if action_id == "leave":
            return Text("控制项：离开商店")
        if action_id == "inspect":
            return Text("控制项：查看资料")
        if action_id == "save":
            return Text("控制项：保存游戏")
        if action_id == "load":
            return Text("控制项：读取存档")
        if action_id == "quit":
            return Text("控制项：退出游戏")
        card_id = _shop_offer_by_action_id(session, action_id, offer_type="buy_card", item_key="card")
        if card_id is not None:
            return _text_from_lines(format_card_detail_lines(f"{card_id}#shop", _content_provider(session)))
        relic_id = _shop_offer_by_action_id(session, action_id, offer_type="buy_relic", item_key="relic")
        if relic_id is not None:
            return _text_from_lines(format_relic_detail_lines(relic_id, _content_provider(session)))
        potion_id = _shop_offer_by_action_id(session, action_id, offer_type="buy_potion", item_key="potion")
        if potion_id is not None:
            return _text_from_lines(format_potion_detail_lines(potion_id, _content_provider(session)))
    return None


def _inspect_list_menu(title: str, labels: list[str]) -> MenuDefinition:
    options = [(f"item:{index}", label) for index, label in enumerate(labels, start=1)]
    options.append(("back", "返回上一步"))
    return build_menu(title=title, options=options)


def _build_target_action_menu(session: SessionState) -> MenuDefinition | None:
    combat_state = _combat_state_from_session(session)
    selected_card = session.menu_state.selected_card_instance_id
    if combat_state is None or not isinstance(selected_card, str):
        return None

    registry = _content_provider(session)
    card_def = registry.cards().get(card_id_from_instance_id(selected_card))
    current_card_name = render_card_name(card_def)
    effect_types = {str(effect.get("type")) for effect in card_def.effects}
    requires_enemy_target = bool(effect_types & {"damage", "vulnerable", "weak"})
    requires_hand_target = bool(effect_types & {"exhaust_target_card", "upgrade_target_card"})

    target_options: list[tuple[str, str | Text]] = []
    if requires_enemy_target or not requires_hand_target:
        living_enemies = [enemy for enemy in combat_state.enemies if enemy.hp > 0]
        for index, enemy in enumerate(living_enemies, start=1):
            enemy_name = registry.enemies().get(enemy.enemy_id).name
            target_options.append((f"target_enemy:{index}", f"敌人 {enemy_name}"))
    if requires_hand_target:
        selectable_cards = [card_instance_id for card_instance_id in combat_state.hand if card_instance_id != selected_card]
        for index, card_instance_id in enumerate(selectable_cards, start=1):
            card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
            target_options.append(
                (
                    f"target_hand:{index}",
                    Text.assemble("手牌 ", render_card_name(card_def), f" ({card_instance_id})"),
                )
            )

    return build_target_menu(target_options=target_options, current_card_name=current_card_name)


def _current_action_menu(session: SessionState) -> MenuDefinition | None:
    registry = _content_provider(session)
    room_state = session.room_state
    menu_mode = session.menu_state.mode

    if session.run_phase != "active":
        return build_terminal_phase_menu(run_phase=session.run_phase)
    if menu_mode == "root":
        return build_root_menu(room_state=room_state)
    if menu_mode == "select_next_room":
        next_node_ids = room_state.payload.get("next_node_ids", [])
        if not isinstance(next_node_ids, list):
            next_node_ids = []
        return build_next_room_menu(options=[(f"next_node:{node_id}", str(node_id)) for node_id in next_node_ids])
    if menu_mode == "select_event_choice":
        event_id = room_state.payload.get("event_id")
        if not isinstance(event_id, str):
            return build_event_choice_menu(options=[])
        event_def = registry.events().get(event_id)
        return build_event_choice_menu(
            options=[(f"choice:{choice.get('id')}", str(choice.get("label"))) for choice in event_def.choices]
        )
    if menu_mode == "event_upgrade_card":
        options = room_state.payload.get("upgrade_options", [])
        if not isinstance(options, list):
            options = []
        return build_event_upgrade_menu(
            options=[
                (
                    f"upgrade_card:{card_instance_id}",
                    render_card_name(registry.cards().get(card_id_from_instance_id(card_instance_id))),
                )
                for card_instance_id in options
            ]
        )
    if menu_mode == "event_remove_card":
        candidates = room_state.payload.get("remove_candidates", [])
        if not isinstance(candidates, list):
            candidates = []
        return build_event_remove_menu(
            options=[
                (
                    f"remove_card:{card_instance_id}",
                    render_card_name(registry.cards().get(card_id_from_instance_id(card_instance_id))),
                )
                for card_instance_id in candidates
            ]
        )
    if menu_mode == "select_reward":
        return build_reward_menu(room_state=room_state, registry=registry)
    if menu_mode == "select_boss_reward":
        return build_boss_reward_menu(_boss_rewards(session) or {})
    if menu_mode == "select_boss_relic":
        boss_rewards = _boss_rewards(session) or {}
        offers = boss_rewards.get("boss_relic_offers", [])
        if not isinstance(offers, list):
            offers = []
        return build_boss_relic_menu(offers, registry=registry)
    if menu_mode == "shop_root":
        return build_shop_root_menu(run_state=session.run_state, room_state=room_state, registry=registry)
    if menu_mode == "shop_remove_card":
        return build_shop_remove_menu(room_state=room_state, registry=registry)
    if menu_mode == "rest_root":
        return build_rest_root_menu(room_state=room_state, run_state=session.run_state)
    if menu_mode == "rest_upgrade_card":
        return build_rest_upgrade_menu(room_state=room_state, registry=registry)
    if menu_mode == "select_card":
        combat_state = _combat_state_from_session(session)
        if combat_state is None:
            return None
        return build_select_card_menu(combat_state=combat_state, registry=registry)
    if menu_mode == "select_target":
        return _build_target_action_menu(session)
    if menu_mode == "inspect_root":
        return build_inspect_root_menu(room_state=room_state)
    if menu_mode == "inspect_deck":
        labels = [registry.cards().get(card_id_from_instance_id(card_instance_id)).name for card_instance_id in session.run_state.deck]
        return _inspect_list_menu("牌组列表", labels)
    if menu_mode in COMBAT_INSPECT_CARD_LIST_MODES:
        combat_state = _combat_state_from_session(session)
        if combat_state is None:
            return None
        pile_map = {
            "inspect_hand": ("手牌列表", combat_state.hand),
            "inspect_draw_pile": ("抽牌堆列表", combat_state.draw_pile),
            "inspect_discard_pile": ("弃牌堆列表", combat_state.discard_pile),
            "inspect_exhaust_pile": ("消耗堆列表", combat_state.exhaust_pile),
        }
        title, pile = pile_map[menu_mode]
        labels = [registry.cards().get(card_id_from_instance_id(card_instance_id)).name for card_instance_id in pile]
        return _inspect_list_menu(title, labels)
    if menu_mode == "inspect_enemy_list":
        combat_state = _combat_state_from_session(session)
        if combat_state is None:
            return None
        labels = [registry.enemies().get(enemy.enemy_id).name for enemy in combat_state.enemies]
        return _inspect_list_menu("敌人列表", labels)
    if menu_mode == "inspect_card_detail":
        return build_card_detail_menu()
    if menu_mode == "inspect_enemy_detail":
        return build_enemy_detail_menu()

    leaf_title = inspect_leaf_title(menu_mode)
    if leaf_title is not None:
        return build_leaf_menu(title=leaf_title)
    return None


class SlayApp(App[None]):
    """Slay the Spire Textual UI。"""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #map-panel {
        width: 2fr;
        height: 1fr;
        background: antiquewhite;
        color: black;
        border: solid wheat;
        padding: 0;
        overflow: auto;
    }

    #right-panel {
        width: 3fr;
        height: 1fr;
        layout: vertical;
    }

    #game-log {
        height: 1fr;
        border: solid grey;
        overflow-y: auto;
    }

    #action-summary {
        height: auto;
        background: $surface;
        padding: 0 1;
        color: $text-muted;
    }

    #hover-preview {
        height: 7;
        border: solid grey;
        padding: 0 1;
        color: $text-muted;
        overflow-y: auto;
    }

    #action-list {
        height: 12;
        border: solid green;
    }

    #flash-msg {
        height: 1;
        background: $surface;
        color: yellow;
        padding: 0 1;
    }

    Footer {
        height: 1;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "退出"),
        ("ctrl+q", "quit", "退出"),
    ]

    def __init__(self, session: SessionState) -> None:
        super().__init__()
        self._session = session
        self._action_choices: list[str] = []
        self._action_ids: list[str] = []
        self._hovered_node_id: str | None = None
        self.console.push_theme(TERMINAL_THEME)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal():
            # 左侧：地图
            with Vertical(id="map-panel"):
                yield MapWidget(self._session.act_state, id="map-widget")
            # 右侧：日志 + 输入
            with Vertical(id="right-panel"):
                yield RichLog(id="game-log", highlight=True, markup=True, wrap=True)
                yield Static("", id="action-summary")
                yield Static("", id="hover-preview")
                yield OptionList(id="action-list")
                yield Static("", id="flash-msg")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_log()
        self._refresh_actions()
        self.query_one("#action-list", OptionList).focus()

    def _refresh_log(self) -> None:
        log = self.query_one("#game-log", RichLog)
        log.clear()
        renderable = _render_to_rich(self._session)
        log.write(renderable)
        log.scroll_end(animate=False)

    def _refresh_map(self) -> None:
        try:
            map_widget = self.query_one("#map-widget", MapWidget)
            map_widget.update_act(self._session.act_state)
        except NoMatches:
            pass

    def _set_flash(self, msg: str) -> None:
        try:
            self.query_one("#flash-msg", Static).update(msg)
        except NoMatches:
            pass

    def _refresh_actions(self) -> None:
        menu = _current_action_menu(self._session)
        action_summary = self.query_one("#action-summary", Static)
        action_list = self.query_one("#action-list", OptionList)
        action_list.clear_options()
        self._action_choices = []
        self._action_ids = []

        if menu is None:
            action_summary.update("当前没有可点击操作。")
            self._refresh_hover_preview()
            return

        summary = Text(menu.title)
        for line in menu.header_lines:
            summary.append("\n")
            if isinstance(line, Text):
                summary.append_text(line)
            else:
                summary.append(str(line))
        hover_summary = self._hover_summary()
        if hover_summary is not None:
            summary.append("\n")
            summary.append(hover_summary)
        action_summary.update(summary)

        prompts: list[str | Text] = []
        for index, option in enumerate(menu.options, start=1):
            prompts.append(Text.assemble(f"{index}. ", option.label))
            self._action_choices.append(str(index))
            self._action_ids.append(option.action_id)
        action_list.add_options(prompts)
        self._refresh_hover_preview()

    def _refresh_hover_preview(self, action_id: str | None = None) -> None:
        preview = self.query_one("#hover-preview", Static)
        menu_mode = self._session.menu_state.mode
        if action_id is not None:
            rendered = _hover_preview_renderable(self._session, action_id)
            if rendered is not None:
                preview.update(rendered)
                preview.display = True
                return
        guidance = _hover_preview_guidance(menu_mode)
        if guidance is not None:
            preview.update(guidance)
            preview.display = True
        else:
            preview.update(Text(""))
            preview.display = False

    def _process_command(self, cmd: str) -> None:
        running, new_session, message = route_menu_choice(cmd, session=self._session)
        self._session = new_session
        self._refresh_log()
        self._refresh_map()
        self._refresh_actions()
        rendered = render_session(new_session)
        self._set_flash("" if message == rendered else message)
        if not running:
            self._set_flash("游戏已结束，按 Ctrl+C 退出。")
            self.query_one("#action-list", OptionList).disabled = True

    @on(OptionList.OptionSelected, "#action-list")
    def handle_action_selected(self, event: OptionList.OptionSelected) -> None:
        option_index = event.option_index
        if option_index < 0 or option_index >= len(self._action_choices):
            return
        self._process_command(self._action_choices[option_index])

    @on(OptionList.OptionHighlighted, "#action-list")
    def handle_action_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_index < 0 or event.option_index >= len(self._action_ids):
            self._refresh_hover_preview()
            return
        self._refresh_hover_preview(self._action_ids[event.option_index])

    @on(events.MouseMove, "#action-list")
    def handle_action_list_mouse_move(self, event: events.MouseMove) -> None:
        option_index = event.style.meta.get("option")
        if not isinstance(option_index, int) or option_index < 0 or option_index >= len(self._action_ids):
            self._refresh_hover_preview()
            return
        self._refresh_hover_preview(self._action_ids[option_index])

    @on(events.Leave, "#action-list")
    def handle_action_list_leave(self, _: events.Leave) -> None:
        self._refresh_hover_preview()

    @on(MapWidget.NodeSelected)
    def handle_node_selected(self, event: MapWidget.NodeSelected) -> None:
        node_id = event.node_id
        session = self._session
        if session.menu_state.mode == "select_next_room":
            next_choice = self._next_node_choice(node_id)
            if next_choice is not None:
                self._process_command(next_choice)
            return

        if session.menu_state.mode != "root" or not session.room_state.is_resolved:
            return

        root_choice = _menu_choice_for_action(build_root_menu(room_state=session.room_state), "next_room")
        if root_choice is None:
            return
        self._process_command(root_choice)
        next_choice = self._next_node_choice(node_id)
        if next_choice is not None:
            self._process_command(next_choice)

    @on(MapWidget.NodeHovered)
    def handle_node_hovered(self, event: MapWidget.NodeHovered) -> None:
        self._hovered_node_id = event.node_id
        self._refresh_actions()

    def _next_node_choice(self, node_id: str) -> str | None:
        next_node_ids = self._session.room_state.payload.get("next_node_ids", [])
        if not isinstance(next_node_ids, list) or node_id not in next_node_ids:
            return None
        menu = build_next_room_menu(options=[(f"next_node:{next_id}", str(next_id)) for next_id in next_node_ids])
        return _menu_choice_for_action(menu, f"next_node:{node_id}")

    def _hover_summary(self) -> str | None:
        node_id = self._hovered_node_id
        if node_id is None:
            return None
        node = next((item for item in self._session.act_state.nodes if item.node_id == node_id), None)
        if node is None:
            return None
        room_label = _ROOM_LABELS.get(node.room_type, node.room_type)
        if node.node_id == self._session.act_state.current_node_id:
            state_label = "当前"
        elif node.node_id in self._session.act_state.reachable_node_ids:
            state_label = "可达"
        else:
            state_label = "不可达"
        return f"当前悬停：{room_label}（{state_label}）"
