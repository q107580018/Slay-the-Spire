"""MapWidget – Textual 自绘地图组件。"""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.cells import cell_len
from rich.style import Style
from rich.segment import Segment
from textual.geometry import Region, Size
from textual.message import Message
from textual.reactive import reactive
from textual.scroll_view import ScrollView
from textual.strip import Strip

if TYPE_CHECKING:
    from slay_the_spire.domain.models.act_state import ActNodeState, ActState

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

_NODE_COLORS: dict[str, str] = {
    "combat": "grey23",
    "elite": "dark_goldenrod",
    "boss": "dark_red",
    "event": "dark_cyan",
    "shop": "purple",
    "rest": "dark_green",
}

_CURRENT_BG   = "bright_cyan"
_CURRENT_FG   = "black"
_REACHABLE_BG = "steel_blue"
_REACHABLE_FG = "bright_white"
_HOVER_BG     = "grey50"
_HOVER_FG     = "bright_white"

_NODE_W      = 7
_NODE_H      = 3
_COL_SPACING = 12
_ROW_SPACING = 4
_MARGIN_X    = 6
_MARGIN_Y    = 2


def _center(text: str, width: int) -> str:
    clen = cell_len(text)
    pad = max(0, width - clen)
    return " " * (pad // 2) + text + " " * (pad - pad // 2)


def _stable_wobble(node_id: str) -> int:
    return (sum(ord(ch) for ch in node_id) % 5) - 2


def _display_anchor(node: "ActNodeState", *, last_row: int) -> tuple[int, int]:
    base_x = _MARGIN_X + node.col * _COL_SPACING
    x = base_x + _stable_wobble(node.node_id)
    y = _MARGIN_Y + (last_row - node.row) * _ROW_SPACING
    return x, y


def _safe_set(canvas: list[list[str]], y: int, x: int, ch: str) -> None:
    if 0 <= y < len(canvas) and 0 <= x < len(canvas[y]):
        canvas[y][x] = ch


def _edge_points(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    x1, y1 = start
    x2, y2 = end
    steps = max(abs(x2 - x1), abs(y2 - y1))
    if steps == 0:
        return [start]
    points: list[tuple[int, int]] = []
    for step in range(steps + 1):
        ratio = step / steps
        x = round(x1 + (x2 - x1) * ratio)
        y = round(y1 + (y2 - y1) * ratio)
        point = (x, y)
        if not points or points[-1] != point:
            points.append(point)
    return points


def _edge_glyph(previous: tuple[int, int], current: tuple[int, int]) -> str:
    dx = current[0] - previous[0]
    dy = current[1] - previous[1]
    if dx == 0:
        return "·"
    return "╱" if dx * dy < 0 else "╲"


def _draw_edge(
    canvas: list[list[str]], fx: int, fy: int, tx: int, ty: int
) -> None:
    box_half_h = 1
    start_y = fy - box_half_h
    end_y   = ty + box_half_h
    points = _edge_points((fx, start_y), (tx, end_y))
    for step, point in enumerate(points[1:], start=1):
        if step % 2 != 0:
            continue
        _safe_set(canvas, point[1], point[0], _edge_glyph(points[step - 1], point))


def _node_lines(
    node: "ActNodeState",
) -> list[str]:
    icon  = _NODE_ICONS.get(node.room_type, "?")
    label = _NODE_LABELS.get(node.room_type, node.room_type[:2])
    return [
        _center(icon, _NODE_W),
        _center(label, _NODE_W),
        " " * _NODE_W,
    ]


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
        self._canvas_lines: list[str] = []
        self._style_rows: list[list[Style]] = []
        self._node_regions: dict[str, tuple[int, int, int, int]] = {}
        self._canvas_size: Size = Size(0, 0)
        self.show_horizontal_scrollbar = True
        self.show_vertical_scrollbar = True
        self._rebuild()

    def update_act(self, act_state: "ActState") -> None:
        self._act_state = act_state
        self._rebuild()
        self.refresh()
        self.call_after_refresh(self.center_on_current_node)

    def _rebuild(self) -> None:
        act = self._act_state
        if not act.nodes:
            self._canvas_lines = ["  (地图为空)"]
            self._style_rows = [[]]
            self._canvas_size = Size(20, 1)
            self._node_regions = {}
            return

        last_row  = max(n.row for n in act.nodes)
        max_col   = max(n.col for n in act.nodes)
        max_wobble = 2
        canvas_w  = _MARGIN_X * 2 + max_col * _COL_SPACING + _NODE_W + max_wobble * 2 + 4
        canvas_h  = _MARGIN_Y * 2 + last_row * _ROW_SPACING + _NODE_H + 2

        raw: list[list[str]] = [[" "] * canvas_w for _ in range(canvas_h)]

        centers: dict[str, tuple[int, int]] = {
            n.node_id: _display_anchor(n, last_row=last_row) for n in act.nodes
        }

        for node in act.nodes:
            fx, fy = centers[node.node_id]
            for nid in node.next_node_ids:
                if nid in centers:
                    tx, ty = centers[nid]
                    _draw_edge(raw, fx, fy, tx, ty)

        self._node_regions = {}
        for node in act.nodes:
            cx, cy = centers[node.node_id]
            is_current   = node.node_id == act.current_node_id
            is_reachable = node.node_id in act.reachable_node_ids
            lines = _node_lines(node)
            bw, bh = _NODE_W, _NODE_H
            x0 = cx - bw // 2
            y0 = cy - bh // 2
            for ro, line in enumerate(lines):
                yy = y0 + ro
                if yy < 0 or yy >= canvas_h:
                    continue
                for co, ch in enumerate(line):
                    xx = x0 + co
                    if 0 <= xx < canvas_w:
                        raw[yy][xx] = ch
            self._node_regions[node.node_id] = (
                max(0, x0), max(0, y0), bw, bh
            )

        self._canvas_lines = ["".join(row) for row in raw]
        self._canvas_size  = Size(canvas_w, canvas_h)
        self.virtual_size = self._canvas_size

        conn_chars = set("·╱╲")
        conn_style = Style(color="grey42")
        self._style_rows = []
        for y, line in enumerate(self._canvas_lines):
            row: list[Style] = [Style()] * len(line)
            for x, ch in enumerate(line):
                if ch in conn_chars:
                    row[x] = conn_style
            for node in act.nodes:
                region = self._node_regions.get(node.node_id)
                if region is None:
                    continue
                rx, ry, rw, rh = region
                if not (ry <= y < ry + rh):
                    continue
                is_current   = node.node_id == act.current_node_id
                is_reachable = node.node_id in act.reachable_node_ids
                is_hovered   = node.node_id == self._hovered

                if is_current:
                    bg, fg = _CURRENT_BG, _CURRENT_FG
                elif is_hovered and is_reachable:
                    bg, fg = _HOVER_BG, _HOVER_FG
                elif is_reachable:
                    bg, fg = _REACHABLE_BG, _REACHABLE_FG
                else:
                    bg, fg = None, _NODE_COLORS.get(node.room_type, "white")

                ns = Style(color=fg, bgcolor=bg, bold=(is_current or is_reachable))
                for x in range(rx, min(rx + rw, len(row))):
                    row[x] = ns
            self._style_rows.append(row)

    def get_content_width(self, container: Size, viewport: Size) -> int:
        return self._canvas_size.width

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        del width
        return self._canvas_size.height

    def render_line(self, y: int) -> Strip:
        scroll_y = int(self.scroll_y)
        cy = y + scroll_y
        if cy < 0 or cy >= len(self._canvas_lines):
            return Strip([Segment(" " * self.size.width, Style())], self.size.width)
        line   = self._canvas_lines[cy]
        styles = self._style_rows[cy] if cy < len(self._style_rows) else []

        scroll_x = int(self.scroll_x)
        line   = line[scroll_x:]
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
