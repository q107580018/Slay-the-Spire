# Textual Map Original-Style Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `Textual` 模式下的地图重绘为更接近原版《Slay the Spire》的显示方式：自下往上阅读、图标加小字节点、稀疏虚线连线、浅色地图背景，同时保留现有点击、滚动和右侧菜单联动。

**Architecture:** 保持 `SessionState`、`ActState` 和右侧状态机不变，只在 `Textual` 适配层重做地图展示。核心改动集中在 `MapWidget`：引入稳定的展示坐标层、缩小节点视觉体积、替换连线算法和样式模型，并在 `SlayApp` 中补齐浅色地图容器与轻量悬停信息。

**Tech Stack:** Python 3.12, `uv`, `pytest`, `textual`, `rich`

---

### Task 1: 锁定原版风格地图的关键回归点

**Files:**
- Modify: `tests/adapters/textual/test_slay_app.py`
- Check: `src/slay_the_spire/adapters/textual/map_widget.py`
- Check: `src/slay_the_spire/adapters/textual/slay_app.py`

- [ ] **Step 1: Write the failing tests**

在 `tests/adapters/textual/test_slay_app.py` 追加最小断言，先把目标行为写死：

```python
def test_map_widget_uses_compact_node_regions() -> None:
    widget = MapWidget(start_session(seed=5).act_state)

    width_values = {region[2] for region in widget._node_regions.values()}
    height_values = {region[3] for region in widget._node_regions.values()}

    assert max(width_values) <= 7
    assert max(height_values) <= 3


def test_map_widget_centers_view_above_current_node() -> None:
    async def scenario() -> None:
        app = SlayApp(start_session(seed=5))
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            map_widget = app.query_one("#map-widget", MapWidget)
            assert map_widget.scroll_y >= 0
            assert map_widget.max_scroll_y > 0

    asyncio.run(scenario())
```

再补一条轻量结构测试，确保地图区样式不再依赖深色底：

```python
def test_textual_map_panel_declares_light_background_css() -> None:
    assert "#map-panel" in SlayApp.CSS
    assert "background:" in SlayApp.CSS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -q`

Expected:

- 节点热区尺寸断言失败（当前还是大方框）
- 或地图 CSS/视口定位断言失败

- [ ] **Step 3: Commit**

```bash
git add tests/adapters/textual/test_slay_app.py
git commit -m "test: lock textual original-style map regressions"
```

### Task 2: 建立稳定的展示坐标层和新视口定位

**Files:**
- Modify: `src/slay_the_spire/adapters/textual/map_widget.py`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Write the failing tests**

在 `tests/adapters/textual/test_slay_app.py` 补坐标与定位测试：

```python
def test_display_positions_are_stable_for_same_act_state() -> None:
    act_state = start_session(seed=5).act_state

    left = MapWidget(act_state)
    right = MapWidget(act_state)

    assert left._node_regions == right._node_regions


def test_current_node_region_is_not_centered_exactly() -> None:
    widget = MapWidget(start_session(seed=5).act_state)
    region = widget._current_node_region()

    assert region is not None
    assert region.height <= 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -q`

Expected: FAIL，因为当前实现仍是固定网格方框坐标和旧尺寸热区。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/adapters/textual/map_widget.py`：

- 提取展示布局 helper，例如：

```python
def _display_anchor(node: ActNodeState, *, last_row: int) -> tuple[int, int]:
    base_x = _MARGIN_X + node.col * _COL_SPACING
    wobble = _stable_wobble(node.node_id)
    x = base_x + wobble
    y = _MARGIN_Y + (last_row - node.row) * _ROW_SPACING
    return x, y
```

- 用稳定 hash / 字符串求和生成小范围横向偏移，保证同一节点每次重绘位置一致
- 调整 `center_on_current_node()`，从“严格 center”改成“当前节点靠下、上方留更多观察空间”的 region 滚动策略
- 根据新节点尺寸重算 `_canvas_size`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/textual/map_widget.py tests/adapters/textual/test_slay_app.py
git commit -m "refactor: add original-style map display coordinates"
```

### Task 3: 把节点从方框改成图标加小字

**Files:**
- Modify: `src/slay_the_spire/adapters/textual/map_widget.py`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Write the failing tests**

在 `tests/adapters/textual/test_slay_app.py` 增加节点内容测试：

```python
def test_map_widget_renders_icon_with_label_for_current_floor() -> None:
    widget = MapWidget(start_session(seed=5).act_state)

    canvas = "\n".join(widget._canvas_lines)
    assert "⚔" in canvas or "💀" in canvas or "👑" in canvas
    assert "战斗" in canvas or "精英" in canvas or "商店" in canvas
    assert "┌" not in canvas
    assert "╔" not in canvas
```

再补一条状态样式测试：

```python
def test_current_and_reachable_nodes_use_distinct_styles() -> None:
    widget = MapWidget(start_session(seed=5).act_state)

    styles = [style for row in widget._style_rows for style in row]
    assert any(style.bold for style in styles)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -q`

Expected: FAIL，因为当前 canvas 里还存在 box drawing 方框字符。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/adapters/textual/map_widget.py`：

- 删除 `_node_box_lines()` 这类方框拼装
- 改为紧凑节点绘制 helper，例如：

```python
def _node_lines(node: ActNodeState) -> list[str]:
    icon = _NODE_ICONS.get(node.room_type, "?")
    label = _NODE_LABELS.get(node.room_type, node.room_type[:2])
    return [icon, label]
```

- 将节点命中区域收缩为“图标 + 小字”的 2~3 行区域
- 状态样式从“整块背景色”改成：
  - 普通节点：类型颜色前景/轻描边
  - 当前节点：高亮背景或亮色 ring
  - 可达节点：次级高亮

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/textual/map_widget.py tests/adapters/textual/test_slay_app.py
git commit -m "feat: render textual map nodes as icon labels"
```

### Task 4: 用稀疏虚线路径替换直角连线

**Files:**
- Modify: `src/slay_the_spire/adapters/textual/map_widget.py`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Write the failing test**

在 `tests/adapters/textual/test_slay_app.py` 增加连线风格断言：

```python
def test_map_widget_avoids_boxy_edge_glyphs() -> None:
    widget = MapWidget(start_session(seed=5).act_state)

    canvas = "\n".join(widget._canvas_lines)
    assert "│" not in canvas
    assert "─" not in canvas
```

如果这个断言太严格，可以改成“连接字符集合不再只包含 `│─`”，例如检查存在 `/`, `\\`, `·` 之类的新路径字符。

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -q`

Expected: FAIL，因为当前边是纯直角线。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/adapters/textual/map_widget.py`：

- 删除 `_draw_vline()` / `_draw_hline()` 主导的直角路径拼接
- 引入更接近手绘路线的分段路径算法，例如：

```python
def _draw_dashed_path(canvas: list[list[str]], start: tuple[int, int], end: tuple[int, int]) -> None:
    for step, (x, y) in enumerate(_interpolate_points(start, end)):
        if step % 2 == 0:
            _safe_set(canvas, y, x, _path_glyph_for_step(...))
```

- 允许使用 `/`, `\\`, `⋅`, `·`, `╱`, `╲` 等字符逼近稀疏斜向虚线
- 更新连接字符样式集合，确保路径颜色单独控制

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/textual/map_widget.py tests/adapters/textual/test_slay_app.py
git commit -m "feat: render textual map edges as dashed paths"
```

### Task 5: 补齐地图面板样式与悬停联动

**Files:**
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
- Modify: `src/slay_the_spire/adapters/textual/map_widget.py`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Write the failing tests**

在 `tests/adapters/textual/test_slay_app.py` 增加两条回归：

```python
def test_textual_map_panel_css_uses_light_background() -> None:
    assert "#map-panel" in SlayApp.CSS
    assert "background:" in SlayApp.CSS


def test_textual_log_renderable_still_omits_footer_menu_after_map_polish() -> None:
    session = start_session(seed=5)
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None, theme=TERMINAL_THEME)

    console.print(_render_to_rich(session))

    assert "可选操作" not in buffer.getvalue()
```

如果 `Textual` 测试桩不适合精确模拟 hover，则至少锁定：

- `#map-panel` 存在浅色背景样式
- `_render_to_rich()` 仍不带 footer 菜单

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -q`

Expected: FAIL，直到 CSS 和轻量提示联动补齐。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/adapters/textual/slay_app.py`：

- 为 `#map-panel` 设置浅色纸面背景与更弱的边框
- 如实现悬停提示，则复用已有 `#action-summary`，不要新增独立输入/图例区域
- 确保右侧仍只有一份可点击菜单，不回退到重复 footer

如需要，在 `MapWidget` 增加一个轻量 hover message，例如：

```python
class NodeHovered(Message):
    def __init__(self, node_id: str | None) -> None:
        super().__init__()
        self.node_id = node_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/textual/slay_app.py src/slay_the_spire/adapters/textual/map_widget.py tests/adapters/textual/test_slay_app.py
git commit -m "feat: polish textual original-style map panel"
```

### Task 6: 做完整回归并手工验证 Textual 地图

**Files:**
- Check: `src/slay_the_spire/adapters/textual/map_widget.py`
- Check: `src/slay_the_spire/adapters/textual/slay_app.py`
- Check: `tests/adapters/textual/test_slay_app.py`
- Check: `tests/app/test_cli_textual.py`

- [ ] **Step 1: Run focused automated tests**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py tests/app/test_cli_textual.py -q`

Expected: PASS

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest -q`

Expected: PASS

- [ ] **Step 3: Do a manual smoke run**

Run: `uv run slay-the-spire --ui textual new --seed 5`

Manual checklist:

- 地图自下往上阅读
- 当前节点附近默认可见
- 节点是图标 + 小字，不再是方框
- 连线不再是直角流程图
- 鼠标仍能点击可达节点
- 右侧菜单不重复

- [ ] **Step 4: Commit**

```bash
git add src/slay_the_spire/adapters/textual/map_widget.py src/slay_the_spire/adapters/textual/slay_app.py tests/adapters/textual/test_slay_app.py tests/app/test_cli_textual.py
git commit -m "feat: restyle textual map to original-inspired layout"
```
