# Textual Hover Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `Textual` 模式下的奖励和商店列表增加统一的悬停预览面板，让鼠标悬停和键盘高亮都能即时展示卡牌、遗物、药水或控制项说明。

**Architecture:** 保持 `SessionState`、菜单 action id 和 `route_menu_choice()` 不变，只在 `Textual` 适配层增加“预览详情”展示与解析。`SlayApp` 负责右侧面板布局和 `OptionList.OptionHighlighted` 联动，`inspect.py` 负责复用或补齐卡牌、遗物、药水的详情文本格式化，测试集中放在 `tests/adapters/textual/test_slay_app.py`。

**Tech Stack:** Python 3.12, `uv`, `pytest`, `textual`, `rich`

---

### Task 1: 锁定奖励和商店悬停预览的 UI 回归点

**Files:**
- Modify: `tests/adapters/textual/test_slay_app.py`
- Check: `src/slay_the_spire/adapters/textual/slay_app.py`
- Check: `src/slay_the_spire/app/session.py`

- [ ] **Step 1: Write the failing tests**

先在 `tests/adapters/textual/test_slay_app.py` 增加最小结构测试，锁定支持预览的菜单模式会显示预览面板。例如：

```python
def test_reward_preview_panel_is_present_in_reward_menu() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="combat",
            stage="completed",
            is_resolved=True,
            rewards=["card_offer:anger", "gold:15"],
        ),
        menu_state=replace(base.menu_state, mode="select_reward"),
    )

    async def scenario() -> None:
        app = SlayApp(session)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#hover-preview", Static).display is True

    asyncio.run(scenario())
```

再补一条离开奖励/商店菜单后不残留预览的测试：

```python
def test_hover_preview_panel_is_hidden_outside_preview_modes() -> None:
    async def scenario() -> None:
        app = SlayApp(start_session(seed=5))
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.query_one("#hover-preview", Static).display is False

    asyncio.run(scenario())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k 'hover_preview_panel' -q`

Expected:

- FAIL，因为当前 `SlayApp` 还没有 `#hover-preview`
- 或 panel 存在性 / display 断言失败

- [ ] **Step 3: Commit**

```bash
git add tests/adapters/textual/test_slay_app.py
git commit -m "test: lock textual hover preview panel behavior"
```

### Task 2: 为 Textual 右侧布局加入共享预览面板

**Files:**
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Write the failing test**

增加一个引导态测试，确保进入奖励/商店菜单但尚未明确悬停目标时，会显示引导文本而不是空白：

```python
def test_hover_preview_panel_shows_guidance_in_reward_menu() -> None:
    ...
    preview = app.query_one("#hover-preview", Static)
    assert "查看说明" in preview.renderable.plain
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k 'guidance_in_reward_menu' -q`

Expected: FAIL，因为当前没有预览面板和引导文案。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/adapters/textual/slay_app.py`：

- 在 `compose()` 里新增 `Static("", id="hover-preview")`
- 在 `CSS` 里为 `#hover-preview` 增加固定高度、边框和 padding
- 增加 helper：

```python
def _supports_hover_preview(menu_mode: str) -> bool:
    return menu_mode in {"select_reward", "select_boss_reward", "select_boss_relic", "shop_root"}
```

- 在 `_refresh_actions()` 末尾调用新的 `_refresh_hover_preview()`，根据当前 menu mode 决定：
  - 显示引导文案
  - 清空并隐藏面板

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k 'hover_preview_panel or guidance_in_reward_menu' -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/textual/slay_app.py tests/adapters/textual/test_slay_app.py
git commit -m "feat: add textual hover preview panel scaffold"
```

### Task 3: 先锁定并实现奖励列表中的卡牌与控制项预览

**Files:**
- Modify: `tests/adapters/textual/test_slay_app.py`
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
- Check: `src/slay_the_spire/app/menu_definitions.py`
- Check: `src/slay_the_spire/adapters/terminal/inspect.py`

- [ ] **Step 1: Write the failing tests**

补最小交互测试，直接通过 `OptionList` 的高亮状态驱动预览刷新：

```python
def test_hover_preview_shows_card_reward_details_for_highlighted_reward() -> None:
    ...
    action_list = app.query_one("#action-list", OptionList)
    action_list.highlighted = 0
    await pilot.pause()
    preview = app.query_one("#hover-preview", Static)
    assert "愤怒" in preview.renderable.plain
    assert "效果" in preview.renderable.plain


def test_hover_preview_shows_control_hint_for_claim_all() -> None:
    ...
    action_list.highlighted = 2
    await pilot.pause()
    preview = app.query_one("#hover-preview", Static)
    assert "全部领取" in preview.renderable.plain
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k 'card_reward_details or control_hint_for_claim_all' -q`

Expected: FAIL，因为当前没有高亮事件联动和 reward action 解析。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/adapters/textual/slay_app.py`：

- 新增 `@on(OptionList.OptionHighlighted, "#action-list")`
- 在 `_refresh_actions()` 里除 `self._action_choices` 外，再同步保留 action id 列表，例如：

```python
self._action_ids = [option.action_id for option in menu.options]
```

- 增加 helper：

```python
def _hover_preview_renderable(session: SessionState, action_id: str) -> Any: ...
def _reward_preview_renderable(session: SessionState, action_id: str) -> Any: ...
```

- `select_reward` 下优先支持：
  - `claim_reward:card_offer:*`
  - `claim_reward:card:*`
  - `claim_reward:gold:*`
  - `claim_all`
  - `back`
  - `skip_card_rewards`

卡牌详情先复用现有摘要能力，不要重新写规则文案。

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k 'card_reward_details or control_hint_for_claim_all' -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/textual/slay_app.py tests/adapters/textual/test_slay_app.py
git commit -m "feat: preview textual reward hover details"
```

### Task 4: 补齐遗物和药水详情格式化能力

**Files:**
- Modify: `src/slay_the_spire/adapters/terminal/inspect.py`
- Test: `tests/adapters/textual/test_slay_app.py`
- Check: `src/slay_the_spire/content/registries.py`

- [ ] **Step 1: Write the failing tests**

为遗物和药水详情加断言：

```python
def test_hover_preview_shows_boss_relic_details() -> None:
    ...
    assert "黑色之血" in preview.renderable.plain
    assert "禁用操作" in preview.renderable.plain or "替换原遗物" in preview.renderable.plain


def test_hover_preview_shows_shop_potion_details() -> None:
    ...
    assert "火焰药水" in preview.renderable.plain
    assert "20" in preview.renderable.plain
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k 'boss_relic_details or shop_potion_details' -q`

Expected:

- Boss relic 测试可能部分失败，因为当前 `slay_app.py` 还未接 `select_boss_relic`
- Potion 测试失败，因为 `inspect.py` 还没有药水详情 helper

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/adapters/terminal/inspect.py`：

- 新增药水详情格式化 helper，例如：

```python
def format_potion_detail_lines(potion_id: str, registry: ContentProviderPort) -> list[Text]:
    potion_def = registry.potions().get(potion_id)
    return [
        Text.assemble(("名称: ", "summary.label"), potion_def.name),
        Text.assemble(("药水: ", "summary.label"), potion_id),
        Text.assemble(("效果: ", "summary.label"), summarize_effect(potion_def.effect)),
    ]
```

在 `src/slay_the_spire/adapters/textual/slay_app.py`：

- 让 `select_boss_relic` 的 `claim_boss_relic:*` 走遗物详情
- 让 `shop_root` 的：
  - `buy_relic:*` 走遗物详情
  - `buy_potion:*` 走药水详情

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k 'boss_relic_details or shop_potion_details' -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/terminal/inspect.py src/slay_the_spire/adapters/textual/slay_app.py tests/adapters/textual/test_slay_app.py
git commit -m "feat: add hover preview for relics and potions"
```

### Task 5: 完成商店控制项与 Boss 奖励入口说明

**Files:**
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
- Test: `tests/adapters/textual/test_slay_app.py`
- Check: `src/slay_the_spire/app/menu_definitions.py`

- [ ] **Step 1: Write the failing tests**

补控制项说明测试：

```python
def test_hover_preview_shows_shop_remove_service_hint() -> None:
    ...
    assert "删牌服务" in preview.renderable.plain


def test_hover_preview_shows_boss_reward_entry_hint() -> None:
    ...
    assert "进入 Boss 遗物选择" in preview.renderable.plain
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k 'remove_service_hint or boss_reward_entry_hint' -q`

Expected: FAIL，因为当前控制项说明还不完整。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/adapters/textual/slay_app.py` 的统一解析层中补全：

- `shop_root`：
  - `remove`
  - `leave`
  - `inspect`
  - `save`
  - `load`
  - `quit`
- `select_boss_reward`：
  - `claim_boss_gold`
  - `claimed_boss_gold`
  - `choose_boss_relic`
  - `claimed_boss_relic`
  - `back`

保持所有面向玩家文案为中文，不把内部 action id 直接显示给用户。

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py -k 'remove_service_hint or boss_reward_entry_hint' -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/textual/slay_app.py tests/adapters/textual/test_slay_app.py
git commit -m "feat: complete textual hover control-item hints"
```

### Task 6: 跑完整 Textual 回归并清理实现

**Files:**
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
- Modify: `tests/adapters/textual/test_slay_app.py`
- Check: `src/slay_the_spire/adapters/terminal/inspect.py`

- [ ] **Step 1: Run the focused test suite**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py`

Expected: 全部 PASS。

- [ ] **Step 2: Refactor only if needed**

若 `slay_app.py` 中出现过长的分支链，把预览解析拆成小 helper，例如：

```python
def _shop_preview_renderable(...)
def _boss_reward_preview_renderable(...)
def _control_hint_renderable(...)
```

前提是 refactor 后仍保持测试全绿。

- [ ] **Step 3: Run the focused test suite again**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py`

Expected: 全部 PASS。

- [ ] **Step 4: Run a small smoke suite for奖励/商店流程**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py tests/e2e/test_two_act_smoke.py -q`

Expected: PASS；至少不应因为 `Textual` 预览逻辑破坏奖励和 Boss 奖励流转。

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/textual/slay_app.py src/slay_the_spire/adapters/terminal/inspect.py tests/adapters/textual/test_slay_app.py
git commit -m "feat: add textual hover previews for rewards and shop"
```
