"""MapWidget – Textual 自绘地图组件。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.segment import Segment
from rich.style import Style
from textual.geometry import Region, Size
from textual.message import Message
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip

from slay_the_spire.adapters.textual.map_layout import VerticalMapLayout, build_vertical_map_layout

if TYPE_CHECKING:
    from slay_the_spire.domain.models.act_state import ActState

_CURRENT_BG = "bright_cyan"
_CURRENT_FG = "black"
_REACHABLE_BG = "steel_blue"
_REACHABLE_FG = "bright_white"
_REACHABLE_DIM_BG = "grey23"
_REACHABLE_DIM_FG = "grey85"
_ROUTE_ROOT_BG = "gold3"
_ROUTE_ROOT_FG = "black"
_ROUTE_CHAIN_BG = "dark_green"
_ROUTE_CHAIN_FG = "white"
_HOVER_BG = "grey50"
_HOVER_FG = "bright_white"
_NODE_H = 3
_CONNECTION_CHARS = set("│─├┤┬┴┼")


def _route_connection_cells(
    act_state: "ActState",
    layout: VerticalMapLayout,
    route_preview_node_ids: set[str],
) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    if not route_preview_node_ids:
        return cells

    def add_step(x: int, y: int) -> None:
        if 0 <= y < len(layout.canvas_lines) and 0 <= x < len(layout.canvas_lines[y]):
            cells.add((x, y))

    def add_segment(start: tuple[int, int], end: tuple[int, int]) -> None:
        x1, y1 = start
        x2, y2 = end
        if x1 != x2 and y1 != y2:
            raise ValueError("segments must be orthogonal")
        if x1 == x2 and y1 == y2:
            return
        if x1 == x2:
            step = 1 if y2 > y1 else -1
            y = y1
            while y != y2:
                next_y = y + step
                add_step(x1, y)
                add_step(x1, next_y)
                y = next_y
            return

        step = 1 if x2 > x1 else -1
        x = x1
        while x != x2:
            next_x = x + step
            add_step(x, y1)
            add_step(next_x, y1)
            x = next_x

    for node in act_state.nodes:
        if node.node_id not in route_preview_node_ids:
            continue
        parent_pos = layout.node_positions.get(node.node_id)
        if parent_pos is None:
            continue
        for next_node_id in node.next_node_ids:
            if next_node_id not in route_preview_node_ids:
                continue
            child_pos = layout.node_positions.get(next_node_id)
            if child_pos is None:
                continue
            parent_x, parent_y = parent_pos
            child_x, child_y = child_pos
            start_y = parent_y - (_NODE_H // 2)
            end_y = child_y + (_NODE_H // 2)
            slot_count = len(node.next_node_ids)
            slot_index = node.next_node_ids.index(next_node_id)
            if parent_x == child_x:
                add_segment((parent_x, start_y), (child_x, end_y))
                continue

            bend_y = start_y - 1 - min(slot_index, max(0, slot_count - 1))
            if bend_y <= end_y:
                bend_y = (start_y + end_y) // 2
            bend_y = max(0, min(len(layout.canvas_lines) - 1, bend_y))
            add_segment((parent_x, start_y), (parent_x, bend_y))
            add_segment((parent_x, bend_y), (child_x, bend_y))
            add_segment((child_x, bend_y), (child_x, end_y))
    return cells


def _build_style_rows(
    act_state: "ActState",
    layout: VerticalMapLayout,
    hovered: str | None,
    route_preview_root: str | None,
    route_preview_node_ids: set[str],
    route_connection_cells: set[tuple[int, int]],
) -> list[list[Style]]:
    style_rows: list[list[Style]] = []
    for y, line in enumerate(layout.canvas_lines):
        row: list[Style] = [Style()] * len(line)
        for x, ch in enumerate(line):
            if ch in _CONNECTION_CHARS:
                row[x] = Style(color="grey42")
                if (x, y) in route_connection_cells:
                    row[x] = Style(color="gold1", bold=True)
        for node in act_state.nodes:
            region = layout.node_regions.get(node.node_id)
            if region is None:
                continue
            rx, ry, rw, rh = region
            if not (ry <= y < ry + rh):
                continue
            if route_preview_root is not None and node.node_id == route_preview_root:
                bg, fg = _ROUTE_ROOT_BG, _ROUTE_ROOT_FG
            elif node.node_id in route_preview_node_ids:
                bg, fg = _ROUTE_CHAIN_BG, _ROUTE_CHAIN_FG
            elif node.node_id == act_state.current_node_id:
                bg, fg = _CURRENT_BG, _CURRENT_FG
            elif route_preview_root is not None and node.node_id in act_state.reachable_node_ids:
                bg, fg = _REACHABLE_DIM_BG, _REACHABLE_DIM_FG
            elif hovered == node.node_id and node.node_id in act_state.reachable_node_ids:
                bg, fg = _HOVER_BG, _HOVER_FG
            elif node.node_id in act_state.reachable_node_ids:
                bg, fg = _REACHABLE_BG, _REACHABLE_FG
            else:
                bg, fg = None, None
            if bg is None:
                continue
            ns = Style(color=fg, bgcolor=bg, bold=True)
            for x in range(rx, min(rx + rw, len(row))):
                row[x] = ns
        style_rows.append(row)
    return style_rows


def _reachable_descendants(act_state: "ActState", node_id: str) -> set[str]:
    lookup = {node.node_id: node for node in act_state.nodes}
    if node_id not in lookup:
        return set()

    reachable: set[str] = set()
    stack = [node_id]
    while stack:
        current = stack.pop()
        if current in reachable:
            continue
        node = lookup.get(current)
        if node is None:
            continue
        reachable.add(current)
        stack.extend(node.next_node_ids)
    return reachable


class MapWidget(ScrollView):
    """Textual 自绘地图 Widget，支持彩色节点、连线、悬停和点击。"""

    DEFAULT_CSS = """
    MapWidget {
        width: 1fr;
        height: 1fr;
        overflow-x: auto;
        overflow-y: auto;
    }
    """

    class NodeSelected(Message):
        def __init__(self, node_id: str) -> None:
            super().__init__()
            self.node_id = node_id

    class NodeHovered(Message):
        def __init__(self, node_id: str | None) -> None:
            super().__init__()
            self.node_id = node_id

    _hovered: reactive[str | None] = reactive(None, repaint=False)

    def __init__(self, act_state: "ActState", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._act_state = act_state
        self._layout = build_vertical_map_layout(act_state)
        self._canvas_lines: list[str] = []
        self._style_rows: list[list[Style]] = []
        self._node_regions: dict[str, tuple[int, int, int, int]] = {}
        self._canvas_size: Size = Size(0, 0)
        self._route_preview_enabled = True
        self._route_preview_override_root: str | None = None
        self._route_preview_root: str | None = None
        self._route_preview_node_ids: set[str] = set()
        self.show_horizontal_scrollbar = True
        self.show_vertical_scrollbar = True
        self._rebuild()

    def set_route_preview_enabled(self, enabled: bool) -> None:
        if self._route_preview_enabled == enabled:
            return
        self._route_preview_enabled = enabled
        if not enabled:
            self._route_preview_override_root = None
        self._rebuild()
        self.refresh()

    def set_route_preview_root(self, node_id: str | None) -> None:
        if not self._route_preview_enabled:
            self._route_preview_override_root = None
            return
        if self._route_preview_override_root == node_id:
            return
        self._route_preview_override_root = node_id
        self._rebuild()
        self.refresh()

    def _refresh_route_preview(self) -> None:
        if not self._route_preview_enabled:
            self._route_preview_root = None
            self._route_preview_node_ids = set()
            return
        preview_root = self._route_preview_override_root if self._route_preview_override_root is not None else self._hovered
        if preview_root is None:
            self._route_preview_root = None
            self._route_preview_node_ids = set()
            return
        if preview_root not in self._act_state.reachable_node_ids and preview_root != self._act_state.current_node_id:
            self._route_preview_root = None
            self._route_preview_node_ids = set()
            return
        self._route_preview_root = preview_root
        self._route_preview_node_ids = _reachable_descendants(self._act_state, preview_root)

    def update_act(self, act_state: "ActState") -> None:
        self._act_state = act_state
        self._rebuild()
        self.refresh()
        self.call_after_refresh(self.center_on_current_node)

    def _rebuild(self) -> None:
        layout = build_vertical_map_layout(self._act_state)
        self._layout = layout
        self._canvas_lines = list(layout.canvas_lines)
        self._node_regions = dict(layout.node_regions)
        self._canvas_size = Size(layout.canvas_width, layout.canvas_height)
        self._refresh_route_preview()
        route_connection_cells = _route_connection_cells(self._act_state, layout, self._route_preview_node_ids)
        self._style_rows = _build_style_rows(
            self._act_state,
            layout,
            self._hovered,
            self._route_preview_root,
            self._route_preview_node_ids,
            route_connection_cells,
        )
        self.virtual_size = self._canvas_size

    def get_content_width(self, container: Size, viewport: Size) -> int:
        del container, viewport
        return self._canvas_size.width

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        del container, viewport, width
        return self._canvas_size.height

    def render_line(self, y: int) -> Strip:
        scroll_y = int(self.scroll_y)
        cy = y + scroll_y
        if cy < 0 or cy >= len(self._canvas_lines):
            return Strip([Segment(" " * self.size.width, Style())], self.size.width)

        line = self._canvas_lines[cy]
        styles = self._style_rows[cy] if cy < len(self._style_rows) else []

        scroll_x = int(self.scroll_x)
        line = line[scroll_x:]
        styles = styles[scroll_x:]

        if not styles:
            return Strip([Segment(line, Style())])

        segs: list[Segment] = []
        cur_st = styles[0]
        buf = ""
        for i, ch in enumerate(line):
            st = styles[i] if i < len(styles) else Style()
            if st == cur_st:
                buf += ch
            else:
                if buf:
                    segs.append(Segment(buf, cur_st))
                buf = ch
                cur_st = st
        if buf:
            segs.append(Segment(buf, cur_st))
        return Strip(segs)

    def _hit_node(self, cx: int, cy: int) -> str | None:
        for nid, (rx, ry, rw, rh) in self._node_regions.items():
            if rx <= cx < rx + rw and ry <= cy < ry + rh:
                return nid
        return None

    def _current_node_region(self) -> Region | None:
        current_node_id = self._act_state.current_node_id
        region_data = self._node_regions.get(current_node_id)
        if region_data is None:
            return None
        x, y, width, height = region_data
        return Region(x=x, y=y, width=width, height=height)

    def center_on_current_node(self) -> None:
        region = self._current_node_region()
        if region is None:
            return
        target_y = max(0, region.y - max(2, self.size.height // 3))
        target_x = max(0, region.x - max(0, (self.size.width - region.width) // 2))
        self.scroll_to_region(
            Region(x=target_x, y=target_y, width=region.width, height=region.height),
            center=False,
            force=True,
            animate=False,
            immediate=True,
        )

    def on_mount(self) -> None:
        self.call_after_refresh(self.center_on_current_node)

    def on_mouse_move(self, event: object) -> None:
        from textual.events import MouseMove

        if not isinstance(event, MouseMove):
            return
        cx = event.x + int(self.scroll_x)
        cy = event.y + int(self.scroll_y)
        hovered = self._hit_node(cx, cy)
        if hovered != self._hovered:
            self._hovered = hovered
            self._rebuild()
            self.refresh()
            self.post_message(self.NodeHovered(hovered))

    def on_leave(self) -> None:
        if self._hovered is None:
            return
        self._hovered = None
        self._rebuild()
        self.refresh()
        self.post_message(self.NodeHovered(None))

    def on_click(self, event: object) -> None:
        from textual.events import Click

        if not isinstance(event, Click):
            return
        cx = event.x + int(self.scroll_x)
        cy = event.y + int(self.scroll_y)
        nid = self._hit_node(cx, cy)
        if nid and nid in self._act_state.reachable_node_ids:
            self.post_message(self.NodeSelected(nid))
