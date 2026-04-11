---
phase: 03-奖励与经济统一
verified: 2026-04-11T12:49:06Z
status: human_needed
score: 7/7 must-haves verified
overrides_applied: 0
human_verification:
  - test: "在真实 Textual TUI 中领取混合奖励"
    expected: "奖励菜单中的升级/复制/跳过/卡牌奖励编号、中文文案与返回逻辑一致，领取后状态变化与提示不冲突"
    why_human: "自动化已验证状态与菜单文本，但无法确认真实 TUI 渲染、焦点切换和玩家体感是否一致"
  - test: "在宝箱与 Boss 宝箱界面查看未实现奖励提示"
    expected: "placeholder 或缺失遗物显示“未实现/不可用”，且玩家仍能理解可领取/不可用状态，不产生误导"
    why_human: "自动化仅验证字符串存在，无法判断终端排版与交互语义是否足够清晰"
---

# Phase 3: 奖励与经济统一 Verification Report

**Phase Goal:** 奖励系统在所有入口使用一致标识和 apply 流程，玩家获得结果可信且可反馈。
**Verified:** 2026-04-11T12:49:06Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | 战后、Boss、商店、事件、宝箱、Neow、休息点的奖励入口都走统一奖励标识与 apply 链路。 | ✓ VERIFIED | `reward_actions.py:52-91` 定义统一 reward id 解析；`apply_reward.py:376-380` 统一入口；`opening_flow.py:165-199,320-379`、`shop_action.py:282-297`、`rest_action.py:109-154,173-181`、`event_action.py:225-233,372-457`、`session.py:499-521,640-689,718-749` 均复用该链路；相关测试通过：Neow/事件/商店/休息点/宝箱定向 pytest。 |
| 2 | 随机奖励池默认不投放未实现或 placeholder 遗物；若明确标记未实现，也不会破坏流程。 | ✓ VERIFIED | `reward_generator.py:19-38` 统一过滤 `implementation_status == "placeholder"`；`start_run.py:21-33` 与 `opening_flow.py:270-280` 复用 helper；`apply_reward.py:263-308,325-334` 对固定 placeholder/unknown 奖励安全 no-op；`menu_definitions.py:389-419,517-527` 明确显示“未实现/不可用”；`test_start_run.py:144-193`、`test_apply_reward.py:951-984`、`test_menu_definitions.py:553-591` 覆盖。 |
| 3 | 金币、卡牌奖励、遗物、药水、移除、升级、转换、复制、跳过等奖励类型都有可验证结果与玩家反馈。 | ✓ VERIFIED | `apply_reward.py:285-370` 实现 `gold/relic/card/card_offer/potion/remove/upgrade/transform/duplicate/skip/noop`；`test_apply_reward.py:48-179,844-984` 覆盖行为；`menu_definitions.py:385-469` 为 gold/relic/potion/card/remove/upgrade/transform/duplicate/skip 提供中文标签；`test_menu_definitions.py:439-591` 与 `test_inspect_menus.py:425-538` 验证菜单与领取反馈。 |
| 4 | 奖励经济相关遗物效果在对应入口按规则触发并可通过测试验证。 | ✓ VERIFIED | `apply_reward.py:35-47,104-148,325-334` 实现 `golden_idol / ectoplasm / sozu / ceramic_fish` 等；`shop_action.py:409-495` 处理 `the_courier / sozu`；`rest_action.py:173-181` 处理 `dream_catcher`；`reward_generator.py:202-295` 处理 `white_beast_statue / prayer_wheel / question_card / sozu / black_star`；测试覆盖 combat/boss/shop/event/treasure/neow/rest：`test_apply_reward.py:237-376`、`test_event_actions.py:174-213,394-403`、`test_shop_and_rest_actions.py:127-139,198-357,423-449`、`test_opening_flow.py:84-175`、`test_room_recovery.py:211-320`。 |
| 5 | 入口动作不再各自复制奖励结算逻辑。 | ✓ VERIFIED | `opening_flow.py:329-378`、`shop_action.py:282-297`、`rest_action.py:109-154`、`event_action.py:53-55,182-233` 统一调用 `apply_reward(...)`，未再出现各入口分别实现升级/移除/金币结算的并行分支。 |
| 6 | 入口改造后仍保持可回放与可测试。 | ✓ VERIFIED | 奖励子流程和恢复路径有回归：`test_room_recovery.py:65-208,211-320` 覆盖 event/shop/rest/treasure 的 save/load 或重复进入场景；`test_inspect_menus.py:469-538` 覆盖 session 领取后的 `claimed_reward_ids` 与菜单状态。 |
| 7 | 开发者可通过 README 提供的命令复现实测结果。 | ✓ VERIFIED | `README.md:162-191` 明确列出 phase 03 覆盖范围与 4 条 `uv run pytest ...` 验证命令，且命令所引用测试文件在仓库内存在并可执行。 |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `src/slay_the_spire/use_cases/reward_actions.py` | 统一奖励协议与解析 | ✓ VERIFIED | 存在；`RewardAction` + `parse_reward_action()` 实现于 `1-91`。 |
| `src/slay_the_spire/use_cases/apply_reward.py` | 统一 apply 执行器 | ✓ VERIFIED | 存在；`apply_reward_action()` / `apply_reward()` 位于 `285-380`，含 placeholder 安全降级。 |
| `src/slay_the_spire/use_cases/opening_flow.py` | Neow 奖励统一为 reward id + apply | ✓ VERIFIED | `165-199,320-379` 将 gold/relic/potion/card/upgrade/remove 收敛到 reward id。 |
| `src/slay_the_spire/use_cases/shop_action.py` | 商店购买/删牌统一走 apply | ✓ VERIFIED | `_apply_shop_reward()` 位于 `282-297`，被买牌/买遗物/买药水/删牌调用。 |
| `src/slay_the_spire/use_cases/rest_action.py` | 休息点升级/删牌与奖励联动 | ✓ VERIFIED | `109-154,173-181` 走 `apply_reward` 与 combat reward generator。 |
| `src/slay_the_spire/use_cases/event_action.py` | 事件奖励统一走 apply 并安全降级 | ✓ VERIFIED | `225-233` 统一金币；`414-457` 统一遗物；`479-491` 非法 payload completed no-op。 |
| `src/slay_the_spire/domain/rewards/reward_generator.py` | 随机奖励池过滤与战后/Boss 生成 | ✓ VERIFIED | `19-38,225-322` 实现 placeholder 过滤与 combat/boss 奖励生成。 |
| `src/slay_the_spire/app/session.py` | session 领取路由、宝箱/Boss 奖励接线 | ✓ VERIFIED | `439-521,640-749` 更新 `claimed_reward_ids`、宝箱/Boss 领奖与去重。 |
| `src/slay_the_spire/app/menu_definitions.py` | 奖励菜单中文反馈与 unavailable 标签 | ✓ VERIFIED | `_reward_label()` / `build_reward_menu()` / `build_boss_relic_menu()` 位于 `385-531`。 |
| `tests/use_cases/test_apply_reward.py` | 统一动作与经济遗物回归 | ✓ VERIFIED | 984 行实质测试，覆盖 apply、combat、boss、treasure、placeholder。 |
| `tests/use_cases/test_opening_flow.py` | Neow 奖励与经济联动回归 | ✓ VERIFIED | `84-175` 覆盖 potion/upgrade/gold 与 sozu/golden_idol/ectoplasm。 |
| `tests/use_cases/test_shop_and_rest_actions.py` | 商店/休息点联动回归 | ✓ VERIFIED | `127-139,198-357,423-449,708-781` 覆盖 sozu/the_courier/dream_catcher/apply wiring。 |
| `tests/use_cases/test_event_actions.py` | 事件奖励与异常降级回归 | ✓ VERIFIED | `174-213,262-353,394-403` 覆盖 golden_idol/ectoplasm/relic routing/invalid payload。 |
| `README.md` | phase 03 覆盖与验证命令 | ✓ VERIFIED | `162-191` 明确记录统一协议、placeholder 策略与命令。 |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `reward_actions.py` | `apply_reward.py` | `parse_reward_action -> apply_reward_action` | ✓ WIRED | `apply_reward.py:8,376-380` 导入并调用 `parse_reward_action()`，再进入 `apply_reward_action()`。`gsd-tools` 对该计划的 regex 误报为无效模式，人工读取确认接线存在。 |
| `opening_flow.py / shop_action.py / rest_action.py / event_action.py` | `apply_reward.py` | 入口统一调用 apply | ✓ WIRED | `opening_flow.py:330-378`、`shop_action.py:293-297`、`rest_action.py:109-154`、`event_action.py:53-55,182-233`。`gsd-tools` 对 `*_action.py` 通配写法误报 source not found，人工核对通过。 |
| `session.py` | `apply_reward.py` | `claim_reward` / treasure / boss claim | ✓ WIRED | `session.py:503-507,666-670,729-733`。 |
| `reward_generator.py` | `start_run.py` / `opening_flow.py` | `rewardable_relic_ids_for_pool(...)` | ✓ WIRED | `start_run.py:21-33` 与 `opening_flow.py:270-280` 都导入并使用共享过滤 helper。 |
| `menu_definitions.py` | app tests | 奖励文案与 unavailable 标签断言 | ✓ WIRED | `test_menu_definitions.py:439-591`、`test_inspect_menus.py:425-538`。 |
| `reward_generator.py` | use-case tests | combat/boss economy assertions | ✓ WIRED | `test_apply_reward.py:181-376,598-660` 与 `test_start_run.py:144-193`。 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `src/slay_the_spire/app/menu_definitions.py` | `room_state.rewards` in `build_reward_menu()` | 来自 combat/boss generator、rest dream rewards、session treasure/boss/claim 流程，随后经 `_reward_label()` 解析 registry 内容 | Yes — `reward_generator.py:225-322`、`rest_action.py:173-181`、`session.py:640-749` 产生真实 reward id 列表 | ✓ FLOWING |
| `src/slay_the_spire/app/session.py` | `updated_run_state` / `claimed_reward_ids` | `apply_reward(...)` + `_room_with_rewards_claimed(...)` | Yes — `apply_reward.py:285-380` 真实变更 gold/deck/relics/potions，`session.py:439-465` 同步 room_state | ✓ FLOWING |
| `src/slay_the_spire/use_cases/opening_flow.py` | `reward_payload["reward_id"]` | `_build_reward_payload()` 基于 registry / relic pool / rng 生成，再由 `_apply_reward()` 消费 | Yes — `opening_flow.py:162-199,320-379` 使用真实内容注册表与种子 RNG | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| 统一 apply 动作可运行 | `uv run pytest tests/use_cases/test_apply_reward.py -k "transform_replaces_target_card_and_preserves_suffix or duplicate_adds_new_instance_without_replacing_original or placeholder_relic_is_safe_noop" -x` | `3 passed` | ✓ PASS |
| Neow / 事件 / 商店 / 休息点复用统一奖励链路 | `uv run pytest tests/use_cases/test_opening_flow.py tests/use_cases/test_event_actions.py tests/use_cases/test_shop_and_rest_actions.py -k "routes_potion_reward_through_apply_reward_chain or event_reward_relic_routes_through_apply_reward_replacement_rules or shop_buy_relic_routes_through_apply_reward_replacement_rules or dream_catcher_rest_adds_three_card_reward_choices" -x` | `4 passed` | ✓ PASS |
| 奖励菜单反馈与 session 领取流程一致 | `uv run pytest tests/app/test_menu_definitions.py tests/app/test_inspect_menus.py -k "labels_unified_reward_actions or claiming_unified_reward_actions_updates_state_and_claimed_ids or marks_placeholder_rewards_as_unavailable" -x` | `3 passed` | ✓ PASS |
| 宝箱奖励流程可恢复且不重复应用 | `uv run pytest tests/use_cases/test_room_recovery.py -k "open_treasure_via_menu_grants_relic_marks_room_resolved_and_is_not_reapplied_after_load" -x` | `1 passed` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| REWARD-01 | 03-01, 03-02, 03-03 | 所有奖励入口使用一致标识和 apply 流程 | ✓ SATISFIED | 统一解析/执行在 `reward_actions.py` + `apply_reward.py`；入口接线覆盖 `opening_flow.py`、`shop_action.py`、`rest_action.py`、`event_action.py`、`session.py`；菜单与领取测试覆盖。 |
| REWARD-02 | 03-04 | 随机池不投放 placeholder，固定未实现奖励不破流程 | ✓ SATISFIED | `reward_generator.py:19-38` 过滤；`apply_reward.py` safe no-op；`menu_definitions.py` 标明 unavailable；对应 tests 通过。 |
| REWARD-03 | 03-01, 03-02, 03-03, 03-04 | 各类奖励有可验证行为与玩家反馈 | ✓ SATISFIED | `apply_reward.py:285-370` + `menu_definitions.py:385-469` + `test_apply_reward.py` / app tests。 |
| REWARD-04 | 03-02, 03-05 | 经济遗物在各入口按规则生效 | ✓ SATISFIED | combat/boss/shop/event/treasure/neow/rest 均有实现与测试，见 `test_apply_reward.py`、`test_event_actions.py`、`test_shop_and_rest_actions.py`、`test_opening_flow.py`、`test_room_recovery.py`。 |

**Requirement IDs from PLAN frontmatter:** REWARD-01, REWARD-02, REWARD-03, REWARD-04 — 全部已在 `REQUIREMENTS.md` 中找到并已逐项核对。  
**Orphaned requirements for Phase 3:** None.

### Anti-Patterns Found

未在 phase 03 相关源码/测试中发现会阻断目标的 TODO、placeholder 注释、空实现或仅日志实现。  
`gsd-tools verify key-links` 对 03-01/03-02 出现的是模式/通配符层面的工具误报，不是代码接线缺失。

### Human Verification Required

### 1. 真实 Textual 奖励菜单流

**Test:** 启动 TUI，依次进入包含混合奖励（金币、卡牌奖励、升级/复制/跳过）的奖励菜单，实际领取并返回。  
**Expected:** 编号顺序、中文标签、领取后菜单刷新、返回根菜单时机与自动化断言一致，没有视觉混乱或误导。  
**Why human:** 自动化验证了状态与字符串，但未验证真实终端布局、焦点/滚动和玩家体感。

### 2. 未实现奖励在宝箱/Boss 宝箱中的可理解性

**Test:** 在 TUI 中打开普通宝箱或 Boss 宝箱，观察 placeholder/unknown relic 的显示与可选行为。  
**Expected:** “未实现/不可用”标签清晰，不会让玩家误以为奖励已正常生效；可领取与不可用状态可直观看懂。  
**Why human:** 这属于真实 UI 呈现与语义清晰度检查，无法仅靠单元测试确认。

### Gaps Summary

未发现阻断 phase 03 目标达成的自动化缺口。统一 reward id / apply 链路、placeholder 安全策略、玩家反馈文本以及经济遗物跨入口行为都已有代码和测试证据。剩余事项仅为真实 Textual TUI 的视觉与交互一致性人工确认，因此本次结论为 **human_needed** 而非 `passed`。

---

_Verified: 2026-04-11T12:49:06Z_  
_Verifier: the agent (gsd-verifier)_
