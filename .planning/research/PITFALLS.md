# Domain Pitfalls

**Domain:** Slay the Spire TUI 原版 1 代复刻（Pitfalls 维度）
**Researched:** 2026-04-11
**Confidence:** HIGH（基于仓库现状文档与 codebase map）

## Critical Pitfalls

### Pitfall 1: 效果解析器膨胀导致规则时序漂移
**What goes wrong:** 新卡牌/遗物不断堆进 `effect_resolver.py`，触发顺序、目标解析、副作用入队互相污染，出现“单卡可用、联动错乱”。
**触发信号:**
- 新增效果后，已有回归不是该效果所属模块
- 同一局面多次重放结果不一致
- 修一个分支后另一个触发时机（开局/出牌后/回合结束）失真
**预防策略:**
- roadmap 先排“规则引擎分层 phase”：拆分为目标解析、状态变更、触发器入队、日志映射四层
- 新效果接入必须走统一 effect schema，不允许散落在 session/use case 特判
- 对高耦合效果采用表驱动测试（按触发时机 + 先后顺序断言）
**应该放在哪类 phase 中处理:** 架构治理 phase（早于大批量内容补齐）
**必须配套的测试或文档检查:**
- `tests/domain/test_effect_resolver.py` 增加触发顺序参数化用例
- 新增“效果接入约束”文档段落到 README 的开发说明（入口、禁止绕过点）

### Pitfall 2: 会话路由膨胀导致菜单状态机回归
**What goes wrong:** `session.py` 分支继续增长，inspect/奖励/药水/跨幕路径互相干扰，出现“能进不能退”或菜单编号行为漂移。
**触发信号:**
- 新增菜单模式需要改动大量 `_route_*` 分支
- 非战斗操作后 `menu_state.mode` 落在意外状态
- `boss -> boss_chest -> next_act/victory` 链路间歇性断裂
**预防策略:**
- roadmap 排“路由解耦 phase”：按 opening/combat/non-combat 分处理器并建立统一分发表
- 先定义模式迁移图，再实现分支
- 禁止在渲染层修补状态机错误（只允许在 session/use case 修）
**应该放在哪类 phase 中处理:** 会话与交互架构 phase（早中期）
**必须配套的测试或文档检查:**
- `tests/app/test_session.py` 增加模式迁移矩阵测试
- `tests/e2e/test_single_act_smoke.py`、`tests/e2e/test_two_act_smoke.py` 补 boss 链路与 inspect 交叉路径
- README 菜单流程说明随状态机变化同步更新

### Pitfall 3: 内容覆盖率“看起来完成”但运行时入口漏接
**What goes wrong:** JSON 已录入，但掉落池、奖励入口、事件选项、商店池、地图房间概率没有接通，形成“数据存在但永远拿不到/触发不到”。
**触发信号:**
- 内容总数增长快，但实际游玩很少遇到新增内容
- `implementation_status` 与实际可触发集合不一致
- 同一批内容在不同入口（战后奖励/商店/Boss/Neow）表现不一致
**预防策略:**
- roadmap 把“内容录入 phase”和“入口联通 phase”拆开，不允许合并验收
- 对每批内容维护“可触达矩阵”（来源 -> 内容 ID）
- 奖励与掉落统一由单一策略层管理，避免各用例各自筛选
**应该放在哪类 phase 中处理:** 内容批量导入 phase + 奖励系统治理 phase（中期持续）
**必须配套的测试或文档检查:**
- `tests/content/test_registry_validation.py` 增加可触达性校验（池子引用、ID 存在、权重合法）
- `tests/use_cases/test_apply_reward.py` 与 `tests/domain/...reward...` 增加入口一致性断言
- README“当前覆盖率”需区分“已录入”和“可运行”

### Pitfall 4: 存档结构与运行时状态脱节
**What goes wrong:** 新机制只改了运行态，未同步序列化/反序列化，读档后状态丢失或变形（尤其战斗中状态、临时效果、计数器）。
**触发信号:**
- 同一存档“即时继续”与“退出重进”结果不同
- 新增字段只出现在 `to_dict` 或只出现在 `from_dict`
- `schema_version=3` 下出现隐式兼容分支
**预防策略:**
- 每个新增运行时字段都绑定存档检查清单
- 明确“战斗内临时状态是否允许持久化”的统一策略
- 涉及结构变化时显式决策是否 bump schema（不要隐式扩展）
**应该放在哪类 phase 中处理:** 存档与回放稳定性 phase（中期，且每批机制都要复核）
**必须配套的测试或文档检查:**
- `tests/use_cases/test_save_load.py` 增加新字段 round-trip
- `tests/domain/test_state_serialization.py` 增加模型序列化对照
- README 存档段落同步记录 schema 与不兼容策略

## Moderate Pitfalls

### Pitfall 5: 房间类型新增只改一层，三层展示/路由未闭环
**What goes wrong:** 地图已生成新房间，但 use case、共享展示层、Textual 组件之一未补，最终出现空白页或错误菜单。
**触发信号:**
- 能进入节点但没有可执行动作
- Rich 展示正常但 Textual 面板缺按钮（或反之）
- room payload 结构与 UI 读取字段不一致
**预防策略:**
- 把“房间类型引入”作为独立模板 phase，强制包含 map + session/use case + presentation + textual 四项任务
- 每个房间定义最小可玩闭环（进入、交互、退出）
**应该放在哪类 phase 中处理:** 房间系统扩展 phase
**必须配套的测试或文档检查:**
- `tests/adapters/presentation/` 与 `tests/adapters/textual/test_slay_app.py` 同步补用例
- `tests/e2e/` 增加至少一条经过该房间的路径 smoke

### Pitfall 6: 规则实现散落在 use case/session，无法复用
**What goes wrong:** 为赶进度把特例写进 session 或单个 use case，后续同类机制重复实现，行为逐步分叉。
**触发信号:**
- 同一概念（如费用覆写、消耗、抽弃联动）出现多处“临时 if”
- 新机制总是需要复制旧逻辑再改一处
**预防策略:**
- roadmap 设“机制归并 phase”：把共性规则下沉到 domain 层
- code review 门禁：新增规则若不在 domain 统一入口，默认阻断
**应该放在哪类 phase 中处理:** 规则归并与重构 phase（穿插进行）
**必须配套的测试或文档检查:**
- 对应 domain 测试新增“共享机制覆盖”案例
- README 开发说明维护“规则入口索引”

### Pitfall 7: UI 文案与实际效果说明漂移
**What goes wrong:** 中文描述、inspect 详情、奖励说明未随规则更新，玩家看到的提示与实际结算不一致。
**触发信号:**
- 卡牌/遗物文本与日志结算数字冲突
- hover 详情与选择后行为不一致
**预防策略:**
- 文案字段尽量引用结构化效果数据生成，减少硬编码描述
- 把“文案一致性检查”纳入每批内容验收
**应该放在哪类 phase 中处理:** 展示一致性与可观测性 phase
**必须配套的测试或文档检查:**
- `tests/adapters/presentation/test_inspect.py` 与 renderer 测试增加关键文案快照断言
- README“当前实现”中高复杂机制描述与代码一致性复核

## Minor Pitfalls

### Pitfall 8: 地图异常输入缺少保护导致渲染脆弱
**What goes wrong:** 出现环或坏边时布局/路径渲染异常，影响整局流程稳定性。
**触发信号:**
- 地图渲染卡顿、递归过深、路径显示异常
- 某些 seed 稳定复现 UI 崩溃
**预防策略:**
- DFS 增加 visited 与深度保护
- 对坏图采用降级展示而非直接失败
**应该放在哪类 phase 中处理:** 地图稳健性 phase
**必须配套的测试或文档检查:**
- `tests/adapters/textual/test_map_layout.py` 增加环/断链/非法 next_node_ids 测试

### Pitfall 9: 仅靠 smoke 测试，缺少机制级回归护栏
**What goes wrong:** E2E 能过，但复杂联动悄悄退化，问题延后到内容大批量合并后才暴露。
**触发信号:**
- 每次回归都在后期发现“老机制被新机制破坏”
- 测试主要断言“流程能走完”，缺少规则细节断言
**预防策略:**
- 建“机制回归清单 phase”：按关键机制（费用、消耗、触发时机、奖励入口、存档 round-trip）建参数化测试
- 规定每个内容批次最少新增一组机制级测试，不只补数据测试
**应该放在哪类 phase 中处理:** 测试基建 phase（尽早）
**必须配套的测试或文档检查:**
- 扩充 `tests/domain/`、`tests/use_cases/` 参数化用例覆盖
- README 增加“批次验收清单”简表（内容、入口、测试、文档四项）

## Phase-Specific Warnings（Roadmap 直接可用）

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| 架构治理（规则引擎） | effect_resolver 持续膨胀 | 先拆层再补内容；建立 effect schema + 顺序断言测试 |
| 会话路由重整 | `session.py` 分支冲突 | 按模式拆处理器；迁移图测试先行 |
| 内容批量导入 | “录入即完成”错觉 | 录入/联通分 phase；维护可触达矩阵 |
| 奖励与掉落系统 | 未实现内容被投放 | 单一投放策略层；入口一致性测试 |
| 存档与回放 | 新字段未序列化 | round-trip 测试绑定每次结构变更 |
| 房间扩展 | 只改 map 不改 UI/路由 | 四层闭环模板（map/use case/presentation/textual） |
| 展示与文案 | 文案与结算漂移 | inspect/renderer 快照 + 术语统一复核 |
| 测试基建 | 过度依赖 smoke | 机制级参数化回归套件前置建设 |

## Sources

- `.planning/PROJECT.md`（2026-04-11）
- `.planning/codebase/CONCERNS.md`（2026-04-11）
- `.planning/codebase/ARCHITECTURE.md`（2026-04-11）
- `.planning/codebase/TESTING.md`（2026-04-11）
- `README.md`（仓库当前实现与约束）
- `AGENTS.md`（协作规则与联动检查）
