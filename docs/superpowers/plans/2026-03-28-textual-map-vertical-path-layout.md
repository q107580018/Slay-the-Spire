# Textual Map Vertical Path Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the left Textual map as a vertical path layout that clearly exposes each reachable branch from the start node down to the end of the act.

**Architecture:** Keep the domain map graph unchanged. Add a small Textual-local layout helper that computes stable display lanes, routes edges through terminal-friendly channels, and returns canvas metadata for hit testing. Refactor `MapWidget` to consume that helper and render a denser vertical path map with the existing hover/click/scroll behavior preserved.

**Tech Stack:** Python 3.12, `textual`, `rich`, `pytest`, `uv`

**Hard constraints:**
- Only files under `src/slay_the_spire/adapters/textual/*` and `tests/adapters/textual/*` may change for this feature.
- Do not touch `src/slay_the_spire/domain/*` or `src/slay_the_spire/adapters/rich_ui/*`.
- Avoid changing `src/slay_the_spire/adapters/textual/slay_app.py` unless the widget cannot function without a one-line mount or sizing fix.
- Keep the layout helper deterministic and independent of viewport size or refresh timing.

---

### Task 1: Add a pure Textual map layout helper

**Files:**
- Create: `src/slay_the_spire/adapters/textual/map_layout.py`
- Create: `tests/adapters/textual/test_map_layout.py`

- [ ] **Step 1: Write the failing test**

```python
from slay_the_spire.adapters.textual.map_layout import build_vertical_map_layout
from slay_the_spire.domain.models.act_state import ActNodeState, ActState


def test_vertical_layout_assigns_stable_lanes_and_routes_branches():
    act_state = ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=["r1c0", "r1c1"]),
            ActNodeState(node_id="r1c0", row=1, col=0, room_type="event", next_node_ids=["r2c0"]),
            ActNodeState(node_id="r1c1", row=1, col=1, room_type="shop", next_node_ids=["r2c0"]),
            ActNodeState(node_id="r2c0", row=2, col=0, room_type="boss", next_node_ids=[]),
        ],
        visited_node_ids=["start"],
    )
    layout = build_vertical_map_layout(act_state)

    assert layout.canvas_width > 0
    assert layout.canvas_height > 0
    assert layout.node_positions["start"][1] > layout.node_positions["r1c0"][1]
    assert layout.node_positions["r1c0"][0] != layout.node_positions["r1c1"][0]
    assert layout.canvas_lines
    assert layout.node_regions["start"][2] > 0
    assert layout.node_regions["start"][3] > 0


def test_vertical_layout_is_stable_for_same_input_and_input_order():
    first = build_vertical_map_layout(act_state)
    second = build_vertical_map_layout(act_state)
    shuffled = ActState(
        act_id=act_state.act_id,
        current_node_id=act_state.current_node_id,
        nodes=list(reversed(act_state.nodes)),
        visited_node_ids=list(act_state.visited_node_ids),
    )
    shuffled_layout = build_vertical_map_layout(shuffled)

    assert first.node_positions == second.node_positions
    assert first.node_regions == second.node_regions
    assert first.canvas_lines == second.canvas_lines
    assert first.node_positions == shuffled_layout.node_positions
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/adapters/textual/test_map_layout.py -v`

Expected: FAIL because `build_vertical_map_layout` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement `build_vertical_map_layout(act_state)` plus a small `VerticalMapLayout` dataclass with explicit, stable coordinates. The helper should return:

- `node_positions`
- `node_regions`
- `canvas_lines`
- `canvas_width`
- `canvas_height`
- enough route metadata for the widget to build its own styles and hit testing

Coordinate contract:

- `node_positions[node_id] == (x, y)` uses terminal cell coordinates
- `node_regions[node_id] == (x, y, width, height)` uses the rendered node bounding box
- `canvas_lines` is the raw character canvas before Textual styling
- the helper must be deterministic for identical `ActState` input
- screen `y` decreases as `row` increases, so the start node remains lower on screen and later floors move upward toward the boss

Keep the helper pure and deterministic. It should not touch Textual widgets directly.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/adapters/textual/test_map_layout.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/textual/map_layout.py tests/adapters/textual/test_map_layout.py
git commit -m "feat(textual): add vertical map layout helper"
```

### Task 2: Refactor MapWidget to use the new layout helper

**Files:**
- Modify: `src/slay_the_spire/adapters/textual/map_widget.py`
- Modify: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Write the failing test**

Add or adjust focused tests in `tests/adapters/textual/test_slay_app.py` that assert:

- the widget still exposes scrollbars
- the widget still centers around the current node
- the widget canvas contains vertical-path connector glyphs such as `│`, `╱`, `╲`, or junction characters such as `├`, `┤`, `┼`
- node glyphs are not overwritten by connector glyphs
- current and reachable nodes remain styled distinctly

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -v -k "test_map_widget or test_map_initially_scrolls_toward_current_node or test_current_and_reachable_nodes_use_distinct_styles"`

Expected: FAIL on the old widget behavior.

- [ ] **Step 3: Write minimal implementation**

Replace the ad hoc grid drawing in `MapWidget` with the new helper output. Preserve:

- `update_act()`
- hover messages
- click selection
- automatic centering
- scrollbar behavior

Make sure the widget still builds `_canvas_lines`, `_style_rows`, `_node_regions`, and `virtual_size` from the helper result.

Add one precise regression check for centering, using the current node region and the widget scroll offsets rather than a visual-only assertion.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -v -k "map_widget or map_initially_scrolls_toward_current_node or current_and_reachable_nodes_use_distinct_styles"`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/textual/map_widget.py tests/adapters/textual/test_slay_app.py
git commit -m "feat(textual): render vertical path map"
```

### Task 3: Full verification

**Files:**
- No new files expected

- [ ] **Step 1: Run the focused map suite**

Run: `uv run pytest tests/adapters/textual/test_map_layout.py tests/adapters/textual/test_slay_app.py -v`

Expected: PASS.

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest`

Expected: PASS, or only pre-existing unrelated failures.

- [ ] **Step 3: Commit any final fixes**

If any final regression fix was needed during verification, commit it with a message that describes the user-visible map layout change.
