# Requirements: Slay the Spire TUI 原版复刻

**Defined:** 2026-04-11
**Core Value:** 玩家可以在终端中完成一局尽可能贴近原版 1 代规则与内容的《杀戮尖塔》流程，并且运行结果可存档、可回放、可测试。

## v1 Requirements

Requirements for the current roadmap. Each requirement maps to exactly one roadmap phase.

### Guardrails

- [x] **GUARD-01**: 开发者可以运行覆盖 session 菜单模式、跨幕推进、reward generate/apply、effect 时序和 save/load round-trip 的回归测试。
- [ ] **GUARD-02**: 内容覆盖校验能区分“已录入内容”和“运行时可触达内容”，并能暴露 placeholder 遗物或未接入奖励池的内容。
- [ ] **GUARD-03**: 新增内容批次有一致的验收清单，覆盖 `content/`、registry、domain/use case、session、presentation/Textual 和 README 更新。

### Mainline Run

- [ ] **RUN-01**: 玩家可以从新开局推进完整 Act 1 -> Act 2 -> Act 3 -> Boss Chest -> Victory 的主线流程。
- [ ] **RUN-02**: Act 3 地图、房间分布、普通战斗、精英、Boss 与 Boss 宝箱能通过现有 Textual TUI 正常进入、展示和结算。
- [ ] **RUN-03**: 失败、胜利、保存、读取和继续游戏在三幕流程中保持状态一致，不破坏 `schema_version=3` 存档 round-trip。

### Rewards & Economy

- [ ] **REWARD-01**: 战斗奖励、Boss 奖励、商店、事件、宝箱、Neow 与休息点相关奖励入口使用一致的奖励标识和 apply 流程。
- [ ] **REWARD-02**: 随机奖励池默认不投放未实现或 placeholder 遗物，除非 UI 明确标记其未实现状态且不会破坏流程。
- [ ] **REWARD-03**: 金币、卡牌奖励、遗物、药水、移除、升级、转换、复制、跳过等奖励类型都有可验证的行为与玩家反馈。
- [ ] **REWARD-04**: 与奖励经济相关的遗物效果在对应入口生效，包括战斗后、Boss、商店、事件、宝箱、Neow 与休息点场景。

### Combat Content

- [ ] **COMBAT-01**: 原版 1 代普通敌人、精英、Boss 与遭遇组按幕逐批录入，并可通过地图或测试入口触达。
- [ ] **COMBAT-02**: 敌人意图、行动模式、多敌人战斗、特殊 buff/debuff 与回合时序按原版规则实现，并有领域测试覆盖关键分支。
- [ ] **COMBAT-03**: 原版状态牌、诅咒牌、无色牌与复杂战斗关键字在当前 effect/hook 系统中可组合运行。

### Cards & Characters

- [ ] **CHAR-01**: 角色系统支持多角色内容隔离，包括初始牌组、卡池、角色状态、奖励池过滤和角色选择流程。
- [ ] **CHAR-02**: Silent 可以端到端游玩，包含初始牌组、完整绿卡池、升级、弃牌/毒等核心机制、奖励池接入和展示文本。
- [ ] **CHAR-03**: Defect 可以端到端游玩，包含初始牌组、完整蓝卡池、升级、充能球等核心机制、奖励池接入和展示文本。
- [ ] **CHAR-04**: Watcher 可以端到端游玩，包含初始牌组、完整紫卡池、升级、姿态等核心机制、奖励池接入和展示文本。
- [ ] **CARD-01**: 原版 1 代全角色卡、无色牌、诅咒牌和状态牌的费用、目标、升级、消耗、保留、虚无、抽弃牌和牌堆移动规则可验证。

### Events & Non-Combat

- [ ] **EVENT-01**: 原版 1 代事件按幕逐批录入，并支持选项、代价、奖励、牌组/遗物/金币/生命变化与事件专属交互。
- [ ] **EVENT-02**: 商店、休息点、普通宝箱、Boss 宝箱和 Neow 的关键交互规则与相关遗物联动可验证。
- [ ] **EVENT-03**: 非战斗房间的 Textual 展示、hover/inspect 信息、菜单编号和错误提示与共享 Rich 展示保持一致。

### Full-Game Validation

- [ ] **VALID-01**: 项目提供覆盖原版内容目录的缺口报告，能列出未录入、已录入未实现、已实现未触达的角色、卡牌、敌人、事件、遗物和药水。
- [ ] **VALID-02**: 至少一条固定 seed 的端到端烟雾流程可以覆盖三幕推进、奖励选择、存档读取和胜利/失败终局。
- [ ] **VALID-03**: README 与本地 wiki 能反映当前覆盖率、运行命令、内容真源和已知未实现范围。

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### High-Fidelity Balancing

- **BAL-01**: 精确复刻原版所有概率分布、权重、解锁状态、Ascension 修正和事件出现条件。
- **BAL-02**: 建立大规模随机长跑或 Monte Carlo 回归，发现稀有路线、概率边界和长局存档问题。

### Extended Tooling

- **TOOL-01**: 提供开发者专用覆盖率仪表盘或诊断命令，用于查看内容池、掉落池和触发入口。
- **TOOL-02**: 提供更细粒度的本地参考资料同步工具，自动比对外部 Wiki 与 `content/` 差异。

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Web、GUI 或桌面图形客户端 | 当前项目边界是 Textual TUI，本轮 roadmap 不做第二套 UI。 |
| 服务端、账号、排行榜、云存档 | 当前目标是本地单机、可存读档、可回放流程。 |
| 多人模式、MOD 框架、创意工坊兼容 | 与原版 1 代内容复刻目标不同，会显著扩大范围。 |
| 默认采用《杀戮尖塔 2》机制 | 当前基线是原版 1 代，除非后续需求明确切换。 |
| 旧存档兼容承诺 | 当前开发阶段默认不保旧存档兼容；改 schema 时显式处理即可。 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GUARD-01 | Phase 1 | Complete |
| GUARD-02 | Phase 1 | Pending |
| GUARD-03 | Phase 1 | Pending |
| RUN-01 | Phase 2 | Pending |
| RUN-02 | Phase 2 | Pending |
| RUN-03 | Phase 2 | Pending |
| REWARD-01 | Phase 3 | Pending |
| REWARD-02 | Phase 3 | Pending |
| REWARD-03 | Phase 3 | Pending |
| REWARD-04 | Phase 3 | Pending |
| COMBAT-01 | Phase 2 | Pending |
| COMBAT-02 | Phase 6 | Pending |
| COMBAT-03 | Phase 6 | Pending |
| CHAR-01 | Phase 5 | Pending |
| CHAR-02 | Phase 5 | Pending |
| CHAR-03 | Phase 6 | Pending |
| CHAR-04 | Phase 6 | Pending |
| CARD-01 | Phase 6 | Pending |
| EVENT-01 | Phase 4 | Pending |
| EVENT-02 | Phase 4 | Pending |
| EVENT-03 | Phase 4 | Pending |
| VALID-01 | Phase 7 | Pending |
| VALID-02 | Phase 7 | Pending |
| VALID-03 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0

---
*Requirements defined: 2026-04-11*
*Last updated: 2026-04-11 after roadmap mapping*
