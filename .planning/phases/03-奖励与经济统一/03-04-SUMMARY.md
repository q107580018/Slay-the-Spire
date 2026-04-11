---
phase: 03-奖励与经济统一
plan: 04
subsystem: rewards
tags: [placeholder-filtering, reward-safety, neow, boss-rewards, menu-feedback]
requires:
  - phase: 03-奖励与经济统一
    provides: 03-03 已连通的 session/menu 奖励协议与中文反馈基线
provides:
  - 随机遗物池统一复用 placeholder 过滤 helper
  - 固定奖励中的 placeholder/未知内容安全降级为 no-op
  - 奖励菜单与 Boss 遗物菜单显示未实现/不可用中文提示
affects: [reward-generator, opening-flow, apply-reward, reward-menu]
tech-stack:
  added: []
  patterns: [shared-random-relic-filter, safe-fixed-reward-noop, unavailable-reward-visible-feedback]
key-files:
  created: []
  modified: [src/slay_the_spire/domain/rewards/reward_generator.py, src/slay_the_spire/use_cases/start_run.py, src/slay_the_spire/use_cases/opening_flow.py, src/slay_the_spire/use_cases/apply_reward.py, src/slay_the_spire/app/menu_definitions.py, tests/use_cases/test_start_run.py, tests/use_cases/test_apply_reward.py, tests/app/test_menu_definitions.py, README.md]
key-decisions:
  - "随机遗物来源统一通过 reward_generator 中的共享 helper 过滤 placeholder，避免 start_run 与 Neow 再各自维护条件。"
  - "固定奖励中的未知卡牌、药水与非替换型 placeholder 遗物统一降级为 no-op，但仍保留替换型 placeholder Boss 遗物的合法替换链路。"
  - "奖励与 Boss 遗物菜单对未实现或缺失内容直接展示‘未实现/不可用’，不再静默回退成普通奖励文案。"
patterns-established:
  - "Random relic filtering: start_run / Neow 共用 rewardable_relic_ids_for_pool(...)。"
  - "Fixed reward fallback: apply_reward 对异常固定奖励返回原 run_state，UI 负责显式提示不可用。"
requirements-completed: [REWARD-02, REWARD-03]
duration: 5 min
completed: 2026-04-11
---

# Phase 03 Plan 04: placeholder 安全过滤与固定奖励降级反馈 Summary

**随机遗物池现在统一排除 placeholder，而固定奖励命中未实现或未知内容时会安全降级并在菜单中明确显示不可用提示。**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-11T12:17:00Z
- **Completed:** 2026-04-11T12:22:29Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- `reward_generator.py` 提供共享随机遗物过滤 helper，`start_run.py` 与 `opening_flow.py` 不再各自维护 placeholder 判定。
- `apply_reward.py` 为固定奖励补齐 placeholder/未知卡牌、药水与遗物的 no-op 降级，不再击穿流程。
- `menu_definitions.py` 为奖励菜单和 Boss 遗物菜单补齐“未实现/不可用”中文反馈，README 同步说明安全策略。

## Task Commits

Each task was committed atomically:

1. **Task 1: 统一随机奖励 placeholder 过滤** - `ccaf2e6` (feat)
2. **Task 2: 固定奖励命中未实现内容时安全降级并可见** - `785db0e` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `src/slay_the_spire/domain/rewards/reward_generator.py` - 提供共享随机遗物过滤 helper。
- `src/slay_the_spire/use_cases/start_run.py` - 开局遗物序列改为复用共享过滤策略。
- `src/slay_the_spire/use_cases/opening_flow.py` - Neow 随机遗物改为复用共享过滤策略。
- `src/slay_the_spire/use_cases/apply_reward.py` - 固定奖励对未知内容与非替换型 placeholder 做安全 no-op。
- `src/slay_the_spire/app/menu_definitions.py` - 奖励菜单/Boss 遗物菜单显示“未实现/不可用”。
- `tests/use_cases/test_start_run.py` - 验证开局与 Neow 都经过共享过滤 helper。
- `tests/use_cases/test_apply_reward.py` - 验证固定奖励的 placeholder/unknown no-op 与替换链路保留。
- `tests/app/test_menu_definitions.py` - 验证不可用奖励在菜单中可见。
- `README.md` - 同步 placeholder 过滤与固定奖励降级说明。

## Decisions Made
- 将随机遗物过滤收口到领域层 helper，而不是继续在 `start_run` / `opening_flow` 复制条件，降低后续宝箱或其他随机入口漂移风险。
- 固定奖励安全策略区分“随机池禁止投放”和“固定奖励可见降级”：前者彻底过滤，后者允许 UI 展示但执行时 no-op。
- 对 `ring_of_the_serpent` 这类替换型 placeholder 遗物保留替换行为，避免误伤已有角色 Boss 遗物链路。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 收窄 placeholder 遗物 no-op 范围以保留替换链路**
- **Found during:** Task 2
- **Issue:** 初版把所有 placeholder 遗物都降级为 no-op，导致 `ring_of_the_serpent` 这类替换型 Boss 遗物不再替换起始遗物。
- **Fix:** 改为仅对非替换型 placeholder 遗物执行 no-op；保留 `replaces_relic_id` 链路的合法替换语义。
- **Files modified:** `src/slay_the_spire/use_cases/apply_reward.py`, `tests/use_cases/test_apply_reward.py`
- **Verification:** `uv run pytest tests/use_cases/test_apply_reward.py tests/app/test_menu_definitions.py -k "placeholder or reward" -x`
- **Committed in:** `785db0e`

**2. [Rule 2 - Missing Critical] 同步 README 的 placeholder 安全策略说明**
- **Found during:** Task 2 收尾
- **Issue:** AGENTS.md 要求流程、测试基线与玩家可见行为变化后同步更新 README；本计划原文未单列文档步骤。
- **Fix:** 在 README 增补随机遗物共享过滤与固定奖励不可用提示说明。
- **Files modified:** `README.md`
- **Verification:** README 包含新说明，且整体验证测试继续通过。
- **Committed in:** `785db0e`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** 均为保证正确性与文档一致性的必要补充，没有引入额外范围蔓延。

## Issues Encountered
- 固定奖励中的 placeholder 遗物并不全等于“完全不可领取”：部分 Boss 替换遗物虽然效果未补齐，但仍承担替换起始遗物的流程语义，因此实现中保留了替换链路，仅对非替换型 placeholder 做 no-op。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- 随机池与固定奖励的 placeholder 风险都已收口，03-05 可以专注做奖励经济遗物跨入口回归矩阵。
- 奖励菜单已具备对异常内容的显式中文反馈，后续新增奖励类型只需补充 apply 与 label 映射即可复用同一安全策略。

## Self-Check: PASSED
- Found: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Found: `src/slay_the_spire/use_cases/apply_reward.py`
- Found: `src/slay_the_spire/app/menu_definitions.py`
- Found: `tests/use_cases/test_start_run.py`
- Found: `tests/use_cases/test_apply_reward.py`
- Found: `tests/app/test_menu_definitions.py`
- Found commits: `ccaf2e6`, `785db0e`
