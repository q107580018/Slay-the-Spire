# Phase 2: 三幕主线闭环 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-11
**Phase:** 02-三幕主线闭环
**Areas discussed:** Act 3 敌人/遭遇组范围, Act 3 事件与非战斗房间, 终局流程与胜利画面, E2E 测试策略

---

## Act 3 敌人/遭遇组范围

| Option | Description | Selected |
|--------|-------------|----------|
| 全量原版敌人（推荐） | 覆盖原版 Act 3 全部普通敌人、精英和 Boss（约 15+ 种敌人），包含完整行为模式和意图 | ✓ |
| 最小可玩集 | 每类（普通/精英/Boss）选 2-3 种代表性敌人完整实现，其余在后续 Phase 补齐 | |
| 定义优先，行为 stub | 只录入 JSON 定义和遭遇组配置，敌人 AI 行为用简化 stub（如固定循环攻击），后续 Phase 6 再补齐完整行为 | |

**User's choice:** 全量原版敌人
**Notes:** 与 Act 1/2 保持一致的完整度水平。

---

## Act 3 事件与非战斗房间

| Option | Description | Selected |
|--------|-------------|----------|
| 事件延后到 Phase 4（推荐） | Phase 2 只确保商店/休息/宝箱可进，事件房使用现有通用事件或空占位；完整 Act 3 事件内容留给 Phase 4 | |
| 同步补齐 Act 3 事件 | Phase 2 同时补齐 Act 3 原版事件（约 10+ 个事件），含选项、代价、奖励 | ✓ |
| 少量代表性事件 | Phase 2 先收录 3-5 个代表性 Act 3 事件作为可玩示例，其余事件留给 Phase 4 | |

**User's choice:** 同步补齐 Act 3 事件
**Notes:** 用户选择在 Phase 2 就完整录入 Act 3 事件，不等到 Phase 4。

---

## 终局流程与胜利画面

| Option | Description | Selected |
|--------|-------------|----------|
| 统计面板（推荐） | 胜利后展示简洁统计面板：层数、金币、牌组、遗物、药水、生命值，类似原版结算画面 | ✓ |
| 简单胜利文字 | 只显示"恍惚终杀"胜利文字 + 返回主菜单选项，不做统计汇总 | |
| You decide | 由实现时决定 | |

**User's choice:** 统计面板

### 失败流程

| Option | Description | Selected |
|--------|-------------|----------|
| 对称处理胜利/失败（推荐） | 生命值归零时结束战斗并展示失败统计，与胜利对称处理 | ✓ |
| 延后处理失败 | 失败流程保持现状，Phase 2 只关注胜利路径 | |

**User's choice:** 对称处理胜利/失败
**Notes:** RUN-03 要求胜利和失败都保持状态一致。

---

## E2E 测试策略

| Option | Description | Selected |
|--------|-------------|----------|
| 全程 smoke + 分幕 stub（推荐） | 固定 seed 三幕全程 smoke（每幕走最短路径）+ 分幕 stub 测试覆盖 act 边界转换 | ✓ |
| 仅全程 smoke | 只做固定 seed 三幕全程 smoke，不做分幕转换测试 | |
| 扩展现有测试 | 只在现有 two_act_smoke 基础上加 Act 3 段，不新增测试文件 | |

**User's choice:** 全程 smoke + 分幕 stub
**Notes:** 现有 test_two_act_smoke 的 act2 -> victory 断言需适配 act2 -> act3 变更。

---

## the agent's Discretion

- Act 3 地图具体配置参数（floor_count, room weights, fixed floors）
- 统计面板布局和渲染细节
- 固定 seed 选择和最短路径构造方式

## Deferred Ideas

- 奖励经济统一 — Phase 3
- 非战斗系统深度规则扩展 — Phase 4
- 高复杂度敌人行为收敛 — Phase 6
