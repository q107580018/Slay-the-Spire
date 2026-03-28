# 卡牌分类最小实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把卡牌的可获取来源与展示分类收口到显式标签上，逐步移除商店对卡牌 `can_appear_in_shop` 的依赖，同时保持当前单职业、双幕和现有 `CardInstance` 字符串实例结构不变。

**Architecture:** 先用内容校验和用例测试锁定卡牌来源语义，再迁移商店和奖励筛选的入口，最后删除卡牌层面的重复开关并做双目录内容同步。`relic` 的 `can_appear_in_shop` 继续保留，避免把卡牌和遗物的商店规则混在一起。

**Tech Stack:** Python 3.12、`uv`、`pytest`

---

## File Map

- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/use_cases/test_enter_room.py`
- Modify: `tests/use_cases/test_apply_reward.py`
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `content/cards/*.json`
- Modify: `src/slay_the_spire/data/content/cards/*.json`

### Task 1: 锁定卡牌来源标签与内容边界

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Modify: `content/cards/*.json`
- Modify: `src/slay_the_spire/data/content/cards/*.json`

- [ ] **Step 1: 写失败测试**

补充内容校验，锁定以下约束：

- 普通战斗奖励只允许从带 `combat_reward` 的卡池抽取
- 商店卡只允许从带 `shop` 的卡池抽取
- `burn` 继续标记为 `generated` / `status`
- `doubt`、`injury` 继续标记为 `event` / `curse`
- 起始牌继续保留 `starter` 标签

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/content/test_registry_validation.py -q`

- [ ] **Step 3: 做最小实现**

同步两套内容目录，补齐或修正卡牌标签，确保：

- 商店牌池有明确 `shop` 标签
- 战斗奖励牌池有明确 `combat_reward` 标签
- 生成牌、事件牌、诅咒牌都有显式来源标签

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/content/test_registry_validation.py -q`

### Task 2: 迁移商店卡筛选入口

**Files:**
- Modify: `tests/use_cases/test_enter_room.py`
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`

- [ ] **Step 1: 写失败测试**

补测试锁定商店牌池来源：

- 商店牌只从带 `shop` 标签的卡中抽取
- `doubt`、`injury`、`burn` 不会进商店
- 遗物商店仍沿用遗物自己的 `can_appear_in_shop`

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/use_cases/test_enter_room.py tests/use_cases/test_start_run.py -q`

- [ ] **Step 3: 做最小实现**

把 `_build_shop_payload()` 中的卡牌筛选从 `card.can_appear_in_shop` 迁移到 `card.acquisition_tags`，优先认 `shop` 标签。

如果内容还没完全迁移完，允许短期保留兼容分支，但新内容必须走标签。

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/use_cases/test_enter_room.py tests/use_cases/test_start_run.py -q`

### Task 3: 统一普通奖励与来源标签

**Files:**
- Modify: `tests/use_cases/test_apply_reward.py`
- Modify: `src/slay_the_spire/domain/rewards/reward_generator.py`

- [ ] **Step 1: 写失败测试**

补测试锁定：

- 普通战斗奖励只采样带 `combat_reward` 的卡
- `status` / `curse` 卡不会进入普通奖励池
- 奖励池不会依赖“看效果推导类型”这类隐式规则

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -q`

- [ ] **Step 3: 做最小实现**

保持现有奖励生成流程不变，只强化筛选条件和内容标签约束。

如果后续确实需要扩展精英、Boss、事件或生成牌的来源语义，再按同一套标签体系补独立配置，避免继续堆隐式约定。

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -q`

### Task 4: 删除卡牌层面的重复开关并全量回归

**Files:**
- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/use_cases/test_enter_room.py`
- Modify: `tests/use_cases/test_start_run.py`

- [ ] **Step 1: 写失败测试**

补测试锁定：

- 卡牌内容不再依赖 `can_appear_in_shop`
- 只有遗物继续保留 `can_appear_in_shop`
- 迁移后商店和奖励行为不回退

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/content/test_registry_validation.py tests/use_cases/test_enter_room.py tests/use_cases/test_start_run.py -q`

- [ ] **Step 3: 做最小实现**

删除 `CardDef` 上的重复商店开关，并同步调整卡牌注册、商店筛选和测试断言。

保留遗物层面的 `can_appear_in_shop`，不要把两类内容的规则混在一起。

- [ ] **Step 4: 运行全量相关测试**

Run: `uv run pytest tests/content/test_registry_validation.py tests/use_cases/test_enter_room.py tests/use_cases/test_start_run.py tests/use_cases/test_apply_reward.py -q`

- [ ] **Step 5: 做最终检查**

确认两套内容目录一致，且没有残留的卡牌商店开关依赖。

如果后续要继续推进 `CardInstance`、多职业或无色牌池，另起新计划，不要塞进本次最小迁移。
