# Terminal Rich UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改动 `session/use_cases/domain` 规则边界的前提下，把当前中文数字菜单 CLI 升级为基于 `rich` 的面板式终端 UI，并覆盖战斗、事件、奖励、路径选择四类决策屏。

**Architecture:** 保持 `render_room(run_state, act_state, room_state, registry, menu_state) -> str` 这个外部接口不变，`renderer.py` 内部改为“场景调度 + Rich Console 导出文本”模式。共享样式放进 `theme.py`，局部视图控件放进 `widgets.py`，战斗与非战斗场景分别落在 `screens/combat.py` 与 `screens/non_combat.py`，公共布局骨架放进 `screens/layout.py`，这样 session 层继续只持有 `MenuState` 与 `SessionState`，不会吸收排版逻辑。

**Tech Stack:** Python 3.12+, `uv`, `rich`, `pytest`, dataclasses, existing content registries and session/menu flow

---

## File Structure Map

### 现有文件继续承担的职责

- Modify: `pyproject.toml`
  增加 `rich` 运行时依赖，保持 `uv` 为唯一 Python 依赖入口。
- Modify: `src/slay_the_spire/adapters/terminal/renderer.py`
  从单文件字符串拼接器重构为场景调度器，并通过 `Console(record=True)` 输出最终字符串。
- Modify: `src/slay_the_spire/adapters/terminal/prompts.py`
  保持数字输入提示，但让提示文案与 Rich UI 风格一致。
- Modify: `src/slay_the_spire/app/session.py`
  仅做必要的小幅接线调整，继续调用 `render_room`，不把 Rich 细节带进 session 路由。
- Modify: `tests/e2e/test_single_act_smoke.py`
  把 smoke 断言从旧的逐行文本切换到新的 Rich 面板输出，同时保留中文编号菜单验证。

### 新增终端 UI 模块

- Create: `src/slay_the_spire/adapters/terminal/theme.py`
  定义 `Theme`、颜色 token、面板边框风格、状态文本样式和血条颜色阈值。
- Create: `src/slay_the_spire/adapters/terminal/widgets.py`
  提供血条、格挡标签、状态标签、敌人意图摘要、手牌摘要、奖励摘要、菜单面板等可复用组件。
- Create: `src/slay_the_spire/adapters/terminal/screens/__init__.py`
  暴露 screen 模块入口，避免 renderer 直接堆叠内部细节。
- Create: `src/slay_the_spire/adapters/terminal/screens/layout.py`
  封装顶部摘要、中部主体、底部操作区和双栏主体的标准布局骨架。
- Create: `src/slay_the_spire/adapters/terminal/screens/combat.py`
  负责战斗主屏、选牌屏、选目标屏三种战斗场景。
- Create: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`
  负责事件屏、奖励屏、路径选择屏和通用房间摘要屏。

### 新增测试文件

- Create: `tests/adapters/terminal/test_widgets.py`
  断言共享 Rich 组件的文本输出和中文摘要规则。
- Create: `tests/adapters/terminal/test_renderer.py`
  断言 renderer 在不同 `room_state + menu_state` 组合下选择正确 screen，并保留完整决策上下文。

## Task 1: 建立 Rich 渲染骨架与可测试导出路径

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/slay_the_spire/adapters/terminal/renderer.py`
- Create: `tests/adapters/terminal/test_renderer.py`

- [ ] **Step 1: 写一个会失败的 renderer 集成测试**

```python
from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.content.provider import StarterContentProvider


def test_render_room_exports_rich_panelized_combat_screen() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "╭" in output or "┌" in output
    assert "当前能量" in output
    assert "抽牌堆" in output
    assert "可选操作" in output
```

- [ ] **Step 2: 运行测试并确认它按预期失败**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py::test_render_room_exports_rich_panelized_combat_screen -v`
Expected: FAIL，因为当前输出仍是纯文本，没有 `rich` 面板边框，也没有新的顶部摘要字段。

- [ ] **Step 3: 引入 `rich` 依赖并把 renderer 改成“Rich renderable -> 字符串”导出骨架**

```python
from rich.console import Console, RenderableType


def _render_to_text(renderable: RenderableType) -> str:
    console = Console(
        width=100,
        record=True,
        force_terminal=False,
        color_system=None,
    )
    console.print(renderable)
    return console.export_text(clear=False).rstrip()
```

需要同时完成：

- 使用 `uv add rich` 更新依赖，然后同步 `pyproject.toml`
- 保留 `render_room(run_state, act_state, room_state, registry, menu_state) -> str` 签名
- 先用一个最小的 summary `Panel` 占住新出口，确保后续 screen 模块可以渐进替换

- [ ] **Step 4: 重新运行目标测试**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py::test_render_room_exports_rich_panelized_combat_screen -v`
Expected: PASS，输出已经经过 `Console` 导出，包含 box drawing 字符和基础摘要字段。

- [ ] **Step 5: 提交这一小步**

```bash
git add pyproject.toml src/slay_the_spire/adapters/terminal/renderer.py tests/adapters/terminal/test_renderer.py
git commit -m "feat: scaffold rich terminal renderer"
```

## Task 2: 提取主题与共享 widgets，统一视觉语言

**Files:**
- Create: `src/slay_the_spire/adapters/terminal/theme.py`
- Create: `src/slay_the_spire/adapters/terminal/widgets.py`
- Create: `tests/adapters/terminal/test_widgets.py`
- Modify: `src/slay_the_spire/adapters/terminal/renderer.py`

- [ ] **Step 1: 写 widgets 的失败测试，锁定血条、状态、菜单的文本规则**

```python
from rich.console import Console

from slay_the_spire.adapters.terminal.widgets import (
    render_hp_bar,
    render_menu,
    render_statuses,
)
from slay_the_spire.domain.models.statuses import StatusState


def _export(renderable) -> str:
    console = Console(width=80, record=True, force_terminal=False, color_system=None)
    console.print(renderable)
    return console.export_text(clear=False)


def test_render_hp_bar_uses_full_and_empty_blocks() -> None:
    output = _export(render_hp_bar(current=18, maximum=30))
    assert "█" in output
    assert "░" in output
    assert "18/30" in output


def test_render_statuses_returns_compact_chinese_labels() -> None:
    output = _export(render_statuses([StatusState(status_id="vulnerable", stacks=2)]))
    assert "易伤 2" in output


def test_render_menu_preserves_numbered_choices() -> None:
    output = _export(render_menu(["1. 查看战场", "2. 出牌"]))
    assert "1. 查看战场" in output
    assert "2. 出牌" in output
```

- [ ] **Step 2: 运行 widgets 测试并确认失败**

Run: `uv run pytest tests/adapters/terminal/test_widgets.py -v`
Expected: FAIL，因为 `theme.py` / `widgets.py` 还不存在。

- [ ] **Step 3: 实现 theme 与 widgets**

```python
from rich import box
from rich.theme import Theme

TERMINAL_THEME = Theme(
    {
        "summary.label": "bold cyan",
        "player.name": "bold green",
        "enemy.name": "bold red",
        "menu.number": "bold yellow",
        "menu.border": "yellow",
        "hp.high": "green",
        "hp.medium": "yellow",
        "hp.low": "bold red",
        "status.buff": "black on bright_cyan",
        "status.debuff": "black on bright_magenta",
    }
)

PANEL_BOX = box.SQUARE
HP_BAR_WIDTH = 18
```

```python
def hp_style_for_ratio(ratio: float) -> str:
    if ratio <= 0.25:
        return "hp.low"
    if ratio <= 0.6:
        return "hp.medium"
    return "hp.high"


def render_hp_bar(current: int, maximum: int, *, width: int = HP_BAR_WIDTH) -> Text:
    ratio = 0 if maximum <= 0 else max(0, min(current / maximum, 1))
    filled = round(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    return Text.assemble((bar, hp_style_for_ratio(ratio)), f" {current}/{maximum}")
```

```python
def render_menu(options: list[str], *, title: str = "可选操作") -> Panel:
    body = Group(*(Text(option) for option in options))
    return Panel(body, title=title, box=PANEL_BOX, border_style="menu.border")
```

实现时一并处理：

- 状态标签统一走中文映射，空状态显示 `无`
- 格挡显示为 `🛡 5`
- 敌人意图先做“只读预览”，根据 `EnemyDef.move_table` 生成短文本，不改 domain 状态
- 手牌摘要使用卡牌效果拼一句中文，例如 `造成 6 伤害`、`获得 5 格挡`

- [ ] **Step 4: 跑 widgets 测试确认全部通过**

Run: `uv run pytest tests/adapters/terminal/test_widgets.py -v`
Expected: PASS，血条、状态标签、菜单面板都能稳定导出为中文 Rich 文本。

- [ ] **Step 5: 提交共享组件**

```bash
git add src/slay_the_spire/adapters/terminal/theme.py src/slay_the_spire/adapters/terminal/widgets.py src/slay_the_spire/adapters/terminal/renderer.py tests/adapters/terminal/test_widgets.py
git commit -m "feat: add rich terminal theme and widgets"
```

## Task 3: 实现战斗 screen 与固定四段布局

**Files:**
- Create: `src/slay_the_spire/adapters/terminal/screens/__init__.py`
- Create: `src/slay_the_spire/adapters/terminal/screens/layout.py`
- Create: `src/slay_the_spire/adapters/terminal/screens/combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/renderer.py`
- Modify: `tests/adapters/terminal/test_renderer.py`

- [ ] **Step 1: 先写战斗 screen 的失败测试**

```python
from dataclasses import replace

from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.adapters.terminal.renderer import render_room


def test_combat_root_screen_keeps_full_context_and_hand_panel() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "回合 1" in output
    assert "当前能量 3" in output
    assert "玩家状态" in output
    assert "敌人意图" in output
    assert "手牌" in output
    assert "1. 打击 (1)" in output


def test_select_card_only_replaces_bottom_menu_panel() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(mode="select_card"),
    )

    assert "当前能量 3" in output
    assert "手牌" in output
    assert "返回上一步" in output
```

- [ ] **Step 2: 运行战斗 screen 测试并确认失败**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py::test_combat_root_screen_keeps_full_context_and_hand_panel tests/adapters/terminal/test_renderer.py::test_select_card_only_replaces_bottom_menu_panel -v`
Expected: FAIL，因为 renderer 还没有分离出 Rich 布局骨架和战斗专用 screen。

- [ ] **Step 3: 在 `layout.py` 与 `combat.py` 中实现战斗四段布局**

```python
def build_standard_screen(*, summary, body, footer) -> Group:
    return Group(summary, body, footer)


def build_two_column_body(*, left, right) -> Columns:
    return Columns([left, right], equal=True, expand=True)
```

```python
def render_combat_screen(
    *,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    combat_state: CombatState,
    registry: ContentProviderPort,
    menu_state: Any,
) -> RenderableType:
    summary = render_summary_bar(
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        combat_state=combat_state,
        registry=registry,
    )
    body = build_two_column_body(
        left=render_player_panel(combat_state, registry),
        right=render_enemy_panel(combat_state, registry),
    )
    hand_panel = render_hand_panel(combat_state, registry)
    footer = render_menu_panel_for_combat(room_state, combat_state, registry, menu_state)
    return build_standard_screen(summary=summary, body=Group(body, hand_panel), footer=footer)
```

实现要求：

- 顶部摘要条显示角色、章节、房间类型、回合、能量、抽牌堆/弃牌堆数量
- 中部双栏左侧固定玩家面板，右侧为敌方列表或敌方卡片组
- 根菜单时显示完整手牌区；`select_card` / `select_target` 时保留上方摘要和战场，仅替换底部操作区
- 战斗已结算且仍留在当前房间时，不把战场信息清空，避免“奖励前信息丢失”

- [ ] **Step 4: 跑战斗相关 renderer 测试**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py -k 'combat or select_card' -v`
Expected: PASS，战斗屏具备固定四段布局，选牌时上半屏上下文保持不变。

- [ ] **Step 5: 提交战斗 screen**

```bash
git add src/slay_the_spire/adapters/terminal/screens/__init__.py src/slay_the_spire/adapters/terminal/screens/layout.py src/slay_the_spire/adapters/terminal/screens/combat.py src/slay_the_spire/adapters/terminal/renderer.py tests/adapters/terminal/test_renderer.py
git commit -m "feat: add rich combat screen"
```

## Task 4: 实现事件、奖励、路径选择等非战斗 screen

**Files:**
- Create: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/renderer.py`
- Modify: `tests/adapters/terminal/test_renderer.py`

- [ ] **Step 1: 写非战斗 screen 的失败测试**

```python
from dataclasses import replace

from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.content.provider import StarterContentProvider


def test_event_screen_shows_body_and_options_panel() -> None:
    session = start_session(seed=5)
    session = replace(
        session,
        room_state=replace(
            session.room_state,
            room_type="event",
            payload={
                "node_id": "event",
                "room_kind": "event",
                "event_id": "shining_light",
                "next_node_ids": ["boss"],
            },
        ),
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(mode="select_event_choice"),
    )

    assert "事件" in output
    assert "发光的牧师向你献上力量。" in output
    assert "1. 接受" in output


def test_resolved_room_with_rewards_uses_reward_screen() -> None:
    session = start_session(seed=5)
    resolved_room = replace(session.room_state, is_resolved=True, rewards=["gold:12", "card:reward_strike"])
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=resolved_room,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "奖励" in output
    assert "金币 12" in output
    assert "卡牌 打击+" in output


def test_select_next_room_uses_branch_selection_screen() -> None:
    session = start_session(seed=5)
    resolved_room = replace(
        session.room_state,
        is_resolved=True,
        payload={
            **session.room_state.payload,
            "next_node_ids": ["hallway", "event"],
        },
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=resolved_room,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(mode="select_next_room"),
    )

    assert "请选择下一个房间" in output
    assert "1. 走廊" in output
    assert "2. 事件" in output
```

- [ ] **Step 2: 运行非战斗测试并确认失败**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py -k 'event_screen or reward_screen' -v`
Expected: FAIL，因为 renderer 还没有把事件正文、结果面板、奖励列表和路径菜单拆成独立 screen。

- [ ] **Step 3: 在 `non_combat.py` 里实现事件屏、奖励屏、路径选择屏**

```python
def render_event_screen(
    *,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    registry: ContentProviderPort,
    menu_state: Any,
) -> RenderableType:
    panels = [
        render_summary_bar(run_state=run_state, act_state=act_state, room_state=room_state),
        render_event_body(room_state=room_state, registry=registry),
    ]
    if room_state.payload.get("result") is not None:
        panels.append(render_event_result_panel(room_state))
    panels.append(render_menu(event_menu_options(room_state=room_state, registry=registry, menu_state=menu_state)))
    return Group(*panels)
```

```python
def render_reward_screen(
    *,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
) -> RenderableType:
    return build_standard_screen(
        summary=render_summary_bar(
            run_state=run_state,
            act_state=act_state,
            room_state=room_state,
            title="战斗奖励",
        ),
        body=render_rewards_panel(room_state.rewards),
        footer=render_menu(root_reward_options(room_state)),
    )
```

实现要求：

- 事件屏分离“事件正文”和“结果”两个面板，已结算结果单独强调
- 奖励屏不要求引入新的 `room_type`，直接根据 `room_state.is_resolved and room_state.rewards` 派发
- 路径选择屏在 `select_next_room` 模式下单独渲染分支列表，不画整张地图
- 默认房间摘要屏用于兜底 room 类型，避免 renderer 再退回大段 `if/else` 字符串拼接

- [ ] **Step 4: 跑非战斗 renderer 测试**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py -k 'event or reward or next_room' -v`
Expected: PASS，事件、奖励、路径选择都进入统一的 Rich 面板布局。

- [ ] **Step 5: 提交非战斗 screen**

```bash
git add src/slay_the_spire/adapters/terminal/screens/non_combat.py src/slay_the_spire/adapters/terminal/renderer.py tests/adapters/terminal/test_renderer.py
git commit -m "feat: add rich non-combat screens"
```

## Task 5: 接线、提示文案与端到端回归

**Files:**
- Modify: `src/slay_the_spire/adapters/terminal/prompts.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `tests/e2e/test_single_act_smoke.py`

- [ ] **Step 1: 先写 smoke 回归断言，覆盖 Rich UI 的关键可见行为**

```python
def test_session_loop_uses_rich_chinese_numbered_menus() -> None:
    session = start_session(seed=5)
    result = interactive_loop(session=session, input_port=_InputPort(["2", "1", "2", "1", "3", "6"]))

    assert "┌" in result.outputs[0]
    assert "当前能量 3" in result.outputs[0]
    assert "1. 查看战场" in result.outputs[0]
    assert "1. 打击 (1)" in result.outputs[1]
    assert "返回上一步" in result.outputs[1]
    assert "奖励" in result.outputs[4]
    assert result.outputs[6] == "已退出游戏。"
```

- [ ] **Step 2: 运行 e2e smoke，并确认在真实 loop 下失败**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py -v`
Expected: FAIL，旧的 smoke 仍在断言逐行文本格式，新 Rich 输出尚未全部接线稳定。

- [ ] **Step 3: 完成 session/prompts 的最小接线，并更新 smoke 断言**

```python
def prompt_for_session(session: Any) -> str:
    del session
    return "请选择编号 > "
```

```python
def render_session(session: SessionState) -> str:
    return render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_content_provider(session),
        menu_state=session.menu_state,
    )
```

这个步骤重点不是重写路由，而是：

- 确认 `interactive_loop` 在多轮输出下仍然只传字符串
- 确认所有菜单模式仍然接受原有数字输入
- 把 e2e 断言改为验证“有完整上下文 + 中文编号菜单”，而不是依赖旧的逐行排列细节

- [ ] **Step 4: 运行完整终端相关测试并确认通过**

Run: `uv run pytest tests/adapters/terminal/test_widgets.py tests/adapters/terminal/test_renderer.py tests/e2e/test_single_act_smoke.py -v`
Expected: PASS，Rich widgets、screen 派发和交互回归全部通过。

- [ ] **Step 5: 提交收尾改动**

```bash
git add src/slay_the_spire/adapters/terminal/prompts.py src/slay_the_spire/app/session.py tests/e2e/test_single_act_smoke.py
git commit -m "test: cover rich terminal ui flow"
```

## Task 6: 全量回归并确认未污染规则边界

**Files:**
- Modify: `docs/superpowers/plans/2026-03-24-terminal-rich-ui-implementation.md`
  仅在执行中打勾，不新增需求。

- [ ] **Step 1: 运行完整测试集**

Run: `uv run pytest -v`
Expected: PASS，包括 domain/use_cases/content/e2e 在内的既有测试全部通过。

- [ ] **Step 2: 手工跑一次 CLI 新建流程**

Run: `uv run python -m slay_the_spire.app.cli new --seed 5`
Expected: 终端出现 Rich 面板式首屏，输入 `6` 后退出并打印 `已退出游戏。`

- [ ] **Step 3: 检查变更范围只停留在 UI 适配层**

Run: `git diff --stat`
Expected: 改动集中在 `adapters/terminal/`、极少量 `app/session.py` 接线，以及对应测试；不应把 `rich` 逻辑带入 `domain/` 或 `use_cases/`。

- [ ] **Step 4: 做一次最终验证提交**

```bash
git add pyproject.toml src/slay_the_spire/adapters/terminal src/slay_the_spire/app/session.py tests/adapters/terminal tests/e2e/test_single_act_smoke.py docs/superpowers/plans/2026-03-24-terminal-rich-ui-implementation.md
git commit -m "feat: ship rich terminal ui"
```

- [ ] **Step 5: 执行完成后再决定整合方式**

执行完成后，使用 `superpowers:finishing-a-development-branch` 决定是直接整理分支、生成 PR，还是继续追加小步修复。
