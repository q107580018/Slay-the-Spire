# Architecture

**Analysis Date:** 2026-04-11

## Pattern Overview

**Overall:** 菜单驱动的分层单体（App Orchestrator + Use Cases + Domain + Adapters）

**Key Characteristics:**
- `src/slay_the_spire/app/session.py` 作为单一编排中心，统一维护会话状态、菜单状态、路由与跨幕推进。
- 业务动作以 `src/slay_the_spire/use_cases/*.py` 函数方式实现，输入/输出以 `RunState`、`RoomState`、`CombatState` 等模型传递。
- 领域规则集中在 `src/slay_the_spire/domain/`，内容读取与存档读写通过 `ports` + `adapters` 连接。

## Layers

**CLI / Entry Layer:**
- Purpose: 解析命令行参数并启动会话。
- Location: `src/slay_the_spire/app/cli.py`
- Contains: `argparse` 子命令 `new/load`、seed 生成、Textual 启动调用。
- Depends on: `src/slay_the_spire/app/session.py`, `src/slay_the_spire/adapters/textual/textual_runner.py`
- Used by: `pyproject.toml` 的 `slay-the-spire = "slay_the_spire.app.cli:main"`

**Application Orchestration Layer:**
- Purpose: 维护 `SessionState`，将菜单动作路由到对应 use case，并组装渲染输出。
- Location: `src/slay_the_spire/app/session.py`, `src/slay_the_spire/app/menu_definitions.py`, `src/slay_the_spire/app/next_room_options.py`
- Contains: 菜单模式状态机（`MenuState.mode`）、`route_menu_choice` 分发、`render_session(_renderable)`、开局流程与 Boss 链路处理。
- Depends on: `use_cases/*`, `domain/models/*`, `domain/rewards/reward_generator.py`, `content/provider.py`, `adapters/presentation/*`, `adapters/persistence/save_files.py`
- Used by: Textual 应用 `src/slay_the_spire/adapters/textual/slay_app.py`

**Use Case Layer:**
- Purpose: 实现玩家动作与房间行为（进入房间、出牌、结束回合、商店/休息点/事件、奖励、存读档）。
- Location: `src/slay_the_spire/use_cases/`
- Contains: `start_run.py`, `enter_room.py`, `play_card.py`, `end_turn.py`, `shop_action.py`, `rest_action.py`, `event_action.py`, `apply_reward.py`, `save_game.py`, `load_game.py` 等。
- Depends on: `domain/*`, `ports/*`, `content/registries.py`；部分文件直接依赖 `adapters/presentation/widgets.py`（如 `use_potion.py`, `combat_events.py`）。
- Used by: `app/session.py`

**Domain Layer:**
- Purpose: 封装核心规则与状态模型。
- Location: `src/slay_the_spire/domain/`
- Contains: 
  - 状态模型 `models/*.py`
  - 战斗规则 `combat/turn_flow.py`, `effects/effect_resolver.py`
  - Hook 系统 `hooks/*`
  - 地图生成 `map/map_generator.py`
  - 奖励生成 `rewards/reward_generator.py`
- Depends on: `ports/content_provider.py`, `content/registries.py`, `shared/*`
- Used by: `use_cases/*`, `app/session.py`

**Content & Registry Layer:**
- Purpose: 从 JSON 内容构建强类型注册表并进行启动期校验。
- Location: `src/slay_the_spire/content/catalog.py`, `src/slay_the_spire/content/provider.py`, `src/slay_the_spire/content/registries.py`, `content/`
- Contains: JSON 加载、池子成员与权重、`CardDef/RelicDef/...` 注册与完整性检查。
- Depends on: `src/slay_the_spire/content/loaders.py`, `src/slay_the_spire/shared/types.py`
- Used by: `app/session.py`, `use_cases/*`, `domain/*`

**Adapter Layer (Presentation / Textual / Persistence):**
- Purpose: 提供渲染、交互与存储实现。
- Location:
  - `src/slay_the_spire/adapters/presentation/`
  - `src/slay_the_spire/adapters/textual/`
  - `src/slay_the_spire/adapters/persistence/save_files.py`
- Contains: Rich renderable 组装、Textual 组件与 UI 事件、JSON 文件存档仓储。
- Depends on: `app/*`, `domain/models/*`, `ports/*`
- Used by: `app/cli.py`, `app/session.py`

## Data Flow

**新开局到首房间流程:**

1. `src/slay_the_spire/app/cli.py` 调用 `start_new_game_session`，先构建 `OpeningState`。
2. `src/slay_the_spire/app/session.py` 在开局菜单中通过 `use_cases/opening_flow.py` 处理 Neow 选项，形成 `run_blueprint`。
3. 同文件调用 `use_cases/enter_room.py` + `domain/map/map_generator.py` 进入首节点，生成 `RoomState`（含可选 `combat_state`）。

**战斗菜单动作流程:**

1. `route_menu_choice` 在 `menu_state.mode` 为 `select_card/select_target` 时路由到 `use_cases/play_card.py` 或 `use_cases/end_turn.py`。
2. 用例调用 `domain/combat/turn_flow.py` 与 `domain/effects/effect_resolver.py` 变更 `CombatState`，并生成战斗日志条目。
3. `app/session.py` 将 `CombatState` 回写 `room_state.payload["combat_state"]`，若战斗结束则通过 `domain/rewards/reward_generator.py` 注入奖励并切换房间阶段。

**存档读写流程:**

1. `app/session.py` 使用 `adapters/persistence/save_files.py::JsonFileSaveRepository`。
2. `use_cases/save_game.py` 统一序列化 `RunState/ActState/RoomState/CombatState`（`schema_version=3`）。
3. `use_cases/load_game.py` 校验 schema、恢复模型并合并 combat_state 双来源。

**State Management:**
- 会话级状态集中在 `SessionState`（`src/slay_the_spire/app/session.py`），运行态核心为 `RunState`、`ActState`、`RoomState`，战斗子状态放在 `RoomState.payload["combat_state"]`（`CombatState.to_dict()`）。

## Key Abstractions

**SessionState / MenuState:**
- Purpose: 会话生命周期与菜单状态机抽象。
- Examples: `src/slay_the_spire/app/session.py`
- Pattern: `dataclass(slots=True)` + `replace(...)` 不可变式更新风格。

**RunState / ActState / RoomState / CombatState:**
- Purpose: 运行全局、地图、房间、战斗四层状态模型。
- Examples: `src/slay_the_spire/domain/models/run_state.py`, `src/slay_the_spire/domain/models/act_state.py`, `src/slay_the_spire/domain/models/room_state.py`, `src/slay_the_spire/domain/models/combat_state.py`
- Pattern: `to_dict/from_dict` + `__post_init__` 强校验 + schema version。

**Port Abstractions:**
- Purpose: 解耦内容来源与持久化实现。
- Examples: `src/slay_the_spire/ports/content_provider.py`, `src/slay_the_spire/ports/save_repository.py`
- Pattern: `Protocol` 接口 + `StarterContentProvider` / `JsonFileSaveRepository` 适配器实现。

## Entry Points

**CLI Entry:**
- Location: `src/slay_the_spire/app/cli.py`
- Triggers: 命令 `slay-the-spire new|load`
- Responsibilities: 参数解析、创建/加载 session、交给 Textual UI 托管。

**Textual Runtime Entry:**
- Location: `src/slay_the_spire/adapters/textual/textual_runner.py`
- Triggers: `run_textual_session(session=...)`
- Responsibilities: 初始化 `SlayApp` 并运行主 UI 循环。

**Build Content Entry:**
- Location: `src/slay_the_spire/build_content.py`, `tests/test_build_content.py`
- Triggers: 构建流程/测试调用
- Responsibilities: 将根目录 `content/` 同步到 `src/slay_the_spire/data/content/`。

## Error Handling

**Strategy:** 显式异常 + 路由层转换为玩家可读提示。

**Patterns:**
- 模型与注册表强校验：`TypeError/ValueError`（如 `domain/models/*.py`, `content/registries.py`）。
- 会话路由容错：在 `src/slay_the_spire/app/session.py` 中捕获异常并返回中文状态消息，而不是让异常冒泡到 UI。

## Cross-Cutting Concerns

**Logging:** 使用战斗文本日志而非标准 logging，入口在 `src/slay_the_spire/use_cases/combat_log.py`，UI 显示由 `adapters/textual/slay_app.py` 的日志面板承接。  
**Validation:** 内容与状态双重校验，启动阶段 `content/catalog.py -> validate_startup_integrity(...)`，运行阶段由 dataclass `__post_init__` 与 use case 判定约束。  
**Authentication:** Not applicable（本地单机，无账号体系与外部鉴权）。  

---

*Architecture analysis: 2026-04-11*
