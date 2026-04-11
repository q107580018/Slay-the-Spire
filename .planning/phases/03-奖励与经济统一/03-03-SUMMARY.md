---
phase: 03-奖励与经济统一
plan: 03
subsystem: rewards
tags: [session-routing, reward-menu, inspect, pytest]
requires:
  - phase: 03-奖励与经济统一
    provides: 03-02 建立的非战斗 reward id 入口统一与 apply 链路
provides:
  - session 领取路由支持统一奖励动作与重复领取保护
  - reward 菜单中文文案覆盖 remove/upgrade/transform/duplicate/skip
  - select_reward 序号与 footer 动作顺序稳定测试
affects: [session, menu-feedback, reward-routing, inspect]
tech-stack:
  added: []
  patterns: [session-claim-guard, reward-menu-safe-fallback, stable-select-reward-order]
key-files:
  created: []
  modified: [src/slay_the_spire/app/session.py, src/slay_the_spire/app/menu_definitions.py, tests/app/test_inspect_menus.py, tests/app/test_menu_definitions.py, README.md]
key-decisions:
  - "session 层在领取前先校验 reward_id 仍存在于 room_state.rewards，重复或非法选择直接返回中文提示而不抛异常。"
  - "奖励菜单对未知或缺失内容的 reward id 回退显示原始 ID，避免把未识别奖励误标成已获得文案。"
patterns-established:
  - "Claim guard: select_reward 中所有 claim_reward 动作都先做 reward_id 可领取性检查。"
  - "Menu fallback: 奖励标签解析失败时保留原始 reward id 文本。"
requirements-completed: [REWARD-01, REWARD-03]
duration: 1 min
completed: 2026-04-11
---

# Phase 03 Plan 03: session/menu 奖励路由与反馈统一 Summary

**session 领取流程现已稳定接入统一奖励动作，奖励菜单可用中文一致展示移除、升级、转换、复制与跳过反馈。**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-11T12:13:10Z
- **Completed:** 2026-04-11T12:14:37Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- `session.py` 的奖励领取路由现在会保护重复/失效奖励，保持 `claimed_reward_ids` 语义稳定。
- `menu_definitions.py` 为统一奖励动作补齐中文文案，并在未知奖励上安全回退到原始 ID。
- app 层测试补齐 `select_reward` 的状态更新、文案显示与“跳过卡牌奖励 / 全部领取 / 返回上一步”序号稳定性断言。

## Task Commits

Each task was committed atomically:

1. **Task 1: 更新 session 领取路由支持新增奖励动作** - `8c32973` (feat)
2. **Task 2: 更新奖励菜单文案与编号稳定性测试** - `d4370de` (feat)

**Plan metadata:** pending

## Files Created/Modified
- `src/slay_the_spire/app/session.py` - 为 `claim_reward` 增加可领取性检查与去重保护。
- `src/slay_the_spire/app/menu_definitions.py` - 新增 remove/upgrade/transform/duplicate/skip 奖励标签与安全回退。
- `tests/app/test_inspect_menus.py` - 验证统一奖励动作领取后的状态与 `claimed_reward_ids`。
- `tests/app/test_menu_definitions.py` - 验证奖励文案与 `select_reward` 编号顺序稳定。
- `README.md` - 同步说明 session / 奖励菜单已对齐统一奖励协议。

## Decisions Made
- 在 session 层拦截无效 `claim_reward`，比依赖深层 `apply_reward` no-op 更适合向玩家返回明确中文提示。
- 奖励菜单文案优先展示结构化中文反馈；一旦解析或注册表查询失败，直接回退原始 reward id 以满足 threat model 的安全降级要求。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] 为重复/失效奖励领取补齐 session 防护**
- **Found during:** Task 1
- **Issue:** `claim_reward` 直接依赖房间列表命中；若奖励已被领取或 reward_id 非法，session 层会出现异常路径，不满足 threat model 对合法 reward_id 白名单处理的要求。
- **Fix:** 在 `_claim_session_reward` 与 `_route_reward_menu` 中先检查 reward 是否仍在 `room_state.rewards`，并对重复/失效选择返回中文提示。
- **Files modified:** `src/slay_the_spire/app/session.py`, `tests/app/test_inspect_menus.py`
- **Verification:** `uv run pytest tests/app/test_inspect_menus.py -k reward -x`
- **Committed in:** `8c32973`

**2. [Rule 2 - Missing Critical] 为未知奖励标签补齐安全回退并同步 README**
- **Found during:** Task 2
- **Issue:** 计划 threat model 要求未知奖励前缀降级显示原 ID；同时 AGENTS.md 要求流程与测试基线变化后同步更新 README。
- **Fix:** 扩展 `_reward_label` 支持统一奖励动作中文文案，并在解析失败时回退显示原始 reward id；同时更新 README 说明 session/menu 已完成对齐。
- **Files modified:** `src/slay_the_spire/app/menu_definitions.py`, `tests/app/test_menu_definitions.py`, `README.md`
- **Verification:** `uv run pytest tests/app/test_menu_definitions.py tests/app/test_inspect_menus.py -k "reward or inspect" -x`
- **Committed in:** `d4370de`

---

**Total deviations:** 2 auto-fixed (2 missing critical)
**Impact on plan:** 均为正确性与文档一致性补齐，直接支持统一奖励协议在 session/menu 层稳定落地。

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- session / menu / use case 三层的统一奖励协议已连通，03-04 可以继续处理 placeholder 与固定奖励降级反馈。
- 奖励菜单对未知输入已具备安全回退，后续新增奖励类型只需补充 label 映射与相应 app 测试即可。

## Self-Check: PASSED
- Found: `.planning/phases/03-奖励与经济统一/03-03-SUMMARY.md`
- Found: `src/slay_the_spire/app/session.py`
- Found: `src/slay_the_spire/app/menu_definitions.py`
- Found: `tests/app/test_inspect_menus.py`
- Found: `tests/app/test_menu_definitions.py`
- Found commits: `8c32973`, `d4370de`
