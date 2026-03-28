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
_HOVER_BG = "grey50"
_HOVER_FG = "bright_white"
_CONNECTION_CHARS = set("│─├┤┬┴┼")


def _build_style_rows(act_state: "ActState", layout: VerticalMapLayout, hovered: str | None) -> list[list[Style]]:
    style_rows: list[list[Style]] = []
    for y, line in enumerate(layout.canvas_lines):
        row: list[Style] = [Style()] * len(line)
        for x, ch in enumerate(line):
            if ch in _CONNECTION_CHARS:
                row[x] = Style(color="grey42")
        for node in act_state.nodes:
            region = layout.node_regions.get(node.node_id)
            if region is None:
                continue
            rx, ry, rw, rh = region
            if not (ry <= y < ry + rh):
                continue
            if node.node_id == act_state.current_node_id:
                bg, fg = _CURRENT_BG, _CURRENT_FG
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
        self.show_horizontal_scrollbar = True
        self.show_vertical_scrollbar = True
        self._rebuild()

    def update_act(self, act_state: "ActState") -> None:
        self._act_state = act_state
        self._rebuild()
        self.refresh()
        self.call_after_refresh(self.center_on_current_node)

    def _rebuild(self) -> None:
        layout = build_vertical_map_layout(self._act_state)
        self._layout = layout
        self._canvas_lines = list(layout.canvas_lines)
        self._style_rows = _build_style_rows(self._act_state, layout, self._hovered)
        self._node_regions = dict(layout.node_regions)
        self._canvas_size = Size(layout.canvas_width, layout.canvas_height)
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
