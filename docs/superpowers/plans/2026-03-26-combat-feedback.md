# Combat Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让主战斗页能持续显示最近战斗记录，并让敌人意图根据当前战斗状态动态展示。

**Architecture:** 继续复用 `CombatState.log` 作为日志承载，在战斗用例层追加“结算结果 -> 中文日志”转换，不把终端文案塞进纯领域结算。终端战斗页增加一个日志面板，并把敌人意图切换到基于 `preview_enemy_move(...)` 的动态预览。

**Tech Stack:** Python 3.12, pytest, rich

---

### Task 1: 先锁定战斗日志行为

**Files:**
- Modify: `src/slay_the_spire/use_cases/play_card.py`
- Modify: `src/slay_the_spire/use_cases/end_turn.py`
- Test: `tests/use_cases/test_play_card.py`
- Test: `tests/domain/test_combat_flow.py`

- [ ] **Step 1: 写失败测试，定义玩家出牌日志**

在 `tests/use_cases/test_play_card.py` 新增测试，验证打出 `strike` 后：

- `combat_state.log` 追加中文日志
- 日志包含卡牌名、目标敌人名和造成伤害

- [ ] **Step 2: 运行单测，确认按预期失败**

Run: `uv run pytest tests/use_cases/test_play_card.py -q`
Expected: FAIL，提示日志内容缺失或不匹配

- [ ] **Step 3: 写失败测试，定义敌人回合日志**

在 `tests/domain/test_combat_flow.py` 或 `tests/use_cases` 新增测试，验证结束回合后：

- 敌人攻击日志包含基础伤害、格挡抵消和实际掉血
- 睡眠敌人会写入“沉睡，暂不行动”

- [ ] **Step 4: 运行单测，确认按预期失败**

Run: `uv run pytest tests/domain/test_combat_flow.py -q`
Expected: FAIL，提示日志内容缺失或不匹配

### Task 2: 实现日志组装与裁剪

**Files:**
- Create: `src/slay_the_spire/use_cases/combat_log.py`
- Modify: `src/slay_the_spire/use_cases/play_card.py`
- Modify: `src/slay_the_spire/use_cases/end_turn.py`
- Modify: `src/slay_the_spire/domain/models/combat_state.py`
- Test: `tests/use_cases/test_play_card.py`
- Test: `tests/domain/test_combat_flow.py`

- [ ] **Step 1: 在新模块中实现日志辅助函数**

实现职责：

- 采集最小的结算前快照
- 把 `resolved_effects` 转成中文日志
- 向 `combat_state.log` 追加并裁剪到最近固定条数

- [ ] **Step 2: 在 `play_card` 中接入日志**

在出牌前记录必要快照，结算后追加：

- 打出了哪张牌
- 对谁造成了多少伤害
- 是否获得格挡 / 抽牌 / 施加易伤

- [ ] **Step 3: 在 `end_turn` 中接入日志**

在敌人回合前记录玩家血量与格挡，结算后追加：

- 哪个敌人行动了
- 伤害、格挡吸收、实际掉血
- 睡眠敌人的提示

- [ ] **Step 4: 跑相关测试，确认转绿**

Run: `uv run pytest tests/use_cases/test_play_card.py tests/domain/test_combat_flow.py -q`
Expected: PASS

### Task 3: 先锁定动态意图与渲染

**Files:**
- Modify: `src/slay_the_spire/adapters/terminal/screens/combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/widgets.py`
- Test: `tests/adapters/terminal/test_renderer.py`

- [ ] **Step 1: 写失败测试，定义战斗记录面板渲染**

在 `tests/adapters/terminal/test_renderer.py` 新增测试，验证主战斗页：

- 出现 `战斗记录`
- 能显示最近日志内容

- [ ] **Step 2: 写失败测试，定义动态敌人意图**

新增测试，验证：

- 睡眠中的 `lagavulin` 显示睡眠
- 苏醒后显示攻击意图

- [ ] **Step 3: 运行测试，确认按预期失败**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py -q`
Expected: FAIL，提示日志面板或意图文案缺失

### Task 4: 实现战斗页改动

**Files:**
- Modify: `src/slay_the_spire/adapters/terminal/screens/combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/widgets.py`
- Test: `tests/adapters/terminal/test_renderer.py`

- [ ] **Step 1: 新增战斗记录面板**

在主战斗页主体下方增加 `战斗记录` 面板，显示最近 5 条日志；无日志时显示占位文本。

- [ ] **Step 2: 把敌人意图改成动态预览**

战斗页敌人面板不再直接使用静态定义摘要，而是基于当前 `CombatState` 的 `preview_enemy_move(...)` 渲染。

- [ ] **Step 3: 跑渲染测试，确认转绿**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py -q`
Expected: PASS

### Task 5: 全量回归相关测试

**Files:**
- Test: `tests/use_cases/test_play_card.py`
- Test: `tests/domain/test_combat_flow.py`
- Test: `tests/adapters/terminal/test_renderer.py`
- Test: `tests/e2e/test_single_act_smoke.py`

- [ ] **Step 1: 跑聚焦测试集**

Run: `uv run pytest tests/use_cases/test_play_card.py tests/domain/test_combat_flow.py tests/adapters/terminal/test_renderer.py tests/e2e/test_single_act_smoke.py -q`
Expected: PASS

- [ ] **Step 2: 如有必要，再跑全量测试**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 3: 整理最终结果**

记录：

- 新增了哪些玩家可见反馈
- 哪些测试验证了行为
- 是否有未覆盖的残余风险
