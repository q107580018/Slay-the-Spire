---
phase: 03-奖励与经济统一
reviewed: 2026-04-11T13:14:46Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/slay_the_spire/app/session.py
  - src/slay_the_spire/adapters/presentation/screens/non_combat.py
  - src/slay_the_spire/use_cases/event_action.py
  - src/slay_the_spire/use_cases/apply_reward.py
  - src/slay_the_spire/use_cases/reward_actions.py
  - src/slay_the_spire/app/menu_definitions.py
  - tests/use_cases/test_room_recovery.py
  - tests/use_cases/test_apply_reward.py
  - tests/use_cases/test_event_actions.py
  - tests/use_cases/test_opening_flow.py
  - tests/use_cases/test_shop_and_rest_actions.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-04-11T13:14:46Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

本次 re-review 重点复查了此前报告的“未实现/不可用奖励会被消耗”问题，并重新检查了 Phase 03 当前奖励与经济统一链路。

结论：`f329f8c` 已修复 **宝箱遗物** 与 **Boss 遗物** 两条消耗路径；对应阻断逻辑与回归测试均已到位，相关问题不再复现。`uv run pytest tests/use_cases/test_room_recovery.py -q` 与相关奖励/economy 回归测试均通过。

但 **普通奖励菜单（select_reward）** 仍保留同类缺陷：当奖励在 `apply_reward()` 中被安全降级为 no-op 时，session 层仍会把它记为已领取并从奖励列表移除，玩家会丢失这次奖励机会。

## Warnings

### WR-01: 普通奖励菜单仍会消耗未实际获得的不可用奖励

**File:** `src/slay_the_spire/app/session.py:499-531`
**Issue:** `_claim_session_reward()` 无论 `apply_reward()` 是否真正发放奖励，都会立即调用 `_room_with_rewards_claimed()` 把奖励从 `room_state.rewards` 中移除；`claim_all` 也复用了这条路径。结合 `apply_reward()` 对 placeholder relic/potion/card reward 的 safe no-op 语义，这意味着普通奖励房里一旦出现“未实现/不可用”的 fixed reward，玩家仍可能在没有任何收益的情况下失去奖励选择权。此前的 Boss/宝箱修复没有覆盖这条通用奖励领取链路。
**Fix:** 在 session 层为 `claim_reward` / `claim_all` 增加“可领取”校验，只在奖励可实际发放时才标记为已领取。最小修复可以复用与 Boss/宝箱一致的 unavailable 检测逻辑，对 placeholder/解析失败奖励直接返回提示并保留在列表中；同时补一条 app 级回归测试，验证选择 `relic:astrolabe` 这类不可用普通奖励后，`room_state.rewards` 不减少。

```python
provider = _content_provider(session)
if _reward_is_unavailable(reward_id, registry=provider):
    return replace(session, menu_state=MenuState(mode="select_reward"))

updated_run_state = apply_reward(
    run_state=session.run_state,
    reward_id=reward_id,
    registry=provider,
)
updated_room_state = _room_with_rewards_claimed(session.room_state, reward_id)
```

---

_Reviewed: 2026-04-11T13:14:46Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
