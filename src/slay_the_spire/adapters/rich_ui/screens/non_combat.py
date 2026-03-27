from __future__ import annotations

from typing import Any

from rich.console import Group, RenderableType
from rich.cells import cell_len
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.rich_ui.inspect import (
    render_shared_potions_panel,
    render_shared_relics_panel,
    render_shared_stats_panel,
    render_reward_detail_panel,
)
from slay_the_spire.adapters.rich_ui.inspect_registry import format_shared_inspect_menu, render_shared_inspect_panel
from slay_the_spire.app.menu_definitions import (
    build_boss_relic_menu,
    build_boss_reward_menu,
    build_event_choice_menu,
    build_event_remove_menu,
    build_event_upgrade_menu,
    build_inspect_root_menu,
    build_leaf_menu,
    build_next_room_menu,
    build_reward_detail_menu,
    build_reward_list_menu,
    build_reward_root_menu,
    build_reward_menu,
    build_root_menu,
    build_rest_root_menu,
    build_rest_upgrade_menu,
    build_shop_remove_menu,
    build_shop_root_menu,
    build_terminal_phase_menu,
    format_menu_entries,
    format_menu_lines,
)
from slay_the_spire.adapters.rich_ui.screens.layout import build_standard_screen
from slay_the_spire.adapters.rich_ui.theme import PANEL_BOX
from slay_the_spire.adapters.rich_ui.widgets import render_card_name, render_menu
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

_MAP_ROOM_TYPE_LABELS = {
    "combat": "战斗",
    "elite": "精英",
    "boss": "Boss",
    "event": "事件",
    "shop": "商店",
    "rest": "休息",
}

_MAP_NODE_CELL_WIDTH = 8

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


def _format_reachable_node_summary(act_state: ActState, node_id: object) -> str:
    node = _node_lookup(act_state, node_id)
    if node is None:
        return _format_node_id(node_id)
    label = _MAP_ROOM_TYPE_LABELS.get(node.room_type, node.room_type)
    return f"[{label}] {node.node_id} ({node.row},{node.col})"


def _format_next_nodes(act_state: ActState, room_state: RoomState) -> str:
    next_node_ids = room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list) or not next_node_ids:
        return "-"
    return ", ".join(_format_node_choice(act_state, node_id) for node_id in next_node_ids)


def _format_card_instance_label(card_instance_id: str, registry: ContentProviderPort) -> Text:
    card_id = card_id_from_instance_id(card_instance_id)
    card_def = registry.cards().get(card_id)
    return Text.assemble(render_card_name(card_def), f" ({card_instance_id})")


def _reward_card_id(reward_name: str) -> str:
    if reward_name == "reward_strike":
        return "strike_plus"
    if reward_name == "reward_defend":
        return "defend_plus"
    return reward_name


def _format_reward_label(reward_id: str, registry: ContentProviderPort) -> str | Text:
    if reward_id.startswith("gold:"):
        return f"金币 +{reward_id.split(':', 1)[1]}"
    if reward_id.startswith("card_offer:"):
        reward_name = reward_id.split(":", 1)[1]
        card_def = registry.cards().get(_reward_card_id(reward_name))
        return Text.assemble("卡牌 ", render_card_name(card_def))
    if reward_id.startswith("card:"):
        reward_name = reward_id.split(":", 1)[1]
        card_def = registry.cards().get(_reward_card_id(reward_name))
        return Text.assemble("卡牌 ", render_card_name(card_def))
    if reward_id.startswith("event:"):
        result = reward_id.split(":", 1)[1]
        if result == "gain_upgrade":
            return "事件结果 获得升级"
        if result == "nothing":
            return "事件结果 什么也没有发生"
        return f"事件结果 {result}"
    return reward_id


def _format_reward_lines(rewards: list[str], registry: ContentProviderPort) -> list[str | Text]:
    if not rewards:
        return ["-"]
    lines: list[str | Text] = []
    for index, reward in enumerate(rewards, start=1):
        label = _format_reward_label(reward, registry)
        if isinstance(label, Text):
            lines.append(Text.assemble(f"{index}. ", label))
        else:
            lines.append(f"{index}. {label}")
    return lines


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


_DIR_TO_CHAR = {
    frozenset({"N", "S"}): "│",
    frozenset({"E", "W"}): "─",
    frozenset({"S", "E"}): "┌",
    frozenset({"S", "W"}): "┐",
    frozenset({"N", "E"}): "└",
    frozenset({"N", "W"}): "┘",
    frozenset({"N", "S", "E"}): "├",
    frozenset({"N", "S", "W"}): "┤",
    frozenset({"E", "W", "S"}): "┬",
    frozenset({"E", "W", "N"}): "┴",
    frozenset({"N", "S", "E", "W"}): "┼",
}

_DIR_VECTORS = {
    "N": (0, -1),
    "S": (0, 1),
    "E": (1, 0),
    "W": (-1, 0),
}

_OPPOSITE_DIR = {
    "N": "S",
    "S": "N",
    "E": "W",
    "W": "E",
}


def _node_token(act_state: ActState, node: ActNodeState) -> str:
    marker = _MAP_ROOM_TYPE_LABELS.get(node.room_type, node.room_type[:1].upper())
    if node.node_id == act_state.current_node_id:
        raw = f">{marker}<"
    elif node.node_id in act_state.reachable_node_ids:
        raw = f"[{marker}]"
    else:
        raw = f" {marker} "
    return _center_cell_text(raw, _MAP_NODE_CELL_WIDTH)


def _node_token_styles(act_state: ActState, node: ActNodeState) -> tuple[str, str]:
    if node.node_id == act_state.current_node_id:
        base_style = "map.node.current"
    elif node.node_id in act_state.reachable_node_ids:
        base_style = "map.node.reachable"
    else:
        base_style = "map.node.default"
    return base_style, f"map.room.{node.room_type}"


def _center_cell_text(text: str, width: int) -> str:
    padding = max(0, width - cell_len(text))
    left = padding // 2
    right = padding - left
    return f"{' ' * left}{text}{' ' * right}"


def _text_to_cells(text: str) -> list[str]:
    cells: list[str] = []
    for char in text:
        char_width = cell_len(char)
        cells.append(char)
        cells.extend("" for _ in range(max(0, char_width - 1)))
    return cells


def _cell_to_text_index(cells: list[str], cell_position: int) -> int:
    return sum(1 for cell in cells[:cell_position] if cell != "")


def _node_label_cell_range(act_state: ActState, node: ActNodeState) -> tuple[int, int]:
    label = _MAP_ROOM_TYPE_LABELS.get(node.room_type, node.room_type[:1].upper())
    if node.node_id == act_state.current_node_id or node.node_id in act_state.reachable_node_ids:
        raw = f"x{label}x"
        offset = 1
    else:
        raw = f" {label} "
        offset = 1
    left_pad = max(0, (_MAP_NODE_CELL_WIDTH - cell_len(raw)) // 2)
    start = left_pad + offset
    end = start + cell_len(label)
    return start, end


def _map_positions(act_state: ActState, *, col_spacing: int, row_spacing: int, margin_x: int) -> dict[str, tuple[int, int]]:
    last_row = max(node.row for node in act_state.nodes)
    return {
        node.node_id: (margin_x + (node.col * col_spacing), (last_row - node.row) * row_spacing)
        for node in act_state.nodes
    }


def _blank_direction_canvas(width: int, height: int) -> list[list[set[str]]]:
    return [[set() for _ in range(width)] for _ in range(height)]


def _add_step(canvas: list[list[set[str]]], x: int, y: int, direction: str) -> None:
    if 0 <= y < len(canvas) and 0 <= x < len(canvas[y]):
        canvas[y][x].add(direction)


def _add_segment(canvas: list[list[set[str]]], start: tuple[int, int], end: tuple[int, int]) -> None:
    x, y = start
    end_x, end_y = end
    if x != end_x and y != end_y:
        raise ValueError("segments must be orthogonal")
    if x == end_x and y == end_y:
        return
    if x == end_x:
        step = 1 if end_y > y else -1
        direction = "S" if step > 0 else "N"
        while y != end_y:
            next_y = y + step
            _add_step(canvas, x, y, direction)
            _add_step(canvas, x, next_y, _OPPOSITE_DIR[direction])
            y = next_y
        return
    step = 1 if end_x > x else -1
    direction = "E" if step > 0 else "W"
    while x != end_x:
        next_x = x + step
        _add_step(canvas, x, y, direction)
        _add_step(canvas, next_x, y, _OPPOSITE_DIR[direction])
        x = next_x


def _draw_edge(
    canvas: list[list[set[str]]],
    *,
    from_pos: tuple[int, int],
    to_pos: tuple[int, int],
) -> None:
    from_x, from_y = from_pos
    to_x, to_y = to_pos
    start = (from_x, from_y - 1)
    end = (to_x, to_y + 1)
    if from_x == to_x:
        _add_segment(canvas, start, end)
        return
    mid_y = (from_y + to_y) // 2
    _add_segment(canvas, start, (from_x, mid_y))
    _add_segment(canvas, (from_x, mid_y), (to_x, mid_y))
    _add_segment(canvas, (to_x, mid_y), end)


def _render_direction_canvas(direction_canvas: list[list[set[str]]]) -> list[list[str]]:
    rendered: list[list[str]] = []
    for row in direction_canvas:
        rendered.append([_DIR_TO_CHAR.get(frozenset(cell), " ") for cell in row])
    return rendered


def _metric_line(label: str, value: str) -> Text:
    return Text.assemble((label, "map.metric.label"), ("  ", "map.metric.sep"), (value, "map.metric.value"))


def _tip_line(message: str) -> Text:
    return Text.assemble(("TIP", "map.legend.label"), (" | ", "map.legend.sep"), (message, "map.legend.value"))


def _legend_line(label: str, entries: list[tuple[str, str, str | None]]) -> Text:
    line = Text()
    line.append(label, style="map.legend.label")
    line.append(" | ", style="map.legend.sep")
    for index, (marker, description, marker_style) in enumerate(entries):
        line.append(marker, style=marker_style or "map.legend.value")
        line.append(f"={description}", style="map.legend.value")
        if index < len(entries) - 1:
            line.append(" ", style="map.legend.sep")
    return line


def _type_legend_line() -> Text:
    line = Text()
    line.append("TYPE", style="map.legend.label")
    line.append(" | ", style="map.legend.sep")
    entries = [
        ("战斗", "map.room.combat"),
        ("精英", "map.room.elite"),
        ("Boss", "map.room.boss"),
        ("事件", "map.room.event"),
        ("商店", "map.room.shop"),
        ("休息", "map.room.rest"),
    ]
    for index, (name, style) in enumerate(entries):
        line.append(name, style=style)
        if index < len(entries) - 1:
            line.append(" ", style="map.legend.sep")
    return line


def _status_legend_line() -> Text:
    line = Text()
    line.append("STAT", style="map.legend.label")
    line.append(" | ", style="map.legend.sep")
    line.append(">当前<", style="map.node.current")
    line.append(" 所在 ", style="map.legend.value")
    line.append("[可达]", style="map.node.reachable")
    line.append(" 下一步 ", style="map.legend.value")
    line.append("节点", style="map.node.default")
    line.append(" 其他", style="map.legend.value")
    return line


def _full_map_lines(act_state: ActState) -> list[Text]:
    current_row, current_col = act_state.current_coord()
    row_numbers = sorted({node.row for node in act_state.nodes})
    next_nodes = ", ".join(_format_reachable_node_summary(act_state, node_id) for node_id in act_state.reachable_node_ids) or "-"
    total_cols = max(node.col for node in act_state.nodes) + 1
    col_spacing = 14
    row_spacing = 4
    margin_x = 6
    positions = _map_positions(act_state, col_spacing=col_spacing, row_spacing=row_spacing, margin_x=margin_x)
    grid_width = margin_x * 2 + max(1, total_cols - 1) * col_spacing + _MAP_NODE_CELL_WIDTH
    grid_height = max(row_numbers) * row_spacing + 1
    direction_canvas = _blank_direction_canvas(grid_width, grid_height)

    for node in act_state.nodes:
        from_pos = positions[node.node_id]
        for next_node_id in node.next_node_ids:
            _draw_edge(direction_canvas, from_pos=from_pos, to_pos=positions[next_node_id])

    rendered_canvas = [list(row) for row in _render_direction_canvas(direction_canvas)]
    for node in act_state.nodes:
        x, y = positions[node.node_id]
        token_cells = _text_to_cells(_node_token(act_state, node))
        start_x = x - (_MAP_NODE_CELL_WIDTH // 2)
        for offset, char in enumerate(token_cells):
            target_x = start_x + offset
            if 0 <= y < len(rendered_canvas) and 0 <= target_x < len(rendered_canvas[y]):
                rendered_canvas[y][target_x] = char

    lines: list[Text] = [
        _metric_line("POS", f"({current_row}, {current_col})"),
        _metric_line("ROW", f"L{row_numbers[0]:02d}..L{row_numbers[-1]:02d}"),
        _metric_line("NEXT", next_nodes),
        Text(""),
    ]

    last_row = max(row_numbers)
    for display_y, row_cells in enumerate(rendered_canvas):
        logical_row = last_row - (display_y // row_spacing)
        prefix = f"L{logical_row:02d} | " if display_y % row_spacing == 0 else "    | "
        body = "".join(row_cells)
        line = Text()
        line.append(prefix, style="map.ruler")
        if body:
            line.append(body, style="map.connector")
        for node in act_state.nodes:
            node_x, node_y = positions[node.node_id]
            if node_y != display_y:
                continue
            token_start_cell = node_x - (_MAP_NODE_CELL_WIDTH // 2)
            token_end_cell = token_start_cell + _MAP_NODE_CELL_WIDTH
            start = len(prefix) + _cell_to_text_index(row_cells, token_start_cell)
            end = len(prefix) + _cell_to_text_index(row_cells, token_end_cell)
            base_style, room_style = _node_token_styles(act_state, node)
            if start < end:
                line.stylize(base_style, start, end)

            label_start_cell, label_end_cell = _node_label_cell_range(act_state, node)
            label_start = len(prefix) + _cell_to_text_index(row_cells, token_start_cell + label_start_cell)
            label_end = len(prefix) + _cell_to_text_index(row_cells, token_start_cell + label_end_cell)
            if label_start < label_end:
                line.stylize(room_style, label_start, label_end)
        lines.append(line)

    lines.extend(
        [
            Text(""),
            _tip_line("只有 [可达] 节点可以作为下一步；线条只表示整张地图的连接关系。"),
            _type_legend_line(),
            _status_legend_line(),
        ]
    )
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


def _format_event_upgrade_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str | Text]:
    options = room_state.payload.get("upgrade_options", [])
    if not isinstance(options, list):
        options = []
    return format_menu_entries(
        build_event_upgrade_menu(
            options=[
                (f"upgrade_card:{card_instance_id}", _format_card_instance_label(card_instance_id, registry))
                for card_instance_id in options
            ]
        )
    )


def _format_event_remove_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str | Text]:
    candidates = room_state.payload.get("remove_candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    return format_menu_entries(
        build_event_remove_menu(
            options=[
                (f"remove_card:{card_instance_id}", _format_card_instance_label(card_instance_id, registry))
                for card_instance_id in candidates
            ]
        )
    )


def _format_reward_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str | Text]:
    return format_menu_entries(build_reward_menu(room_state=room_state, registry=registry))


def _format_reward_root_menu() -> list[str]:
    return format_menu_lines(build_reward_root_menu())


def _format_reward_list_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str | Text]:
    rewards = room_state.rewards if isinstance(room_state.rewards, list) else []
    return format_menu_entries(build_reward_list_menu(rewards, registry=registry))


def _format_reward_list_lines(room_state: RoomState, registry: ContentProviderPort) -> list[str | Text]:
    lines: list[str | Text] = ["当前可领取奖励:"]
    rewards = room_state.rewards if isinstance(room_state.rewards, list) else []
    if not rewards:
        lines.append("-")
        return lines
    for index, reward in enumerate(rewards, start=1):
        if isinstance(reward, str):
            label = _format_reward_label(reward, registry)
            if isinstance(label, Text):
                lines.append(Text.assemble(f"{index}. ", label))
            else:
                lines.append(f"{index}. {label}")
        else:
            lines.append(f"{index}. {reward}")
    return lines


def _format_reward_detail_menu(menu_state: Any) -> list[str]:
    reward_id = getattr(menu_state, "inspect_item_id", "")
    return format_menu_lines(build_reward_detail_menu(reward_id if isinstance(reward_id, str) else ""))


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
) -> list[str | Text]:
    mode = _menu_mode(menu_state)
    if mode == "inspect_reward_root":
        return _format_reward_root_menu()
    if mode == "inspect_reward_list":
        return _format_reward_list_menu(room_state, registry)
    if mode == "inspect_reward_detail":
        return _format_reward_detail_menu(menu_state)
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
    if mode == "inspect_reward_root":
        lines: list[str | Text] = ["当前可领取奖励:"]
        if not room_state.rewards:
            lines.append("-")
        else:
            for reward in room_state.rewards:
                if isinstance(reward, str):
                    label = _format_reward_label(reward, registry)
                    if isinstance(label, Text):
                        lines.append(Text.assemble("- ", label))
                    else:
                        lines.append(f"- {label}")
        lines.extend(["", "可先查看奖励详情，再决定是否领取。"])
        return Panel(Group(*[line if isinstance(line, Text) else Text(line) for line in lines]), title="奖励主页", box=PANEL_BOX, expand=False)
    if mode == "inspect_reward_list":
        lines = _format_reward_list_lines(room_state, registry)
        return Panel(
            Group(*[line if isinstance(line, Text) else Text(line) for line in lines]),
            title="奖励详情列表",
            box=PANEL_BOX,
            expand=False,
        )
    if mode == "inspect_reward_detail":
        reward_id = getattr(menu_state, "inspect_item_id", None)
        if isinstance(reward_id, str):
            return render_reward_detail_panel(reward_id, registry)
        return Panel(Group(Text("-")), title="奖励详情", box=PANEL_BOX, expand=False)
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


def _format_shop_root_menu(room_state: RoomState, registry: ContentProviderPort, run_state: RunState) -> list[str | Text]:
    return format_menu_entries(build_shop_root_menu(run_state=run_state, room_state=room_state, registry=registry))


def _format_shop_remove_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str | Text]:
    return format_menu_entries(build_shop_remove_menu(room_state=room_state, registry=registry))


def _format_rest_root_menu(room_state: RoomState, run_state: RunState) -> list[str]:
    return format_menu_lines(build_rest_root_menu(room_state=room_state, run_state=run_state))


def _format_rest_upgrade_menu(room_state: RoomState, registry: ContentProviderPort) -> list[str | Text]:
    return format_menu_entries(build_rest_upgrade_menu(room_state=room_state, registry=registry))


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
    return Panel(Group(*_full_map_lines(act_state)), title="完整地图", box=PANEL_BOX, expand=False)


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
            lines.append(Text.assemble("- ", _format_card_instance_label(option, registry)))
    if room_state.stage == "select_event_remove_card":
        lines.extend(["", "可移除卡牌:"])
        for option in room_state.payload.get("remove_candidates", []) if isinstance(room_state.payload.get("remove_candidates", []), list) else []:
            lines.append(Text.assemble("- ", _format_card_instance_label(option, registry)))
    body = [line if isinstance(line, Text) else Text(line) for line in lines]
    return Panel(Group(*body), title="事件正文", box=PANEL_BOX, expand=False)


def render_reward_panel(room_state: RoomState, registry: ContentProviderPort) -> Panel:
    body: list[RenderableType] = []
    event_result = _format_event_result(room_state) if room_state.room_type == "event" else None
    if event_result is not None:
        body.append(Text.assemble(("结果: ", "summary.label"), event_result))
    body.extend(line if isinstance(line, Text) else Text(line) for line in _format_reward_lines(room_state.rewards, registry))
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
    lines: list[RenderableType] = [Text(f"当前金币: {run_state.gold}"), Text(""), Text("卡牌商品:")]
    for offer in cards if isinstance(cards, list) else []:
        if isinstance(offer, dict):
            card_id = offer.get("card_id")
            card_name = render_card_name(registry.cards().get(card_id)) if isinstance(card_id, str) else Text(str(card_id))
            status = _shop_offer_status(
                price=offer.get("price"),
                sold=offer.get("sold") is True,
                current_gold=run_state.gold,
            )
            lines.append(Text.assemble("- ", card_name, f" / {offer.get('price')} 金币 [{status}]"))
    lines.append(Text(""))
    lines.append(Text("遗物商品:"))
    for offer in relics if isinstance(relics, list) else []:
        if isinstance(offer, dict):
            relic_id = offer.get("relic_id")
            relic_name = registry.relics().get(relic_id).name if isinstance(relic_id, str) else relic_id
            status = _shop_offer_status(
                price=offer.get("price"),
                sold=offer.get("sold") is True,
                current_gold=run_state.gold,
            )
            lines.append(Text(f"- {relic_name} / {offer.get('price')} 金币 [{status}]"))
    lines.append(Text(""))
    lines.append(Text("药水商品:"))
    for offer in potions if isinstance(potions, list) else []:
        if isinstance(offer, dict):
            potion_id = offer.get("potion_id")
            potion_name = registry.potions().get(potion_id).name if isinstance(potion_id, str) else potion_id
            status = _shop_offer_status(
                price=offer.get("price"),
                sold=offer.get("sold") is True,
                current_gold=run_state.gold,
            )
            lines.append(Text(f"- {potion_name} / {offer.get('price')} 金币 [{status}]"))
    lines.append(Text(""))
    remove_status = _remove_service_status(
        remove_used=room_state.payload.get("remove_used") is True,
        remove_price=remove_price,
        current_gold=run_state.gold,
    )
    lines.append(Text(f"删牌服务: {remove_price} 金币 [{remove_status}]"))
    return Panel(Group(*lines), title="商店", box=PANEL_BOX, expand=False)


def render_rest_panel(room_state: RoomState, registry: ContentProviderPort) -> Panel:
    if room_state.stage == "select_upgrade_card":
        options = room_state.payload.get("upgrade_options", [])
        lines: list[RenderableType] = [Text("可升级卡牌:")]
        for option in options if isinstance(options, list) else []:
            lines.append(Text.assemble("- ", _format_card_instance_label(option, registry)))
        return Panel(Group(*lines), title="休息点", box=PANEL_BOX, expand=False)
    lines: list[RenderableType] = [Text("可用动作:"), Text("- 休息"), Text("- 锻造")]
    return Panel(Group(*lines), title="休息点", box=PANEL_BOX, expand=False)


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
        footer = render_menu(_format_rest_root_menu(room_state, run_state))
    elif mode == "rest_upgrade_card":
        footer = render_menu(_format_rest_upgrade_menu(room_state, registry))
    else:
        footer = render_menu(_format_default_menu(room_state))
    return build_standard_screen(summary=summary, body=Group(*body), footer=footer)
