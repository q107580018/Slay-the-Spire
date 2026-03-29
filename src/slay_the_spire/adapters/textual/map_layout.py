"""Vertical Textual map layout helper.

Layout contract:
- Screen coordinates use terminal cells with ``x`` increasing to the right and ``y`` increasing downward.
- Act rows are rendered from bottom to top, so row 0 stays lowest on screen and later floors move upward.
- Layout must be deterministic for the same ActState input, regardless of node list order.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.cells import cell_len

if TYPE_CHECKING:
    from slay_the_spire.domain.models.act_state import ActNodeState, ActState

_NODE_W = 7
_NODE_H = 3
_ROW_SPACING = 6
_LANE_SPACING = 13
_MIN_NODE_GAP = 4
_MARGIN_X = 4
_MARGIN_Y = 2
_CHILD_SPREAD = 4

_NODE_ICONS: dict[str, str] = {
    "combat": "⚔",
    "elite": "💀",
    "boss": "👑",
    "event": "❓",
    "shop": "🛒",
    "rest": "🔥",
}

_NODE_LABELS: dict[str, str] = {
    "combat": "战斗",
    "elite": "精英",
    "boss": "Boss",
    "event": "事件",
    "shop": "商店",
    "rest": "休息",
}

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

_OPPOSITE_DIR = {
    "N": "S",
    "S": "N",
    "E": "W",
    "W": "E",
}


@dataclass(slots=True)
class VerticalMapLayout:
    node_positions: dict[str, tuple[int, int]]
    node_regions: dict[str, tuple[int, int, int, int]]
    canvas_lines: list[str]
    canvas_width: int
    canvas_height: int
    reachable_paths: list[tuple[str, ...]]


def _center(text: str, width: int) -> str:
    pad = max(0, width - cell_len(text))
    left = pad // 2
    right = pad - left
    return f"{' ' * left}{text}{' ' * right}"


def _node_lines(node: "ActNodeState") -> list[str]:
    icon = _NODE_ICONS.get(node.room_type, "?")
    label = _NODE_LABELS.get(node.room_type, node.room_type[:2])
    return [
        _center(icon, _NODE_W),
        _center(label, _NODE_W),
        " " * _NODE_W,
    ]


def _node_lookup(act_state: "ActState") -> dict[str, "ActNodeState"]:
    return {node.node_id: node for node in act_state.nodes}


def _reachable_node_ids(act_state: "ActState") -> set[str]:
    lookup = _node_lookup(act_state)
    if act_state.current_node_id not in lookup:
        return set()

    reachable: set[str] = set()
    stack = [act_state.current_node_id]
    while stack:
        node_id = stack.pop()
        if node_id in reachable:
            continue
        node = lookup.get(node_id)
        if node is None:
            continue
        reachable.add(node_id)
        stack.extend(node.next_node_ids)
    return reachable


def _rows_by_layer(nodes: list["ActNodeState"]) -> dict[int, list["ActNodeState"]]:
    rows: dict[int, list["ActNodeState"]] = {}
    for node in nodes:
        rows.setdefault(node.row, []).append(node)
    for row_nodes in rows.values():
        row_nodes.sort(key=lambda node: (node.col, node.node_id))
    return rows


def _parents_by_node(nodes: list["ActNodeState"]) -> dict[str, list[str]]:
    parents: dict[str, list[str]] = {}
    for node in nodes:
        for next_node_id in node.next_node_ids:
            parents.setdefault(next_node_id, []).append(node.node_id)
    return parents


def _child_slot_offset(slot_index: int, slot_count: int) -> int:
    centered = slot_index - (slot_count - 1) / 2
    return round(centered * _CHILD_SPREAD)


def _build_positions(act_state: "ActState", nodes: list["ActNodeState"]) -> dict[str, tuple[int, int]]:
    rows = _rows_by_layer(nodes)
    if not rows:
        return {}

    last_row = max(rows)
    parents = _parents_by_node(nodes)
    positions: dict[str, tuple[int, int]] = {}
    max_row_width = max(len(row_nodes) for row_nodes in rows.values())
    root_x = _MARGIN_X + (_NODE_W // 2) + ((_LANE_SPACING * max(0, max_row_width - 1)) // 2)

    for row in sorted(rows):
        row_nodes = rows[row]
        y = _MARGIN_Y + (last_row - row) * _ROW_SPACING
        if row == 0:
            x = root_x
            for node in row_nodes:
                positions[node.node_id] = (x, y)
                x += _LANE_SPACING
            continue

        preferred_positions: dict[str, float] = {}
        for node in row_nodes:
            incoming = parents.get(node.node_id, [])
            if incoming:
                contributions: list[float] = []
                for parent_id in incoming:
                    parent = act_state.get_node(parent_id)
                    child_ids = list(parent.next_node_ids)
                    if node.node_id not in child_ids:
                        continue
                    slot_index = child_ids.index(node.node_id)
                    parent_x = positions[parent_id][0]
                    contributions.append(parent_x + _child_slot_offset(slot_index, len(child_ids)))
                if contributions:
                    preferred_positions[node.node_id] = sum(contributions) / len(contributions)
                    continue
            preferred_positions[node.node_id] = _MARGIN_X + (node.col * _LANE_SPACING)

        prev_x: int | None = None
        for node in sorted(row_nodes, key=lambda item: (preferred_positions[item.node_id], item.col, item.node_id)):
            target_x = round(preferred_positions[node.node_id])
            if prev_x is None:
                x = max(target_x, _MARGIN_X + (_NODE_W // 2))
            else:
                x = max(target_x, prev_x + _NODE_W + _MIN_NODE_GAP)
            positions[node.node_id] = (x, y)
            prev_x = x

    return positions


def _blank_direction_canvas(width: int, height: int) -> list[list[set[str]]]:
    return [[set() for _ in range(width)] for _ in range(height)]


def _add_step(canvas: list[list[set[str]]], x: int, y: int, direction: str) -> None:
    if 0 <= y < len(canvas) and 0 <= x < len(canvas[y]):
        canvas[y][x].add(direction)


def _add_segment(canvas: list[list[set[str]]], start: tuple[int, int], end: tuple[int, int]) -> None:
    x1, y1 = start
    x2, y2 = end
    if x1 != x2 and y1 != y2:
        raise ValueError("segments must be orthogonal")
    if x1 == x2 and y1 == y2:
        return
    if x1 == x2:
        step = 1 if y2 > y1 else -1
        direction = "S" if step > 0 else "N"
        y = y1
        while y != y2:
            next_y = y + step
            _add_step(canvas, x1, y, direction)
            _add_step(canvas, x1, next_y, _OPPOSITE_DIR[direction])
            y = next_y
        return

    step = 1 if x2 > x1 else -1
    direction = "E" if step > 0 else "W"
    x = x1
    while x != x2:
        next_x = x + step
        _add_step(canvas, x, y1, direction)
        _add_step(canvas, next_x, y1, _OPPOSITE_DIR[direction])
        x = next_x


def _draw_edge(
    canvas: list[list[set[str]]],
    *,
    parent_pos: tuple[int, int],
    child_pos: tuple[int, int],
    slot_index: int,
    slot_count: int,
) -> None:
    parent_x, parent_y = parent_pos
    child_x, child_y = child_pos
    start_y = parent_y - (_NODE_H // 2)
    end_y = child_y + (_NODE_H // 2)
    if parent_x == child_x:
        _add_segment(canvas, (parent_x, start_y), (child_x, end_y))
        return

    bend_y = start_y - 1 - min(slot_index, max(0, slot_count - 1))
    if bend_y <= end_y:
        bend_y = (start_y + end_y) // 2
    bend_y = max(0, min(len(canvas) - 1, bend_y))
    _add_segment(canvas, (parent_x, start_y), (parent_x, bend_y))
    _add_segment(canvas, (parent_x, bend_y), (child_x, bend_y))
    _add_segment(canvas, (child_x, bend_y), (child_x, end_y))


def _render_direction_canvas(direction_canvas: list[list[set[str]]]) -> list[list[str]]:
    rendered: list[list[str]] = []
    for row in direction_canvas:
        rendered.append([_DIR_TO_CHAR.get(frozenset(cell), " ") for cell in row])
    return rendered


def _canvas_dimensions(positions: dict[str, tuple[int, int]], act_state: "ActState") -> tuple[int, int]:
    if not positions:
        return 20, 1
    last_row = max(node.row for node in act_state.nodes)
    max_x = max(center_x + (_NODE_W // 2) for center_x, _ in positions.values())
    canvas_width = max_x + _MARGIN_X + 1
    canvas_height = _MARGIN_Y + (last_row * _ROW_SPACING) + _NODE_H + _MARGIN_Y
    return canvas_width, canvas_height


def _render_paths(act_state: "ActState") -> list[tuple[str, ...]]:
    lookup = _node_lookup(act_state)
    if act_state.current_node_id not in lookup:
        return []

    paths: list[tuple[str, ...]] = []

    def dfs(node_id: str, path: list[str]) -> None:
        node = lookup[node_id]
        if not node.next_node_ids:
            paths.append(tuple(path))
            return
        for next_node_id in node.next_node_ids:
            if next_node_id not in lookup:
                continue
            dfs(next_node_id, path + [next_node_id])

    dfs(act_state.current_node_id, [act_state.current_node_id])
    return paths


def build_vertical_map_layout(act_state: "ActState") -> VerticalMapLayout:
    visible_node_ids = _reachable_node_ids(act_state)
    visible_nodes = [node for node in act_state.nodes if node.node_id in visible_node_ids]
    positions = _build_positions(act_state, visible_nodes)
    canvas_width, canvas_height = _canvas_dimensions(positions, act_state)
    direction_canvas = _blank_direction_canvas(canvas_width, canvas_height)

    for node in visible_nodes:
        parent_pos = positions[node.node_id]
        for slot_index, next_node_id in enumerate(node.next_node_ids):
            if next_node_id not in positions:
                continue
            _draw_edge(
                direction_canvas,
                parent_pos=parent_pos,
                child_pos=positions[next_node_id],
                slot_index=slot_index,
                slot_count=len(node.next_node_ids),
            )

    rendered_canvas = _render_direction_canvas(direction_canvas)
    node_regions: dict[str, tuple[int, int, int, int]] = {}
    for node in visible_nodes:
        cx, cy = positions[node.node_id]
        x0 = max(0, cx - (_NODE_W // 2))
        y0 = max(0, cy - (_NODE_H // 2))
        node_regions[node.node_id] = (x0, y0, _NODE_W, _NODE_H)
        lines = _node_lines(node)
        for row_offset, line in enumerate(lines):
            yy = y0 + row_offset
            if yy < 0 or yy >= canvas_height:
                continue
            for col_offset, ch in enumerate(line):
                xx = x0 + col_offset
                if 0 <= xx < canvas_width:
                    rendered_canvas[yy][xx] = ch

    canvas_lines = ["".join(row) for row in rendered_canvas]
    return VerticalMapLayout(
        node_positions=positions,
        node_regions=node_regions,
        canvas_lines=canvas_lines,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        reachable_paths=_render_paths(act_state),
    )
