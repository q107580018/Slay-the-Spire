from __future__ import annotations

from typing import Any

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.terminal.screens.layout import build_standard_screen
from slay_the_spire.adapters.terminal.theme import PANEL_BOX
from slay_the_spire.adapters.terminal.widgets import render_menu
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort

_ROOM_TYPE_LABELS = {
    "combat": "普通战斗",
    "elite": "精英战斗",
    "boss": "Boss战",
    "event": "事件",
}

_STAGE_LABELS = {
    "waiting_input": "等待操作",
    "completed": "已完成",
    "defeated": "已失败",
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


def _format_event_result(room_state: RoomState) -> str | None:
    result = room_state.payload.get("result")
    if not isinstance(result, str):
        return None
    if result == "gain_upgrade":
        return "获得升级"
    if result == "nothing":
        return "什么也没有发生"
    return result


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
    lines.append(f"{len(room_state.rewards) + 1}. 返回上一步")
    return lines


def _format_default_menu(room_state: RoomState) -> list[str]:
    if room_state.room_type == "event":
        return [
            "可选操作:",
            "1. 查看事件",
            "2. 进行选择",
            "3. 保存游戏",
            "4. 读取存档",
            "5. 退出游戏",
        ]
    if room_state.is_resolved and room_state.rewards:
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
        "1. 查看当前状态",
        "2. 前往下一个房间",
        "3. 保存游戏",
        "4. 读取存档",
        "5. 退出游戏",
    ]


def render_summary_panel(*, run_state: RunState, act_state: ActState, room_state: RoomState, registry: ContentProviderPort) -> Panel:
    node_id = room_state.payload.get("node_id", act_state.current_node_id)
    room_kind = room_state.payload.get("room_kind", room_state.room_type)
    character_name = registry.characters().get(run_state.character_id).name
    act_name = registry.acts().get(act_state.act_id).name
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
        Text.assemble(("阶段 ", "summary.label"), str(_STAGE_LABELS.get(room_state.stage, room_state.stage)), f" (阶段: {_STAGE_LABELS.get(room_state.stage, room_state.stage)})"),
        Text.assemble(("房间已完成 ", "summary.label"), "是" if room_state.is_resolved else "否", f" (房间已完成: {'是' if room_state.is_resolved else '否'})"),
        Text.assemble(("下一房间 ", "summary.label"), str(_format_next_nodes(room_state)), f" (下一房间: {_format_next_nodes(room_state)})"),
    ]
    return Panel(Group(*lines), title="房间摘要", box=PANEL_BOX, expand=False)


def render_default_body(room_state: RoomState) -> Panel:
    lines = [
        Text.assemble(("阶段 ", "summary.label"), str(_STAGE_LABELS.get(room_state.stage, room_state.stage))),
        Text.assemble(("已完成 ", "summary.label"), "是" if room_state.is_resolved else "否"),
        Text.assemble(("下一房间 ", "summary.label"), str(_format_next_nodes(room_state))),
    ]
    return Panel(Group(*lines), title="房间状态", box=PANEL_BOX, expand=False)


def render_event_body(room_state: RoomState, registry: ContentProviderPort) -> Panel:
    event_id = room_state.payload.get("event_id")
    if not isinstance(event_id, str):
        return Panel(Group(Text("-")), title="事件正文", box=PANEL_BOX, expand=False)
    event_def = registry.events().get(event_id)
    return Panel(Group(Text(event_def.text)), title="事件正文", box=PANEL_BOX, expand=False)


def render_event_result(room_state: RoomState) -> Panel | None:
    result = _format_event_result(room_state)
    if result is None:
        return None
    return Panel(Group(Text.assemble(("结果: ", "summary.label"), result)), title="结果", box=PANEL_BOX, expand=False)


def render_reward_panel(room_state: RoomState) -> Panel:
    return Panel(Group(*[Text(line) for line in _format_reward_lines(room_state.rewards)]), title="奖励", box=PANEL_BOX, expand=False)


def render_branch_selection_panel(room_state: RoomState) -> Panel:
    return Panel(Group(*[Text(line) for line in _format_next_room_menu(room_state)]), title="路径选择", box=PANEL_BOX, expand=False)


def render_non_combat_screen(
    *,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    registry: ContentProviderPort,
    menu_state: Any,
) -> RenderableType:
    summary = render_summary_panel(run_state=run_state, act_state=act_state, room_state=room_state, registry=registry)
    mode = _menu_mode(menu_state)
    body: list[RenderableType] = []

    if mode == "select_next_room":
        body.append(render_branch_selection_panel(room_state))
    elif room_state.room_type == "event":
        body.append(render_event_body(room_state, registry))
        result_panel = render_event_result(room_state)
        if result_panel is not None:
            body.append(result_panel)
        if room_state.rewards:
            body.append(render_reward_panel(room_state))
    elif room_state.is_resolved and room_state.rewards:
        body.append(render_reward_panel(room_state))
    else:
        body.append(render_default_body(room_state))

    if mode == "select_next_room":
        footer = render_menu(_format_next_room_menu(room_state))
    elif mode == "select_event_choice":
        footer = render_menu(_format_event_menu(room_state, registry))
    elif mode == "select_reward":
        footer = render_menu(_format_reward_menu(room_state))
    else:
        footer = render_menu(_format_default_menu(room_state))
    return build_standard_screen(summary=summary, body=Group(*body), footer=footer)
