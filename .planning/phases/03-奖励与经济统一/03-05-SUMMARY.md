---
phase: 03-奖励与经济统一
plan: 05
subsystem: rewards
tags: [economy-relics, cross-entrance-regression, pytest, readme]
requires:
  - phase: 03-奖励与经济统一
    provides: 03-04 已建立的 placeholder 安全降级与奖励菜单不可用反馈基线
provides:
  - 经济遗物跨 combat/boss/shop/event/treasure/neow/rest 的回归测试矩阵
  - 事件金币统一复用 apply_reward 的单点结算
  - README 中可复现的 phase 03 验证命令与覆盖入口说明
affects: [reward-generator, event-action, shop, rest, neow, treasure, documentation]
tech-stack:
  added: []
  patterns: [cross-entrance-economy-regression-matrix, event-gold-single-source]
key-files:
  created: [.planning/phases/03-奖励与经济统一/03-05-SUMMARY.md]
  modified: [src/slay_the_spire/use_cases/event_action.py, tests/use_cases/test_apply_reward.py, tests/use_cases/test_event_actions.py, tests/use_cases/test_shop_and_rest_actions.py, tests/use_cases/test_opening_flow.py, README.md]
key-decisions:
  - "事件金币奖励不再预先叠加 golden_idol，而是统一交给 apply_reward 计算，避免跨入口双重加成。"
  - "跨入口经济遗物回归同时覆盖触发与阻断/降级路径，避免只断言 message 而漏掉 run_state 演进。"
patterns-established:
  - "Cross-entrance matrix: combat/boss/shop/event/treasure/neow/rest 每个入口都保留经济遗物的自动化证据。"
  - "Single-source gold handling: 非战斗入口的金币发放统一走 apply_reward，复用 golden_idol/ectoplasm 规则。"
requirements-completed: [REWARD-04]
duration: 3 min
completed: 2026-04-11
---

# Phase 03 Plan 05: 奖励经济遗物跨入口回归与文档同步 Summary

**经济遗物现已在 combat、boss、shop、event、treasure、neow 与 rest 入口形成统一回归矩阵，README 也提供了可直接复现的 phase 03 验证命令。**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-11T12:30:24Z
- **Completed:** 2026-04-11T12:33:31Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- 为 `golden_idol`、`ectoplasm`、`sozu`、`the_courier`、`dream_catcher` 补齐跨入口触发/阻断/降级测试，覆盖 combat、boss、shop、event、treasure、neow、rest 7 个入口。
- 修正事件金币链路中的重复加成 bug，让事件金币与其他奖励入口统一复用 `apply_reward` 的经济规则。
- 在 README 新增“Phase 03：奖励与经济统一”章节，明确统一协议、placeholder 安全策略与可执行 pytest 命令。

## Task Commits

Each task was committed atomically:

1. **Task 1: 增加奖励经济遗物跨入口回归测试矩阵** - `cfdf031` (test), `bad20dc` (feat)
2. **Task 2: 更新 README 的 phase 03 验证命令与覆盖说明** - `c97560e` (docs)

_Note: Task 1 followed TDD RED → GREEN and therefore produced two commits._

## Files Created/Modified
- `src/slay_the_spire/use_cases/event_action.py` - 删除事件金币的重复 idol 加成，统一走 `apply_reward` 金币规则。
- `tests/use_cases/test_apply_reward.py` - 增加 boss / treasure 后续经济遗物行为断言。
- `tests/use_cases/test_event_actions.py` - 增加事件入口的 `golden_idol` / `ectoplasm` 断言，并把 placeholder 事件遗物对齐为降级路径。
- `tests/use_cases/test_shop_and_rest_actions.py` - 增加 `the_courier` 未触发降级路径与 `dream_catcher` 未触发路径。
- `tests/use_cases/test_opening_flow.py` - 增加 Neow 入口的 `golden_idol` / `ectoplasm` / `sozu` 经济联动断言。
- `README.md` - 新增 phase 03 奖励与经济统一章节及 4 条可执行验证命令。

## Decisions Made
- 事件入口的金币效果不再自行处理 `golden_idol` / `ectoplasm`，而是直接生成 `gold:*` 交给 `apply_reward`，避免规则漂移。
- 跨入口回归矩阵优先断言 `run_state.gold`、`relics`、`potions`、`room_state.rewards` 等状态变化，而不是只检查提示文案。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 修复事件金币与 golden_idol 的双重加成**
- **Found during:** Task 1（奖励经济遗物跨入口回归测试矩阵）
- **Issue:** `event_action.py` 先手动调用一次 `golden_idol` 加成，再把结果交给 `apply_reward("gold:...")`，导致事件金币入口比 combat / neow / treasure 多算一次加成。
- **Fix:** 删除事件层的重复金币修正，只保留 `apply_reward` 的统一结算。
- **Files modified:** `src/slay_the_spire/use_cases/event_action.py`, `tests/use_cases/test_apply_reward.py`
- **Verification:** `uv run pytest tests/use_cases/test_apply_reward.py tests/use_cases/test_event_actions.py tests/use_cases/test_shop_and_rest_actions.py tests/use_cases/test_opening_flow.py -x`
- **Committed in:** `bad20dc`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** 该修复直接消除了跨入口规则漂移，属于完成 REWARD-04 所必需的正确性修正。

## Issues Encountered
- 现有 `ominous_forge -> warped_tongs` 测试仍假设 placeholder 事件遗物可以直接发放；本计划在补矩阵时把它对齐到 03-04 已建立的“placeholder 固定奖励安全降级”合同，只保留诅咒副作用断言。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 03 的统一奖励协议、placeholder 安全策略和经济遗物跨入口联动都已有自动化证据，当前 phase 可以视为完成。
- 后续 Phase 04 可以在此基础上继续扩展非战斗系统，而不必重复处理奖励经济入口一致性问题。

## Self-Check: PASSED
- Found: `.planning/phases/03-奖励与经济统一/03-05-SUMMARY.md`
- Found commits: `cfdf031`, `bad20dc`, `c97560e`
