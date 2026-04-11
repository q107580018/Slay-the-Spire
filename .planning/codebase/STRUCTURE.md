# Codebase Structure

**Analysis Date:** 2026-04-11

## Directory Layout

```text
Slay-the-Spire/
├── content/                         # 运行时内容真源（角色/卡牌/敌人/事件/遗物/药水/幕）
├── src/slay_the_spire/              # 主包源码
│   ├── app/                         # 会话与菜单编排层
│   ├── use_cases/                   # 动作用例层
│   ├── domain/                      # 领域规则与状态模型
│   ├── content/                     # 内容加载与注册表
│   ├── adapters/                    # 表现层、Textual UI、持久化适配器
│   ├── ports/                       # Protocol 抽象接口
│   ├── shared/                      # 通用类型与随机工具
│   └── build_content.py             # 打包内容同步工具
├── tests/                           # app/use_cases/domain/adapters/e2e 测试
├── docs/reference/                  # 本地参考资料（不参与运行时加载）
├── saves/                           # 本地存档目录（默认 latest.json）
└── pyproject.toml                   # 包配置与脚本入口
```

## Directory Purposes

**`src/slay_the_spire/app`:**
- Purpose: 会话状态、菜单定义、路由分发、开场流程挂接。
- Contains: `session.py`, `menu_definitions.py`, `next_room_options.py`, `opening_state.py`。
- Key files: `src/slay_the_spire/app/session.py`, `src/slay_the_spire/app/menu_definitions.py`

**`src/slay_the_spire/use_cases`:**
- Purpose: 玩家动作与房间行为编排（函数式用例）。
- Contains: 战斗动作、房间进入、事件/商店/休息点、奖励、存读档。
- Key files: `src/slay_the_spire/use_cases/play_card.py`, `src/slay_the_spire/use_cases/enter_room.py`, `src/slay_the_spire/use_cases/save_game.py`

**`src/slay_the_spire/domain`:**
- Purpose: 纯规则核心与状态模型。
- Contains: `models/`, `combat/`, `effects/`, `hooks/`, `map/`, `rewards/`。
- Key files: `src/slay_the_spire/domain/combat/turn_flow.py`, `src/slay_the_spire/domain/effects/effect_resolver.py`, `src/slay_the_spire/domain/models/run_state.py`

**`src/slay_the_spire/content`:**
- Purpose: 从 JSON 目录构建注册表并提供查询。
- Contains: `catalog.py`, `provider.py`, `registries.py`, `loaders.py`。
- Key files: `src/slay_the_spire/content/catalog.py`, `src/slay_the_spire/content/registries.py`

**`src/slay_the_spire/adapters/presentation`:**
- Purpose: Rich 渲染组件与战斗/非战斗屏幕拼装。
- Contains: `renderer.py`, `widgets.py`, `opening_renderer.py`, `screens/*.py`。
- Key files: `src/slay_the_spire/adapters/presentation/renderer.py`, `src/slay_the_spire/adapters/presentation/screens/combat.py`

**`src/slay_the_spire/adapters/textual`:**
- Purpose: Textual App、地图组件、交互与布局。
- Contains: `slay_app.py`, `map_widget.py`, `map_layout.py`, `textual_runner.py`。
- Key files: `src/slay_the_spire/adapters/textual/slay_app.py`, `src/slay_the_spire/adapters/textual/map_widget.py`

**`src/slay_the_spire/adapters/persistence`:**
- Purpose: JSON 存档文件读写实现。
- Contains: `save_files.py`
- Key files: `src/slay_the_spire/adapters/persistence/save_files.py`

**`src/slay_the_spire/ports`:**
- Purpose: 内容、输入、渲染、存储协议定义。
- Contains: `content_provider.py`, `save_repository.py`, `input_port.py`, `renderer.py`
- Key files: `src/slay_the_spire/ports/content_provider.py`

**`content`:**
- Purpose: 运行时唯一内容真源。
- Contains: `acts/`, `cards/`, `characters/`, `encounters/`, `enemies/`, `events/`, `potions/`, `relics/`。
- Key files: `content/acts/act1_map.json`, `content/cards/ironclad_starter.json`, `content/relics/common_relics.json`

## Key File Locations

**Entry Points:**
- `pyproject.toml`: CLI 脚本入口声明 `slay-the-spire = "slay_the_spire.app.cli:main"`
- `src/slay_the_spire/app/cli.py`: 程序入口（new/load）
- `src/slay_the_spire/adapters/textual/textual_runner.py`: Textual 运行入口

**Configuration:**
- `pyproject.toml`: Python 版本、依赖、pytest、setuptools 配置
- `src/slay_the_spire/build_content.py`: 内容打包同步路径策略

**Core Logic:**
- `src/slay_the_spire/app/session.py`: 会话主状态机与路由
- `src/slay_the_spire/use_cases/`: 所有玩家动作用例
- `src/slay_the_spire/domain/`: 核心规则与模型
- `src/slay_the_spire/content/`: 内容注册与加载

**Testing:**
- `tests/app/`: 会话与菜单行为
- `tests/use_cases/`: 用例行为
- `tests/domain/`: 领域规则与序列化
- `tests/adapters/textual/`: Textual UI
- `tests/e2e/`: 端到端烟雾流程

## Naming Conventions

**Files:**
- `snake_case.py`: 例如 `start_run.py`, `reward_generator.py`, `map_layout.py`

**Directories:**
- 分层目录名语义化：`app`, `use_cases`, `domain`, `content`, `adapters`, `ports`, `shared`

## Where to Add New Code

**New Feature:**
- Primary code:  
  - 菜单/会话路由：`src/slay_the_spire/app/session.py` 与 `src/slay_the_spire/app/menu_definitions.py`
  - 业务动作：`src/slay_the_spire/use_cases/` 下新增或扩展文件
  - 规则实现：`src/slay_the_spire/domain/` 对应子目录
  - 新内容定义：根目录 `content/`（不要手改 `src/slay_the_spire/data/content/`）
- Tests:  
  - 会话路由：`tests/app/test_session.py`
  - 用例：`tests/use_cases/`
  - 领域规则：`tests/domain/`
  - Textual 交互：`tests/adapters/textual/test_slay_app.py`
  - 端到端流程：`tests/e2e/`

**New Component/Module:**
- Implementation:  
  - 新渲染组件：`src/slay_the_spire/adapters/presentation/`
  - 新 Textual 组件：`src/slay_the_spire/adapters/textual/`
  - 新协议：`src/slay_the_spire/ports/`
  - 新适配器实现：`src/slay_the_spire/adapters/`

**Utilities:**
- Shared helpers: `src/slay_the_spire/shared/`

## Special Directories

**`content/`:**
- Purpose: 运行时内容真源（开发期只改这里）
- Generated: No
- Committed: Yes

**`src/slay_the_spire/data/content/`:**
- Purpose: wheel 构建时的包内内容副本
- Generated: Yes（由 `src/slay_the_spire/build_content.py` 同步）
- Committed: Yes（作为包数据）

**`saves/`:**
- Purpose: 本地存档输出目录（默认 `saves/latest.json`）
- Generated: Yes（运行时）
- Committed: No（按协作约束不需要提交）

**`docs/reference/`:**
- Purpose: 本地参考资料，供开发校验术语与内容
- Generated: No
- Committed: Yes

**`src/slay_the_spire/adapters/terminal/` 与 `src/slay_the_spire/adapters/rich_ui/`:**
- Purpose: 当前仓库中仅见 `__pycache__` 目录，未检测到对应 `.py` 源文件
- Generated: Yes（Python 运行缓存）
- Committed: Yes（当前状态下存在）

---

*Structure analysis: 2026-04-11*
