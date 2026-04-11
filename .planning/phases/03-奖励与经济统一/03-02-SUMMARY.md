---
phase: 03-奖励与经济统一
plan: 02
subsystem: rewards
tags: [reward-routing, neow, shop, event, rest, apply-reward]
requires:
  - phase: 03-奖励与经济统一
    provides: 03-01 建立的 RewardAction 解析与 apply_reward_action 执行器
provides:
  - Neow/商店入口改为先生成 reward id 再统一 apply
  - 事件/休息点升级与移除动作改为统一奖励协议
  - 非法事件 payload 安全降级为 completed no-op
affects: [session, menu-feedback, reward-routing]
tech-stack:
  added: []
  patterns: [reward-id-first, use-case-entrypoint-unification, safe-event-noop-fallback]
key-files:
  created: []
  modified: [src/slay_the_spire/use_cases/opening_flow.py, src/slay_the_spire/use_cases/shop_action.py, src/slay_the_spire/use_cases/rest_action.py, src/slay_the_spire/use_cases/event_action.py, tests/use_cases/test_opening_flow.py, tests/use_cases/test_shop_and_rest_actions.py, tests/use_cases/test_event_actions.py, README.md]
key-decisions:
  - "Neow、商店、休息点与事件的金币/遗物/药水/升级/移除统一先编码为 reward id，再复用 apply_reward。"
  - "事件非法 effect payload 不再中断流程，而是完成房间并保持 run_state 不变。"
  - "未进入注册表的事件诅咒牌仍保留直接入牌组逻辑，避免破坏既有内容行为。"
patterns-established:
  - "Entrypoint routing: 非战斗入口先做成本结算，再把奖励效果交给 apply_reward。"
  - "Threat mitigation: 事件 effect 解析异常统一降级到 completed no-op。"
requirements-completed: [REWARD-01, REWARD-03, REWARD-04]
duration: 9 min
completed: 2026-04-11
---

# Phase 03 Plan 02: use case 奖励入口统一 Summary

**Neow、商店、事件与休息点现已把主要非战斗奖励入口统一路由到 reward id + apply_reward 链路，同时为非法事件 payload 提供安全 no-op 降级。**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-11T11:56:47Z
- **Completed:** 2026-04-11T12:06:06Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Neow 的药水、升级、移除奖励不再直接改 run_state，而是统一交给 `apply_reward`。
- 商店买牌、买遗物、买药水与删牌服务统一生成 reward id，保留金币扣减与 Courier 重补货语义。
- 休息点与事件的升级/移除动作接入统一 apply 链路，并为非法事件 effect payload 增加 completed no-op 降级。

## Task Commits

Each task was committed atomically:

1. **Task 1: 迁移 Neow/商店奖励动作到统一 reward 协议** - `5f97c5e` (feat)
2. **Task 2: 迁移事件/休息点奖励动作到统一 reward 协议** - `35e690a` (feat)

**Additional docs:** `780aea2` (docs)

## Files Created/Modified
- `src/slay_the_spire/use_cases/opening_flow.py` - 让 Neow 奖励统一产出 reward id 并复用 `apply_reward`。
- `src/slay_the_spire/use_cases/shop_action.py` - 把商店购买/删牌入口收敛到统一 reward id 解析与执行。
- `src/slay_the_spire/use_cases/rest_action.py` - 把休息点升级/删牌子流程改为统一 apply 链路。
- `src/slay_the_spire/use_cases/event_action.py` - 把事件升级/删牌/金币奖励接入统一协议，并补齐非法 payload 安全降级。
- `tests/use_cases/test_opening_flow.py` - 覆盖 Neow 药水与目标型奖励走统一链路。
- `tests/use_cases/test_shop_and_rest_actions.py` - 覆盖商店/休息点统一 apply 行为与删牌计数。
- `tests/use_cases/test_event_actions.py` - 覆盖事件升级、删牌与非法 payload no-op 行为。
- `README.md` - 记录非战斗奖励入口已统一接入 apply 链路。

## Decisions Made
- Neow/商店/休息点/事件入口先保留各自成本与房间状态语义，只把奖励执行部分收敛到 `apply_reward`，以降低 session/menu 回归风险。
- 事件 threat model 中要求的非法 payload 防护在 use case 层实现：解析失败直接完成房间并保持原 `run_state`。
- 对未进入注册表的事件诅咒牌保留直接入牌组逻辑，避免把内容缺口误当成奖励协议问题。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] 为事件 effect 解析补齐 no-op 安全降级**
- **Found during:** Task 2
- **Issue:** `event_action.py` 对非法 payload 仍可能抛出 `TypeError`/`ValueError`，不满足计划 threat model 的“非法 payload 回退 no-op”。
- **Fix:** 在事件 effect 分派外层增加异常兜底，异常时完成房间并保持 `run_state` 不变。
- **Files modified:** `src/slay_the_spire/use_cases/event_action.py`, `tests/use_cases/test_event_actions.py`
- **Verification:** `uv run pytest tests/use_cases/test_event_actions.py tests/use_cases/test_shop_and_rest_actions.py -x`
- **Committed in:** `35e690a`

**2. [Rule 2 - Missing Critical] 同步 README 的统一奖励入口说明**
- **Found during:** Plan 收尾
- **Issue:** AGENTS.md 要求代码/流程变化后同步更新 README；本计划落地后 README 尚未反映 Neow/商店/事件/休息点入口统一情况。
- **Fix:** 在 README 增补非战斗奖励入口统一接入 `apply_reward` 与事件非法 payload 安全降级说明。
- **Files modified:** `README.md`
- **Verification:** README 包含更新说明，且 `uv run pytest tests/use_cases/test_opening_flow.py tests/use_cases/test_shop_and_rest_actions.py tests/use_cases/test_event_actions.py -x` 继续通过。
- **Committed in:** `780aea2`

---

**Total deviations:** 2 auto-fixed (2 missing critical)
**Impact on plan:** 均为正确性与文档一致性补齐，无额外范围蔓延。

## Issues Encountered
- 事件中的 `normality` 等诅咒牌并未全部进入内容注册表，不能简单统一成 `card:` reward id；实现中保留了这类事件专用加牌路径，只统一已被 `apply_reward` 支持的奖励类型。

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- use case 层的主要非战斗奖励入口已统一到 reward id/apply 协议，03-03 可以继续对齐 session/menu 路由与中文反馈文案。
- 事件专用诅咒加牌仍有少量直接改牌组分支，后续若要彻底结构化，需要先补齐相应内容注册表与展示合同。

## Self-Check: PASSED
- Found: .planning/phases/03-奖励与经济统一/03-02-SUMMARY.md
- Found commits: 5f97c5e, 35e690a, 780aea2
