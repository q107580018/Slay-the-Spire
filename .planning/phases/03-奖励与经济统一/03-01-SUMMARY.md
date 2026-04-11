---
phase: 03-奖励与经济统一
plan: 01
subsystem: rewards
tags: [reward-actions, apply-reward, tdd, pytest]
requires:
  - phase: 02-三幕主线闭环
    provides: 三幕主线与既有 reward/apply 基线
provides:
  - 统一 RewardAction 协议与安全解析
  - apply_reward_action 分派执行器
  - 覆盖 remove/upgrade/transform/duplicate/skip/noop 的回归测试矩阵
affects: [shop, event, rest, neow, reward-routing]
tech-stack:
  added: []
  patterns: [reward-id-first, safe-noop-fallback, deterministic-targeted-reward-actions]
key-files:
  created: [src/slay_the_spire/use_cases/reward_actions.py]
  modified: [src/slay_the_spire/use_cases/apply_reward.py, tests/use_cases/test_apply_reward.py, README.md]
key-decisions:
  - "奖励字符串统一先解析为 RewardAction，再由 apply_reward_action 执行，未知输入安全降级为 noop。"
  - "目标型奖励使用 card_instance_id 与可选 target_card_id 编码，保持 apply 结果可重复且可测试。"
patterns-established:
  - "RewardAction parser: 所有奖励入口先做结构化解析，再进入执行器。"
  - "No-op fallback: 非法 payload、未知 kind、缺失内容统一返回原 run_state。"
requirements-completed: [REWARD-01, REWARD-03]
duration: 6 min
completed: 2026-04-11
---

# Phase 03 Plan 01: 统一奖励动作协议与 apply 执行器 Summary

**奖励字符串现已统一解析为 RewardAction，并由 apply 执行器稳定处理升级、移除、转换、复制与跳过动作。**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-11T11:46:00Z
- **Completed:** 2026-04-11T11:52:46Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- 新建 `reward_actions.py`，为奖励入口提供统一 `RewardAction` dataclass 与解析契约。
- `apply_reward.py` 改为先解析再分派，兼容旧奖励前缀并新增 remove/upgrade/transform/duplicate/skip 分支。
- `tests/use_cases/test_apply_reward.py` 补齐统一动作回归矩阵，验证 noop 与非法 payload 的确定性降级行为。

## Task Commits

Each task was committed atomically:

1. **Task 1: 建立统一奖励动作协议模块** - `122ff24` (feat)
2. **Task 2: 扩展 apply_reward 为统一动作执行器** - `0f072fa`, `5140b74` (test, feat)
3. **Task 3: 补齐统一动作的最小回归测试矩阵** - `cd48c57` (test)

**Additional docs:** `3f8ac64` (docs)

## Files Created/Modified
- `src/slay_the_spire/use_cases/reward_actions.py` - 定义奖励动作 dataclass、严格解析器与 noop 回退。
- `src/slay_the_spire/use_cases/apply_reward.py` - 新增 `apply_reward_action(...)` 分派器与 targeted reward handlers。
- `tests/use_cases/test_apply_reward.py` - 增加 transform/duplicate/remove/upgrade/skip/noop 行为回归测试。
- `README.md` - 补充统一 reward action 支持范围说明。

## Decisions Made
- 使用 `RewardAction(kind, payload)` 作为奖励合同层，避免后续在 shop/event/rest/neow 继续复制前缀分支。
- `transform` 支持可选显式目标卡 ID；未显式提供时从注册表中稳定选择一个合法候选，保持 deterministic。
- 对未知 reward id、非法 payload、缺失目标或注册表校验失败统一返回原 `run_state`，满足 threat model 的安全降级要求。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] 同步 README 的奖励协议说明**
- **Found during:** Task 3 收尾
- **Issue:** AGENTS.md 要求代码/流程/测试基线变化后同步更新 README；本计划原文未单列文档任务。
- **Fix:** 在 README 中补充统一 reward action 支持范围与非法 reward id 的 no-op 降级说明。
- **Files modified:** README.md
- **Verification:** README 包含统一 reward action 描述；相关测试命令保持通过。
- **Committed in:** `3f8ac64`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** 仅补齐文档一致性，无额外范围蔓延。

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `reward_id -> parse_reward_action -> apply_reward_action` 主合同层已稳定，可供 03-02 收敛 Neow/商店/事件/休息点入口复用。
- 现有旧入口仍有部分直接改 `run_state` 的逻辑，下一计划可逐步替换为统一 reward action 产出。

## Self-Check: PASSED
- Found: src/slay_the_spire/use_cases/reward_actions.py
- Found: src/slay_the_spire/use_cases/apply_reward.py
- Found: tests/use_cases/test_apply_reward.py
- Found commits: 122ff24, 0f072fa, 5140b74, cd48c57, 3f8ac64
