# Slay the Spire TUI 原版复刻

## What This Is

这是一个基于 Python 3.12、Textual 和 Rich 的本地单机 TUI 版《杀戮尖塔》复刻项目。当前已有可运行的菜单驱动原型，后续目标是按批次补齐原版《Slay the Spire》1 代的角色、卡牌、遗物、事件、敌人、Boss、奖励、房间流程与规则交互。

## Core Value

玩家可以在终端中完成一局尽可能贴近原版 1 代规则与内容的《杀戮尖塔》流程，并且运行结果可存档、可回放、可测试。

## Requirements

### Validated

- ✓ Textual TUI 是默认且唯一运行界面，底层复用 Rich 展示组件 — existing
- ✓ CLI 支持新开局与读取存档，并支持 `--seed`、`--character`、`--content-root`、`--save-path` 等本地运行参数 — existing
- ✓ 当前会话层支持 opening、角色选择、Neow 奖励、地图推进、菜单路由、跨幕推进与胜利流程 — existing
- ✓ 当前房间类型覆盖普通战斗、事件、精英、商店、休息点、宝箱、Boss、Boss 宝箱 — existing
- ✓ 当前已支持 Act 1 到 Act 2 的主流程，Act 2 Boss 宝箱后进入 victory — existing
- ✓ 当前已有战斗状态、出牌、结束回合、战斗奖励、Boss 奖励、遗物、药水、商店、休息点升级/跳过等核心系统 — existing
- ✓ Phase 03 已统一战斗奖励、Boss 奖励、商店、事件、宝箱、Neow 与休息点的奖励标识与 apply 流程，并为 placeholder/未实现奖励提供安全降级与可见反馈 — Validated in Phase 03: 奖励与经济统一
- ✓ Phase 03 已为奖励经济相关遗物建立 combat、boss、shop、event、treasure、neow、rest 七类入口的自动化回归证据，并修复宝箱/Boss 宝箱不可用奖励被错误消耗的问题 — Validated in Phase 03: 奖励与经济统一
- ✓ 当前内容以根目录 `content/` 为开发期真源，并通过注册表加载角色、卡牌、敌人、事件、遗物、药水、幕配置等 JSON 内容 — existing
- ✓ 当前 JSON 存档 schema version 为 `3`，默认存档路径为 `saves/latest.json` — existing
- ✓ 当前测试覆盖 app、use case、domain、content validation、Textual adapter 与 E2E smoke 等关键层级 — existing
- ✓ 当前铁甲战士红卡已按原版 1 代补齐，部分复杂卡牌机制已落地 — existing
- ✓ 当前原版 1 代遗物目录已录入 180 种，其中一部分效果已完整实现，剩余遗物以 `implementation_status` 标记 — existing

### Active

- [ ] 按原版 1 代补齐所有角色及其初始牌组、角色状态、角色专属机制与运行时规则。
- [ ] 按原版 1 代补齐所有角色卡牌、无色牌、诅咒牌、状态牌及其升级、费用、目标、消耗、保留、虚无、抽弃牌、牌堆移动等规则。
- [ ] 按原版 1 代补齐所有遗物目录与运行时效果，包括战斗、奖励、商店、休息点、地图、Boss、事件、Neow、牌堆与特殊触发时机。
- [ ] 按原版 1 代补齐普通敌人、精英、Boss、遭遇组、意图、行动模式、特殊 debuff/buff 与多敌人战斗行为。
- [ ] 按原版 1 代补齐事件内容、事件选项、事件结果、特殊奖励、代价、牌组/遗物/金币/生命变化与事件专属交互。
- [ ] 按原版 1 代补齐奖励系统，包括战斗奖励、Boss 遗物、金币、卡牌奖励、药水、跳过、移除、升级、转换、复制等来源。
- [ ] 按原版 1 代补齐药水目录与药水使用效果、目标选择、战斗内外限制、药水槽与相关遗物联动。
- [ ] 按原版 1 代补齐商店、休息点、宝箱、Boss 宝箱、Neow、地图生成、幕推进与胜利/失败流程的细节行为。
- [ ] 建立内容补齐批次的可验证节奏：每批新增内容都要同步内容 JSON、注册表校验、领域规则、会话路由、Textual 展示和测试。 *(Phase 1 GUARD-02 content reachability contract provides automated enforcement)*
- [ ] 持续维护本地参考资料与 README，使实现覆盖率、运行命令和内容真源说明与代码保持一致。 *(Phase 1 GUARD-03 README drift test provides automated enforcement)*

### Out of Scope

- 图形界面或 Web/桌面 GUI — 当前产品边界是 Textual TUI，本项目不是图形界面项目。
- 服务端、账号、排行榜、云存档或外部服务集成 — 当前目标是本地单机、可存读档、可回放流程。
- 多人模式、MOD 框架或创意工坊兼容 — 原版 1 代内容复刻优先，扩展生态会扩大范围。
- 默认转向《杀戮尖塔 2》资料或机制 — 当前基线是原版《Slay the Spire》1 代，除非需求明确指定。
- 兼容旧存档或旧菜单状态 — 当前开发阶段默认不保兼容，除非需求明确要求。

## Context

这是一个 brownfield 项目，已经通过 `.planning/codebase/` 建立代码库地图。当前架构是菜单驱动的分层单体：`src/slay_the_spire/app/session.py` 负责会话与菜单编排，`src/slay_the_spire/use_cases/` 承载玩家动作和房间行为，`src/slay_the_spire/domain/` 承载核心规则与状态模型，`src/slay_the_spire/adapters/` 承载 Rich/Textual 展示和 JSON 存档适配器。

当前状态：Phase 03 已完成，奖励系统已统一到 reward id + apply 链路，随机 placeholder 投放风险已收口，宝箱/Boss 宝箱的不可用奖励不会再被误领取或误消耗。下一阶段转向非战斗系统扩容。

内容开发的事实入口是根目录 `content/`。本地参考资料位于 `docs/reference/`，其中已有卡牌和遗物资料；需要外部交叉校验时，优先参考官方社区 Wiki 和中文 Wiki。当前 README 显示铁甲战士红卡已完整补齐，原版 1 代遗物已录入 180 种但仍有 102 种占位定义，后续主要工作会围绕内容覆盖率、运行时规则覆盖率和跨系统联动展开。

主要技术债集中在会话路由与效果解析器：`src/slay_the_spire/app/session.py` 和 `src/slay_the_spire/domain/effects/effect_resolver.py` 承担了大量分支与副作用。后续批量补内容时要控制改动半径，用测试约束战斗、奖励、事件、商店、休息点、地图与 Textual 展示的联动。

## Constraints

- **Tech stack**: Python 3.12+、Textual、Rich、pytest、uv — 仓库现有技术栈，后续默认沿用。
- **Content source**: 只手工维护根目录 `content/` — `src/slay_the_spire/data/content/` 是构建 wheel 时的包内内容副本，不作为开发期编辑入口。
- **UI boundary**: 默认且唯一运行界面是 Textual TUI — 新功能要优先补齐 TUI 和共享 Rich 展示。
- **Game baseline**: 默认以原版《Slay the Spire》1 代为准 — 1 代、2 代资料或旧设计文档冲突时，以当前 1 代内容基线和已落地行为优先。
- **Persistence**: 当前存档 schema version 是 `3` — 改动存档结构要同步 `save_game.py`、`load_game.py` 和相关测试。
- **Testing**: 内容、领域规则、会话路由、Textual UI 与 E2E 流程都需要按改动风险补测试 — 项目目标是可回放、可验证的本地流程。
- **Docs**: 改动代码、内容、命令入口、流程、测试基线或发布方式后同步更新 README — 只有协作约束变化才更新 AGENTS.md。

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 以原版《Slay the Spire》1 代为默认内容与规则基线 | 用户明确要求完整复刻原版游戏，仓库协作规则也默认 1 代优先 | — Pending |
| 保持 Textual TUI 为唯一运行界面 | 现有架构、README 和 AGENTS.md 都将项目定义为本地单机 TUI，不引入 GUI/Web 分支 | — Pending |
| 分批实现内容与机制，而不是一次性大爆炸补齐 | 原版内容量大且跨系统联动复杂，批次化更适合测试、回归和提交管理 | — Pending |
| 内容 JSON 只维护根目录 `content/` | 仓库约束明确，避免手工编辑包内生成内容造成漂移 | — Pending |
| 每批内容都要检查注册表、掉落入口、展示层和对应测试 | 新增角色、卡牌、敌人、事件、遗物或药水会影响加载、奖励、战斗和 UI 多个层级 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-11 after Phase 03 (奖励与经济统一) completion — unified reward id/apply flow, placeholder reward safety, and cross-entrance economy regression coverage established*
