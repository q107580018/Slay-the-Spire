# Testing Patterns

**Analysis Date:** 2026-04-11

## Test Framework

**Runner:**
- `pytest`（来自 `pyproject.toml` 的 `dev` 依赖：`pytest>=8.0`）
- Config: `pyproject.toml`（`[tool.pytest.ini_options] pythonpath = ["src"]`）

**Assertion Library:**
- `pytest` 原生断言与异常断言（`assert`、`pytest.raises`），示例见 `tests/use_cases/test_play_card.py`、`tests/content/test_registry_validation.py`。

**Run Commands:**
```bash
uv run pytest                 # Run all tests
Not detected                  # Watch mode
Not detected                  # Coverage
```

## Test File Organization

**Location:**
- 按层级分目录组织，集中在 `tests/`，例如：
- `tests/app/`（会话/菜单/CLI）
- `tests/adapters/`（presentation/textual）
- `tests/use_cases/`（流程用例）
- `tests/domain/`（领域逻辑与序列化）
- `tests/content/`（内容注册与校验）
- `tests/e2e/`（主流程冒烟）

**Naming:**
- 文件命名统一 `test_*.py`，例如 `tests/e2e/test_single_act_smoke.py`。
- 测试函数命名统一 `test_<behavior>...`，例如 `test_save_game_persists_json_document_with_schema_version`（`tests/use_cases/test_save_load.py`）。

**Structure:**
```text
tests/
  app/
  adapters/presentation/
  adapters/textual/
  content/
  domain/
  use_cases/
  e2e/
```

## Test Structure

**Suite Organization:**
```python
def _factory_or_helper(...):
    ...

def test_behavior_xxx() -> None:
    state = _factory_or_helper(...)
    result = target_fn(...)
    assert ...
```
- 该结构在 `tests/use_cases/test_play_card.py`、`tests/use_cases/test_save_load.py`、`tests/e2e/test_two_act_smoke.py` 一致存在。

**Patterns:**
- Setup pattern: 使用模块内私有 helper 构造状态（如 `_combat_state`、`_provider_with_card`，见 `tests/use_cases/test_play_card.py`）。
- Teardown pattern: 主要依赖 `tmp_path` 临时目录与 pytest 生命周期自动清理（如 `tests/use_cases/test_save_load.py`）。
- Assertion pattern: 断言业务状态字段、菜单模式、文本片段与异常消息（如 `tests/adapters/presentation/test_renderer.py`、`tests/app/test_cli_textual.py`）。

## Mocking

**Framework:** `pytest` 内置 `monkeypatch`

**Patterns:**
```python
def test_main_new_run_dispatches_first_room_to_textual(monkeypatch) -> None:
    monkeypatch.setattr(
        "slay_the_spire.app.cli.run_textual_session",
        fake_run_textual_session,
    )
```
- 示例来源：`tests/e2e/test_single_act_smoke.py`、`tests/app/test_cli_textual.py`、`tests/use_cases/test_enter_room.py`。

**What to Mock:**
- 外部边界与副作用入口：UI 启动函数、随机种子入口、目录切换等（`tests/app/test_cli_textual.py`、`tests/app/test_opening_session.py`）。

**What NOT to Mock:**
- 领域模型序列化、内容注册、核心用例逻辑通常直接跑真实对象（`tests/domain/test_state_serialization.py`、`tests/content/test_registry_validation.py`、`tests/use_cases/test_apply_reward.py`）。

## Fixtures and Factories

**Test Data:**
```python
def _run_state() -> RunState:
    return RunState(seed=11, character_id="ironclad", current_act_id="act1")
```
- 工厂函数在单个测试模块内本地定义并复用，例如 `tests/use_cases/test_save_load.py`、`tests/use_cases/test_play_card.py`。

**Location:**
- 未检测到共享 `conftest.py`；fixture/factory 以“测试文件内 helper 函数”为主。

## Coverage

**Requirements:** None enforced（未检测到 coverage 配置和阈值）

**View Coverage:**
```bash
Not detected
```

## Test Types

**Unit Tests:**
- 覆盖单模块规则、校验和状态转换，如 `tests/domain/test_effect_resolver.py`、`tests/shared/test_rng.py`。

**Integration Tests:**
- 覆盖跨层流程（内容加载 + 用例 + 存档），如 `tests/use_cases/test_save_load.py`、`tests/use_cases/test_room_recovery.py`。

**E2E Tests:**
- 使用 `pytest` 进行菜单链路冒烟，不依赖独立 E2E 框架；示例 `tests/e2e/test_single_act_smoke.py`、`tests/e2e/test_two_act_smoke.py`。

## Common Patterns

**Async Testing:**
```python
async def scenario() -> None:
    app = SlayApp(start_new_game_session(seed=5))
    async with app.run_test() as pilot:
        await pilot.pause()

asyncio.run(scenario())
```
- 示例来源：`tests/adapters/textual/test_slay_app.py`。

**Error Testing:**
```python
with pytest.raises(ValueError, match="target"):
    play_card(state, "custom_strike#1", None, provider)
```
- 示例来源：`tests/use_cases/test_play_card.py`、`tests/domain/test_state_serialization.py`。

---

*Testing analysis: 2026-04-11*
