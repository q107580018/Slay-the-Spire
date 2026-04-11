# Roadmap: Slay the Spire TUI 原版复刻

## Overview

本路线图以原版 1 代复刻闭环为目标，按“护栏稳定性 -> 三幕可通关 -> 奖励经济可信 -> 非战斗扩容 -> 多角色扩展 -> 全量验证收敛”推进，持续保持 Python/Textual/Rich 本地单机 TUI 边界。

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: 护栏与交付契约** - 先建立稳定回归与内容可触达校验，锁定后续批量开发节奏。
- [x] **Phase 2: 三幕主线闭环** - 打通 Act 1 -> Act 3 -> Boss Chest -> Victory 的可游玩主线。 (completed 2026-04-11)
- [ ] **Phase 3: 奖励与经济统一** - 统一奖励入口与应用链路，清理 placeholder 投放风险。
- [ ] **Phase 4: 非战斗系统扩容** - 补齐事件与非战斗房间规则，并统一 Textual/Rich 表现。
- [ ] **Phase 5: 多角色基础与 Silent** - 建立多角色隔离并完成 Silent 端到端可玩。
- [ ] **Phase 6: 高复杂角色与战斗规则收敛** - 完成 Defect/Watcher 与复杂战斗/卡牌规则收敛。
- [ ] **Phase 7: 全量验证与文档收敛** - 产出缺口报告、固定 seed 烟测与文档覆盖率对齐。

## Phase Details

### Phase 1: 护栏与交付契约
**Goal**: 开发者可稳定验证 session/reward/effect/save-load 关键链路，并对新增内容批次执行统一验收。
**Depends on**: Nothing (first phase)
**Requirements**: GUARD-01, GUARD-02, GUARD-03
**Success Criteria** (what must be TRUE):
  1. 开发者可以运行一组回归测试，覆盖 session 菜单模式、跨幕推进、reward generate/apply、effect 时序和 save/load round-trip。
  2. 覆盖校验报告能区分“已录入”与“可触达”，并明确列出 placeholder 遗物和未接入奖励池内容。
  3. 每次新增内容批次都能按统一验收清单落地，且提交中可观察到 `content/`、registry、domain/use case、session、presentation/Textual、README 的对应更新。
**Plans:** 3 plans
Plans:
- [x] 01-01-PLAN.md — 注册 pytest guardrail marker 并标记关键回归测试
- [x] 01-02-PLAN.md — 建立内容可触达报告并过滤 placeholder 随机遗物池
- [x] 01-03-PLAN.md — 在 README 固化 guardrail 命令与新增内容批次验收清单

### Phase 2: 三幕主线闭环
**Goal**: 玩家可从新开局走完三幕并完成终局结算，主线状态在存读档后保持一致。
**Depends on**: Phase 1
**Requirements**: RUN-01, RUN-02, RUN-03, COMBAT-01
**Success Criteria** (what must be TRUE):
  1. 玩家可以从新开局连续推进 Act 1 -> Act 2 -> Act 3 -> Boss Chest -> Victory。
  2. Act 3 地图与房间（普通战斗、精英、Boss、Boss 宝箱）可在 Textual 菜单中正常进入、展示和结算。
  3. 任意三幕流程中保存、读取和继续游戏后，状态一致且 `schema_version=3` round-trip 不破坏流程。
  4. 原版普通敌人/精英/Boss 与遭遇组至少具备按幕触达入口（地图或测试入口可验证）。
**Plans:** 3/3 plans complete
Plans:
- [x] 02-01-PLAN.md — 录入 Act 3 全量敌人/遭遇组/事件与地图配置，更新 Act 2 跨幕链接
- [x] 02-02-PLAN.md — 扩展胜利/失败面板为包含运行统计的结算画面
- [x] 02-03-PLAN.md — 新增三幕 E2E smoke 测试、更新跨幕边界测试、验证存档 round-trip
**UI hint**: yes

### Phase 3: 奖励与经济统一
**Goal**: 奖励系统在所有入口使用一致标识和 apply 流程，玩家获得结果可信且可反馈。
**Depends on**: Phase 2
**Requirements**: REWARD-01, REWARD-02, REWARD-03, REWARD-04
**Success Criteria** (what must be TRUE):
  1. 战后、Boss、商店、事件、宝箱、Neow、休息点的奖励入口都走统一奖励标识与 apply 链路。
  2. 随机奖励池默认不投放未实现或 placeholder 遗物；若明确标记未实现，也不会破坏流程。
  3. 金币、卡牌奖励、遗物、药水、移除、升级、转换、复制、跳过等奖励类型都有可验证结果与玩家反馈。
  4. 奖励经济相关遗物效果在对应入口按规则触发并可通过测试验证。
**Plans**: 5 plans
Plans:
- [x] 03-01-PLAN.md — 建立统一 reward action 协议并扩展 apply_reward 核心
- [x] 03-02-PLAN.md — 先收敛 use case 入口（Neow/商店/事件/休息点）到统一奖励协议
- [x] 03-03-PLAN.md — 再对齐 session/menu 奖励路由与中文反馈文案
- [x] 03-04-PLAN.md — 独立完成 placeholder 安全过滤与固定奖励降级反馈
- [ ] 03-05-PLAN.md — 建立奖励经济遗物跨入口回归矩阵并同步 README
**UI hint**: yes

### Phase 4: 非战斗系统扩容
**Goal**: 事件与非战斗房间规则按原版 1 代扩展，且交互与展示一致可用。
**Depends on**: Phase 3
**Requirements**: EVENT-01, EVENT-02, EVENT-03
**Success Criteria** (what must be TRUE):
  1. 原版事件可按幕触发，玩家可选择选项并观察代价、奖励与牌组/遗物/金币/生命变化。
  2. 商店、休息点、普通宝箱、Boss 宝箱、Neow 的关键交互及相关遗物联动都可验证。
  3. 非战斗房间的 Textual 展示、hover/inspect 信息、菜单编号和错误提示与共享 Rich 展示一致。
**Plans**: TBD
**UI hint**: yes

### Phase 5: 多角色基础与 Silent
**Goal**: 建立多角色隔离能力，并完成 Silent 从开局到终局的端到端可玩。
**Depends on**: Phase 4
**Requirements**: CHAR-01, CHAR-02
**Success Criteria** (what must be TRUE):
  1. 角色系统可在角色选择中区分并加载独立初始牌组、卡池、角色状态与奖励池过滤规则。
  2. Silent 可端到端游玩三幕流程，弃牌/毒等核心机制在战斗与奖励链路中生效。
  3. Silent 相关卡牌升级、奖励池接入与展示文本一致，玩家可直接在 TUI 中验证。
**Plans**: TBD
**UI hint**: yes

### Phase 6: 高复杂角色与战斗规则收敛
**Goal**: 完成 Defect/Watcher 与复杂战斗规则整合，使全卡池与关键字机制可组合运行。
**Depends on**: Phase 5
**Requirements**: CHAR-03, CHAR-04, COMBAT-02, COMBAT-03, CARD-01
**Success Criteria** (what must be TRUE):
  1. Defect 可端到端游玩，充能球机制在战斗内外流程可验证。
  2. Watcher 可端到端游玩，姿态机制在战斗与奖励链路可验证。
  3. 敌人意图、行动模式、多敌人战斗与特殊 buff/debuff 时序按规则运行，关键分支有领域测试覆盖。
  4. 状态牌、诅咒牌、无色牌和复杂关键字（消耗/保留/虚无/抽弃牌/牌堆移动）可与全角色卡池组合运行并验证。
**Plans**: TBD
**UI hint**: yes

### Phase 7: 全量验证与文档收敛
**Goal**: 项目具备面向复刻范围的缺口可视化、固定 seed 烟测与文档同步机制。
**Depends on**: Phase 6
**Requirements**: VALID-01, VALID-02, VALID-03
**Success Criteria** (what must be TRUE):
  1. 项目可产出缺口报告，列出未录入、已录入未实现、已实现未触达的角色/卡牌/敌人/事件/遗物/药水。
  2. 至少一条固定 seed 的 E2E 烟测覆盖三幕推进、奖励选择、存档读取与胜利/失败终局。
  3. README 与本地 wiki 同步反映覆盖率、运行命令、内容真源和已知未实现范围。
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. 护栏与交付契约 | 0/3 | Not started | - |
| 2. 三幕主线闭环 | 3/3 | Complete    | 2026-04-11 |
| 3. 奖励与经济统一 | 3/5 | In Progress|  |
| 4. 非战斗系统扩容 | 0/3 | Not started | - |
| 5. 多角色基础与 Silent | 0/2 | Not started | - |
| 6. 高复杂角色与战斗规则收敛 | 0/4 | Not started | - |
| 7. 全量验证与文档收敛 | 0/2 | Not started | - |
