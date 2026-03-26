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

_NODE_COLORS: dict[str, tuple[str, str]] = {
    "combat":  ("grey23",         "white"),
    "elite":   ("dark_goldenrod", "bright_white"),
    "boss":    ("dark_red",       "bright_white"),
    "event":   ("dark_cyan",      "bright_white"),
    "shop":    ("purple",         "bright_white"),
    "rest":    ("dark_green",     "bright_white"),
}

_CURRENT_BG   = "bright_cyan"
_CURRENT_FG   = "black"
_REACHABLE_BG = "steel_blue"
_REACHABLE_FG = "bright_white"
_HOVER_BG     = "grey50"
_HOVER_FG     = "bright_white"

_NODE_W      = 8
_COL_SPACING = 14
_ROW_SPACING = 5
_MARGIN_X    = 5
_MARGIN_Y    = 1


def _center(text: str, width: int) -> str:
    clen = cell_len(text)
    pad = max(0, width - clen)
    return " " * (pad // 2) + text + " " * (pad - pad // 2)


def _node_center(node: "ActNodeState", last_row: int) -> tuple[int, int]:
    cx = _MARGIN_X + node.col * _COL_SPACING
    cy = _MARGIN_Y + (last_row - node.row) * _ROW_SPACING
    return cx, cy


def _safe_set(canvas: list[list[str]], y: int, x: int, ch: str) -> None:
    if 0 <= y < len(canvas) and 0 <= x < len(canvas[y]):
        canvas[y][x] = ch


def _draw_vline(canvas: list[list[str]], x: int, y1: int, y2: int) -> None:
    for y in range(min(y1, y2), max(y1, y2) + 1):
        _safe_set(canvas, y, x, "│")


def _draw_hline(canvas: list[list[str]], y: int, x1: int, x2: int) -> None:
    for x in range(min(x1, x2), max(x1, x2) + 1):
        _safe_set(canvas, y, x, "─")


def _draw_edge(
    canvas: list[list[str]], fx: int, fy: int, tx: int, ty: int
) -> None:
    box_half_h = 2
    start_y = fy - box_half_h
    end_y   = ty + box_half_h
    mid_y   = (start_y + end_y) // 2
    if fx == tx:
        _draw_vline(canvas, fx, end_y, start_y)
    else:
        _draw_vline(canvas, fx, mid_y, start_y)
        _draw_hline(canvas, mid_y, fx, tx)
        _draw_vline(canvas, tx, end_y, mid_y)


def _node_box_lines(
    node: "ActNodeState",
    *,
    is_current: bool,
    is_reachable: bool,
) -> list[str]:
    icon  = _NODE_ICONS.get(node.room_type, "?")
    label = _NODE_LABELS.get(node.room_type, node.room_type[:2])
    w = _NODE_W
    if is_current or is_reachable:
        tl, tr, bl, br, side, h = "╔", "╗", "╚", "╝", "║", "═"
        top    = tl + h * w + tr
        bottom = bl + h * w + br
    else:
        tl, tr, bl, br, side, h = "┌", "┐", "└", "┘", "│", "─"
        top    = tl + h * w + tr
        bottom = bl + h * w + br
    return [
        top,
        f"{side}{_center(icon,  w)}{side}",
        f"{side}{_center(label, w)}{side}",
        f"{side}{' ' * w}{side}",
        bottom,
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
        canvas_w  = _MARGIN_X * 2 + max_col * _COL_SPACING + _NODE_W + 4
        canvas_h  = _MARGIN_Y * 2 + last_row * _ROW_SPACING + 5

        raw: list[list[str]] = [[" "] * canvas_w for _ in range(canvas_h)]

        centers: dict[str, tuple[int, int]] = {
            n.node_id: _node_center(n, last_row) for n in act.nodes
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
            lines = _node_box_lines(node, is_current=is_current, is_reachable=is_reachable)
            bw, bh = _NODE_W + 2, 5
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

        conn_chars = set("─│╭╮╰╯┼┬┴├┤")
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
                    bg, fg = _NODE_COLORS.get(node.room_type, ("grey23", "white"))

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
        self.scroll_to_region(
            region,
            center=True,
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

    def on_click(self, event: object) -> None:
        from textual.events import Click
        if not isinstance(event, Click):
            return
        cx = event.x + int(self.scroll_x)
        cy = event.y + int(self.scroll_y)
        nid = self._hit_node(cx, cy)
        if nid and nid in self._act_state.reachable_node_ids:
            self.post_message(self.NodeSelected(nid))
