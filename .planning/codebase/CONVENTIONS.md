# Coding Conventions

**Analysis Date:** 2026-04-11

## Naming Patterns

**Files:**
- 源码与测试文件使用 `snake_case.py`，例如 `src/slay_the_spire/use_cases/play_card.py`、`tests/use_cases/test_play_card.py`。
- 测试文件统一 `test_*.py`，按领域分目录，例如 `tests/domain/test_state_serialization.py`、`tests/e2e/test_two_act_smoke.py`。

**Functions:**
- 公有函数使用 `snake_case`，例如 `start_new_game_session`（`src/slay_the_spire/app/session.py`）、`generate_act_state`（`src/slay_the_spire/domain/map/map_generator.py`）。
- 模块内私有辅助函数使用前缀下划线，例如 `_require_int`（`src/slay_the_spire/domain/models/run_state.py`）、`_menu_choice_for_action`（`src/slay_the_spire/adapters/textual/slay_app.py`）。

**Variables:**
- 局部变量和参数使用 `snake_case`，例如 `card_instance_id`、`combat_state`（`src/slay_the_spire/use_cases/play_card.py`）。
- 常量使用全大写下划线风格，例如 `_ENEMY_TARGET_EFFECT_TYPES`（`src/slay_the_spire/app/session.py`）、`SAVE_SCHEMA_VERSION`（`src/slay_the_spire/use_cases/save_game.py`）。

**Types:**
- 数据模型优先 `@dataclass` + 类型注解，例如 `RunState`（`src/slay_the_spire/domain/models/run_state.py`）、`CombatState`（`src/slay_the_spire/domain/models/combat_state.py`）。
- 协议接口使用 `Protocol`，例如 `ContentProviderPort`（`src/slay_the_spire/ports/content_provider.py`）、`RendererPort`（`src/slay_the_spire/ports/renderer.py`）。
- JSON 结构通过 `TypeAlias` / `TypedDict` 描述，例如 `JsonDict`（`src/slay_the_spire/shared/types.py`）、`SavedGameDocument`（`src/slay_the_spire/use_cases/save_game.py`）。

## Code Style

**Formatting:**
- 未检测到 `black`/`ruff format`/`isort` 专用配置文件（根目录未发现 `ruff.toml`、`.ruff.toml`、`pyproject` 中未配置格式化工具）。
- 实际代码风格为 PEP8 风格、广泛使用类型注解与 `from __future__ import annotations`（例如 `src/slay_the_spire/app/cli.py`、`src/slay_the_spire/domain/models/run_state.py`）。

**Linting:**
- 未检测到 `ruff`/`flake8`/`pylint`/`mypy`/`pyright` 配置（`pyproject.toml` 仅配置 pytest 与打包）。
- 当前质量基线主要由测试约束（`tests/`）与运行时类型/值校验（例如 `src/slay_the_spire/content/registries.py`）保障。

## Import Organization

**Order:**
1. `from __future__ import annotations` 放在文件开头（如 `src/slay_the_spire/use_cases/play_card.py`、`tests/use_cases/test_save_load.py`）。
2. 标准库导入（如 `argparse`、`pathlib.Path`，见 `src/slay_the_spire/app/cli.py`、`src/slay_the_spire/app/session.py`）。
3. 第三方库导入（如 `pytest`、`textual`、`rich`，见 `tests/adapters/textual/test_slay_app.py`、`src/slay_the_spire/adapters/textual/slay_app.py`）。
4. 项目内导入 `slay_the_spire.*`（全仓普遍采用）。

**Path Aliases:**
- 未使用路径别名；统一使用包绝对导入 `slay_the_spire.*`（例如 `src/slay_the_spire/use_cases/apply_reward.py`、`tests/app/test_session.py`）。

## Error Handling

**Patterns:**
- 输入与数据结构校验失败时，按语义抛出 `TypeError`/`ValueError`（例如 `_require_*` 系列在 `src/slay_the_spire/domain/models/run_state.py` 和 `src/slay_the_spire/content/registries.py`）。
- 查找缺失内容时抛出 `KeyError`（例如 `_BaseRegistry.get` 在 `src/slay_the_spire/content/registries.py`）。
- 用例层对非法操作即时失败（如 `play_card` 相关校验，见 `src/slay_the_spire/use_cases/play_card.py`）。

## Logging

**Framework:** Rich/Textual UI 输出；未使用标准日志框架

**Patterns:**
- 未检测到 `logging`/`logger` 体系（`src/` 与 `tests/` 中无 `logging.getLogger`）。
- 运行时展示通过 Rich 渲染与 Textual 组件输出，例如 `render_room`（`src/slay_the_spire/adapters/presentation/renderer.py`）、`RichLog` 面板（`src/slay_the_spire/adapters/textual/slay_app.py`）。

## Comments

**When to Comment:**
- 代码内注释偏少，主要在复杂测试路径用简短中文说明意图，例如 `tests/e2e/test_single_act_smoke.py` 的 Boss 路径注释。

**JSDoc/TSDoc:**
- 不适用（Python 项目）。
- 文档字符串少量使用，例如模块级 docstring：`src/slay_the_spire/adapters/textual/slay_app.py`。

## Function Design

**Size:** 采用“编排函数 + 私有辅助函数”风格；复杂模块把规则拆到多个 `_helper`（例如 `src/slay_the_spire/app/session.py`、`src/slay_the_spire/use_cases/play_card.py`）。

**Parameters:** 参数显式 typed，常见关键字参数与 `| None` 可空类型（例如 `start_new_game_session` 在 `src/slay_the_spire/app/session.py`）。

**Return Values:** 返回 dataclass、TypedDict 或明确 tuple；测试也依赖稳定返回结构（如 `route_menu_choice` 在 `src/slay_the_spire/app/session.py`、`LoadedGame` 在 `src/slay_the_spire/use_cases/load_game.py`）。

## Module Design

**Exports:** 直接模块导入为主；无集中 re-export 规则。调用方通常从具体模块导入目标符号（例如 `tests/use_cases/test_play_card.py` 直接导入 `slay_the_spire.use_cases.play_card`）。

**Barrel Files:** Python 包 `__init__.py` 仅做包标识，未形成 TS 风格 barrel（如 `src/slay_the_spire/adapters/presentation/screens/__init__.py`、`src/slay_the_spire/adapters/textual/__init__.py`）。

---

*Convention analysis: 2026-04-11*
