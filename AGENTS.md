# AGENTS

## 文档职责

- `AGENTS.md` 只用于给代理/协作者说明本仓库的协作约束、代码事实入口和修改注意事项。
- 项目介绍、当前功能说明、快速开始、运行命令等面向人类读者的内容放在 `README.md`，不要在这里重复维护。
- 若 `AGENTS.md` 与其他文档冲突，优先以代码和测试为准。

## 项目边界

- 这是一个 Python 3.12 的 `textual` TUI 版《Slay the Spire》原型项目。
- 当前玩法内容与系统基线默认以原版《Slay the Spire》1 代为主。
- 默认且唯一运行界面是基于 `textual` 的 TUI；底层复用共享的 `rich` 展示组件。
- 目标是本地单机、可回放的菜单驱动流程，不是图形界面项目，也不是服务端项目。
- Python 相关环境、依赖管理和命令执行默认都使用 `uv`。

## 代码事实入口

- `pyproject.toml`：包配置、依赖、pytest 配置、脚本入口、打包声明。
- `docs/reference/`：本地参考资料，包含红色牌和无色牌的卡牌列表；仅作开发参考，不参与运行时加载。
- `src/slay_the_spire/app/cli.py`：CLI 入口。
- `src/slay_the_spire/app/session.py`：会话状态、菜单路由、默认路径、跨幕推进。
- `src/slay_the_spire/app/menu_definitions.py`：编号菜单定义。
- `src/slay_the_spire/adapters/presentation/`：共享终端展示/渲染、inspect、combat/non-combat 屏幕。
- `src/slay_the_spire/adapters/textual/`：Textual 入口、地图组件、日志和交互面板。
- `src/slay_the_spire/adapters/persistence/save_files.py`：JSON 存档读写。
- `src/slay_the_spire/content/`：内容加载与注册表。
- `src/slay_the_spire/domain/`：战斗、状态模型、Hook、地图生成、奖励生成等领域逻辑。
- `src/slay_the_spire/use_cases/`：开始游戏、出牌、结束回合、进房间、事件、商店、休息、奖励、存读档等用例。
- `content/`：唯一内容真源，开发时编辑的内容 JSON。
- `src/slay_the_spire/data/content/`：构建 wheel 时临时生成的包内内容 JSON。
- `tests/`：UI、内容校验、领域逻辑、存档和 E2E 测试。

## 协作规则

- 默认优先相信 `src/slay_the_spire/app/session.py`、`tests/` 和 `content/`，不要优先相信旧设计文档。
- 面向玩家的菜单、事件、奖励、效果说明等 UI 文案默认统一写中文；代码标识、命令、路径和必要专有名词可保留原文。
- 做设计取舍时，如果 1 代、2 代资料或旧设计文档冲突，默认以“当前代码中的 1 代内容基线 + 已落地行为”优先；只有需求明确指定时才转向 2 代。
- 若需要参考原版资料，优先查看本地参考资料 `docs/reference/`；需要补充上下文或交叉校验时，再查询外部 Wiki。
- 外部英文资料优先参考官方社区 Wiki：[Slay the Spire Wiki](https://slay-the-spire.fandom.com/wiki/)。
- 中文卡牌中英对照与术语校对优先参考：[杀戮尖塔中文 Wiki](https://sts.huijiwiki.com/wiki/) 需要用tvly skill访问。

## 修改约束

- 修改内容 JSON 时，只改根目录 `content/`。
- 默认运行优先读取根目录 `content/`；`src/slay_the_spire/data/content/` 仅在构建 wheel 时临时生成，不应手工维护。
- 当前存档 `schema_version` 是 `3`；如果改动存档结构，要同步处理 `save_game.py`、`load_game.py` 和相关测试。
- 当前开发阶段默认不需要兼容旧存档或旧菜单状态；若重构需要删除旧分支，可直接清理，除非需求明确要求兼容。
- 仓库当前没有 `.env` / `.env.example`，也没有外部服务凭据依赖。
- 存档文件默认写入 `saves/latest.json`；用户已明确说明：存档不需要提交。

## 变更联动检查

- 新增房间类型前，先确认地图内容、use case / session 路由、共享展示层 / Textual 展示三层都补齐。
- 调整 Boss 奖励或跨幕流程时，同时检查 `boss -> boss_chest -> 下一幕 / victory` 这条完整链路。
- 新增角色、卡牌、敌人、事件、遗物或药水时，同时检查内容注册表、掉落入口和对应测试。
- 新增战斗后奖励或 Boss 奖励时，同时检查 `src/slay_the_spire/domain/rewards/reward_generator.py`、`src/slay_the_spire/use_cases/apply_reward.py` 和对应测试。
- 修改菜单、渲染或会话路由时，优先检查 `tests/adapters/presentation/` 和 `tests/e2e/`。
- 修改 Textual UI 时，优先检查 `tests/adapters/textual/test_slay_app.py`。
- 修改内容注册表或 JSON 结构时，优先检查 `tests/content/test_registry_validation.py`。
- 修改存档结构时，优先检查 `tests/use_cases/test_save_load.py`。

## 文档维护

- 改动代码、内容、命令入口、流程、测试基线或发布方式后，同步更新 `README.md`。
- 新增、迁移或更新本地参考资料目录后，同步更新 `README.md` 中的资料入口；只有协作约束或资料优先级规则变化时才更新 `AGENTS.md`。
- 只有当协作约束、仓库事实入口或修改约束发生变化时，才更新 `AGENTS.md`。

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Slay the Spire TUI 原版复刻**

这是一个基于 Python 3.12、Textual 和 Rich 的本地单机 TUI 版《杀戮尖塔》复刻项目。当前已有可运行的菜单驱动原型，后续目标是按批次补齐原版《Slay the Spire》1 代的角色、卡牌、遗物、事件、敌人、Boss、奖励、房间流程与规则交互。

**Core Value:** 玩家可以在终端中完成一局尽可能贴近原版 1 代规则与内容的《杀戮尖塔》流程，并且运行结果可存档、可回放、可测试。

### Constraints

- **Tech stack**: Python 3.12+、Textual、Rich、pytest、uv — 仓库现有技术栈，后续默认沿用。
- **Content source**: 只手工维护根目录 `content/` — `src/slay_the_spire/data/content/` 是构建 wheel 时的包内内容副本，不作为开发期编辑入口。
- **UI boundary**: 默认且唯一运行界面是 Textual TUI — 新功能要优先补齐 TUI 和共享 Rich 展示。
- **Game baseline**: 默认以原版《Slay the Spire》1 代为准 — 1 代、2 代资料或旧设计文档冲突时，以当前 1 代内容基线和已落地行为优先。
- **Persistence**: 当前存档 schema version 是 `3` — 改动存档结构要同步 `save_game.py`、`load_game.py` 和相关测试。
- **Testing**: 内容、领域规则、会话路由、Textual UI 与 E2E 流程都需要按改动风险补测试 — 项目目标是可回放、可验证的本地流程。
- **Docs**: 改动代码、内容、命令入口、流程、测试基线或发布方式后同步更新 README — 只有协作约束变化才更新 AGENTS.md。
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12+ - 主业务代码与测试，见 `pyproject.toml`、`src/slay_the_spire/`、`tests/`
- JSON - 游戏内容与存档数据，见 `content/`、`src/slay_the_spire/data/content/`、`saves/latest.json`
- Markdown - 项目文档与本地 Wiki 输出，见 `README.md`、`docs/`、`scripts/generate_local_wiki.py`
## Runtime
- CPython 3.12+（仓库约束）- 见 `pyproject.toml` 的 `requires-python = ">=3.12"`
- `uv`（版本未在仓库固定）- 见 `README.md` 中 `uv sync` / `uv run` / `uv build`
- Lockfile: present（`uv.lock`）
## Frameworks
- `textual>=8.1.1` - 默认且唯一 TUI 运行界面，见 `pyproject.toml`、`src/slay_the_spire/adapters/textual/slay_app.py`
- `rich>=14.3.3` - 终端渲染与共享展示组件，见 `pyproject.toml`、`src/slay_the_spire/adapters/presentation/renderer.py`
- `pytest>=8.0` - 单元/集成/E2E 测试执行，见 `pyproject.toml`、`tests/`
- `setuptools>=64` + `wheel` - 构建后端与打包，见 `pyproject.toml`
- `uv` - 依赖同步、运行、构建入口，见 `README.md`
## Key Dependencies
- `textual` - 驱动主交互与 UI 事件循环，见 `src/slay_the_spire/adapters/textual/textual_runner.py`
- `rich` - 驱动屏幕布局、面板、文本渲染，见 `src/slay_the_spire/adapters/presentation/widgets.py`
- Python 标准库 `argparse` / `pathlib` / `json` / `dataclasses` - CLI、路径、序列化、状态模型，见 `src/slay_the_spire/app/cli.py`、`src/slay_the_spire/adapters/persistence/save_files.py`
## Configuration
- 未检测到 `.env` 依赖；运行参数通过 CLI 显式传入，见 `src/slay_the_spire/app/cli.py`
- 关键运行参数：`--content-root`、`--save-path`、`--seed`、`--character`，见 `src/slay_the_spire/app/cli.py`
- `pyproject.toml` - 依赖、入口脚本、pytest、setuptools 配置
- `setup.py` - 打包补充声明
- `MANIFEST.in` - 打包文件包含规则
## Platform Requirements
- 本地终端环境（支持 Textual TUI）+ Python 3.12+ + `uv`，见 `README.md`
- 本地可写文件系统（存档写入 `saves/`），见 `src/slay_the_spire/app/session.py`、`src/slay_the_spire/adapters/persistence/save_files.py`
- 本地单机 CLI/TUI 运行（非服务端部署），见 `README.md`
- 可打包为 wheel/sdist，本地安装后通过 `slay-the-spire` 命令启动，见 `pyproject.toml`、`README.md`
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- 源码与测试文件使用 `snake_case.py`，例如 `src/slay_the_spire/use_cases/play_card.py`、`tests/use_cases/test_play_card.py`。
- 测试文件统一 `test_*.py`，按领域分目录，例如 `tests/domain/test_state_serialization.py`、`tests/e2e/test_two_act_smoke.py`。
- 公有函数使用 `snake_case`，例如 `start_new_game_session`（`src/slay_the_spire/app/session.py`）、`generate_act_state`（`src/slay_the_spire/domain/map/map_generator.py`）。
- 模块内私有辅助函数使用前缀下划线，例如 `_require_int`（`src/slay_the_spire/domain/models/run_state.py`）、`_menu_choice_for_action`（`src/slay_the_spire/adapters/textual/slay_app.py`）。
- 局部变量和参数使用 `snake_case`，例如 `card_instance_id`、`combat_state`（`src/slay_the_spire/use_cases/play_card.py`）。
- 常量使用全大写下划线风格，例如 `_ENEMY_TARGET_EFFECT_TYPES`（`src/slay_the_spire/app/session.py`）、`SAVE_SCHEMA_VERSION`（`src/slay_the_spire/use_cases/save_game.py`）。
- 数据模型优先 `@dataclass` + 类型注解，例如 `RunState`（`src/slay_the_spire/domain/models/run_state.py`）、`CombatState`（`src/slay_the_spire/domain/models/combat_state.py`）。
- 协议接口使用 `Protocol`，例如 `ContentProviderPort`（`src/slay_the_spire/ports/content_provider.py`）、`RendererPort`（`src/slay_the_spire/ports/renderer.py`）。
- JSON 结构通过 `TypeAlias` / `TypedDict` 描述，例如 `JsonDict`（`src/slay_the_spire/shared/types.py`）、`SavedGameDocument`（`src/slay_the_spire/use_cases/save_game.py`）。
## Code Style
- 未检测到 `black`/`ruff format`/`isort` 专用配置文件（根目录未发现 `ruff.toml`、`.ruff.toml`、`pyproject` 中未配置格式化工具）。
- 实际代码风格为 PEP8 风格、广泛使用类型注解与 `from __future__ import annotations`（例如 `src/slay_the_spire/app/cli.py`、`src/slay_the_spire/domain/models/run_state.py`）。
- 未检测到 `ruff`/`flake8`/`pylint`/`mypy`/`pyright` 配置（`pyproject.toml` 仅配置 pytest 与打包）。
- 当前质量基线主要由测试约束（`tests/`）与运行时类型/值校验（例如 `src/slay_the_spire/content/registries.py`）保障。
## Import Organization
- 未使用路径别名；统一使用包绝对导入 `slay_the_spire.*`（例如 `src/slay_the_spire/use_cases/apply_reward.py`、`tests/app/test_session.py`）。
## Error Handling
- 输入与数据结构校验失败时，按语义抛出 `TypeError`/`ValueError`（例如 `_require_*` 系列在 `src/slay_the_spire/domain/models/run_state.py` 和 `src/slay_the_spire/content/registries.py`）。
- 查找缺失内容时抛出 `KeyError`（例如 `_BaseRegistry.get` 在 `src/slay_the_spire/content/registries.py`）。
- 用例层对非法操作即时失败（如 `play_card` 相关校验，见 `src/slay_the_spire/use_cases/play_card.py`）。
## Logging
- 未检测到 `logging`/`logger` 体系（`src/` 与 `tests/` 中无 `logging.getLogger`）。
- 运行时展示通过 Rich 渲染与 Textual 组件输出，例如 `render_room`（`src/slay_the_spire/adapters/presentation/renderer.py`）、`RichLog` 面板（`src/slay_the_spire/adapters/textual/slay_app.py`）。
## Comments
- 代码内注释偏少，主要在复杂测试路径用简短中文说明意图，例如 `tests/e2e/test_single_act_smoke.py` 的 Boss 路径注释。
- 不适用（Python 项目）。
- 文档字符串少量使用，例如模块级 docstring：`src/slay_the_spire/adapters/textual/slay_app.py`。
## Function Design
## Module Design
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- `src/slay_the_spire/app/session.py` 作为单一编排中心，统一维护会话状态、菜单状态、路由与跨幕推进。
- 业务动作以 `src/slay_the_spire/use_cases/*.py` 函数方式实现，输入/输出以 `RunState`、`RoomState`、`CombatState` 等模型传递。
- 领域规则集中在 `src/slay_the_spire/domain/`，内容读取与存档读写通过 `ports` + `adapters` 连接。
## Layers
- Purpose: 解析命令行参数并启动会话。
- Location: `src/slay_the_spire/app/cli.py`
- Contains: `argparse` 子命令 `new/load`、seed 生成、Textual 启动调用。
- Depends on: `src/slay_the_spire/app/session.py`, `src/slay_the_spire/adapters/textual/textual_runner.py`
- Used by: `pyproject.toml` 的 `slay-the-spire = "slay_the_spire.app.cli:main"`
- Purpose: 维护 `SessionState`，将菜单动作路由到对应 use case，并组装渲染输出。
- Location: `src/slay_the_spire/app/session.py`, `src/slay_the_spire/app/menu_definitions.py`, `src/slay_the_spire/app/next_room_options.py`
- Contains: 菜单模式状态机（`MenuState.mode`）、`route_menu_choice` 分发、`render_session(_renderable)`、开局流程与 Boss 链路处理。
- Depends on: `use_cases/*`, `domain/models/*`, `domain/rewards/reward_generator.py`, `content/provider.py`, `adapters/presentation/*`, `adapters/persistence/save_files.py`
- Used by: Textual 应用 `src/slay_the_spire/adapters/textual/slay_app.py`
- Purpose: 实现玩家动作与房间行为（进入房间、出牌、结束回合、商店/休息点/事件、奖励、存读档）。
- Location: `src/slay_the_spire/use_cases/`
- Contains: `start_run.py`, `enter_room.py`, `play_card.py`, `end_turn.py`, `shop_action.py`, `rest_action.py`, `event_action.py`, `apply_reward.py`, `save_game.py`, `load_game.py` 等。
- Depends on: `domain/*`, `ports/*`, `content/registries.py`；部分文件直接依赖 `adapters/presentation/widgets.py`（如 `use_potion.py`, `combat_events.py`）。
- Used by: `app/session.py`
- Purpose: 封装核心规则与状态模型。
- Location: `src/slay_the_spire/domain/`
- Contains: 
- Depends on: `ports/content_provider.py`, `content/registries.py`, `shared/*`
- Used by: `use_cases/*`, `app/session.py`
- Purpose: 从 JSON 内容构建强类型注册表并进行启动期校验。
- Location: `src/slay_the_spire/content/catalog.py`, `src/slay_the_spire/content/provider.py`, `src/slay_the_spire/content/registries.py`, `content/`
- Contains: JSON 加载、池子成员与权重、`CardDef/RelicDef/...` 注册与完整性检查。
- Depends on: `src/slay_the_spire/content/loaders.py`, `src/slay_the_spire/shared/types.py`
- Used by: `app/session.py`, `use_cases/*`, `domain/*`
- Purpose: 提供渲染、交互与存储实现。
- Location:
- Contains: Rich renderable 组装、Textual 组件与 UI 事件、JSON 文件存档仓储。
- Depends on: `app/*`, `domain/models/*`, `ports/*`
- Used by: `app/cli.py`, `app/session.py`
## Data Flow
- 会话级状态集中在 `SessionState`（`src/slay_the_spire/app/session.py`），运行态核心为 `RunState`、`ActState`、`RoomState`，战斗子状态放在 `RoomState.payload["combat_state"]`（`CombatState.to_dict()`）。
## Key Abstractions
- Purpose: 会话生命周期与菜单状态机抽象。
- Examples: `src/slay_the_spire/app/session.py`
- Pattern: `dataclass(slots=True)` + `replace(...)` 不可变式更新风格。
- Purpose: 运行全局、地图、房间、战斗四层状态模型。
- Examples: `src/slay_the_spire/domain/models/run_state.py`, `src/slay_the_spire/domain/models/act_state.py`, `src/slay_the_spire/domain/models/room_state.py`, `src/slay_the_spire/domain/models/combat_state.py`
- Pattern: `to_dict/from_dict` + `__post_init__` 强校验 + schema version。
- Purpose: 解耦内容来源与持久化实现。
- Examples: `src/slay_the_spire/ports/content_provider.py`, `src/slay_the_spire/ports/save_repository.py`
- Pattern: `Protocol` 接口 + `StarterContentProvider` / `JsonFileSaveRepository` 适配器实现。
## Entry Points
- Location: `src/slay_the_spire/app/cli.py`
- Triggers: 命令 `slay-the-spire new|load`
- Responsibilities: 参数解析、创建/加载 session、交给 Textual UI 托管。
- Location: `src/slay_the_spire/adapters/textual/textual_runner.py`
- Triggers: `run_textual_session(session=...)`
- Responsibilities: 初始化 `SlayApp` 并运行主 UI 循环。
- Location: `src/slay_the_spire/build_content.py`, `tests/test_build_content.py`
- Triggers: 构建流程/测试调用
- Responsibilities: 将根目录 `content/` 同步到 `src/slay_the_spire/data/content/`。
## Error Handling
- 模型与注册表强校验：`TypeError/ValueError`（如 `domain/models/*.py`, `content/registries.py`）。
- 会话路由容错：在 `src/slay_the_spire/app/session.py` 中捕获异常并返回中文状态消息，而不是让异常冒泡到 UI。
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
