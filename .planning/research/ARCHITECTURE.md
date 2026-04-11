# Architecture Patterns

**Domain:** Slay the Spire TUI 原版 1 代复刻（brownfield 后续内容批次接入）
**Researched:** 2026-04-11

## Recommended Architecture

保持现有“分层单体 + 内容驱动”主结构，不引入新架构形态。后续所有原版内容批次都沿同一流水线接入：

`content/*.json -> ContentCatalog/Registries -> ContentProviderPort -> use_cases/domain -> SessionState 路由 -> Rich Presentation/Textual`

核心原则：
- 内容定义只进 `content/`，运行逻辑只进 `domain/` 与 `use_cases/`，`session.py` 只做编排和状态流转。
- 每个批次按“内容契约 -> 规则实现 -> 用例接线 -> 会话路由 -> 展示”顺序收敛，避免跳层直改 UI。
- 新增机制优先复用既有 effect/hook/reward 通道，不新增平行通道。

## 内容到 UI 的流向（你关心的主链）

1. 内容加载与校验  
`ContentCatalog.from_content_root()` 加载 `characters/cards/enemies/encounters/events/relics/potions/acts` 并调用 `validate_startup_integrity()` 做启动期强校验。

2. Provider 暴露  
`StarterContentProvider` 将 catalog 暴露为 `ContentProviderPort`，供用例和领域层读取（避免直接读 JSON）。

3. Domain / Use Case 消费  
- `use_cases/start_run.py` 用角色定义构建开局 `RunState`。  
- `use_cases/enter_room.py` 用 act/map/encounter/pool 定义构建 `RoomState/CombatState`。  
- `domain/rewards/reward_generator.py` 生成奖励 ID；`use_cases/apply_reward.py` 解释并落地奖励。  
- 战斗效果通过 `play_card/end_turn -> turn_flow -> effect_resolver` 执行。

4. Session 编排  
`app/session.py::route_menu_choice()` 按 `MenuState.mode` 把玩家输入路由到 use case，并维护 `SessionState`（含 `run_state/act_state/room_state`）。

5. Presentation/Textual 渲染  
`adapters/presentation` 负责 Rich 组装；`adapters/textual/slay_app.py` 负责 UI 事件与控件刷新。UI 不应新增业务规则。

## 组件边界（按内容类型）

### 角色（character）
- 改动边界：`content/characters/*.json`、`registries.CharacterDef`、`use_cases/start_run.py`、opening 选择流。
- 不该改：战斗结算细节（除非角色机制要求）。
- 最小测试：内容注册校验 + `start_new_run` 开局状态 + opening 角色菜单路由。

### 卡牌（card）
- 改动边界：`content/cards/*.json`、`CardRegistry` 字段约束、`effect_resolver`/`turn_flow`、`play_card/end_turn`。
- 不该改：Textual 菜单结构（除非新增目标类型）。
- 最小测试：`tests/content`（字段合法性）+ `tests/domain/test_effect_resolver.py`（效果表驱动）+ `tests/use_cases/test_play_card.py`。

### 遗物（relic）
- 改动边界：`content/relics/*.json`、hook 注册/分发、`enter_room.py`（房间/商店/休息点联动）、`reward_generator/apply_reward`。
- 不该改：直接在 UI 层写遗物效果。
- 最小测试：遗物获取/替换、战斗触发、非战斗触发、奖励池与商店价格联动。

### 敌人/遭遇（enemy/encounter）
- 改动边界：`content/enemies/*.json` + `content/encounters/*.json`、`enter_room._select_combat_enemy_ids/_build_enemy_state`、敌方行动规则。
- 不该改：奖励流程（除非击败后规则变化）。
- 最小测试：遭遇池权重与 floor 限制、首回合意图、多敌战斗状态推进。

### 事件（event）
- 改动边界：`content/events/*.json`、`resolve_event_choice.py`、`event_action.py`、session 事件分支与菜单。
- 不该改：战斗 effect 引擎（除非事件发起战斗/效果复用）。
- 最小测试：选项可见性、结果分支、状态变更（血量/金币/牌组/遗物）与 once-per-run。

### 奖励（reward）
- 改动边界：`reward_generator.py`（生成）+ `apply_reward.py`（落地）+ session 奖励菜单路由。
- 不该改：内容注册 schema（除非新增奖励类型协议）。
- 最小测试：生成-应用一致性（同一 reward_id 能被稳定应用）、Boss 奖励链路、跳过/拿取分支。

### 药水（potion）
- 改动边界：`content/potions/*.json`、`reward_generator` 掉落、`apply_reward` 入槽、`use_potion.py` 消耗与目标。
- 不该改：存档 schema（除非药水状态结构变化）。
- 最小测试：掉落概率门控、槽位上限、目标合法性、战斗内外可用时机。

## 建议构建顺序与依赖

1. **Phase A: 先加护栏（抽象最小化 + 测试先行）**  
   - 先补：`session` 路由契约测试、`effect_resolver` 表驱动测试、`reward_generator <-> apply_reward` 一致性测试。  
   - 依赖：无。  
   - 目的：给后续大批内容接入提供回归护栏。

2. **Phase B: 内容契约扩展（JSON/Registry）**  
   - 每批先落 JSON + registry 字段约束。  
   - 依赖：A。  
   - 目的：把错误拦在启动期，不让脏数据进入运行时。

3. **Phase C: 战斗核心批次（卡牌机制 + 敌人遭遇）**  
   - 先完成 effect/hook 可承载的卡牌与敌人行为。  
   - 依赖：A+B。  
   - 目的：先把“战斗闭环”做厚，后续事件/遗物大多复用它。

4. **Phase D: 奖励经济批次（遗物/药水/战斗奖励/Boss 奖励）**  
   - 聚焦 reward pipeline 与 room 结算联动。  
   - 依赖：C（需要稳定战斗结果）+B。  
   - 目的：保证战斗后的长期成长链条正确。

5. **Phase E: 非战斗批次（事件/商店/休息点/Neow）**  
   - 以 use case 为中心接入复杂分支。  
   - 依赖：D（需要完整奖励与资源系统）+A。  
   - 目的：补齐 run 内资源交换与路线决策。

6. **Phase F: 跨幕与终局链路（boss -> boss_chest -> next_act/victory）**  
   - 做全链路回归与文本/菜单打磨。  
   - 依赖：C+D+E。  
   - 目的：稳定一局完整流程。

### 依赖图（简化）

`A -> B -> C -> D -> E -> F`  
`C` 是 `D/E` 的前置；`D` 是 `E` 的强前置。

## 哪些系统要先抽象或先加测试再扩展

### 必须先做（高优先）

1. **`session.py` 路由分发抽象（先测试后拆分）**  
- 现状：超大单文件编排（`route_menu_choice` 集中）。  
- 建议：引入 `mode -> handler` 注册表（可先不搬文件，先建立分发表），并为每个 mode 建立输入/输出契约测试。  
- 原因：后续事件/奖励/inspect 会继续加分支，不先控复杂度会反复回归。

2. **`effect_resolver.py` 效果处理抽象（先表驱动测试）**  
- 现状：规则解释 + 副作用入队耦合。  
- 建议：先补“效果类型矩阵测试”，再把处理器拆成 `normalize/target/apply/enqueue` 四段纯函数。  
- 原因：卡牌和遗物批次都依赖这条主干。

3. **奖励协议收口（先一致性测试）**  
- 现状：`reward_id` 使用字符串协议（如 `gold:*`、`card_offer:*`、`potion:*`）。  
- 建议：新增 `parse_reward_id`/`RewardSpec` 统一解析，测试生成器产物都可被应用器消费。  
- 原因：后续 Boss/事件/商店奖励扩展会放大字符串协议漂移风险。

### 建议尽早做（中优先）

4. **目标类型常量去重（session/textual 共用）**  
- 现状：`_ENEMY_TARGET_EFFECT_TYPES` 等常量在 `session.py` 和 `slay_app.py` 重复。  
- 建议：提取到 shared 模块，避免 UI 和路由目标判定不一致。

5. **Room payload 访问器化**  
- 现状：`room_state.payload` 多处裸 `dict` 读写。  
- 建议：至少为 `combat_state/event/shop/treasure/boss_rewards` 建 typed accessor/helper。  
- 原因：批次扩大后，payload key 漂移会成为高频错误源。

## 测试边界（Roadmap 可直接使用）

| 测试层 | 应覆盖内容 | 不应承担内容 |
|---|---|---|
| `tests/content` | JSON schema、ID 唯一性、跨表引用完整性、pool 合法性 | 运行时战斗数值平衡 |
| `tests/domain` | 纯规则（effect/hook/turn/reward sampling）与序列化一致性 | 菜单输入和 UI 事件 |
| `tests/use_cases` | 动作级状态转换（play/end_turn/enter_room/apply_reward/event/shop/rest/save/load） | Rich/Textual 细节渲染 |
| `tests/app` | `session` 路由、菜单 mode 切换、跨幕链路 | 具体数值公式 |
| `tests/adapters/textual` | 组件挂载、交互事件、面板刷新与降级路径 | 领域规则正确性 |
| `tests/e2e` | 一局主链路 smoke（opening->act->boss->next_act/victory） | 细粒度规则穷举 |

## Phase 级落地建议

- 每个内容批次必须提交同构变更包：  
  `content/*.json` + 对应 `registry/domain/use_case/session/presentation` 最小改动 + 同层测试。  
- 不接受“只加 JSON 不加行为”或“只改 UI 模拟行为”的批次。  
- 对高风险链路固定做回归：  
  `boss -> boss_chest -> next_act/victory`、`reward generate -> apply -> save/load`、`combat end -> room stage -> menu mode`。

## Sources

- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/PROJECT.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/codebase/ARCHITECTURE.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/codebase/STRUCTURE.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/codebase/TESTING.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/.planning/codebase/CONCERNS.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/README.md`
- `/Users/qiuwen/Documents/Slay-the-Spire/src/slay_the_spire/content/catalog.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/src/slay_the_spire/content/registries.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/src/slay_the_spire/use_cases/start_run.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/src/slay_the_spire/use_cases/enter_room.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/src/slay_the_spire/domain/rewards/reward_generator.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/src/slay_the_spire/use_cases/apply_reward.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/src/slay_the_spire/app/session.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/src/slay_the_spire/adapters/textual/slay_app.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/tests/content/test_registry_validation.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/tests/app/test_session.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/tests/use_cases/test_save_load.py`
- `/Users/qiuwen/Documents/Slay-the-Spire/tests/adapters/textual/test_slay_app.py`
