from __future__ import annotations

from typing import Any

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.terminal.inspect import (
    render_shared_potions_panel,
    render_shared_relics_panel,
    render_shared_stats_panel,
)
from slay_the_spire.adapters.terminal.inspect_registry import format_shared_inspect_menu, render_shared_inspect_panel
from slay_the_spire.app.menu_definitions import (
    build_boss_relic_menu,
    build_boss_reward_menu,
    build_event_choice_menu,
    build_event_remove_menu,
    build_event_upgrade_menu,
    build_inspect_root_menu,
    build_leaf_menu,
    build_next_room_menu,
    build_reward_menu,
    build_root_menu,
    build_rest_root_menu,
    build_rest_upgrade_menu,
    build_shop_remove_menu,
    build_shop_root_menu,
    build_terminal_phase_menu,
    format_menu_lines,
)
from slay_the_spire.adapters.terminal.screens.layout import build_standard_screen
from slay_the_spire.adapters.terminal.theme import PANEL_BOX
from slay_the_spire.adapters.terminal.widgets import render_menu
from slay_the_spire.domain.models.act_state import ActState, ActNodeState
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort

_ROOM_TYPE_LABELS = {
    "combat": "普通战斗",
    "elite": "精英战斗",
    "boss": "Boss战",
    "event": "事件",
    "shop": "商店",
    "rest": "休息点",
}

_ROOM_TYPE_MARKERS = {
    "combat": "战",
    "elite": "精",
    "boss": "王",
    "event": "事",
    "shop": "店",
    "rest": "休",
}

_STAGE_LABELS = {
    "waiting_input": "等待操作",
    "completed": "已完成",
    "defeated": "已失败",
    "select_remove_card": "选择删牌",
    "select_upgrade_card": "选择强化",
    "select_event_remove_card": "事件中选择删牌",
    "select_event_upgrade_card": "事件中选择强化",
}

_RUN_PHASE_LABELS = {
    "active": "进行中",
    "victory": "胜利",
    "game_over": "失败",
}


def _menu_mode(menu_state: Any) -> str:
    return str(getattr(menu_state, "mode", "root"))


def _format_node_id(node_id: object) -> str:
    if str(node_id) == "start":
        return "起点"
    return str(node_id)


def _node_lookup(act_state: ActState, node_id: object) -> ActNodeState | None:
    if not isinstance(node_id, str):
        return None
    try:
        return act_state.get_node(node_id)
    except KeyError:
        return None


def _format_node_choice(act_state: ActState, node_id: object) -> str:
    node = _node_lookup(act_state, node_id)
    if node is None:
        return _format_node_id(node_id)
    marker = _ROOM_TYPE_MARKERS.get(node.room_type, node.room_type[:1].upper())
    return f"{marker} {node.node_id} ({node.row},{node.col})"


def _format_next_nodes(act_state: ActState, room_state: RoomState) -> str:
    next_node_ids = room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list) or not next_node_ids:
        return "-"
    return ", ".join(_format_node_choice(act_state, node_id) for node_id in next_node_ids)


def _format_card_instance_label(card_instance_id: str, registry: ContentProviderPort) -> str:
    card_id = card_id_from_instance_id(card_instance_id)
    card_def = registry.cards().get(card_id)
    return f"{card_def.name} ({card_instance_id})"


def _reward_card_id(reward_name: str) -> str:
    if reward_name == "reward_strike":
        return "strike_plus"
    if reward_name == "reward_defend":
        return "defend_plus"
    return reward_name


def _format_reward_label(reward_id: str, registry: ContentProviderPort) -> str:
    if reward_id.startswith("gold:"):
        return f"金币 +{reward_id.split(':', 1)[1]}"
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


def _format_event_result(room_state: RoomState) -> str | None:
    result_text = room_state.payload.get("result_text")
    if isinstance(result_text, str):
        return result_text
    result = room_state.payload.get("result")
    if not isinstance(result, str):
        return None
    if result == "gain_upgrade":
        return "获得升级"
    if result == "nothing":
        return "什么也没有发生"
    return result


def _boss_rewards(room_state: RoomState) -> dict[str, object] | None:
    boss_rewards = room_state.payload.get("boss_rewards")
    if not isinstance(boss_rewards, dict):
        return None
    return boss_rewards


def _has_pending_boss_rewards(room_state: RoomState) -> bool:
    boss_rewards = _boss_rewards(room_state)
    if boss_rewards is None or room_state.room_type != "boss" or not room_state.is_resolved:
        return False
    claimed_relic_id = boss_rewards.get("claimed_relic_id")
    return not (boss_rewards.get("claimed_gold") is True and isinstance(claimed_relic_id, str) and bool(claimed_relic_id))


def _draw_conn(buf: list[str], from_col: int, to_col: int, cell_width: int) -> None:
    from_center = from_col * cell_width + cell_width // 2
    to_center = to_col * cell_width + cell_width // 2
    if from_col == to_col:
        if 0 <= from_center < len(buf):
            buf[from_center] = "|"
        return
    mid = (from_center + to_center) // 2
    if 0 <= mid < len(buf):
        buf[mid] = "/" if from_col < to_col else "\\"


def _full_map_lines(act_state: ActState) -> list[str]:
    current_row, current_col = act_state.current_coord()
    choice_indices = {node_id: index for index, node_id in enumerate(act_state.reachable_node_ids, start=1)}
    node_map = {(node.col, node.row): node for node in act_state.nodes}
    row_numbers = sorted({node.row for node in act_state.nodes})
    rows_by_number = {row_nodes[0].row: row_nodes for row_nodes in act_state.rows_for_display()}
    total_cols = max(node.col for node in act_state.nodes) + 1
    cell_width = 4
    grid_width = total_cols * cell_width

    lines = [
        f"当前坐标: ({current_row}, {current_col})",
        f"层范围: 第 {row_numbers[0]} 层 -> 第 {row_numbers[-1]} 层",
        "",
    ]

    for index in range(len(row_numbers) - 1, -1, -1):
        row_number = row_numbers[index]
        row_buf = list(" " * grid_width)
        annotation_buf = list(" " * grid_width)
        has_annotation = False

        for col in range(total_cols):
            node = node_map.get((col, row_number))
            if node is None:
                continue
            center = col * cell_width + cell_width // 2
            marker = _ROOM_TYPE_MARKERS.get(node.room_type, node.room_type[:1].upper())
            choice_idx = choice_indices.get(node.node_id)
            if node.node_id == act_state.current_node_id and center - 1 >= 0 and center + 1 < len(row_buf):
                row_buf[center - 1 : center + 2] = list(f"[{marker}]")
            else:
                row_buf[center] = marker
            if choice_idx is not None:
                label = f"[{choice_idx}]"
                start = max(0, center - 1)
                for offset, char in enumerate(label):
                    if start + offset < len(annotation_buf):
                        annotation_buf[start + offset] = char
                        has_annotation = True

        lines.append(f"第 {row_number} 层 | {''.join(row_buf).rstrip()}")
        if has_annotation:
            lines.append(f"       | {''.join(annotation_buf).rstrip()}")

        if index > 0:
            lower_row = row_numbers[index - 1]
            conn_buf = list(" " * grid_width)
            for node in rows_by_number[lower_row]:
                for next_node_id in node.next_node_ids:
                    child = act_state.get_node(next_node_id)
                    if child.row == row_number:
                        _draw_conn(conn_buf, node.col, child.col, cell_width)
            lines.append(f"       | {''.join(conn_buf).rstrip()}")

    legend = "图例: 战=战斗 精=精英 王=Boss 事=事件 店=商店 休=休息 [x]=当前 [n]=可选"
    lines.extend(["", legend])
    return lines


def _format_next_room_menu(act_state: ActState, room_state: RoomState) -> list[str]:
    next_node_ids = room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list):
        next_node_ids = []
    return format_menu_lines(
        build_next_room_menu(
            options=[(f"next_node:{node_id}", _format_node_choice(act_state, node_id)) for node_id in next_node_ids],
        )
    )


def _format_event_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str]:
    event_id = room_state.payload.get("event_id")
    if not isinstance(event_id, str):
        return format_menu_lines(build_event_choice_menu(options=[]))
    event_def = registry.events().get(event_id)
    return format_menu_lines(
        build_event_choice_menu(
            options=[(f"choice:{choice.get('id')}", str(choice.get("label"))) for choice in event_def.choices]
        )
    )


def _format_event_upgrade_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str]:
    options = room_state.payload.get("upgrade_options", [])
    if not isinstance(options, list):
        options = []
    return format_menu_lines(
        build_event_upgrade_menu(
            options=[
                (f"upgrade_card:{card_instance_id}", _format_card_instance_label(card_instance_id, registry))
                for card_instance_id in options
            ]
        )
    )


def _format_event_remove_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str]:
    candidates = room_state.payload.get("remove_candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    return format_menu_lines(
        build_event_remove_menu(
            options=[
                (f"remove_card:{card_instance_id}", _format_card_instance_label(card_instance_id, registry))
                for card_instance_id in candidates
            ]
        )
    )


def _format_reward_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str]:
    return format_menu_lines(build_reward_menu(room_state=room_state, registry=registry))


def _format_boss_reward_menu(room_state: RoomState) -> list[str]:
    boss_rewards = _boss_rewards(room_state) or {}
    return format_menu_lines(build_boss_reward_menu(boss_rewards))


def _format_boss_relic_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str]:
    boss_rewards = _boss_rewards(room_state) or {}
    relic_ids = boss_rewards.get("boss_relic_offers")
    if not isinstance(relic_ids, list):
        relic_ids = []
    return format_menu_lines(build_boss_relic_menu(relic_ids, registry=registry))


def format_non_combat_inspect_menu(
    run_state: RunState,
    room_state: RoomState,
    registry: ContentProviderPort,
    menu_state: Any,
) -> list[str]:
    mode = _menu_mode(menu_state)
    shared_menu = format_shared_inspect_menu(
        mode=mode,
        context="non_combat",
        run_state=run_state,
        room_state=room_state,
        registry=registry,
    )
    if shared_menu is not None:
        return shared_menu
    return _format_default_menu(room_state)


def render_non_combat_inspect_panel(
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    registry: ContentProviderPort,
    menu_state: Any,
) -> Panel:
    mode = _menu_mode(menu_state)
    shared_panel = render_shared_inspect_panel(
        mode=mode,
        context="non_combat",
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        registry=registry,
        card_instance_id=getattr(menu_state, "inspect_item_id", None),
    )
    if shared_panel is not None:
        return shared_panel
    lines = [
        "可查看共享资料页。",
        "包含属性、牌组、遗物和药水。",
    ]
    return Panel(Group(*[Text(line) for line in lines]), title="资料总览", box=PANEL_BOX, expand=False)


def _shop_offer_status(*, price: object, sold: bool, current_gold: int) -> str:
    if sold:
        return "已购买"
    if not isinstance(price, int) or current_gold < price:
        return "金币不足"
    return "可购买"


def _remove_service_status(*, remove_used: bool, remove_price: object, current_gold: int) -> str:
    if remove_used:
        return "已使用"
    if not isinstance(remove_price, int) or current_gold < remove_price:
        return "金币不足"
    return "可购买"


def _format_shop_root_menu(room_state: RoomState, registry: ContentProviderPort, run_state: RunState) -> list[str]:
    return format_menu_lines(build_shop_root_menu(run_state=run_state, room_state=room_state, registry=registry))


def _format_shop_remove_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str]:
    return format_menu_lines(build_shop_remove_menu(room_state=room_state, registry=registry))


def _format_rest_root_menu(room_state: RoomState) -> list[str]:
    return format_menu_lines(build_rest_root_menu(room_state=room_state))


def _format_rest_upgrade_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str]:
    return format_menu_lines(build_rest_upgrade_menu(room_state=room_state, registry=registry))


def _format_terminal_phase_menu(run_phase: str) -> list[str]:
    return format_menu_lines(build_terminal_phase_menu(run_phase=run_phase))


def _format_default_menu(room_state: RoomState) -> list[str]:
    return format_menu_lines(build_root_menu(room_state=room_state))


def render_summary_panel(
    *,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    registry: ContentProviderPort,
    run_phase: str,
) -> Panel:
    node_id = room_state.payload.get("node_id", act_state.current_node_id)
    room_kind = room_state.payload.get("room_kind", room_state.room_type)
    character_name = registry.characters().get(run_state.character_id).name
    act_name = registry.acts().get(act_state.act_id).name
    lines = [
        Text.assemble(("种子 ", "summary.label"), str(run_state.seed), f" (种子: {run_state.seed})"),
        Text.assemble(("角色 ", "summary.label"), (character_name, "player.name")),
        Text.assemble(("章节 ", "summary.label"), str(act_name), f" (章节: {act_name})"),
        Text.assemble(("房间 ", "summary.label"), _format_node_id(node_id), f" (房间: {_format_node_id(node_id)})"),
        Text.assemble(
            ("房间类型 ", "summary.label"),
            _ROOM_TYPE_LABELS.get(str(room_kind), str(room_kind)),
            f" (房间类型: {_ROOM_TYPE_LABELS.get(str(room_kind), str(room_kind))})",
        ),
        Text.assemble(("阶段 ", "summary.label"), _STAGE_LABELS.get(room_state.stage, room_state.stage)),
        Text.assemble(("运行阶段 ", "summary.label"), _RUN_PHASE_LABELS.get(run_phase, run_phase)),
        Text.assemble(("玩家生命 ", "summary.label"), f"{run_state.current_hp}/{run_state.max_hp}"),
        Text.assemble(("当前金币 ", "summary.label"), str(run_state.gold)),
        Text.assemble(("下一房间 ", "summary.label"), _format_next_nodes(act_state, room_state)),
    ]
    return Panel(Group(*lines), title="房间摘要", box=PANEL_BOX, expand=False)


def render_full_map_panel(act_state: ActState) -> Panel:
    return Panel(Group(*[Text(line) for line in _full_map_lines(act_state)]), title="完整地图", box=PANEL_BOX, expand=False)


def render_event_body(room_state: RoomState, registry: ContentProviderPort) -> Panel:
    event_id = room_state.payload.get("event_id")
    if not isinstance(event_id, str):
        return Panel(Group(Text("-")), title="事件正文", box=PANEL_BOX, expand=False)
    event_def = registry.events().get(event_id)
    lines = [event_def.text]
    result_text = room_state.payload.get("result_text")
    if isinstance(result_text, str):
        lines.extend(["", f"结果: {result_text}"])
    if room_state.stage == "select_event_upgrade_card":
        lines.extend(["", "可升级卡牌:"])
        for option in room_state.payload.get("upgrade_options", []) if isinstance(room_state.payload.get("upgrade_options", []), list) else []:
            lines.append(f"- {_format_card_instance_label(option, registry)}")
    if room_state.stage == "select_event_remove_card":
        lines.extend(["", "可移除卡牌:"])
        for option in room_state.payload.get("remove_candidates", []) if isinstance(room_state.payload.get("remove_candidates", []), list) else []:
            lines.append(f"- {_format_card_instance_label(option, registry)}")
    return Panel(Group(*[Text(line) for line in lines]), title="事件正文", box=PANEL_BOX, expand=False)


def render_reward_panel(room_state: RoomState, registry: ContentProviderPort) -> Panel:
    body: list[RenderableType] = []
    event_result = _format_event_result(room_state) if room_state.room_type == "event" else None
    if event_result is not None:
        body.append(Text.assemble(("结果: ", "summary.label"), event_result))
    body.extend(Text(line) for line in _format_reward_lines(room_state.rewards, registry))
    return Panel(Group(*body), title="奖励", box=PANEL_BOX, expand=False)


def render_boss_reward_panel(room_state: RoomState, registry: ContentProviderPort) -> Panel:
    boss_rewards = _boss_rewards(room_state) or {}
    gold_reward = boss_rewards.get("gold_reward")
    claimed_gold = boss_rewards.get("claimed_gold") is True
    claimed_relic_id = boss_rewards.get("claimed_relic_id")
    relic_ids = boss_rewards.get("boss_relic_offers")
    if not isinstance(relic_ids, list):
        relic_ids = []
    selected_relic_name = "-"
    if isinstance(claimed_relic_id, str) and claimed_relic_id:
        selected_relic_name = registry.relics().get(claimed_relic_id).name
    lines = [
        Text.assemble(("金币奖励：", "summary.label"), f"+{gold_reward}" if isinstance(gold_reward, int) and not isinstance(gold_reward, bool) else "-"),
        Text.assemble(("金币领取状态：", "summary.label"), "已领取" if claimed_gold else "未领取"),
        Text.assemble(("已选遗物：", "summary.label"), selected_relic_name),
        Text.assemble(("可选遗物数：", "summary.label"), str(len(relic_ids))),
    ]
    if relic_ids:
        lines.append(Text(""))
        lines.append(Text("可选遗物：", style="summary.label"))
        for relic_id in relic_ids:
            if isinstance(relic_id, str):
                lines.append(Text(f"- {registry.relics().get(relic_id).name}"))
    return Panel(Group(*lines), title="Boss奖励", box=PANEL_BOX, expand=False)


def render_shop_panel(room_state: RoomState, registry: ContentProviderPort, run_state: RunState) -> Panel:
    cards = room_state.payload.get("cards", [])
    relics = room_state.payload.get("relics", [])
    potions = room_state.payload.get("potions", [])
    remove_price = room_state.payload.get("remove_price", 75)
    lines = [f"当前金币: {run_state.gold}", "", "卡牌商品:"]
    for offer in cards if isinstance(cards, list) else []:
        if isinstance(offer, dict):
            card_id = offer.get("card_id")
            card_name = registry.cards().get(card_id).name if isinstance(card_id, str) else card_id
            status = _shop_offer_status(
                price=offer.get("price"),
                sold=offer.get("sold") is True,
                current_gold=run_state.gold,
            )
            lines.append(f"- {card_name} / {offer.get('price')} 金币 [{status}]")
    lines.append("")
    lines.append("遗物商品:")
    for offer in relics if isinstance(relics, list) else []:
        if isinstance(offer, dict):
            relic_id = offer.get("relic_id")
            relic_name = registry.relics().get(relic_id).name if isinstance(relic_id, str) else relic_id
            status = _shop_offer_status(
                price=offer.get("price"),
                sold=offer.get("sold") is True,
                current_gold=run_state.gold,
            )
            lines.append(f"- {relic_name} / {offer.get('price')} 金币 [{status}]")
    lines.append("")
    lines.append("药水商品:")
    for offer in potions if isinstance(potions, list) else []:
        if isinstance(offer, dict):
            potion_id = offer.get("potion_id")
            potion_name = registry.potions().get(potion_id).name if isinstance(potion_id, str) else potion_id
            status = _shop_offer_status(
                price=offer.get("price"),
                sold=offer.get("sold") is True,
                current_gold=run_state.gold,
            )
            lines.append(f"- {potion_name} / {offer.get('price')} 金币 [{status}]")
    lines.append("")
    remove_status = _remove_service_status(
        remove_used=room_state.payload.get("remove_used") is True,
        remove_price=remove_price,
        current_gold=run_state.gold,
    )
    lines.append(f"删牌服务: {remove_price} 金币 [{remove_status}]")
    return Panel(Group(*[Text(line) for line in lines]), title="商店", box=PANEL_BOX, expand=False)


def render_rest_panel(room_state: RoomState, registry: ContentProviderPort) -> Panel:
    if room_state.stage == "select_upgrade_card":
        options = room_state.payload.get("upgrade_options", [])
        lines = ["可升级卡牌:"]
        for option in options if isinstance(options, list) else []:
            lines.append(f"- {_format_card_instance_label(option, registry)}")
        return Panel(Group(*[Text(line) for line in lines]), title="休息点", box=PANEL_BOX, expand=False)
    lines = ["可用动作:", "- 休息", "- 锻造"]
    return Panel(Group(*[Text(line) for line in lines]), title="休息点", box=PANEL_BOX, expand=False)


def render_terminal_phase_panel(run_phase: str) -> Panel:
    title = "胜利" if run_phase == "victory" else "游戏结束"
    message = "首领已被击败，本轮冒险已完成。" if run_phase == "victory" else "玩家已倒下，本轮冒险结束。"
    return Panel(Group(Text(message)), title=title, box=PANEL_BOX, expand=False)


def render_non_combat_screen(
    *,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    registry: ContentProviderPort,
    menu_state: Any,
    run_phase: str,
) -> RenderableType:
    summary = render_summary_panel(
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        registry=registry,
        run_phase=run_phase,
    )
    mode = _menu_mode(menu_state)
    body: list[RenderableType] = [render_full_map_panel(act_state)]

    if run_phase != "active":
        body.append(render_terminal_phase_panel(run_phase))
    elif mode.startswith("inspect_"):
        body.append(render_non_combat_inspect_panel(run_state, act_state, room_state, registry, menu_state))
    elif mode == "select_next_room":
        body.append(Panel(Group(*[Text(line) for line in _format_next_room_menu(act_state, room_state)]), title="路径选择", box=PANEL_BOX, expand=False))
    elif room_state.room_type == "shop":
        body.append(render_shop_panel(room_state, registry, run_state))
    elif room_state.room_type == "rest":
        body.append(render_rest_panel(room_state, registry))
    elif mode in {"select_boss_reward", "select_boss_relic"} or _has_pending_boss_rewards(room_state):
        body.append(render_boss_reward_panel(room_state, registry))
    elif room_state.is_resolved and room_state.rewards:
        body.append(render_reward_panel(room_state, registry))
    elif room_state.room_type == "event":
        body.append(render_event_body(room_state, registry))
    else:
        body.append(Panel(Group(Text("等待下一步操作。")), title="房间状态", box=PANEL_BOX, expand=False))

    if run_phase != "active":
        footer = render_menu(_format_terminal_phase_menu(run_phase))
    elif mode.startswith("inspect_"):
        footer = render_menu(format_non_combat_inspect_menu(run_state, room_state, registry, menu_state))
    elif mode == "select_next_room":
        footer = render_menu(_format_next_room_menu(act_state, room_state))
    elif mode == "select_event_choice":
        footer = render_menu(_format_event_menu(room_state, registry))
    elif mode == "event_upgrade_card":
        footer = render_menu(_format_event_upgrade_menu(room_state, registry))
    elif mode == "event_remove_card":
        footer = render_menu(_format_event_remove_menu(room_state, registry))
    elif mode == "select_reward":
        footer = render_menu(_format_reward_menu(room_state, registry))
    elif mode == "select_boss_reward":
        footer = render_menu(_format_boss_reward_menu(room_state))
    elif mode == "select_boss_relic":
        footer = render_menu(_format_boss_relic_menu(room_state, registry))
    elif mode == "shop_root":
        footer = render_menu(_format_shop_root_menu(room_state, registry, run_state))
    elif mode == "shop_remove_card":
        footer = render_menu(_format_shop_remove_menu(room_state, registry))
    elif mode == "rest_root":
        footer = render_menu(_format_rest_root_menu(room_state))
    elif mode == "rest_upgrade_card":
        footer = render_menu(_format_rest_upgrade_menu(room_state, registry))
    else:
        footer = render_menu(_format_default_menu(room_state))
    return build_standard_screen(summary=summary, body=Group(*body), footer=footer)
