# Reward Menu Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除无效的“查看战场/查看奖励”入口，并让普通奖励与 Boss 奖励在未处理完成前持续停留在奖励菜单中。

**Architecture:** 保持现有 Rich/Textual 渲染结构不变，只精简 `build_root_menu()` 暴露的动作，并在 `session.py` 中收缩普通奖励为单层菜单。奖励领取逻辑继续由现有 `apply_reward` 与 Boss 奖励辅助函数驱动，但根据剩余奖励状态决定是否留在当前菜单。

**Tech Stack:** Python 3.12、`uv`、`pytest`、Rich、Textual

---

## File Map

- Modify: `src/slay_the_spire/app/menu_definitions.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `tests/app/test_menu_definitions.py`
- Modify: `tests/app/test_inspect_menus.py`

### Task 1: 锁定新的根菜单行为

**Files:**
- Modify: `tests/app/test_menu_definitions.py`
- Modify: `src/slay_the_spire/app/menu_definitions.py`

- [ ] **Step 1: 写失败测试**

补充或改写根菜单测试，要求：

- 战斗根菜单不再包含“查看战场”
- 待领取普通奖励与待领取 Boss 奖励的根菜单不再包含“查看奖励”

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/app/test_menu_definitions.py -q`

- [ ] **Step 3: 做最小实现**

在 `build_root_menu()` 中移除：

- 战斗根菜单的 `view_current`
- 已结算奖励根菜单的 `view_rewards`

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/app/test_menu_definitions.py -q`

### Task 2: 锁定普通奖励的单层菜单与停留行为

**Files:**
- Modify: `tests/app/test_inspect_menus.py`
- Modify: `src/slay_the_spire/app/session.py`

- [ ] **Step 1: 写失败测试**

增加覆盖：

- 根菜单直接进入 `select_reward`
- 领取金币后如果仍有卡牌奖励，保持在 `select_reward`
- 最后一项奖励处理完成后才回根菜单

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/app/test_inspect_menus.py -q`

- [ ] **Step 3: 做最小实现**

在 `session.py` 中：

- 删除普通奖励详情入口与对应菜单路由
- 调整 `_claim_session_reward()`、`_claim_all_session_rewards()`、`_skip_card_offer_rewards()` 的返回菜单模式
- 根菜单的 `claim_rewards` 直接进入 `select_reward`

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/app/test_inspect_menus.py -q`

### Task 3: 锁定 Boss 奖励未完成前不退出

**Files:**
- Modify: `tests/app/test_inspect_menus.py`
- Modify: `src/slay_the_spire/app/session.py`

- [ ] **Step 1: 写失败测试**

增加覆盖：

- 在 `select_boss_reward` 中领取金币后，如果遗物未选，仍停留在 `select_boss_reward`
- 在 `select_boss_relic` 中选遗物后，如果金币未领，回到 `select_boss_reward`

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/app/test_inspect_menus.py -q`

- [ ] **Step 3: 做最小实现**

调整 `_claim_boss_gold()` 与 `_claim_boss_relic()`，根据完成状态决定：

- 未完成：返回 Boss 奖励菜单
- 已完成：进入既有 act 推进 / victory 流程

- [ ] **Step 4: 运行针对性测试确认通过**

Run: `uv run pytest tests/app/test_menu_definitions.py tests/app/test_inspect_menus.py -q`

### Task 4: 完整回归

**Files:**
- Modify: `tests/app/test_menu_definitions.py`
- Modify: `tests/app/test_inspect_menus.py`
- Modify: `src/slay_the_spire/app/menu_definitions.py`
- Modify: `src/slay_the_spire/app/session.py`

- [ ] **Step 1: 运行完整相关测试**

Run: `uv run pytest tests/app/test_menu_definitions.py tests/app/test_inspect_menus.py tests/e2e/test_single_act_smoke.py tests/e2e/test_two_act_smoke.py -q`

- [ ] **Step 2: 检查失败并做最小修正**

仅修正与本次菜单流改动直接相关的问题，不顺手重构其他模块。

- [ ] **Step 3: 再次运行验证**

Run: `uv run pytest tests/app/test_menu_definitions.py tests/app/test_inspect_menus.py tests/e2e/test_single_act_smoke.py tests/e2e/test_two_act_smoke.py -q`
