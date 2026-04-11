# Feature Landscape

**Domain:** Slay the Spire TUI 原版 1 代复刻（Features）
**Researched:** 2026-04-11

## 当前基线快照（用于划分优先级）

- 已有 1 个角色：`ironclad`
- 已有幕流程：`act1 -> act2 -> victory`（缺 `act3`，且未进入更完整终局链路）
- 卡牌：`content/cards/` 当前仅 `ironclad_starter.json + curses.json`（共 170 条，含升级与状态/诅咒）
- 遗物：180 条目录已录入，`implemented=82`、`placeholder=98`
- 事件：`act1=11`、`act2=4`
- 敌人与遭遇：仅 Act1/Act2
- 药水：3 种

---

## Table Stakes（完整复刻 1 代必须补齐）

| Feature | 为什么是 Table Stakes | 复杂度 | 关键依赖 |
|---------|----------------------|--------|----------|
| 三幕主线完整通关链路（Act1/2/3 + 每幕 Boss + Boss Chest + 结算） | 这是 1 代标准跑图主干；缺 Act3 不算完整复刻 | 高 | `acts/*`、`encounters/*`、`session.py` 跨幕路由、胜利判定 |
| 角色全集（Ironclad / Silent / Defect / Watcher）+ 各自初始卡组与起始遗物 | 角色可玩性是原版核心内容边界 | 高 | 角色内容注册、卡池隔离、遗物池隔离、奖励掉落规则 |
| 角色卡池完整（含升级、状态/诅咒、X 费、保留、消耗、虚无、生成牌） | 卡牌与效果解析是战斗系统主体 | 高 | `effect_resolver.py`、出牌/抽弃牌/牌堆迁移、目标选择 UI |
| 敌人/精英/Boss 完整遭遇池（按幕分层） | 战斗节奏和难度曲线主要由敌人与遭遇池决定 | 高 | `enemies/*`、`encounters/*`、意图与行动脚本、战斗奖励 |
| 事件池补齐（至少三幕主事件） | 事件是地图房间分布与构筑变化的关键来源 | 中高 | 事件效果类型、选项分支、金币/生命/卡牌/遗物联动 |
| 遗物完整可用（不再掉落 placeholder） | 遗物掉落是局内长期构筑核心；占位掉落会破坏体验 | 高 | 遗物触发时机、奖励/商店/宝箱/Neow 掉落过滤 |
| 药水系统完整（目录、掉落、使用限制、目标选择、联动遗物） | 药水是战斗中短期策略资源，缺失会削弱原版策略层 | 中高 | 药水池、战斗内选择流程、药水槽、Sozu/White Beast Statue 等联动 |
| 奖励系统完整（战后奖励、Boss 奖励、移除/升级/转换/复制来源） | 卡组演进与局外决策核心入口 | 高 | `reward_generator.py`、`apply_reward.py`、商店/事件/休息点来源一致性 |
| 地图与房间规则贴近原版（精英/商店/休息点分布约束） | 路线决策是 STS 核心体验之一 | 中高 | map 生成参数、路径渲染、房间进入路由 |
| 存档与回放一致性（schema v3 持续可验证） | 本项目目标是“可回放 + 可测试”，一致性属于产品基线 | 中 | save/load、跨幕状态序列化、E2E 回放测试 |

---

## Deferred（后续里程碑再做的 polish / 高阶校验）

| Feature | 为什么 Deferred | 复杂度 | 依赖 |
|---------|------------------|--------|------|
| Ascension（高阶难度）与难度修饰细节 | 非“先完整复刻普通流程”的阻塞项 | 高 | 全内容先稳定，敌人与奖励平衡基线先落地 |
| 事件/敌人数值逐项对齐与概率精修 | 先保证规则正确与可通关，再做精调 | 中高 | 完整内容池 + 可复现实验脚本 |
| 更细粒度战斗日志与诊断视图 | 属于开发效率提升，不是玩家必需功能 | 中 | 当前 Textual/Rich 渲染稳定后再扩展 |
| 大规模随机种子回归（长跑 Monte Carlo） | 质量强化项，非 MVP 功能 | 中 | 核心规则冻结 + 性能可接受 |
| 多语言术语一致性工具化（批量校对） | 体验提升项，不阻塞玩法完备 | 低中 | 内容基本稳定，避免反复改文案 |

---

## Anti-Features（明确不做）

| Anti-Feature | 为什么不做 | 替代方案 |
|--------------|-----------|----------|
| GUI 客户端（Unity/Unreal/桌面图形界面） | 与仓库边界冲突；会分散规则复刻资源 | 保持 Textual TUI + Rich 组件 |
| Web/服务端/账号/排行榜/云存档 | 当前目标是本地单机可回放，不是在线产品 | 本地 JSON 存档与命令行运行 |
| 多人模式/联机对战 | 非原版核心复刻路径，复杂度极高 | 聚焦单人 run 完整性与规则一致性 |
| 以 STS2 机制为默认基线 | 与“原版 1 代复刻”目标冲突 | 仅以 1 代为准，除非需求明确切换 |
| 为旧存档/旧菜单状态做长期兼容 | 当前协作约束已明确默认不兼容 | 允许 schema 演进并同步测试更新 |

---

## Feature Dependencies

```text
内容池完整（角色/卡牌/敌人/事件/遗物/药水）
  -> 掉落与奖励正确（战后/Boss/商店/事件/休息点/Neow）
  -> 三幕地图与路由完整（Act1->Act2->Act3->结算）
  -> 存档/回放一致性
  -> 才能做 Ascension 与概率精调
```

---

## 当前 v1 Roadmap 建议批次（建议直接进入近期 roadmap）

1. **批次 A：主线闭环补齐（Act3 + 终局链路）**
   - 范围：Act3 地图、Act3 普通/精英/Boss 敌人与遭遇、`boss -> boss_chest -> victory` 完整结算。
   - 复杂度：高
   - 依赖：现有 `session.py` 跨幕路由、`acts/enemies/encounters` 内容装载。
   - 价值：先把“可完整跑完一局”从 Act2 终止提升到标准三幕通关。

2. **批次 B：奖励与掉落“去占位化”**
   - 范围：基于 `implementation_status` 过滤 placeholder 遗物；补齐当前常见掉落链路所需遗物与药水；校正 Boss 奖励池。
   - 复杂度：高
   - 依赖：`reward_generator.py`、`apply_reward.py`、遗物触发 Hook。
   - 价值：避免玩家拿到“无效果奖励”，显著提升可玩性与可信度。

3. **批次 C：事件与非战斗系统扩容（先 Act1/2 全量，再进 Act3）**
   - 范围：补足事件池、商店/休息点/宝箱行为差异、关键事件结果类型。
   - 复杂度：中高
   - 依赖：事件 effect 类型、卡牌操作（移除/升级/变化）、金币与生命结算。
   - 价值：提高路径决策密度，避免流程“只剩战斗”。

4. **批次 D：第二角色（建议 Silent）端到端落地**
   - 范围：角色定义、起始套牌、角色卡池、关键机制（弃牌/毒）与关联遗物。
   - 复杂度：高
   - 依赖：卡池按角色隔离、奖励池按角色发放、战斗效果扩展。
   - 价值：验证“多角色架构”是否成立，尽早暴露设计缺陷，避免后期返工。

5. **批次 E：Defect + Watcher 与剩余全量内容补齐**
   - 范围：两角色卡池与机制（充能球、姿态等）、剩余敌人/事件/遗物/药水、全池校验。
   - 复杂度：高
   - 依赖：前四批完成后再进入，避免并行爆炸。
   - 价值：完成“完整复刻 1 代”定义闭环。

---

## MVP Recommendation（当前里程碑）

优先做：
1. 批次 A（Act3 主线闭环）
2. 批次 B（奖励去占位化）
3. 批次 D（Silent 作为多角色样板）

暂缓：
- 批次 E（Defect/Watcher 全量）与 Ascension：在 A/B/D 稳定后进入下一里程碑更稳妥。

---

## Sources

- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/PROJECT.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/codebase/STRUCTURE.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/codebase/CONCERNS.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/README.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/AGENTS.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/content/*`
- `/Users/qiuwen/Documents/Slay-the-Spire/docs/reference/*`
