from __future__ import annotations

from typing import Any

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.terminal.screens.layout import build_standard_screen, build_two_column_body
from slay_the_spire.adapters.terminal.theme import PANEL_BOX
from slay_the_spire.adapters.terminal.widgets import (
    preview_enemy_intent,
    render_block,
    render_hp_bar,
    render_menu,
    render_statuses,
    summarize_card_effects,
)
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
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


def _format_reward_label(reward_id: str) -> str:
    if reward_id.startswith("gold:"):
        return f"金币 {reward_id.split(':', 1)[1]}"
    if reward_id.startswith("card:"):
        reward_name = reward_id.split(":", 1)[1]
        if reward_name == "reward_strike":
            return "卡牌 打击+"
        if reward_name == "reward_defend":
            return "卡牌 防御+"
        return f"卡牌 {reward_name}"
    if reward_id.startswith("event:"):
        result = reward_id.split(":", 1)[1]
        if result == "gain_upgrade":
            return "事件结果 获得升级"
        if result == "nothing":
            return "事件结果 什么也没有发生"
        return f"事件结果 {result}"
    return reward_id


def _format_reward_lines(rewards: list[str]) -> list[str]:
    if not rewards:
        return ["-"]
    return [f"{index}. {_format_reward_label(reward)}" for index, reward in enumerate(rewards, start=1)]


def _format_root_menu(room_state: RoomState) -> list[str]:
    if room_state.is_resolved:
        if room_state.rewards:
            return [
                "可选操作:",
                "1. 查看奖励",
                "2. 领取奖励",
                "3. 前往下一个房间",
                "4. 保存游戏",
                "5. 读取存档",
                "6. 退出游戏",
            ]
        return [
            "可选操作:",
            "1. 前往下一个房间",
            "2. 保存游戏",
            "3. 读取存档",
            "4. 退出游戏",
        ]
    return [
        "可选操作:",
        "1. 查看战场",
        "2. 出牌",
        "3. 结束回合",
        "4. 保存游戏",
        "5. 读取存档",
        "6. 退出游戏",
    ]


def _format_next_room_menu(room_state: RoomState) -> list[str]:
    lines = ["请选择下一个房间:"]
    next_node_ids = room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list):
        next_node_ids = []
    for index, node_id in enumerate(next_node_ids, start=1):
        lines.append(f"{index}. {_format_node(node_id)}")
    lines.append(f"{len(next_node_ids) + 1}. 返回上一步")
    return lines


def _format_event_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str]:
    event_id = room_state.payload.get("event_id")
    if not isinstance(event_id, str):
        return ["事件选项:", "1. 返回上一步"]
    event_def = registry.events().get(event_id)
    lines = ["事件选项:"]
    for index, choice in enumerate(event_def.choices, start=1):
        lines.append(f"{index}. {choice.get('label')}")
    lines.append(f"{len(event_def.choices) + 1}. 返回上一步")
    return lines


def _format_reward_menu(room_state: RoomState) -> list[str]:
    lines = ["奖励:"]
    lines.extend(_format_reward_lines(room_state.rewards))
    lines.append(f"{len(room_state.rewards) + 1}. 全部领取")
    lines.append(f"{len(room_state.rewards) + 2}. 返回上一步")
    return lines


def _format_card_menu(combat_state: CombatState, registry: ContentProviderPort) -> list[str]:
    if not combat_state.hand:
        return ["手牌:", "1. 返回上一步"]
    lines = ["手牌:"]
    for index, card_instance_id in enumerate(combat_state.hand, start=1):
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        lines.append(f"{index}. {card_def.name} 费用{card_def.cost} - {summarize_card_effects(card_def.effects)}")
    lines.append(f"{len(combat_state.hand) + 1}. 返回上一步")
    return lines


def _format_target_menu(combat_state: CombatState, registry: ContentProviderPort, selected_card: str | None) -> list[str]:
    lines = ["选择目标:"]
    if selected_card is not None:
        card_def = registry.cards().get(card_id_from_instance_id(selected_card))
        lines.append(f"当前卡牌: {card_def.name}")
    living_enemies = [enemy for enemy in combat_state.enemies if enemy.hp > 0]
    for index, enemy in enumerate(living_enemies, start=1):
        enemy_def = registry.enemies().get(enemy.enemy_id)
        line = Text(f"{index}. ")
        line.append(enemy_def.name, style="enemy.name")
        line.append(" 生命: ")
        line.append_text(render_hp_bar(enemy.hp, enemy.max_hp))
        lines.append(line)
    lines.append(f"{len(living_enemies) + 1}. 返回上一步")
    return lines


def _format_menu(
    room_state: RoomState,
    combat_state: CombatState,
    registry: ContentProviderPort,
    menu_state: Any,
) -> list[str | Text]:
    mode = _menu_mode(menu_state)
    if mode == "select_card":
        return _format_card_menu(combat_state, registry)
    if mode == "select_target":
        return _format_target_menu(combat_state, registry, _selected_card_instance_id(menu_state))
    if mode == "select_next_room":
        return _format_next_room_menu(room_state)
    if mode == "select_event_choice":
        return _format_event_menu(room_state, registry)
    if mode == "select_reward":
        return _format_reward_menu(room_state)
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
    lines = [
        Text.assemble(("格挡 ", "summary.label"), render_block(combat_state.player.block)),
        Text.assemble(("状态 ", "summary.label"), render_statuses(combat_state.player.statuses)),
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
        intent_preview = preview_enemy_intent(enemy_def)
        if intent_preview != "-":
            line.append(f" 意图: {intent_preview}")
        lines.append(line)
    return Panel(Group(*lines), title="敌人意图", box=PANEL_BOX, expand=False)


def render_hand_panel(combat_state: CombatState, registry: ContentProviderPort) -> Panel:
    if not combat_state.hand:
        return Panel(Group(Text("-")), title="手牌", box=PANEL_BOX, expand=False)
    lines: list[RenderableType] = []
    for index, card_instance_id in enumerate(combat_state.hand, start=1):
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        lines.append(f"{index}. {card_def.name} ({card_def.cost}) - {summarize_card_effects(card_def.effects)}")
    return Panel(Group(*lines), title="手牌", box=PANEL_BOX, expand=False)


def render_menu_panel_for_combat(
    room_state: RoomState,
    combat_state: CombatState,
    registry: ContentProviderPort,
    menu_state: Any,
) -> Panel:
    return render_menu(_format_menu(room_state, combat_state, registry, menu_state))


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
    body = build_two_column_body(
        left=render_player_panel(combat_state, registry),
        right=render_enemy_panel(combat_state, registry),
    )
    hand_panel = render_hand_panel(combat_state, registry)
    body_group = [body, hand_panel]
    footer = render_menu_panel_for_combat(room_state, combat_state, registry, menu_state)
    return build_standard_screen(summary=summary, body=Group(*body_group), footer=footer)
