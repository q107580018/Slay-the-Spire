# Phase 2: 三幕主线闭环 - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 打通从新开局到三幕终局的完整主线流程：Act 1 -> Act 2 -> Act 3 -> Boss Chest -> Victory（及 HP 归零失败）。交付范围包括 Act 3 地图配置、全量原版 Act 3 敌人/遭遇组、Act 3 事件、胜利/失败统计面板，以及三幕贯通的 E2E 测试。不在此 Phase 扩展奖励经济统一（Phase 3）或非战斗系统深度规则（Phase 4），但 Act 3 事件按原版 1 代内容同步录入。

</domain>

<decisions>
## Implementation Decisions

### Act 3 敌人与遭遇组
- **D-01:** 全量覆盖原版 1 代 Act 3 普通敌人、精英和 Boss，包含完整行为模式（意图、move set、特殊 buff/debuff）。
- **D-02:** 遵循现有 Act 1/2 敌人 JSON 结构与遭遇组配置格式，Act 3 内容文件与现有文件保持一致。

### Act 3 事件与非战斗房间
- **D-03:** Act 3 事件在 Phase 2 同步补齐，不延后到 Phase 4；事件内容按原版 1 代录入，含选项、代价、奖励。
- **D-04:** 商店、休息点、宝箱等非战斗房间在 Act 3 的行为复用现有 Act 1/2 通用逻辑，无需 Act 3 特殊处理。

### Act 3 地图与跨幕推进
- **D-05:** 创建 `content/acts/act3_map.json`，引用 Act 3 敌人/遭遇/事件池，`next_act_id` 为空以触发终局。
- **D-06:** 更新 `content/acts/act2_map.json` 的 `next_act_id` 为 `"act3"`，使 Act 2 Boss Chest 后进入 Act 3。
- **D-07:** 地图生成器和跨幕推进路由均为数据驱动，不需要代码修改。

### 终局流程
- **D-08:** 胜利画面展示统计面板：层数、金币、牌组、遗物、药水、生命值，类似原版结算画面。
- **D-09:** 失败流程与胜利对称处理——HP 归零时结束战斗，展示失败统计面板（同样包含运行统计信息）。
- **D-10:** 胜利/失败面板渲染通过共享 Rich 展示层实现，Textual UI 复用同一渲染组件。

### E2E 测试策略
- **D-11:** 新增固定 seed 三幕全程 smoke 测试，每幕走最短路径，验证 Act 1 -> Act 2 -> Act 3 -> Boss Chest -> Victory。
- **D-12:** 保留分幕 stub 测试覆盖 act 边界转换：act1 -> act2、act2 -> act3、act3 -> victory。
- **D-13:** 修改现有 `test_two_act_smoke.py` 的 act2 -> victory 断言，适配 act2 -> act3 的变更。

### 存档一致性
- **D-14:** 存档 schema 保持 version 3 不变——`current_act_id` 和 `act_id` 字段已支持任意 act ID，无需 schema 变更。
- **D-15:** 三幕任意阶段的 save/load round-trip 需通过测试验证。

### the agent's Discretion
- Act 3 地图的具体 floor_count、room weights、fixed floors 配置可由 planner/researcher 参考原版数据决定。
- 统计面板的具体布局、渲染细节和字段排列由实现阶段根据现有 Rich 组件模式决定。
- 固定 seed 的具体选择和最短路径构造方式可由实现阶段决定。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria (RUN-01, RUN-02, RUN-03, COMBAT-01), dependency on Phase 1.
- `.planning/REQUIREMENTS.md` — `RUN-01`, `RUN-02`, `RUN-03`, `COMBAT-01` definitions and traceability.
- `.planning/PROJECT.md` — project constraints: Python/Textual/Rich TUI boundary, content source, persistence and testing expectations.

### Prior phase context
- `.planning/phases/01-护栏与交付契约/01-CONTEXT.md` — guardrail marker, content reachability contract, and batch acceptance checklist decisions.

### Codebase constraints
- `.planning/codebase/STRUCTURE.md` — source/test directory responsibilities and content file locations.
- `.planning/codebase/CONCERNS.md` — fragile areas around `session.py`, `effect_resolver.py`, map DFS, and UI observability.
- `.planning/codebase/TESTING.md` — current pytest layout, existing E2E smoke test patterns.

### Content reference
- `content/acts/act1_map.json` — Act 1 map config format (reference for Act 3 map creation).
- `content/acts/act2_map.json` — Act 2 map config (needs `next_act_id: "act3"` update).
- `content/enemies/act2_bosses.json` — Act 2 boss format (reference for Act 3 enemy JSON structure).
- `content/encounters/act2_bosses.json` — Act 2 encounter format (reference for Act 3 encounter structure).
- `docs/reference/` — local reference materials for card/relic data; use external Wiki for Act 3 enemy/event cross-validation.

### External reference
- [Slay the Spire Wiki](https://slay-the-spire.fandom.com/wiki/) — Act 3 enemies, encounters, events, boss behavior patterns.
- [杀戮尖塔中文 Wiki](https://sts.huijiwiki.com/wiki/) — 中英对照与术语校对。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/slay_the_spire/domain/map/map_generator.py` — 数据驱动的地图生成器，Act 3 只需内容 JSON 即可工作。
- `src/slay_the_spire/app/session.py` — 跨幕推进逻辑（`_advance_boss_chest`）已支持 `next_act_id` 分派，Act 3 无需代码修改。
- `src/slay_the_spire/use_cases/save_game.py` / `load_game.py` — 存档 schema 已泛化，支持任意 act ID。
- `tests/e2e/test_single_act_smoke.py` 和 `test_two_act_smoke.py` — 现有 smoke 测试模式可作为三幕 smoke 的基础。
- `src/slay_the_spire/adapters/presentation/renderer.py` 和 `widgets.py` — Rich 渲染组件，可用于构建统计面板。

### Established Patterns
- 敌人定义遵循 JSON 结构：`id`, `name`, `hp`, `moves`, `intent_pattern`, `buffs/debuffs`。
- 遭遇组引用敌人 ID 列表，按幕配置权重。
- 事件定义包含选项列表，每个选项有 `effects` 数组描述代价和奖励。
- Act 配置引用 encounter/event pool ID，地图生成器按配置分配房间类型。

### Integration Points
- 新增 `content/acts/act3_map.json` — 地图生成器自动发现。
- 新增 `content/enemies/act3_*.json` — 注册表自动加载。
- 新增 `content/encounters/act3_*.json` — 遭遇池自动注册。
- 新增 `content/events/act3_events.json` — 事件池自动注册。
- 更新 `content/acts/act2_map.json` — 唯一必须修改的现有内容文件。
- 新增胜利/失败渲染 — `src/slay_the_spire/adapters/presentation/` 下可能需要新增 screen 或扩展 renderer。
- 新增/更新测试 — `tests/e2e/` 下新增三幕 smoke，修改现有 two_act_smoke。

</code_context>

<specifics>
## Specific Ideas

- 全量 Act 3 敌人意味着需要覆盖原版 Act 3 的所有普通敌人、精英和 Boss（如 Darklings, Writhing Mass, Giant Head, Nemesis, Reptomancer, Awakened One, Time Eater, Donu & Deca 等）。
- 统计面板应尽可能接近原版结算画面的信息量，但以 TUI 文本布局呈现。
- 失败画面与胜利画面结构相同，仅标题和色调不同。

</specifics>

<deferred>
## Deferred Ideas

- 奖励经济统一（多入口 apply 链路一致性）— Phase 3 范围。
- 非战斗系统深度规则扩展（事件规则引擎、商店定价策略、休息点遗物联动）— Phase 4 范围。
- 敌人意图/行动模式的高复杂度规则收敛（多敌人协同、特殊时序）— Phase 6 范围。

</deferred>

---

*Phase: 02-三幕主线闭环*
*Context gathered: 2026-04-11*
