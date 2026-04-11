# Codebase Concerns

**Analysis Date:** 2026-04-11

## Tech Debt

**会话路由与业务编排过度集中（Monolithic Session Orchestrator）:**
- Issue: `route_menu_choice` 及相关路由/状态变更逻辑集中在单文件 `src/slay_the_spire/app/session.py`（约 2983 行，含大量 `_route_*` 分支函数），菜单路由、战斗后处理、商店/事件/休息/跨幕推进耦合在同一模块。
- Files: `src/slay_the_spire/app/session.py`
- Impact: 新增房间类型、菜单模式或奖励链路时，改动面广且回归半径大，容易引入分支回归（尤其在 `boss -> boss_chest -> next_act/victory` 与 inspect/potion 交叉路径）。
- Fix approach: 按菜单域拆分模块（如 `session_routes/combat.py`、`session_routes/non_combat.py`、`session_routes/opening.py`），保留统一入口但下沉分支处理；为每个子路由建立最小状态转换契约测试。

**效果解析器复杂度高且职责混合（Rule Engine + Queue Mutation）:**
- Issue: `src/slay_the_spire/domain/effects/effect_resolver.py`（约 1789 行）同时承担效果解释、状态变更、遗物/能力触发、副作用入队与日志字段拼装，规则分支多。
- Files: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Impact: 新增卡牌/遗物效果时，易因分支交互导致隐式行为变化（例如入队顺序、触发时机、目标解析），调试成本高。
- Fix approach: 将“效果规范化/目标解析/状态应用/触发器入队”拆为独立纯函数层；为每类 effect 建立表驱动测试样式，减少跨分支副作用。

**展示层存在重复逻辑（Relic Detail 渲染重复）:**
- Issue: 遗物详情字段拼装逻辑在 `format_relic_detail_lines` 与 `format_reward_detail_lines` 中重复（替换遗物、禁用操作、金币规则、实现状态等字段重复实现）。
- Files: `src/slay_the_spire/adapters/presentation/inspect.py`
- Impact: 文案/字段规则调整时易出现双处不一致，增加维护成本。
- Fix approach: 抽取统一的 relic detail builder（如 `_render_relic_metadata_lines` + `_render_relic_runtime_flags`），两个入口复用同一实现。

## Known Bugs

**未发现已在代码中显式标注且可直接复现的已知 Bug（TODO/FIXME/HACK/XXX）:**
- Symptoms: `src/` 内未检出 `TODO|FIXME|HACK|XXX` 注释作为已登记缺陷入口。
- Files: `src/`
- Trigger: Not applicable
- Workaround: Not applicable

## Security Considerations

**存档文件路径固定在工作目录且无写入范围约束:**
- Risk: 默认写入 `Path.cwd()/saves/latest.json`，运行目录受外部启动方式影响；在非常规工作目录下可能写入到非预期位置。
- Files: `src/slay_the_spire/app/session.py`, `src/slay_the_spire/use_cases/save_game.py`, `src/slay_the_spire/adapters/persistence/save_files.py`
- Current mitigation: 仅写入 JSON 本地文件，不涉及外部服务或远程输入。
- Recommendations: 在 CLI 层增加显式 `--save-dir` 白名单策略或路径确认提示；对路径做 `resolve()` 后的项目内校验（若产品允许）。

## Performance Bottlenecks

**每次命令处理后执行全量 UI 刷新链:**
- Problem: `_process_command` 会串行触发 `_refresh_log/_refresh_map/_refresh_combat_summary/_refresh_player_status/_refresh_actions` 等完整刷新。
- Files: `src/slay_the_spire/adapters/textual/slay_app.py`
- Cause: 采用“命令后全量刷新”策略，未按变更域做增量刷新。
- Improvement path: 基于路由结果附带“变更标记”（如 map_changed/combat_changed/menu_changed），按需刷新组件，减少无关渲染。

## Fragile Areas

**Map 路径渲染 DFS 无环保护，对异常图数据脆弱:**
- Files: `src/slay_the_spire/adapters/textual/map_layout.py`
- Why fragile: `_render_paths` 使用递归 DFS 遍历 `next_node_ids`，未维护 visited/recursion stack；若内容或运行态图出现环，可能导致深递归或无限展开。
- Safe modification: 在 DFS 中增加路径级 visited 检测与最大深度保护；遇到环时记录可诊断标记并安全截断。
- Test coverage: `tests/adapters/textual/test_map_layout.py` 仅覆盖稳定性和分支布局，未覆盖环/坏图输入。

**静默吞没 UI 异常降低可观测性:**
- Files: `src/slay_the_spire/adapters/textual/slay_app.py`, `src/slay_the_spire/adapters/presentation/inspect.py`
- Why fragile: 多处 `except NoMatches: pass` 或 `except KeyError: pass`，异常被忽略后 UI 可能降级但无日志，问题定位困难。
- Safe modification: 对可预期缺失分支保留回退，但至少记录 debug 级日志/事件计数；仅在明确可忽略场景使用静默分支。
- Test coverage: `tests/adapters/textual/test_slay_app.py`、`tests/adapters/presentation/test_inspect.py` 覆盖主要行为，但未断言异常吞没时的可观测信号。

## Scaling Limits

**菜单模式扩展的认知与修改成本已接近上限:**
- Current capacity: `src/slay_the_spire/app/session.py` 内已包含大量 `MenuState.mode` 分支与 `_route_*` 函数，跨 opening/active/combat/non-combat 全路径。
- Limit: 新增复杂菜单流（多级目标选择、回退链、inspect 嵌套）时，路由冲突与状态回退错误概率上升。
- Scaling path: 引入“模式 -> 处理器”注册表与统一 `RouteContext`，将分支改为声明式分发，减少 if/elif 链增长。

## Dependencies at Risk

**未检测到高风险外部在线依赖耦合:**
- Risk: 当前为本地单机 TUI，核心依赖集中在 `textual`/`rich`/`pytest`，未发现外部服务 SDK 强绑定。
- Impact: Not applicable
- Migration plan: 持续锁定依赖版本并在 `uv.lock` 变更时跑全量回归测试。

## Missing Critical Features

**运行时异常观测通道不足（缺少统一日志/诊断层）:**
- Problem: UI 层和部分展示层存在静默回退，当前缺少统一诊断输出（例如 debug log sink 或错误事件面板）。
- Blocks: 阻碍线上/玩家反馈场景下的问题定位与复现，延长修复周期。

## Test Coverage Gaps

**地图坏输入鲁棒性未覆盖:**
- What's not tested: 包含环、断链、非法 `next_node_ids` 的 map 在 Textual 布局与路径渲染中的行为。
- Files: `src/slay_the_spire/adapters/textual/map_layout.py`, `tests/adapters/textual/test_map_layout.py`
- Risk: 内容异常时出现栈溢出、渲染失败或路径展示不一致。
- Priority: High

**UI 异常回退路径缺少可观测性断言:**
- What's not tested: `NoMatches/KeyError` 回退分支发生时是否保留可诊断信号（日志、状态标识）。
- Files: `src/slay_the_spire/adapters/textual/slay_app.py`, `src/slay_the_spire/adapters/presentation/inspect.py`, `tests/adapters/textual/test_slay_app.py`, `tests/adapters/presentation/test_inspect.py`
- Risk: 出现功能降级时测试仍通过，但运行时难以定位根因。
- Priority: Medium

**会话路由超长分支的细粒度回归覆盖仍可加强:**
- What's not tested: `session.py` 内多分支互相跳转的组合路径（尤其 inspect 与奖励/药水/跨幕混合流程）的系统化参数化测试。
- Files: `src/slay_the_spire/app/session.py`, `tests/app/test_session.py`, `tests/e2e/test_single_act_smoke.py`, `tests/e2e/test_two_act_smoke.py`
- Risk: 小改动引发边界路径回归而未被现有烟测覆盖。
- Priority: Medium

---

*Concerns audit: 2026-04-11*
