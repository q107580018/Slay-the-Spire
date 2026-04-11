---
phase: 02-三幕主线闭环
verified: 2026-04-11T18:45:00+08:00
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
---

# Phase 02: 三幕主线闭环 Verification Report

**Phase Goal:** 玩家可从新开局走完三幕并完成终局结算，主线状态在存读档后保持一致。
**Verified:** 2026-04-11T18:45:00+08:00
**Status:** passed

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `act3_map.json` 已存在并可加载 | ✓ VERIFIED | `StarterContentProvider(Path('content')).acts().get('act3')` 成功，输出 `第三幕` |
| 2 | `act2_map.json` 已配置 `next_act_id: act3` | ✓ VERIFIED | 文件中 `boss_pool_id` 后存在 `next_act_id` 字段 |
| 3 | Act3 普通/精英/Boss 敌人与遭遇池均已录入 | ✓ VERIFIED | 新增 6 个 JSON：`content/enemies/act3_*.json` 与 `content/encounters/act3_*.json` |
| 4 | Act3 事件池已录入并可加载 | ✓ VERIFIED | 新增 `content/events/act3_events.json`，注册表校验通过 |
| 5 | 胜利/失败终局面板展示运行统计信息 | ✓ VERIFIED | `render_terminal_phase_panel` 增加角色/章节/生命/金币/牌组/遗物/药水/种子 |
| 6 | 终局面板未知 relic/potion ID 不会崩溃 | ✓ VERIFIED | 新增 `test_terminal_phase_panel_handles_unknown_relic_gracefully` |
| 7 | 三幕全程 E2E smoke 可到达 Victory | ✓ VERIFIED | `tests/e2e/test_three_act_smoke.py::test_three_act_full_run_reaches_victory` 通过 |
| 8 | 分幕边界覆盖 Act2->Act3 与 Act3->Victory | ✓ VERIFIED | `test_act2_boss_transitions_to_act3` 与 `test_act3_boss_transitions_to_victory` 通过 |
| 9 | save/load 可 round-trip 保持 act3 状态 | ✓ VERIFIED | `test_save_load_round_trip_with_act3_state`、`test_save_load_round_trip_preserves_act3_progression` 通过 |
| 10 | 全量回归通过，无跨模块回归 | ✓ VERIFIED | `uv run pytest -x` 1107 passed |

## Verification Commands

- `uv run pytest tests/content/test_registry_validation.py -x`
- `uv run pytest tests/adapters/presentation/ -x`
- `uv run pytest tests/e2e/ -x -v`
- `uv run pytest tests/use_cases/test_save_load.py -x -v`
- `uv run pytest -m guardrail`
- `uv run pytest -x`

## Changed Artifacts

- `content/acts/act2_map.json`
- `content/acts/act3_map.json`
- `content/enemies/act3_basic.json`
- `content/enemies/act3_elites.json`
- `content/enemies/act3_bosses.json`
- `content/encounters/act3_basic.json`
- `content/encounters/act3_elites.json`
- `content/encounters/act3_bosses.json`
- `content/events/act3_events.json`
- `src/slay_the_spire/adapters/presentation/screens/non_combat.py`
- `tests/adapters/presentation/test_renderer.py`
- `tests/e2e/test_two_act_smoke.py`
- `tests/e2e/test_three_act_smoke.py`
- `tests/use_cases/test_save_load.py`
- `tests/use_cases/test_room_recovery.py`

## Residual Risks

- Act3 多数新敌人的复杂行为仍为简化 move_table；精确机制收敛留待后续高复杂角色/规则阶段。

