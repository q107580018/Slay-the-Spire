# Textual-Only Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将项目收口为 Textual 唯一运行模式，并把仍在使用的共享 Rich 展示层从 `adapters/terminal/` 中迁出。

**Architecture:** 先用测试锁定 CLI 与共享渲染边界，再将被 `textual`/`session` 复用的 Rich 展示代码迁移到新的共享目录。最后删除 terminal-only runner 与文档/测试残留，确保行为不变、结构更清晰。

**Tech Stack:** Python 3.12, `uv`, `pytest`, `textual`, `rich`

---

### Task 1: 锁定 Textual-only CLI 行为

**Files:**
- Modify: `tests/app/test_cli_textual.py`
- Check: `src/slay_the_spire/app/cli.py`

- [ ] **Step 1: Write the failing tests**

补两类测试：

- 默认 `new --seed 5` 会直接进入 `run_textual_session()`
- 传入 `--ui textual` 或 `--ui terminal` 会被 argparse 视为无效参数

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/app/test_cli_textual.py -q`

Expected: FAIL，因为当前 CLI 仍接受 `--ui` 且默认是 `terminal`。

- [ ] **Step 3: Write minimal implementation**

在 `src/slay_the_spire/app/cli.py` 去掉 `--ui` 参数和 terminal 分流，只保留 `run_textual_session()`。

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/app/test_cli_textual.py -q`

Expected: PASS

### Task 2: 锁定共享 Rich 展示层的迁移边界

**Files:**
- Modify: `tests/adapters/textual/test_slay_app.py`
- Create: `tests/adapters/rich_ui/` 下的新测试文件
- Check: `src/slay_the_spire/adapters/textual/slay_app.py`
- Check: `src/slay_the_spire/app/session.py`

- [ ] **Step 1: Write the failing tests**

补或迁移最小测试，锁定：

- `SlayApp` 只依赖共享展示层，不再从 `adapters.terminal.*` 导入
- `session.py` 仍能生成和返回 Rich renderable
- 已有共享展示行为测试在迁移后继续有效

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py tests/adapters/rich_ui -q`

Expected: FAIL，因为共享层目录和 import 还未迁移。

- [ ] **Step 3: Write minimal implementation**

创建新的共享目录并更新 import，优先保持函数名和行为不变。

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/textual/test_slay_app.py tests/adapters/rich_ui -q`

Expected: PASS

### Task 3: 迁移共享 Rich 展示代码并删除 terminal-only runner

**Files:**
- Create: `src/slay_the_spire/adapters/rich_ui/__init__.py`
- Create: `src/slay_the_spire/adapters/rich_ui/theme.py`
- Create: `src/slay_the_spire/adapters/rich_ui/widgets.py`
- Create: `src/slay_the_spire/adapters/rich_ui/inspect.py`
- Create: `src/slay_the_spire/adapters/rich_ui/inspect_registry.py`
- Create: `src/slay_the_spire/adapters/rich_ui/screens/`
- Create: `src/slay_the_spire/adapters/rich_ui/renderer.py`
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/app/menu_definitions.py`
- Modify: `src/slay_the_spire/use_cases/combat_events.py`
- Delete: `src/slay_the_spire/adapters/terminal/app.py`
- Delete: `src/slay_the_spire/adapters/terminal/prompts.py`

- [ ] **Step 1: Run targeted tests to capture current failures**

Run: `uv run pytest tests/app/test_cli_textual.py tests/adapters/textual/test_slay_app.py tests/adapters/terminal/test_renderer.py tests/adapters/terminal/test_inspect.py -q`

- [ ] **Step 2: Move shared Rich files and update imports**

迁移共享展示代码到 `adapters/rich_ui/`，并让 `textual`、`session`、菜单定义和相关用例只依赖新目录。

- [ ] **Step 3: Delete terminal-only runner code**

删除纯 terminal session loop 与 prompt 层。

- [ ] **Step 4: Run targeted tests to verify behavior**

Run: `uv run pytest tests/app/test_cli_textual.py tests/adapters/textual/test_slay_app.py tests/adapters/rich_ui -q`

Expected: PASS

### Task 4: 清理 terminal 模式残留并补齐文档

**Files:**
- Delete: `tests/adapters/terminal/test_app.py`
- Modify: `tests/e2e/test_single_act_smoke.py`
- Modify: `AGENTS.md`
- Modify: `src/slay_the_spire/__init__.py`
- Check: `pyproject.toml`

- [ ] **Step 1: Write/update failing tests**

把仍显式断言 terminal 模式或 `--ui` 的测试改为 Textual-only 语义。

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py tests/app/test_cli_textual.py -q`

- [ ] **Step 3: Update docs and metadata**

同步更新项目说明、命令示例和包头文案，确保不再宣称支持纯 terminal 模式。

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py tests/app/test_cli_textual.py -q`

Expected: PASS

### Task 5: 全量验证与收尾

**Files:**
- Check: 全仓相关改动

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest`

Expected: PASS

- [ ] **Step 2: Run real startup smoke**

Run: `uv run slay-the-spire new --seed 5`

Expected: Textual 应用能启动，无导入或初始化错误。

- [ ] **Step 3: Review against requirements**

逐项核对：

- CLI 只保留 Textual
- 共享 Rich 层不再放在 `adapters/terminal/`
- terminal-only runner 已删除
- 游戏仍可启动且测试通过
