# Project Research Summary

**Project:** Slay the Spire TUI 原版 1 代复刻
**Domain:** 本地单机、内容驱动的回合制 roguelike TUI 复刻
**Researched:** 2026-04-11
**Confidence:** HIGH

## Executive Summary

该项目是一个 Python 3.12 + Textual + Rich 的本地单机 TUI 复刻工程，目标不是“做新游戏”，而是按原版《Slay the Spire》1 代规则与内容补齐可完整回放的一局流程。研究一致结论是：继续沿用现有分层单体与 JSON 内容驱动架构，不换栈、不并行开新界面、不引入服务端与数据库，把投入集中在“内容接入 + 规则实现 + 路由编排 + 测试护栏”。

roadmap 的主线应先补“可完整通关闭环”（Act3 与终局链路），再补“可玩质量闭环”（奖励/掉落去占位化、事件与非战斗分支），然后再做多角色扩展。顺序上以依赖为准：测试与契约护栏先行，战斗核心先于奖励系统，奖励系统先于复杂非战斗，再做跨幕总链路验收。

最大风险不是“缺内容”，而是“规则与状态机在批量接入时漂移”：`effect_resolver` 膨胀、`session.py` 分支失控、内容录入但入口未接通、存档 round-trip 脱节。缓解策略是把每批验收固定为同构包：`content` + `domain/use_cases/session` + `presentation/textual` + 对应测试。

## Key Findings

### Recommended Stack

**栈约束（保持不变）：**
- Python 3.12+：主运行时与领域逻辑基线，现有代码/测试全部围绕此版本。
- Textual（`>=8.1.1`）+ Rich（`>=14.3.3`）：唯一交互界面与共享渲染层，不走双轨 UI。
- pytest + uv：测试与环境管理统一入口，保证批量内容接入时可回归。
- `content/*.json` + JSON save（`schema_version=3`）：内容真源与本地存档基线。

**明确不要引入：**
- Web 前端栈、桌面 GUI、服务端/API、数据库、外部云服务、多人联机。
- STS2 机制默认化（除非需求显式切换）。

### Expected Features

**当前 roadmap 的 table stakes（必须项）：**
- 三幕主线闭环：Act1/2/3、每幕 Boss、Boss Chest、`next_act/victory` 完整链路。
- 奖励与掉落可用化：不再投放 placeholder 遗物，战后/Boss/商店/事件入口一致。
- 角色与卡池扩展路径：先用 Silent 验证多角色架构，再扩 Defect/Watcher。
- 敌人/遭遇与事件池补齐：保证战斗与非战斗都可持续驱动构筑。
- 存档与回放一致性：`schema_version=3` 下 round-trip 可验证。

**建议后置（v2+ 或下一里程碑）：**
- Ascension 与概率/数值精调。
- 大规模 Monte Carlo 长跑与高级诊断视图。

### Architecture Approach

沿用“`content/*.json -> catalog/registries -> provider -> domain/use_cases -> session -> presentation/textual`”单向流水线；`session.py` 只做编排，业务规则下沉到 `domain/use_cases`，UI 不写规则特判。新增机制优先复用既有 effect/hook/reward 通道，不开平行实现。

**Major components:**
1. Content Catalog/Registries：加载并校验角色、卡牌、敌人、事件、遗物、药水、acts。
2. Domain + Use Cases：实现战斗、奖励、事件、商店、休息点、存读档等规则。
3. Session + Adapters（Rich/Textual）：菜单路由、状态流转与终端交互呈现。

### Critical Pitfalls

1. **`effect_resolver` 膨胀导致触发时序漂移**：先做 effect schema 与顺序断言测试，再批量接卡牌/遗物。
2. **`session.py` 路由膨胀导致状态机回归**：建立 mode->handler 分发表与迁移矩阵测试，禁止在 UI 层补漏洞。
3. **内容“已录入”但“不可触达”**：录入与入口联通分 phase，维护“来源->内容 ID”可触达矩阵。
4. **存档结构与运行态脱节**：新增字段必须绑定 save/load round-trip 测试，必要时显式 schema 决策。
5. **房间扩展只改一层**：强制 map/use_case/session/presentation/textual 四层闭环交付。

## Implications for Roadmap

### Phase 1: 护栏与契约先行
**Rationale:** 后续是高密度内容接入，不先建护栏会放大回归成本。  
**Delivers:** `session` 路由契约测试、effect 表驱动测试、reward generate/apply 一致性测试。  
**Addresses:** 存档与回放一致性、状态机稳定性。  
**Avoids:** 路由膨胀与规则时序漂移。

### Phase 2: Act3 与终局主线闭环
**Rationale:** “能完整跑完一局”是 1 代复刻最小定义。  
**Delivers:** Act3 内容（地图/敌人/遭遇/Boss）与 `boss -> boss_chest -> next_act/victory` 全链路。  
**Addresses:** 三幕主线 table stakes。  
**Avoids:** 跨幕链路断裂与菜单模式错位。

### Phase 3: 奖励与掉落去占位化
**Rationale:** 可玩性瓶颈在奖励可信度，而不是单纯内容数量。  
**Delivers:** placeholder 过滤、遗物/药水可用投放、战后/Boss/商店/事件入口一致。  
**Addresses:** 奖励系统完整性 table stakes。  
**Avoids:** “数据存在但拿不到/拿到无效果”。

### Phase 4: 事件与非战斗系统扩容
**Rationale:** 在战斗与奖励稳定后补足路径决策密度。  
**Delivers:** Act1/2 事件补齐、商店/休息点/宝箱行为细化，逐步推进到 Act3 事件。  
**Addresses:** 非战斗体验 table stakes。  
**Avoids:** 只剩战斗的单调流程与房间层断裂。

### Phase 5: 多角色扩展（先 Silent）
**Rationale:** 用第二角色验证架构扩展性，尽早暴露卡池隔离与机制耦合问题。  
**Delivers:** Silent 角色端到端（起始套牌、核心机制、奖励池联动）。  
**Addresses:** 角色全集路线中的首个扩展样板。  
**Avoids:** 后期一次性并发扩角色导致返工。

### Phase 6: Defect/Watcher 与全量收敛
**Rationale:** 在前述链路稳定后进入高复杂机制收尾。  
**Delivers:** Defect/Watcher、剩余敌人/事件/遗物/药水与全池回归。  
**Addresses:** 完整复刻闭环。  
**Avoids:** 过早并发导致的跨系统不一致。

### Phase Ordering Rationale

- 依赖上必须遵循：护栏 -> 战斗主线 -> 奖励经济 -> 非战斗分支 -> 多角色扩展 -> 全量收敛。
- 架构上遵循单向流水线，避免 UI/Session 侧写入规则特判。
- 验收上统一“内容+规则+路由+展示+测试”同构交付，降低隐性技术债。

### Research Flags

需要在 phase planning 时深挖（建议 `/gsd-research-phase`）：
- **Phase 3（奖励与掉落去占位化）**：涉及投放策略统一、入口一致性与大量遗物触发时机。
- **Phase 5（Silent）**：多角色卡池隔离、弃牌/毒机制与现有效果引擎耦合高。
- **Phase 6（Defect/Watcher）**：充能球/姿态等机制复杂，触发时序风险高。

可按标准模式直接推进（可跳过额外 research）：
- **Phase 1（护栏与契约）**：测试与抽象目标清晰，已有现成文件与测试入口。
- **Phase 2（Act3 主线闭环）**：路径明确，主要是内容接入与既有链路扩展。

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | 与 AGENTS/README/pyproject/现有代码结构完全一致，约束清晰。 |
| Features | HIGH | table stakes 与当前缺口有明确清单和数量基线。 |
| Architecture | HIGH | 分层边界与接入链路已在代码中稳定存在。 |
| Pitfalls | HIGH | 风险点与现有技术债（session/effect/reward/save）直接对应。 |

**Overall confidence:** HIGH

### Gaps to Address

- 原版细节“数值/概率”仍需后续逐条校准：先保规则正确，再做平衡精修。
- 事件与敌人完整覆盖率需要持续量化看板：建议区分“已录入”和“可触达”两类指标。

## Sources

### Primary
- `.planning/research/STACK.md`
- `.planning/research/FEATURES.md`
- `.planning/research/ARCHITECTURE.md`
- `.planning/research/PITFALLS.md`
- `.planning/PROJECT.md`

### Supporting
- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONCERNS.md`
- `.planning/codebase/TESTING.md`

---
*Research completed: 2026-04-11*  
*Ready for roadmap: yes*
