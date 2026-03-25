# Inspect Menus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为终端版《Slay the Spire》补齐统一的“查看资料”入口，让玩家可在非战斗和战斗中查看属性、牌组、遗物、药水，以及战斗堆区和敌人详情，并能进入卡牌/遗物/药水/敌人的详情页。

**Architecture:** 继续沿用当前 `MenuState.mode -> route_menu_choice() -> render_room()` 的编号菜单架构，不引入自由文本命令。将 inspect 信息格式化抽到终端层专用 helper，避免把玩家文案塞进 domain；`session.py` 只负责 inspect 状态切换，`combat.py` 和 `non_combat.py` 负责各自场景的 inspect 页面排版。

**Tech Stack:** Python 3.12, `rich`, `pytest`, `uv`, existing session/router architecture, `StarterContentProvider`

---

## Planned File Changes

- Modify: `src/slay_the_spire/app/session.py`
- Create: `src/slay_the_spire/adapters/terminal/inspect.py`
- Modify: `src/slay_the_spire/adapters/terminal/screens/combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/widgets.py`
- Create: `tests/app/test_inspect_menus.py`
- Create: `tests/adapters/terminal/test_inspect.py`
- Modify: `tests/adapters/terminal/test_widgets.py`
- Modify: `tests/e2e/test_single_act_smoke.py`
- Modify: `tests/use_cases/test_room_recovery.py`

## Implementation Notes

- 全程遵循 `@superpowers/test-driven-development`：先写失败测试，再写最小实现。
- 完成前执行 `@superpowers/verification-before-completion` 的验证思路，至少跑本计划列出的测试命令。
- 新增玩家可见文案默认写中文。
- inspect 详情的“效果说明”优先使用现有结构化字段转中文，不直接暴露原始 effect JSON。

### Task 1: Add inspect menu state and routing

**Files:**
- Modify: `src/slay_the_spire/app/session.py`
- Test: `tests/app/test_inspect_menus.py`

- [ ] **Step 1: Write the failing routing tests**

```python
def test_combat_root_menu_can_enter_inspect_root() -> None:
    session = start_session(seed=5)

    running, next_session, message = route_menu_choice("4", session=session)

    assert running is True
    assert next_session.menu_state.mode == "inspect_root"
    assert "资料总览" in message


def test_inspect_root_can_open_deck_and_return() -> None:
    session = replace(start_session(seed=5), menu_state=MenuState(mode="inspect_root"))

    _running, deck_session, deck_message = route_menu_choice("2", session=session)
    _running, back_session, back_message = route_menu_choice(str(len(deck_session.run_state.deck) + 1), session=deck_session)

    assert deck_session.menu_state.mode == "inspect_deck"
    assert "牌组列表" in deck_message
    assert back_session.menu_state.mode == "inspect_root"
    assert "资料总览" in back_message
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/app/test_inspect_menus.py -v`
Expected: FAIL because inspect routes and/or test file do not exist yet.

- [ ] **Step 3: Write minimal routing implementation**

```python
@dataclass(slots=True)
class MenuState:
    mode: str = "root"
    selected_card_instance_id: str | None = None
    inspect_item_id: str | None = None
    inspect_parent_mode: str | None = None


def _route_inspect_root_menu(choice: str, session: SessionState) -> tuple[bool, SessionState, str]:
    if choice == "1":
        next_session = replace(session, menu_state=MenuState(mode="inspect_stats"))
        return True, next_session, render_session(next_session)
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/app/test_inspect_menus.py -v`
Expected: PASS for new inspect entry and back-navigation tests.

- [ ] **Step 5: Commit**

```bash
git add tests/app/test_inspect_menus.py src/slay_the_spire/app/session.py
git commit -m "feat: add inspect menu routing"
```

### Task 2: Add inspect-specific formatting helpers

**Files:**
- Create: `src/slay_the_spire/adapters/terminal/inspect.py`
- Modify: `src/slay_the_spire/adapters/terminal/widgets.py`
- Test: `tests/adapters/terminal/test_inspect.py`

- [ ] **Step 1: Write the failing formatting tests**

```python
def test_format_card_detail_lines_include_cost_effects_and_upgrade() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    lines = format_card_detail_lines("bash#1", registry)

    assert any("费用" in line.plain for line in lines)
    assert any("造成 8 伤害" in line.plain for line in lines)
    assert any("施加 2 易伤" in line.plain for line in lines)


def test_format_relic_detail_lines_include_passive_effect_description() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    lines = format_relic_detail_lines("burning_blood", registry)

    assert any("燃烧之血" in line.plain for line in lines)
    assert any("回复 6 点生命" in line.plain for line in lines)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/adapters/terminal/test_inspect.py -v`
Expected: FAIL because inspect formatting helpers do not exist.

- [ ] **Step 3: Write minimal formatting implementation**

```python
def format_card_detail_lines(card_instance_id: str, registry: ContentProviderPort) -> list[Text]:
    card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
    lines = [
        Text.assemble(("名称 ", "summary.label"), card_def.name),
        Text.assemble(("实例 ", "summary.label"), card_instance_id),
        Text.assemble(("费用 ", "summary.label"), _format_card_cost(card_def)),
        Text.assemble(("效果 ", "summary.label"), summarize_card_effects(card_def.effects)),
    ]
    if card_def.upgrades_to is not None:
        upgraded = registry.cards().get(card_def.upgrades_to)
        lines.append(Text.assemble(("升级为 ", "summary.label"), upgraded.name))
    return lines
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/adapters/terminal/test_inspect.py -v`
Expected: PASS with human-readable Chinese detail lines.

- [ ] **Step 5: Commit**

```bash
git add tests/adapters/terminal/test_inspect.py src/slay_the_spire/adapters/terminal/inspect.py src/slay_the_spire/adapters/terminal/widgets.py
git commit -m "feat: add inspect detail formatters"
```

### Task 3: Render non-combat inspect pages

**Files:**
- Modify: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`
- Modify: `src/slay_the_spire/app/session.py`
- Test: `tests/adapters/terminal/test_inspect.py`
- Test: `tests/app/test_inspect_menus.py`

- [ ] **Step 1: Write the failing non-combat render tests**

```python
def test_render_non_combat_inspect_root_shows_shared_sections() -> None:
    session = start_session(seed=5)
    session = replace(session, menu_state=MenuState(mode="inspect_root"))

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=session.menu_state,
    )

    assert "资料总览" in output
    assert "1. 属性" in output
    assert "2. 牌组" in output
    assert "3. 遗物" in output
    assert "4. 药水" in output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/adapters/terminal/test_inspect.py::test_render_non_combat_inspect_root_shows_shared_sections -v`
Expected: FAIL because non-combat screen does not understand inspect modes yet.

- [ ] **Step 3: Write minimal non-combat inspect rendering**

```python
def render_non_combat_screen(...):
    ...
    if mode.startswith("inspect_"):
        body.append(render_non_combat_inspect_panel(run_state, act_state, room_state, registry, menu_state))
        footer = render_menu(format_non_combat_inspect_menu(run_state, room_state, registry, menu_state))
        return build_standard_screen(summary=summary, body=Group(*body), footer=footer)
```

- [ ] **Step 4: Run targeted tests**

Run: `uv run pytest tests/app/test_inspect_menus.py tests/adapters/terminal/test_inspect.py -v`
Expected: PASS for non-combat inspect root, stats page, deck list, relic list, potion list, and back-navigation.

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/terminal/screens/non_combat.py src/slay_the_spire/app/session.py tests/app/test_inspect_menus.py tests/adapters/terminal/test_inspect.py
git commit -m "feat: add non-combat inspect screens"
```

### Task 4: Render combat inspect pages and detail panels

**Files:**
- Modify: `src/slay_the_spire/adapters/terminal/screens/combat.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/adapters/terminal/inspect.py`
- Test: `tests/adapters/terminal/test_inspect.py`
- Test: `tests/adapters/terminal/test_widgets.py`

- [ ] **Step 1: Write the failing combat inspect tests**

```python
def test_render_combat_inspect_root_includes_piles_and_enemy_details() -> None:
    session = start_session(seed=5)
    session = replace(session, menu_state=MenuState(mode="inspect_root"))

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=session.menu_state,
    )

    assert "5. 手牌" in output
    assert "6. 抽牌堆" in output
    assert "7. 弃牌堆" in output
    assert "8. 消耗堆" in output
    assert "9. 敌人详情" in output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/adapters/terminal/test_inspect.py::test_render_combat_inspect_root_includes_piles_and_enemy_details -v`
Expected: FAIL because combat screen still only supports root/select_card/select_target.

- [ ] **Step 3: Write minimal combat inspect implementation**

```python
def _format_menu(...):
    if mode == "inspect_root":
        return format_combat_inspect_root_menu(combat_state)
    if mode == "inspect_hand":
        return format_card_instance_menu("手牌列表", combat_state.hand, registry)
    if mode == "inspect_enemy_detail":
        return ["1. 返回敌人列表", "2. 返回资料总览"]
    ...


def render_combat_screen(...):
    if mode.startswith("inspect_"):
        inspect_body = render_combat_inspect_body(run_state, act_state, room_state, combat_state, registry, menu_state)
        footer = render_menu(_format_menu(room_state, combat_state, registry, menu_state))
        return build_standard_screen(summary=summary, body=inspect_body, footer=footer)
```

- [ ] **Step 4: Run targeted combat tests**

Run: `uv run pytest tests/adapters/terminal/test_inspect.py tests/adapters/terminal/test_widgets.py -v`
Expected: PASS for combat inspect root, pile list pages, card detail page, enemy detail page, and existing widget regressions.

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/terminal/screens/combat.py src/slay_the_spire/app/session.py src/slay_the_spire/adapters/terminal/inspect.py tests/adapters/terminal/test_inspect.py tests/adapters/terminal/test_widgets.py
git commit -m "feat: add combat inspect screens"
```

### Task 5: Update regressions, smoke flow, and final verification

**Files:**
- Modify: `tests/e2e/test_single_act_smoke.py`
- Modify: `tests/use_cases/test_room_recovery.py`
- Modify: `tests/app/test_inspect_menus.py`

- [ ] **Step 1: Write/adjust the failing regression tests for shifted menu indices**

```python
def test_game_over_menu_still_supports_view_save_load_exit_after_inspect_addition(...) -> None:
    ...


def test_single_act_smoke_can_open_inspect_in_combat_and_non_combat() -> None:
    session = start_session(seed=1)
    _running, session, message = route_menu_choice("4", session=session)
    assert "资料总览" in message
```

- [ ] **Step 2: Run regression tests to verify failures**

Run: `uv run pytest tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py -v`
Expected: FAIL on old menu numbering assumptions until tests and routing are updated together.

- [ ] **Step 3: Write the minimal compatibility fixes**

```python
def _format_root_menu(room_state: RoomState) -> list[str]:
    return [
        "可选操作:",
        "1. 查看战场",
        "2. 出牌",
        "3. 结束回合",
        "4. 查看资料",
        "5. 保存游戏",
        "6. 读取存档",
        "7. 退出游戏",
    ]
```

- [ ] **Step 4: Run final verification suite**

Run:

```bash
uv run pytest tests/app/test_inspect_menus.py -v
uv run pytest tests/adapters/terminal/test_inspect.py tests/adapters/terminal/test_widgets.py -v
uv run pytest tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py -v
uv run pytest
```

Expected:

- inspect 路由测试全部通过
- inspect 渲染测试全部通过
- 旧的终局、恢复和 smoke 用例在新菜单编号下仍通过
- 全量 `pytest` 绿灯

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/test_single_act_smoke.py tests/use_cases/test_room_recovery.py tests/app/test_inspect_menus.py src/slay_the_spire/app/session.py src/slay_the_spire/adapters/terminal/screens/combat.py src/slay_the_spire/adapters/terminal/screens/non_combat.py src/slay_the_spire/adapters/terminal/inspect.py src/slay_the_spire/adapters/terminal/widgets.py tests/adapters/terminal/test_inspect.py tests/adapters/terminal/test_widgets.py
git commit -m "feat: add inspect menus and detail panels"
```

## Review Checklist

- inspect 入口是否在所有主菜单可见
- 非战斗 inspect 是否覆盖 `属性 / 牌组 / 遗物 / 药水`
- 战斗 inspect 是否覆盖 `手牌 / 抽牌堆 / 弃牌堆 / 消耗堆 / 敌人详情`
- 卡牌/遗物/药水/敌人详情是否都有完整中文说明
- Rich 布局是否比当前纯摘要更清晰而不是更拥挤
- 旧菜单路径是否在 smoke 与 room recovery 用例中保持可用

## Execution Handoff

计划完成后，按以下方式执行：

1. `Subagent-Driven (recommended)`：逐任务派发独立执行者并在任务间审查结果。
2. `Inline Execution`：在当前会话内按任务批次执行，过程中做检查点。

由于当前会话不允许我主动派生子代理执行审稿或实现，若继续执行，默认采用 `Inline Execution`。
