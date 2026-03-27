from __future__ import annotations

from typing import Any

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.terminal.inspect import (
    format_card_detail_menu,
    format_card_list_footer,
    format_enemy_detail_menu,
    format_enemy_list_footer,
    render_card_detail_panel,
    render_card_pile_panel,
    render_enemy_detail_panel,
    render_enemy_list_panel,
    render_shared_potions_panel,
    render_shared_relics_panel,
    render_shared_stats_panel,
)
from slay_the_spire.adapters.terminal.inspect_registry import format_shared_inspect_menu, render_shared_inspect_panel
from slay_the_spire.adapters.terminal.screens.layout import build_standard_screen, build_two_column_body
from slay_the_spire.adapters.terminal.theme import PANEL_BOX
from slay_the_spire.adapters.terminal.widgets import (
    render_block,
    render_card_name,
    render_hp_bar,
    render_menu,
    render_statuses,
    summarize_card_definition,
    summarize_enemy_move_preview,
)
from slay_the_spire.app.menu_definitions import (
    build_event_choice_menu,
    build_inspect_root_menu,
    build_leaf_menu,
    build_next_room_menu,
    build_reward_menu,
    build_root_menu,
    build_select_card_menu,
    build_target_menu,
    format_menu_entries,
    format_menu_lines,
)
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.combat.turn_flow import preview_enemy_move_for_display
from slay_the_spire.ports.content_provider import ContentProviderPort

_ROOM_TYPE_LABELS = {
    "combat": "普通战斗",
    "elite": "精英战斗",
    "boss": "Boss战",
    "event": "事件",
}

_NODE_LABELS = {
    "start": "起点",
    "hallway": "走廊",
    "elite": "精英",
    "event": "事件",
    "boss": "Boss",
}


def _menu_mode(menu_state: Any) -> str:
    return str(getattr(menu_state, "mode", "root"))


def _selected_card_instance_id(menu_state: Any) -> str | None:
    value = getattr(menu_state, "selected_card_instance_id", None)
    return value if isinstance(value, str) else None


def _format_node(node_id: object) -> str:
    return _NODE_LABELS.get(str(node_id), str(node_id))


def _format_next_nodes(room_state: RoomState) -> str:
    next_node_ids = room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list) or not next_node_ids:
        return "-"
    return ", ".join(_format_node(node_id) for node_id in next_node_ids)


def _reward_card_id(reward_name: str) -> str:
    if reward_name == "reward_strike":
        return "strike_plus"
    if reward_name == "reward_defend":
        return "defend_plus"
    return reward_name


def _format_reward_label(reward_id: str, registry: ContentProviderPort) -> str:
    if reward_id.startswith("gold:"):
        return f"金币 {reward_id.split(':', 1)[1]}"
    if reward_id.startswith("card_offer:"):
        reward_name = reward_id.split(":", 1)[1]
        card_def = registry.cards().get(_reward_card_id(reward_name))
        return f"卡牌 {card_def.name}"
    if reward_id.startswith("card:"):
        reward_name = reward_id.split(":", 1)[1]
        card_def = registry.cards().get(_reward_card_id(reward_name))
        return f"卡牌 {card_def.name}"
    if reward_id.startswith("event:"):
        result = reward_id.split(":", 1)[1]
        if result == "gain_upgrade":
            return "事件结果 获得升级"
        if result == "nothing":
            return "事件结果 什么也没有发生"
        return f"事件结果 {result}"
    return reward_id


def _format_reward_lines(rewards: list[str], registry: ContentProviderPort) -> list[str]:
    if not rewards:
        return ["-"]
    return [f"{index}. {_format_reward_label(reward, registry)}" for index, reward in enumerate(rewards, start=1)]


def _format_root_menu(room_state: RoomState) -> list[str]:
    return format_menu_lines(build_root_menu(room_state=room_state))


def _format_inspect_root_menu(room_state: RoomState) -> list[str]:
    return format_menu_lines(build_inspect_root_menu(room_state=room_state))


def _format_inspect_deck_menu(run_state: RunState, registry: ContentProviderPort) -> list[str]:
    lines: list[str] = []
    if not run_state.deck:
        lines.append("-")
    else:
        for index, card_instance_id in enumerate(run_state.deck, start=1):
            card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
            lines.append(f"{index}. {card_def.name}")
    lines.append(f"{len(run_state.deck) + 1}. 返回上一步")
    return lines


def _format_inspect_deck_footer(run_state: RunState) -> list[str]:
    return [
        "输入上方编号查看卡牌详情",
        f"{len(run_state.deck) + 1}. 返回上一步",
    ]


def _format_inspect_leaf_menu(title: str) -> list[str]:
    return format_menu_lines(build_leaf_menu(title=title))


def _format_next_room_menu(room_state: RoomState) -> list[str]:
    next_node_ids = room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list):
        next_node_ids = []
    return format_menu_lines(
        build_next_room_menu(
            options=[(f"next_node:{node_id}", _format_node(node_id)) for node_id in next_node_ids],
        )
    )


def _format_event_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str]:
    event_id = room_state.payload.get("event_id")
    if not isinstance(event_id, str):
        return format_menu_lines(build_event_choice_menu(options=[]))
    event_def = registry.events().get(event_id)
    return format_menu_lines(
        build_event_choice_menu(
            options=[
                (f"choice:{choice.get('id')}", str(choice.get("label")))
                for choice in event_def.choices
            ]
        )
    )


def _format_reward_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str]:
    return format_menu_entries(build_reward_menu(room_state=room_state, registry=registry))


def _format_card_menu(combat_state: CombatState, registry: ContentProviderPort) -> list[str | Text]:
    return format_menu_entries(build_select_card_menu(combat_state=combat_state, registry=registry))


def _format_target_menu(combat_state: CombatState, registry: ContentProviderPort, selected_card: str | None) -> list[str | Text]:
    current_card_name: Text | None = None
    requires_enemy_target = False
    requires_hand_target = False
    if selected_card is not None:
        card_def = registry.cards().get(card_id_from_instance_id(selected_card))
        current_card_name = render_card_name(card_def)
        effect_types = {effect.get("type") for effect in card_def.effects}
        requires_enemy_target = bool(effect_types & {"damage", "vulnerable"})
        requires_hand_target = bool(effect_types & {"exhaust_target_card", "upgrade_target_card"})
    enemy_target_options: list[tuple[str, Text]] = []
    if requires_enemy_target or not requires_hand_target:
        living_enemies = [enemy for enemy in combat_state.enemies if enemy.hp > 0]
        for index, enemy in enumerate(living_enemies, start=1):
            enemy_def = registry.enemies().get(enemy.enemy_id)
            label = Text()
            label.append(enemy_def.name, style="enemy.name")
            label.append(" 生命: ")
            label.append_text(render_hp_bar(enemy.hp, enemy.max_hp))
            enemy_target_options.append((f"target_enemy:{index}", label))
    hand_target_options: list[tuple[str, Text]] = []
    if selected_card is not None and requires_hand_target:
        selectable_hand_cards = [card for card in combat_state.hand if card != selected_card]
        for index, card_instance_id in enumerate(selectable_hand_cards, start=1):
            card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
            label = Text()
            label.append_text(render_card_name(card_def))
            label.append(f" ({card_instance_id})")
            hand_target_options.append((f"target_hand:{index}", label))

    target_options: list[tuple[str, str | Text]] = []
    header_lines: list[str | Text] = []
    title = "选择目标"
    if enemy_target_options and not hand_target_options:
        title = "选择敌人"
        target_options = enemy_target_options
    elif hand_target_options and not enemy_target_options:
        title = "选择手牌"
        target_options = hand_target_options
    else:
        title = "选择目标（敌人或手牌）"
        if enemy_target_options:
            header_lines.append("敌人目标:")
            target_options.extend(enemy_target_options)
        if hand_target_options:
            if target_options:
                header_lines.append("手牌目标:")
            else:
                header_lines.append("手牌目标:")
            target_options.extend(hand_target_options)

    menu = build_target_menu(
        target_options=target_options,
        current_card_name=current_card_name,
        title=title,
        header_lines=header_lines,
    )
    return format_menu_entries(menu)


def _format_menu(
    room_state: RoomState,
    run_state: RunState,
    combat_state: CombatState,
    registry: ContentProviderPort,
    menu_state: Any,
) -> list[str | Text]:
    mode = _menu_mode(menu_state)
    shared_menu = format_shared_inspect_menu(
        mode=mode,
        context="combat",
        run_state=run_state,
        room_state=room_state,
        registry=registry,
    )
    if shared_menu is not None:
        return shared_menu
    if mode == "inspect_hand":
        return format_card_list_footer(back_choice=len(combat_state.hand) + 1)
    if mode == "inspect_draw_pile":
        return format_card_list_footer(back_choice=len(combat_state.draw_pile) + 1)
    if mode == "inspect_discard_pile":
        return format_card_list_footer(back_choice=len(combat_state.discard_pile) + 1)
    if mode == "inspect_exhaust_pile":
        return format_card_list_footer(back_choice=len(combat_state.exhaust_pile) + 1)
    if mode == "inspect_card_detail":
        return format_card_detail_menu()
    if mode == "inspect_enemy_list":
        return format_enemy_list_footer(back_choice=len(combat_state.enemies) + 1)
    if mode == "inspect_enemy_detail":
        return format_enemy_detail_menu()
    if mode == "select_card":
        return _format_card_menu(combat_state, registry)
    if mode == "select_target":
        return _format_target_menu(combat_state, registry, _selected_card_instance_id(menu_state))
    if mode == "select_next_room":
        return _format_next_room_menu(room_state)
    if mode == "select_event_choice":
        return _format_event_menu(room_state, registry)
    if mode == "select_reward":
        return _format_reward_menu(room_state, registry)
    return _format_root_menu(room_state)


def render_summary_bar(
    *,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    combat_state: CombatState,
    registry: ContentProviderPort,
) -> Panel:
    node_id = room_state.payload.get("node_id", act_state.current_node_id)
    room_kind = room_state.payload.get("room_kind", room_state.room_type)
    character_name = registry.characters().get(run_state.character_id).name
    act_name = registry.acts().get(act_state.act_id).name
    player_hp_line = Text.assemble(("玩家生命 ", "summary.label"), render_hp_bar(combat_state.player.hp, combat_state.player.max_hp))
    if combat_state.player.hp != combat_state.player.max_hp:
        player_hp_line.append(f" (玩家生命: {combat_state.player.hp}/{combat_state.player.max_hp})")
    lines = [
        Text.assemble(("种子 ", "summary.label"), str(run_state.seed), f" (种子: {run_state.seed})"),
        Text.assemble(("角色 ", "summary.label"), (character_name, "player.name")),
        Text.assemble(("章节 ", "summary.label"), str(act_name), f" (章节: {act_name})"),
        Text.assemble(("房间 ", "summary.label"), str(_format_node(node_id)), f" (房间: {_format_node(node_id)})"),
        Text.assemble(
            ("房间类型 ", "summary.label"),
            str(_ROOM_TYPE_LABELS.get(str(room_kind), str(room_kind))),
            f" (房间类型: {_ROOM_TYPE_LABELS.get(str(room_kind), str(room_kind))})",
        ),
        Text.assemble(("回合 ", "summary.label"), str(combat_state.round_number), f" (回合: {combat_state.round_number})"),
        Text.assemble(("当前能量 ", "summary.label"), str(combat_state.energy), f" (当前能量: {combat_state.energy})"),
        Text.assemble(("抽牌堆 ", "summary.label"), str(len(combat_state.draw_pile)), f" (抽牌堆: {len(combat_state.draw_pile)})"),
        Text.assemble(("弃牌堆 ", "summary.label"), str(len(combat_state.discard_pile)), f" (弃牌堆: {len(combat_state.discard_pile)})"),
        player_hp_line,
        Text.assemble(
            ("房间已完成 ", "summary.label"),
            "是" if room_state.is_resolved else "否",
            f" (房间已完成: {'是' if room_state.is_resolved else '否'})",
        ),
    ]
    return Panel(Group(*lines), title="战斗摘要", box=PANEL_BOX, expand=False)


def render_player_panel(combat_state: CombatState, registry: ContentProviderPort) -> Panel:
    del registry
    power_labels: list[str] = []
    for power in combat_state.active_powers:
        power_id = power.get("power_id")
        if not isinstance(power_id, str):
            continue
        amount = power.get("amount")
        if isinstance(amount, int):
            power_labels.append(f"{power_id} {amount}")
        else:
            power_labels.append(power_id)
    lines = [
        Text.assemble(("格挡 ", "summary.label"), render_block(combat_state.player.block)),
        Text.assemble(("状态 ", "summary.label"), render_statuses(combat_state.player.statuses)),
        Text.assemble(("持续效果 ", "summary.label"), " / ".join(power_labels) if power_labels else "无"),
    ]
    return Panel(Group(*lines), title="玩家状态", box=PANEL_BOX, expand=False)


def render_enemy_panel(combat_state: CombatState, registry: ContentProviderPort) -> Panel:
    if not combat_state.enemies:
        return Panel(Group(Text("-")), title="敌人意图", box=PANEL_BOX, expand=False)
    lines: list[RenderableType] = []
    for index, enemy in enumerate(combat_state.enemies, start=1):
        enemy_def = registry.enemies().get(enemy.enemy_id)
        line = Text(f"{index}. ")
        line.append(enemy_def.name, style="enemy.name")
        line.append(" 生命: ")
        line.append_text(render_hp_bar(enemy.hp, enemy.max_hp))
        line.append(" 格挡: ")
        line.append_text(render_block(enemy.block))
        line.append(" 状态: ")
        line.append_text(render_statuses(enemy.statuses))
        intent_preview = summarize_enemy_move_preview(preview_enemy_move_for_display(combat_state, enemy, enemy_def))
        if intent_preview != "-":
            line.append(f" 意图: {intent_preview}")
        lines.append(line)
    return Panel(Group(*lines), title="敌人意图", box=PANEL_BOX, expand=False)


def render_hand_panel(combat_state: CombatState, registry: ContentProviderPort) -> Panel:
    title = f"手牌（能量 {combat_state.energy}）"
    if not combat_state.hand:
        return Panel(Group(Text("-")), title=title, box=PANEL_BOX, expand=False)
    lines: list[RenderableType] = []
    for index, card_instance_id in enumerate(combat_state.hand, start=1):
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        lines.append(
            Text.assemble(
                f"{index}. ",
                render_card_name(card_def),
                f" ({card_def.cost}) - {summarize_card_definition(card_def)}",
            )
        )
    return Panel(Group(*lines), title=title, box=PANEL_BOX, expand=False)


def render_menu_panel_for_combat(
    room_state: RoomState,
    run_state: RunState,
    combat_state: CombatState,
    registry: ContentProviderPort,
    menu_state: Any,
) -> Panel:
    return render_menu(_format_menu(room_state, run_state, combat_state, registry, menu_state))


def render_battle_log_panel(combat_state: CombatState) -> Panel:
    entries = combat_state.log[-5:]
    if not entries:
        body: list[RenderableType] = [Text("当前还没有新的战斗记录。")]
    else:
        body = [Text(entry) for entry in entries]
    return Panel(Group(*body), title="战斗记录", box=PANEL_BOX, expand=False)


def _inspect_body_panel(
    menu_state: Any,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    combat_state: CombatState,
    registry: ContentProviderPort,
) -> Panel:
    mode = _menu_mode(menu_state)
    shared_panel = render_shared_inspect_panel(
        mode=mode,
        context="combat",
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        registry=registry,
        card_instance_id=getattr(menu_state, "inspect_item_id", None),
        combat_state=combat_state,
    )
    if shared_panel is not None:
        return shared_panel
    if mode == "inspect_hand":
        return render_card_pile_panel("手牌列表", combat_state.hand, registry)
    if mode == "inspect_draw_pile":
        return render_card_pile_panel("抽牌堆列表", combat_state.draw_pile, registry)
    if mode == "inspect_discard_pile":
        return render_card_pile_panel("弃牌堆列表", combat_state.discard_pile, registry)
    if mode == "inspect_exhaust_pile":
        return render_card_pile_panel("消耗堆列表", combat_state.exhaust_pile, registry)
    if mode == "inspect_enemy_list":
        return render_enemy_list_panel(combat_state, registry)
    if mode == "inspect_enemy_detail":
        enemy_instance_id = getattr(menu_state, "inspect_item_id", None)
        if isinstance(enemy_instance_id, str):
            enemy = next((current for current in combat_state.enemies if current.instance_id == enemy_instance_id), None)
            if enemy is not None:
                return render_enemy_detail_panel(combat_state, enemy, registry)
    return Panel(
        Group(
            Text("当前处于资料总览。"),
            Text("可查看属性、牌组、遗物、药水，以及战斗中的各牌堆与敌人详情。"),
        ),
        title="资料总览",
        box=PANEL_BOX,
        expand=False,
    )


def render_combat_screen(
    *,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    combat_state: CombatState,
    registry: ContentProviderPort,
    menu_state: Any,
) -> RenderableType:
    summary = render_summary_bar(
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        combat_state=combat_state,
        registry=registry,
    )
    mode = _menu_mode(menu_state)
    if mode.startswith("inspect_"):
        body = _inspect_body_panel(menu_state, run_state, act_state, room_state, combat_state, registry)
        body_group = [body]
    else:
        body = build_two_column_body(
            left=render_player_panel(combat_state, registry),
            right=render_enemy_panel(combat_state, registry),
        )
        hand_panel = render_hand_panel(combat_state, registry)
        battle_log_panel = render_battle_log_panel(combat_state)
        body_group = [body, hand_panel, battle_log_panel]
    footer = render_menu_panel_for_combat(room_state, run_state, combat_state, registry, menu_state)
    return build_standard_screen(summary=summary, body=Group(*body_group), footer=footer)
