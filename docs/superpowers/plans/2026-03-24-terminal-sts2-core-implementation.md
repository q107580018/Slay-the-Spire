# Terminal StS2 Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Python 构建一个单人、单 Act、终端文字版的 `Slay the Spire 2` 风格核心爬塔骨架，具备可维护的领域模型、数据驱动内容系统、可恢复存档和基础可玩性。

**Architecture:** 项目采用“领域模型 + 数据驱动 + 适配器隔离”结构。规则层只处理状态与结算，内容层只提供声明式定义，终端层只负责渲染与输入，所有状态变更统一通过 effect 管线和 hooks 触发。

**Tech Stack:** Python 3.12+, `uv`, `pytest`, `dataclasses`, `typing`, `json`, standard-library CLI

---

## File Structure Map

### Core application files

- Create: `pyproject.toml`
- Create: `src/slay_the_spire/__init__.py`
- Create: `src/slay_the_spire/app/cli.py`
- Create: `src/slay_the_spire/app/session.py`
- Create: `src/slay_the_spire/ports/renderer.py`
- Create: `src/slay_the_spire/ports/input_port.py`
- Create: `src/slay_the_spire/ports/save_repository.py`
- Create: `src/slay_the_spire/ports/content_provider.py`
- Create: `src/slay_the_spire/shared/types.py`
- Create: `src/slay_the_spire/shared/ids.py`
- Create: `src/slay_the_spire/shared/rng.py`

### Domain model files

- Create: `src/slay_the_spire/domain/models/run_state.py`
- Create: `src/slay_the_spire/domain/models/act_state.py`
- Create: `src/slay_the_spire/domain/models/room_state.py`
- Create: `src/slay_the_spire/domain/models/combat_state.py`
- Create: `src/slay_the_spire/domain/models/entities.py`
- Create: `src/slay_the_spire/domain/models/statuses.py`
- Create: `src/slay_the_spire/domain/models/cards.py`
- Create: `src/slay_the_spire/domain/models/relics.py`

### Rules and orchestration files

- Create: `src/slay_the_spire/domain/effects/effect_types.py`
- Create: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Create: `src/slay_the_spire/domain/hooks/hook_types.py`
- Create: `src/slay_the_spire/domain/hooks/hook_dispatcher.py`
- Create: `src/slay_the_spire/domain/combat/turn_flow.py`
- Create: `src/slay_the_spire/domain/map/map_generator.py`
- Create: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Create: `src/slay_the_spire/use_cases/start_run.py`
- Create: `src/slay_the_spire/use_cases/enter_room.py`
- Create: `src/slay_the_spire/use_cases/play_card.py`
- Create: `src/slay_the_spire/use_cases/end_turn.py`
- Create: `src/slay_the_spire/use_cases/claim_reward.py`
- Create: `src/slay_the_spire/use_cases/save_game.py`
- Create: `src/slay_the_spire/use_cases/load_game.py`

### Content and adapters

- Create: `src/slay_the_spire/content/registries.py`
- Create: `src/slay_the_spire/content/loaders.py`
- Create: `src/slay_the_spire/content/catalog.py`
- Create: `src/slay_the_spire/content/provider.py`
- Create: `content/characters/ironclad.json`
- Create: `content/cards/ironclad_starter.json`
- Create: `content/enemies/act1_basic.json`
- Create: `content/enemies/act1_elites.json`
- Create: `content/events/act1_events.json`
- Create: `content/relics/starter_relics.json`
- Create: `content/acts/act1_map.json`
- Create: `src/slay_the_spire/adapters/terminal/renderer.py`
- Create: `src/slay_the_spire/adapters/terminal/prompts.py`
- Create: `src/slay_the_spire/adapters/persistence/save_files.py`

### Tests

- Create: `tests/domain/test_effect_resolver.py`
- Create: `tests/domain/test_hook_dispatcher.py`
- Create: `tests/domain/test_combat_flow.py`
- Create: `tests/domain/test_map_generator.py`
- Create: `tests/domain/test_state_serialization.py`
- Create: `tests/use_cases/test_start_run.py`
- Create: `tests/use_cases/test_play_card.py`
- Create: `tests/use_cases/test_save_load.py`
- Create: `tests/use_cases/test_room_recovery.py`
- Create: `tests/content/test_registry_validation.py`
- Create: `tests/e2e/test_single_act_smoke.py`

## Task 1: Bootstrap Project and Test Harness

**Files:**
- Create: `pyproject.toml`
- Create: `src/slay_the_spire/__init__.py`
- Create: `src/slay_the_spire/app/cli.py`
- Create: `src/slay_the_spire/ports/renderer.py`
- Create: `src/slay_the_spire/ports/input_port.py`
- Create: `src/slay_the_spire/ports/save_repository.py`
- Create: `src/slay_the_spire/ports/content_provider.py`
- Test: `tests/use_cases/test_start_run.py`

- [ ] **Step 1: Write the failing bootstrap test**

```python
from slay_the_spire.app.cli import main


def test_main_returns_zero_for_help():
    assert main(["--help"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_start_run.py::test_main_returns_zero_for_help -v`
Expected: FAIL with import error for `slay_the_spire.app.cli`

- [ ] **Step 3: Create minimal project scaffolding**

```toml
[project]
name = "slay-the-spire"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
pythonpath = ["src"]
```

```python
def main(argv: list[str] | None = None) -> int:
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_start_run.py::test_main_returns_zero_for_help -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/slay_the_spire/__init__.py src/slay_the_spire/app/cli.py src/slay_the_spire/ports/renderer.py src/slay_the_spire/ports/input_port.py src/slay_the_spire/ports/save_repository.py src/slay_the_spire/ports/content_provider.py tests/use_cases/test_start_run.py
git commit -m "chore: bootstrap project scaffolding"
```

## Task 2: Establish Shared Types, IDs, and RNG Port

**Files:**
- Create: `src/slay_the_spire/shared/types.py`
- Create: `src/slay_the_spire/shared/ids.py`
- Create: `src/slay_the_spire/shared/rng.py`
- Test: `tests/domain/test_map_generator.py`

- [ ] **Step 1: Write the failing determinism test**

```python
from slay_the_spire.shared.rng import SeededRng


def test_seeded_rng_is_deterministic():
    left = SeededRng(42)
    right = SeededRng(42)
    assert [left.randint(1, 9) for _ in range(5)] == [right.randint(1, 9) for _ in range(5)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain/test_map_generator.py::test_seeded_rng_is_deterministic -v`
Expected: FAIL with import error for `SeededRng`

- [ ] **Step 3: Implement stable IDs and RNG wrapper**

```python
from dataclasses import dataclass
import random


@dataclass(slots=True)
class SeededRng:
    seed: int

    def __post_init__(self) -> None:
        self._random = random.Random(self.seed)
```

- [ ] **Step 4: Run targeted test**

Run: `uv run pytest tests/domain/test_map_generator.py::test_seeded_rng_is_deterministic -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/shared/types.py src/slay_the_spire/shared/ids.py src/slay_the_spire/shared/rng.py tests/domain/test_map_generator.py
git commit -m "feat: add shared ids and deterministic rng"
```

## Task 3: Model Serializable Run, Act, Room, and Combat State

**Files:**
- Create: `src/slay_the_spire/domain/models/run_state.py`
- Create: `src/slay_the_spire/domain/models/act_state.py`
- Create: `src/slay_the_spire/domain/models/room_state.py`
- Create: `src/slay_the_spire/domain/models/combat_state.py`
- Create: `src/slay_the_spire/domain/models/entities.py`
- Create: `src/slay_the_spire/domain/models/statuses.py`
- Test: `tests/domain/test_state_serialization.py`

- [ ] **Step 1: Write the failing state-ownership and round-trip tests**

```python
from slay_the_spire.domain.models.run_state import RunState


def test_run_state_round_trips_to_dict():
    state = RunState.new(character_id="ironclad", seed=7)
    restored = RunState.from_dict(state.to_dict())
    assert restored.to_dict() == state.to_dict()


def test_room_and_combat_state_round_trip_without_python_object_refs():
    ...


def test_schema_version_is_preserved_on_serialization():
    ...


def test_unknown_schema_version_is_rejected_or_migrated_explicitly():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain/test_state_serialization.py::test_run_state_round_trips_to_dict -v`
Expected: FAIL with missing `RunState`

- [ ] **Step 3: Implement dataclass state models with explicit identity rules**

```python
@dataclass(slots=True)
class RunState:
    schema_version: int
    seed: int
    character_id: str
    current_act_id: str | None
```

- [ ] **Step 4: Add derived-field reconstruction and identity validation**

Run: `uv run pytest tests/domain/test_state_serialization.py -v`
Expected: PASS for run/act/room/combat round-trip, schema-version, unknown-version handling, and derived-field reconstruction tests

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/models/run_state.py src/slay_the_spire/domain/models/act_state.py src/slay_the_spire/domain/models/room_state.py src/slay_the_spire/domain/models/combat_state.py src/slay_the_spire/domain/models/entities.py src/slay_the_spire/domain/models/statuses.py tests/domain/test_state_serialization.py
git commit -m "feat: add serializable run act room and combat state models"
```

## Task 4: Build Typed Content Registries, Loaders, and Provider Contracts

**Files:**
- Create: `src/slay_the_spire/content/registries.py`
- Create: `src/slay_the_spire/content/loaders.py`
- Create: `src/slay_the_spire/content/provider.py`
- Create: `content/characters/ironclad.json`
- Create: `content/cards/ironclad_starter.json`
- Create: `content/enemies/act1_basic.json`
- Create: `content/enemies/act1_elites.json`
- Create: `content/events/act1_events.json`
- Create: `content/relics/starter_relics.json`
- Create: `content/acts/act1_map.json`
- Test: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing typed-registry validation tests**

```python
import pytest
from slay_the_spire.content.registries import CardRegistry, EnemyRegistry


def test_registry_rejects_duplicate_ids():
    registry = CardRegistry()
    registry.register({"id": "strike", "cost": 1, "effects": []})
    with pytest.raises(ValueError):
        registry.register({"id": "strike", "cost": 1, "effects": []})


def test_enemy_registry_rejects_missing_move_table():
    registry = EnemyRegistry()
    with pytest.raises(ValueError):
        registry.register({"id": "jaw_worm"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py::test_registry_rejects_duplicate_ids -v`
Expected: FAIL with missing typed registry implementation

- [ ] **Step 3: Implement typed registries, loaders, and provider contract**

```python
class CardRegistry:
    def register(self, payload: dict) -> None: ...
    def get(self, content_id: str) -> dict: ...


class ContentProviderPort:
    def characters(self) -> CharacterRegistry: ...
    def cards(self) -> CardRegistry: ...
    def enemies(self) -> EnemyRegistry: ...
    def relics(self) -> RelicRegistry: ...
    def events(self) -> EventRegistry: ...
    def acts(self) -> ActRegistry: ...
```

职责约束：

- `src/slay_the_spire/ports/content_provider.py` 只定义 `ContentProviderPort`
- `src/slay_the_spire/content/provider.py` 只实现 `ContentProviderPort`
- `use_cases` 只能依赖 `ContentProviderPort`
- `content/loaders.py` 只负责读取原始 JSON
- `content/registries.py` 只负责 typed registry、校验、查找和启动完整性检查
- `content/catalog.py` 只负责遍历内容目录、调用 loaders、组装 registries 并构建 provider 所需的内容目录对象

- [ ] **Step 4: Add starter content JSON and full registry/provider validation tests**

Run: `uv run pytest tests/content/test_registry_validation.py -v`
Expected: PASS for duplicate-ID, missing-field, loader, provider, and startup integrity tests

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/content/registries.py src/slay_the_spire/content/loaders.py src/slay_the_spire/content/catalog.py src/slay_the_spire/content/provider.py content/characters/ironclad.json content/cards/ironclad_starter.json content/enemies/act1_basic.json content/enemies/act1_elites.json content/events/act1_events.json content/relics/starter_relics.json content/acts/act1_map.json tests/content/test_registry_validation.py
git commit -m "feat: add typed content registries and provider contract"
```

## Task 5: Generate Act Map and Room Progression

**Files:**
- Create: `src/slay_the_spire/domain/map/map_generator.py`
- Create: `src/slay_the_spire/use_cases/start_run.py`
- Create: `src/slay_the_spire/use_cases/enter_room.py`
- Update: `content/acts/act1_map.json`
- Test: `tests/domain/test_map_generator.py`
- Test: `tests/use_cases/test_start_run.py`

- [ ] **Step 1: Write failing map determinism and reachability tests**

```python
def test_map_generator_returns_reachable_nodes():
    result = generate_map(seed=5, act_id="act1")
    assert result.start_nodes
    assert result.reachable_from(result.start_nodes[0])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_map_generator.py tests/use_cases/test_start_run.py -v`
Expected: FAIL because map generation and run start are not implemented

- [ ] **Step 3: Implement map graph and run bootstrap use case**

```python
def start_new_run(character_id: str, seed: int, registry: ContentRegistry) -> RunState:
    ...
```

`ContentProviderPort` 在本任务开始前必须已经暴露 `characters()`，这样 `start_new_run(...)` 才能仅依赖端口读取角色定义，而不触碰具体 provider 的内部实现。

`enter_room.py` 在本任务中只负责：

- 根据节点类型创建 `RoomState`
- 为战斗房间初始化 `CombatState`
- 不执行战斗回合逻辑
- 不处理终端渲染

`content/acts/act1_map.json` 在本任务中应为节点提供显式 `room_type` 元数据；`enter_room.py` 必须消费该元数据，不能依赖 `node_id` 命名约定去猜测房间类型。

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_map_generator.py tests/use_cases/test_start_run.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/map/map_generator.py src/slay_the_spire/use_cases/start_run.py src/slay_the_spire/use_cases/enter_room.py tests/domain/test_map_generator.py tests/use_cases/test_start_run.py
git commit -m "feat: generate act map and start runs"
```

## Task 6: Implement Effect Types, Resolver, and Hook Dispatcher

**Files:**
- Create: `src/slay_the_spire/domain/effects/effect_types.py`
- Create: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Create: `src/slay_the_spire/domain/hooks/hook_types.py`
- Create: `src/slay_the_spire/domain/hooks/hook_dispatcher.py`
- Test: `tests/domain/test_effect_resolver.py`
- Test: `tests/domain/test_hook_dispatcher.py`

- [ ] **Step 1: Write failing timing-invariant and tie-break tests**

```python
def test_effects_append_to_queue_tail_in_order():
    ...


def test_hooks_only_append_new_effects_to_queue_tail():
    ...


def test_resolver_never_recurses_synchronously():
    ...


def test_dead_targets_become_noop_effects():
    ...


def test_on_enemy_defeated_enqueues_before_on_combat_end():
    ...


def test_hook_category_priority_is_stable():
    ...


def test_equal_priority_hooks_use_source_type_order_before_instance_id():
    ...


def test_equal_priority_hooks_sort_by_instance_id():
    ...


def test_on_combat_end_fires_once_even_if_multiple_enemies_die():
    ...


def test_hook_registration_order_serializes_stably():
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_effect_resolver.py tests/domain/test_hook_dispatcher.py -v`
Expected: FAIL because resolver and hooks do not exist and timing rules are unimplemented

- [ ] **Step 3: Implement effect queue, hook priority rules, and deterministic ordering**

```python
class EffectResolver:
    def resolve(self, state: CombatState, queue: list[Effect]) -> CombatState:
        ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_effect_resolver.py tests/domain/test_hook_dispatcher.py -v`
Expected: PASS for FIFO queue, tail-append hooks, no-recursion, no-op dead targets, defeat/combat-end ordering, category priority, source-type ordering, tie-break, single-fire combat-end, and stable hook-order serialization tests

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/effects/effect_types.py src/slay_the_spire/domain/effects/effect_resolver.py src/slay_the_spire/domain/hooks/hook_types.py src/slay_the_spire/domain/hooks/hook_dispatcher.py tests/domain/test_effect_resolver.py tests/domain/test_hook_dispatcher.py
git commit -m "feat: add effect resolver and deterministic hooks"
```

## Task 7: Implement Basic Combat Flow and Card Play Use Cases

**Files:**
- Create: `src/slay_the_spire/domain/models/cards.py`
- Create: `src/slay_the_spire/domain/combat/turn_flow.py`
- Create: `src/slay_the_spire/use_cases/play_card.py`
- Create: `src/slay_the_spire/use_cases/end_turn.py`
- Test: `tests/domain/test_combat_flow.py`
- Test: `tests/use_cases/test_play_card.py`

`domain/combat/turn_flow.py` 在本任务中只负责纯战斗状态迁移：

- 回合开始
- 玩家行动后 effect 触发
- 敌人行动
- 回合结束

`use_cases/play_card.py` 和 `use_cases/end_turn.py` 只负责：

- 校验当前动作是否合法
- 调用 `turn_flow.py` 与 `effect_resolver.py`
- 返回新状态与结构化结果

本任务中的 `play_card.py` / `end_turn.py` / `turn_flow.py` 如需解析卡牌定义或敌人定义，必须通过 `ContentProviderPort` 完成；不能把 `Strike/Defend/Bash` 或敌人行为硬编码进 use case。

当前 `CombatState.hand/draw_pile/discard_pile` 里的字符串在本里程碑中视为 `card_instance_id`；`domain/models/cards.py` 可以提供最小 helper 来从实例 ID 解析 `card_id`，但不要回头重写 Task 3 的状态模型。

- [ ] **Step 1: Write failing combat tests**

```python
def test_playing_strike_spends_energy_and_deals_damage():
    ...


def test_end_turn_runs_enemy_intents_and_draws_new_hand():
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_combat_flow.py tests/use_cases/test_play_card.py -v`
Expected: FAIL because turn flow and play-card use case are incomplete

- [ ] **Step 3: Implement minimal starter combat loop**

```python
def play_card(
    combat_state: CombatState,
    card_instance_id: str,
    target_id: str | None,
    registry: ContentProviderPort,
) -> CombatState:
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_combat_flow.py tests/use_cases/test_play_card.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/models/cards.py src/slay_the_spire/domain/combat/turn_flow.py src/slay_the_spire/use_cases/play_card.py src/slay_the_spire/use_cases/end_turn.py tests/domain/test_combat_flow.py tests/use_cases/test_play_card.py
git commit -m "feat: implement basic combat flow"
```

## Task 8: Add Rewards, Save/Load, and Room Recovery

**Files:**
- Create: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Create: `src/slay_the_spire/adapters/persistence/save_files.py`
- Create: `src/slay_the_spire/use_cases/claim_reward.py`
- Create: `src/slay_the_spire/use_cases/save_game.py`
- Create: `src/slay_the_spire/use_cases/load_game.py`
- Create: `src/slay_the_spire/use_cases/resolve_event_choice.py`
- Create: `src/slay_the_spire/use_cases/shop_action.py`
- Create: `src/slay_the_spire/use_cases/rest_action.py`
- Test: `tests/use_cases/test_save_load.py`
- Test: `tests/use_cases/test_room_recovery.py`

- [ ] **Step 1: Write failing save/load, room-recovery, and idempotence tests**

```python
def test_combat_state_round_trips_through_save_file():
    ...


def test_event_room_state_round_trips_at_stable_input_point():
    ...


def test_shop_state_restore_does_not_repeat_committed_purchase():
    ...


def test_rest_site_restore_does_not_repeat_heal_or_upgrade():
    ...


def test_map_state_restore_allows_entering_next_room_once():
    ...


def test_reward_claim_updates_run_state_once():
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/use_cases/test_save_load.py tests/use_cases/test_room_recovery.py -v`
Expected: FAIL because persistence, non-combat room recovery, and reward claiming do not exist

- [ ] **Step 3: Implement JSON save adapter, room recovery rules, and reward claiming**

```python
def save_run(path: Path, run_state: RunState, room_state: RoomState | None, combat_state: CombatState | None) -> None:
    ...
```

实现时必须覆盖：

- 地图态保存/恢复
- 战斗态保存/恢复
- 事件、商店、休息点、奖励选择这四类稳定输入点恢复
- 每类非战斗房间都要有“已提交动作不重复执行”的测试
- `schema_version` 写入与读取
- 未知 `schema_version` 的兼容检查或迁移入口

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/use_cases/test_save_load.py tests/use_cases/test_room_recovery.py -v`
Expected: PASS for map-state, event/shop/rest/reward room-state, combat-state, idempotence, reward, schema-version, and unknown-version compatibility tests

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/rewards/reward_generator.py src/slay_the_spire/adapters/persistence/save_files.py src/slay_the_spire/use_cases/claim_reward.py src/slay_the_spire/use_cases/save_game.py src/slay_the_spire/use_cases/load_game.py src/slay_the_spire/use_cases/resolve_event_choice.py src/slay_the_spire/use_cases/shop_action.py src/slay_the_spire/use_cases/rest_action.py tests/use_cases/test_save_load.py tests/use_cases/test_room_recovery.py
git commit -m "feat: add room recovery and save load flow"
```

## Task 9: Build Terminal Renderer and Interactive Loop

**Files:**
- Create: `src/slay_the_spire/adapters/terminal/renderer.py`
- Create: `src/slay_the_spire/adapters/terminal/prompts.py`
- Modify: `src/slay_the_spire/app/cli.py`
- Create: `src/slay_the_spire/app/session.py`
- Test: `tests/e2e/test_single_act_smoke.py`

- [ ] **Step 1: Write failing CLI smoke test**

```python
def test_cli_can_start_run_and_render_first_room(capsys):
    exit_code = main(["new", "--seed", "5"])
    assert exit_code == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py::test_cli_can_start_run_and_render_first_room -v`
Expected: FAIL because session loop and renderer are missing

- [ ] **Step 3: Implement terminal renderer and prompt loop**

```python
class TerminalRenderer:
    def render_combat(self, combat_state: CombatState) -> str:
        ...
```

- [ ] **Step 4: Run smoke test**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py::test_cli_can_start_run_and_render_first_room -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/terminal/renderer.py src/slay_the_spire/adapters/terminal/prompts.py src/slay_the_spire/app/cli.py src/slay_the_spire/app/session.py tests/e2e/test_single_act_smoke.py
git commit -m "feat: add terminal renderer and session loop"
```

## Task 10: Fill Milestone-1 Content and End-to-End Validation

**Files:**
- Modify: `content/cards/ironclad_starter.json`
- Modify: `content/enemies/act1_basic.json`
- Modify: `content/enemies/act1_elites.json`
- Modify: `content/events/act1_events.json`
- Modify: `content/relics/starter_relics.json`
- Modify: `tests/e2e/test_single_act_smoke.py`

- [ ] **Step 1: Write the failing Act-1 smoke completion test**

```python
def test_seeded_run_can_finish_single_act_without_rule_errors():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py::test_seeded_run_can_finish_single_act_without_rule_errors -v`
Expected: FAIL because content pack is incomplete

- [ ] **Step 3: Add minimum viable content set**

```json
{
  "id": "strike",
  "cost": 1,
  "effects": [{"type": "deal_damage", "amount": 6, "target": "enemy"}]
}
```

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add content/cards/ironclad_starter.json content/enemies/act1_basic.json content/enemies/act1_elites.json content/events/act1_events.json content/relics/starter_relics.json tests/e2e/test_single_act_smoke.py
git commit -m "feat: add milestone one act content pack"
```

## Task 11: Harden Developer Workflow and Documentation

**Files:**
- Modify: `pyproject.toml`
- Create: `README.md`
- Modify: `tests/e2e/test_single_act_smoke.py`

- [ ] **Step 1: Write failing documentation smoke check**

```python
def test_readme_commands_match_cli_entrypoint():
    assert "uv run python -m slay_the_spire.app.cli" in Path("README.md").read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py::test_readme_commands_match_cli_entrypoint -v`
Expected: FAIL because README is missing

- [ ] **Step 3: Add developer commands and README**

```markdown
uv run pytest -v
uv run python -m slay_the_spire.app.cli new --seed 5
```

- [ ] **Step 4: Run final regression suite**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md tests/e2e/test_single_act_smoke.py
git commit -m "docs: add developer workflow guide"
```

## Exit Criteria

- 单人新 run 可启动
- 单 Act 地图可生成并推进
- 基础战斗、出牌、回合切换可运行
- 奖励、商店/事件/休息点至少有最小实现
- 存档/读档覆盖地图态、房间态、战斗态
- 事件、商店、休息点、奖励选择可在稳定输入点恢复
- 已提交房间动作恢复后不会重复执行
- hooks/effect 顺序有测试保护
- 内容定义可通过注册表校验
- `uv run pytest -v` 全绿

## Suggested Execution Order

1. Task 1-3 先稳定工程骨架与状态模型
2. Task 4-7 完成内容注册、地图推进、战斗规则
3. Task 8-10 完成存档、终端交互与最小可玩内容
4. Task 11 收尾开发体验与文档
