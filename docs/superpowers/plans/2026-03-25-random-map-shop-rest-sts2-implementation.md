# Random Map, Shop, and Rest STS2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有终端版项目中实现更贴近 STS2 Early Access 的随机分支地图、`shop/rest` 正式流程、完整地图查看、药水商店、休息点 `Rest/Smith`、删牌递增价格和 boss 通关终局。

**Architecture:** 这次改动沿用现有 `domain -> use_cases -> session -> terminal adapters` 边界。长期 run 数据统一进 `RunState`，房间内多步交互统一进 `RoomState.payload`，地图生成保持在 `domain.map`，终端层只读取状态并渲染完整地图、商店、休息点和胜利页。

**Tech Stack:** Python 3.12, `uv`, `pytest`, `dataclasses`, `rich`, JSON content registries

---

## File Structure Map

### State and save/load

- Modify: `src/slay_the_spire/domain/models/run_state.py`
- Modify: `src/slay_the_spire/domain/models/act_state.py`
- Modify: `src/slay_the_spire/domain/models/room_state.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/use_cases/save_game.py`
- Modify: `src/slay_the_spire/use_cases/load_game.py`
- Test: `tests/domain/test_state_serialization.py`
- Test: `tests/use_cases/test_save_load.py`

### Content and provider layer

- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `src/slay_the_spire/content/catalog.py`
- Modify: `src/slay_the_spire/content/provider.py`
- Modify: `src/slay_the_spire/ports/content_provider.py`
- Modify: `content/acts/act1_map.json`
- Modify: `content/cards/ironclad_starter.json`
- Create: `content/potions/starter_potions.json`
- Modify: `src/slay_the_spire/data/content/acts/act1_map.json`
- Modify: `src/slay_the_spire/data/content/cards/ironclad_starter.json`
- Create: `src/slay_the_spire/data/content/potions/starter_potions.json`
- Test: `tests/content/test_registry_validation.py`

### Map and room orchestration

- Modify: `src/slay_the_spire/domain/map/map_generator.py`
- Modify: `src/slay_the_spire/use_cases/start_run.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `src/slay_the_spire/use_cases/claim_reward.py`
- Modify: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Test: `tests/domain/test_map_generator.py`
- Test: `tests/use_cases/test_start_run.py`

### Shop and rest flows

- Modify: `src/slay_the_spire/use_cases/shop_action.py`
- Modify: `src/slay_the_spire/use_cases/rest_action.py`
- Modify: `src/slay_the_spire/use_cases/resolve_event_choice.py`
- Test: `tests/use_cases/test_room_recovery.py`
- Create or Modify: `tests/use_cases/test_shop_and_rest_actions.py`

### Terminal UI

- Modify: `src/slay_the_spire/adapters/terminal/renderer.py`
- Modify: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/widgets.py`
- Modify: `src/slay_the_spire/adapters/terminal/prompts.py`
- Test: `tests/adapters/terminal/test_renderer.py`
- Test: `tests/adapters/terminal/test_app.py`
- Test: `tests/e2e/test_single_act_smoke.py`

## Task 1: Expand Serializable Run and Session State

**Files:**
- Modify: `src/slay_the_spire/domain/models/run_state.py`
- Modify: `src/slay_the_spire/domain/models/act_state.py`
- Modify: `src/slay_the_spire/domain/models/room_state.py`
- Modify: `src/slay_the_spire/app/session.py`
- Test: `tests/domain/test_state_serialization.py`

- [ ] **Step 1: Write the failing schema-expansion tests**

```python
def test_run_state_round_trips_gold_deck_relics_potions_and_removal_count():
    state = RunState(
        seed=7,
        character_id="ironclad",
        current_act_id="act1",
        current_hp=60,
        max_hp=80,
        gold=99,
        deck=["strike#1", "bash#2"],
        relics=["burning_blood"],
        potions=["fire_potion"],
        card_removal_count=1,
    )
    assert RunState.from_dict(state.to_dict()).to_dict() == state.to_dict()


def test_act_node_state_round_trips_row_col_room_type():
    ...


def test_room_state_payload_round_trips_shop_inventory_fields():
    ...
```

- [ ] **Step 2: Run targeted tests to verify failure**

Run: `uv run pytest tests/domain/test_state_serialization.py -q`
Expected: FAIL because the new `RunState` / `ActNodeState` / `RoomState` fields do not exist yet.

- [ ] **Step 3: Implement minimal schema changes**

```python
@dataclass(slots=True, kw_only=True)
class ActNodeState:
    node_id: str
    row: int
    col: int
    room_type: str
    next_node_ids: list[str] = field(default_factory=list)


@dataclass(slots=True, kw_only=True)
class RunState:
    seed: int
    character_id: str
    current_act_id: str | None
    current_hp: int
    max_hp: int
    gold: int = 99
    deck: list[str] = field(default_factory=list)
    relics: list[str] = field(default_factory=list)
    potions: list[str] = field(default_factory=list)
    card_removal_count: int = 0
```

Implementation notes:
- Add `row`, `col`, and `room_type` to `ActNodeState`
- Wire those fields through `ActState.to_dict()` / `ActState.from_dict()`
- Keep duplicate-node and dangling-edge validation intact

- [ ] **Step 4: Add session-level run phase placeholder**

```python
@dataclass(slots=True)
class SessionState:
    ...
    run_phase: str = "active"
```

Implementation notes:
- Reserve all three values up front: `active`, `victory`, `game_over`
- Keep normal room routing under `active`
- Route defeat and victory to terminal-only end states
- In `start_session()`, always initialize `run_phase="active"`
- In `load_session()`, derive `run_phase` from loaded state:
  - defeated combat room or defeated player HP => `game_over`
  - resolved boss room with claimed rewards and no further map return => `victory`
  - otherwise => `active`

- [ ] **Step 5: Re-run targeted tests**

Run: `uv run pytest tests/domain/test_state_serialization.py -q`
Expected: PASS for the new round-trip coverage.

- [ ] **Step 6: Commit**

```bash
git add src/slay_the_spire/domain/models/run_state.py src/slay_the_spire/domain/models/act_state.py src/slay_the_spire/domain/models/room_state.py src/slay_the_spire/app/session.py tests/domain/test_state_serialization.py
git commit -m "feat: expand run act and room state for sts2 flow"
```

## Task 2: Upgrade Save/Load Schema and Reject Old Saves

**Files:**
- Modify: `src/slay_the_spire/use_cases/save_game.py`
- Modify: `src/slay_the_spire/use_cases/load_game.py`
- Modify: `src/slay_the_spire/adapters/persistence/save_files.py`
- Test: `tests/use_cases/test_save_load.py`

- [ ] **Step 1: Write failing save/load schema tests**

```python
def test_save_game_persists_new_run_state_fields(tmp_path: Path):
    ...


def test_load_game_rejects_previous_schema_version_with_clear_error(tmp_path: Path):
    with pytest.raises(ValueError, match="unsupported save schema_version"):
        load_game(repository=repository)
```

- [ ] **Step 2: Run targeted tests**

Run: `uv run pytest tests/use_cases/test_save_load.py -q`
Expected: FAIL because save documents do not yet include the expanded run/session semantics.

- [ ] **Step 3: Raise save schema and wire new fields through**

```python
SAVE_SCHEMA_VERSION = 2
```

Implementation notes:
- Persist the expanded `RunState`
- Keep combat-state normalization behavior
- Reject old documents instead of migrating

- [ ] **Step 4: Re-run targeted tests**

Run: `uv run pytest tests/use_cases/test_save_load.py -q`
Expected: PASS, including explicit rejection of old saves.

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/use_cases/save_game.py src/slay_the_spire/use_cases/load_game.py src/slay_the_spire/adapters/persistence/save_files.py tests/use_cases/test_save_load.py
git commit -m "feat: bump save schema for random map sts2 flow"
```

## Task 3: Add Potion Content and STS2-Oriented Act Config

**Files:**
- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `src/slay_the_spire/content/catalog.py`
- Modify: `src/slay_the_spire/content/provider.py`
- Modify: `src/slay_the_spire/ports/content_provider.py`
- Modify: `content/acts/act1_map.json`
- Create: `content/potions/starter_potions.json`
- Modify: `src/slay_the_spire/data/content/acts/act1_map.json`
- Create: `src/slay_the_spire/data/content/potions/starter_potions.json`
- Test: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write failing content-registry tests**

```python
def test_content_catalog_loads_potion_pools():
    provider = StarterContentProvider(content_root)
    assert provider.potions().all()


def test_act_registry_accepts_map_config_instead_of_static_nodes():
    ...
```

- [ ] **Step 2: Run targeted tests**

Run: `uv run pytest tests/content/test_registry_validation.py -q`
Expected: FAIL because potion registries and `map_config` parsing do not exist.

- [ ] **Step 3: Add a potion registry and provider API**

```python
@dataclass(slots=True, frozen=True)
class PotionDef:
    id: str
    name: str
    effect: JsonDict
```

- [ ] **Step 4: Replace static act nodes with `map_config` content**

Implementation notes:
- Keep pool ids on `ActDef`
- Parse the full required `map_config` schema:
  - `floor_count`
  - `starting_columns`
  - `min_branch_choices`
  - `max_branch_choices`
  - `boss_room_type`
  - `room_rules`
- Mirror content changes in both `content/` and `src/slay_the_spire/data/content/`
- Validate required fields explicitly instead of defaulting silently
- Represent the start node explicitly in generated `ActNodeState` as row `0`, with the configured `starting_columns` count

- [ ] **Step 5: Re-run targeted tests**

Run: `uv run pytest tests/content/test_registry_validation.py -q`
Expected: PASS for potion loading and `map_config` validation.

- [ ] **Step 6: Commit**

```bash
git add src/slay_the_spire/content/registries.py src/slay_the_spire/content/catalog.py src/slay_the_spire/content/provider.py src/slay_the_spire/ports/content_provider.py content/acts/act1_map.json content/potions/starter_potions.json src/slay_the_spire/data/content/acts/act1_map.json src/slay_the_spire/data/content/potions/starter_potions.json tests/content/test_registry_validation.py
git commit -m "feat: add potion content and map config support"
```

## Task 4: Generate Deterministic Random Branch Maps

**Files:**
- Modify: `src/slay_the_spire/domain/map/map_generator.py`
- Modify: `src/slay_the_spire/domain/models/act_state.py`
- Test: `tests/domain/test_map_generator.py`

- [ ] **Step 1: Write failing map-generation tests**

```python
def test_generate_act_state_builds_row_col_room_type_graph():
    act_state = generate_act_state("act1", seed=7, registry=provider)
    start = act_state.get_node(act_state.current_node_id)
    assert start.row == 0
    assert start.col == 0
    assert start.room_type == "combat"


def test_generate_act_state_guarantees_shop_and_rest():
    ...


def test_generate_act_state_is_deterministic_for_same_seed():
    ...
```

- [ ] **Step 2: Run targeted tests**

Run: `uv run pytest tests/domain/test_map_generator.py -q`
Expected: FAIL because the generator still expects static `nodes`.

- [ ] **Step 3: Implement two-phase generation**

```python
def generate_act_state(act_id: str, seed: int, registry: ContentProviderPort) -> ActState:
    topology = _build_layered_topology(...)
    typed_nodes = _assign_room_types(topology, ...)
    return ActState(...)
```

Implementation notes:
- Topology first, room types second
- Cap width at 3
- Honor `starting_columns` when generating row `0`
- Guarantee one `shop` and one `rest`
- Mark the final single node with the configured `boss_room_type`
- Add small `ActState` helpers for renderer-facing derivations such as `rows_for_display()` and `current_coord()`

- [ ] **Step 4: Re-run targeted tests**

Run: `uv run pytest tests/domain/test_map_generator.py -q`
Expected: PASS for determinism, reachability, room guarantees, and row/col typing.

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/map/map_generator.py src/slay_the_spire/domain/models/act_state.py tests/domain/test_map_generator.py
git commit -m "feat: generate deterministic random act maps"
```

## Task 5: Start Runs with Long-Term Deck, Gold, Relics, Potions, and Visited Nodes

**Files:**
- Modify: `src/slay_the_spire/use_cases/start_run.py`
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `src/slay_the_spire/app/session.py`
- Test: `tests/use_cases/test_start_run.py`

- [ ] **Step 1: Write failing run-start and room-entry tests**

```python
def test_start_new_run_populates_gold_deck_relics_and_empty_potions():
    ...


def test_enter_room_marks_selected_node_visited_immediately():
    ...


def test_enter_room_supports_shop_and_rest_room_types():
    ...
```

- [ ] **Step 2: Run targeted tests**

Run: `uv run pytest tests/use_cases/test_start_run.py -q`
Expected: FAIL because `RunState` is not being populated from content and room entry only supports combat/event/boss.

- [ ] **Step 3: Populate long-term run data from content**

```python
return RunState(
    ...,
    gold=99,
    deck=[...starter instances...],
    relics=list(character.starter_relic_ids),
    potions=[],
)
```

- [ ] **Step 4: Extend room entry to `shop` and `rest`**

Implementation notes:
- Build deterministic `room_id`
- On successful node entry, append to `visited_node_ids`
- Defer shop inventory generation until room creation, using `seed + room_id + payload kind`
- Refactor room-type lookup to read from `ActState.get_node(node_id).room_type`, not `ActDef.nodes`
- Remove or rewrite helpers in `enter_room.py` that still treat act content nodes as the room-type source of truth

- [ ] **Step 5: Re-run targeted tests**

Run: `uv run pytest tests/use_cases/test_start_run.py -q`
Expected: PASS for new run bootstrapping and `shop/rest` room entry.

- [ ] **Step 6: Commit**

```bash
git add src/slay_the_spire/use_cases/start_run.py src/slay_the_spire/use_cases/enter_room.py src/slay_the_spire/app/session.py tests/use_cases/test_start_run.py
git commit -m "feat: start runs with sts2 long-term state and new room types"
```

## Task 6: Implement Shop Flow with Potions and Removal Pricing

**Files:**
- Modify: `src/slay_the_spire/use_cases/shop_action.py`
- Modify: `src/slay_the_spire/app/session.py`
- Test: `tests/use_cases/test_room_recovery.py`
- Create or Modify: `tests/use_cases/test_shop_and_rest_actions.py`

- [ ] **Step 1: Write failing shop tests**

```python
def test_shop_buy_card_spends_gold_and_adds_deck_instance():
    ...


def test_shop_buy_potion_spends_gold_and_adds_potion():
    ...


def test_shop_remove_card_uses_run_level_price_progression():
    ...


def test_shop_cancel_remove_returns_to_root_without_spending_remove_use():
    ...
```

- [ ] **Step 2: Run targeted tests**

Run: `uv run pytest tests/use_cases/test_shop_and_rest_actions.py -q`
Expected: FAIL because `shop_action` still returns flat reward tags instead of mutating `RunState`.

- [ ] **Step 3: Implement root and remove-card subflows**

```python
def shop_action(*, run_state: RunState, room_state: RoomState, action_id: str, ...):
    if action_id == "remove":
        return updated_room_state
```

Implementation notes:
- Root stage: buy card / relic / potion / remove / leave
- Remove stage: select card / cancel
- Update `RunState.gold`, `RunState.deck`, `RunState.relics`, `RunState.potions`, `RunState.card_removal_count`
- Keep failed actions non-destructive
- Persist submenu truth in `RoomState.stage`, not `MenuState`
- Use `RoomState.stage="waiting_input"` for shop root and `RoomState.stage="select_remove_card"` for removal subflow
- Persist `remove_candidates` in `RoomState.payload` so save/load can resume removal selection reliably

- [ ] **Step 4: Add explicit session/menu routing for shop and rest**

Implementation notes:
- Update `MenuState` modes for `shop_root`, `shop_remove_card`, `rest_root`, and `rest_upgrade_card`
- Update `route_menu_choice()` or the equivalent session dispatcher so shop/rest flows are reachable from the CLI
- Ensure save/load resumes into the correct submenu by deriving `MenuState.mode` from `RoomState.stage`

- [ ] **Step 5: Re-run targeted tests**

Run: `uv run pytest tests/use_cases/test_shop_and_rest_actions.py tests/use_cases/test_room_recovery.py -q`
Expected: PASS for purchase, remove flow, idempotent save/load behavior, and failure cases.

- [ ] **Step 6: Commit**

```bash
git add src/slay_the_spire/use_cases/shop_action.py src/slay_the_spire/app/session.py tests/use_cases/test_shop_and_rest_actions.py tests/use_cases/test_room_recovery.py
git commit -m "feat: implement sts2 shop flow with potions and removal pricing"
```

## Task 7: Implement Rest Site Heal/Smith Flow

**Files:**
- Modify: `src/slay_the_spire/use_cases/rest_action.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `content/cards/ironclad_starter.json`
- Modify: `src/slay_the_spire/data/content/cards/ironclad_starter.json`
- Test: `tests/use_cases/test_shop_and_rest_actions.py`

- [ ] **Step 1: Write failing rest-site tests**

```python
def test_rest_heal_restores_thirty_percent_of_max_hp_and_caps():
    ...


def test_rest_smith_transitions_to_select_upgrade_card():
    ...


def test_rest_select_upgrade_card_rewrites_card_instance_to_upgraded_card():
    ...
```

- [ ] **Step 2: Run targeted tests**

Run: `uv run pytest tests/use_cases/test_shop_and_rest_actions.py -q`
Expected: FAIL because rest flow still treats actions as flat one-shot rewards.

- [ ] **Step 3: Add upgrade paths in starter card content**

```json
{
  "id": "bash",
  "upgrades_to": "bash_plus"
}
```

- [ ] **Step 4: Implement `heal` and `smith`**

Implementation notes:
- `heal` = ceil or floor once and document consistently in tests; use one rule and reuse it everywhere
- `smith` enters `select_upgrade_card`
- Cancel returns to root
- Completed upgrade rewrites the chosen instance id to upgraded card id while preserving instance suffix
- Persist submenu truth in `RoomState.stage`, using `waiting_input` for root and `select_upgrade_card` for the upgrade picker
- Persist `upgrade_options` in `RoomState.payload` so save/load can resume upgrade selection reliably

- [ ] **Step 5: Re-run targeted tests**

Run: `uv run pytest tests/use_cases/test_shop_and_rest_actions.py -q`
Expected: PASS for rest healing, upgrade transition, cancel, and upgrade persistence.

- [ ] **Step 6: Commit**

```bash
git add src/slay_the_spire/use_cases/rest_action.py src/slay_the_spire/app/session.py content/cards/ironclad_starter.json src/slay_the_spire/data/content/cards/ironclad_starter.json tests/use_cases/test_shop_and_rest_actions.py
git commit -m "feat: implement rest heal and smith flow"
```

## Task 8: Finish Reward Routing, Boss Victory, and Session End States

**Files:**
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/use_cases/claim_reward.py`
- Modify: `src/slay_the_spire/use_cases/resolve_event_choice.py`
- Modify: `tests/use_cases/test_room_recovery.py`
- Modify: `tests/e2e/test_single_act_smoke.py`

- [ ] **Step 1: Write failing victory and routing tests**

```python
def test_claiming_boss_reward_sets_session_victory_and_does_not_return_to_map():
    ...


def test_non_boss_reward_claim_returns_to_map_selection():
    ...


def test_player_defeat_sets_session_game_over_and_blocks_further_actions():
    ...


def test_event_and_shop_rooms_remain_idempotent_after_save_load():
    ...
```

- [ ] **Step 2: Run targeted tests**

Run: `uv run pytest tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py -q`
Expected: FAIL because the session loop has no victory phase and treats rewards generically.

- [ ] **Step 3: Implement run completion routing**

```python
if room_state.room_type == "boss" and room_state.is_resolved and not room_state.rewards:
    session = replace(session, run_phase="victory")
```

Implementation notes:
- On boss reward completion, set `run_phase="victory"`
- On defeated combat state or defeated room recovery, set `run_phase="game_over"`
- Prevent further map and room actions once `run_phase != "active"`

- [ ] **Step 4: Re-run targeted tests**

Run: `uv run pytest tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py -q`
Expected: PASS for boss victory handoff and normal reward routing.

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/app/session.py src/slay_the_spire/use_cases/claim_reward.py src/slay_the_spire/use_cases/resolve_event_choice.py tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py
git commit -m "feat: add boss victory routing and reward transitions"
```

## Task 9: Render Full Map, Shop, Rest Site, Victory, and Game Over Screens

**Files:**
- Modify: `src/slay_the_spire/adapters/terminal/renderer.py`
- Modify: `src/slay_the_spire/adapters/terminal/screens/non_combat.py`
- Modify: `src/slay_the_spire/adapters/terminal/widgets.py`
- Modify: `src/slay_the_spire/adapters/terminal/prompts.py`
- Test: `tests/adapters/terminal/test_renderer.py`
- Test: `tests/adapters/terminal/test_app.py`

- [ ] **Step 1: Write failing renderer tests**

```python
def test_non_combat_renderer_shows_full_map_rows_and_current_position():
    ...


def test_shop_renderer_shows_cards_relics_potions_and_remove_service():
    ...


def test_rest_renderer_shows_root_and_upgrade_selection_states():
    ...


def test_victory_renderer_blocks_normal_room_menu():
    ...


def test_game_over_renderer_blocks_normal_room_menu():
    ...
```

- [ ] **Step 2: Run targeted tests**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py tests/adapters/terminal/test_app.py -q`
Expected: FAIL because the non-combat renderer only knows event/reward/default screens.

- [ ] **Step 3: Implement renderer branches and prompt mapping**

Implementation notes:
- Add map summary and full-map widget
- Add shop panels for cards / relics / potions / remove
- Add rest-site root and upgrade selection panels
- Add victory and game-over pages keyed off `SessionState.run_phase`

- [ ] **Step 4: Re-run targeted tests**

Run: `uv run pytest tests/adapters/terminal/test_renderer.py tests/adapters/terminal/test_app.py -q`
Expected: PASS for full map, shop, rest-site, victory, and game-over rendering.

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/terminal/renderer.py src/slay_the_spire/adapters/terminal/screens/non_combat.py src/slay_the_spire/adapters/terminal/widgets.py src/slay_the_spire/adapters/terminal/prompts.py tests/adapters/terminal/test_renderer.py tests/adapters/terminal/test_app.py
git commit -m "feat: render random map shop rest and victory states"
```

## Task 10: Full Regression Pass and Packaging Sync

**Files:**
- Modify: `tests/e2e/test_single_act_smoke.py`
- Verify: `content/**`
- Verify: `src/slay_the_spire/data/content/**`

- [ ] **Step 1: Extend or rewrite the smoke test for the new flow**

```python
def test_single_act_smoke_covers_map_shop_rest_and_boss_victory():
    ...
```

- [ ] **Step 2: Run the e2e smoke test**

Run: `uv run pytest tests/e2e/test_single_act_smoke.py -q`
Expected: PASS through one seeded act with map selection, at least one shop or rest interaction, and boss victory.

- [ ] **Step 3: Run the full suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 4: Verify content directories stayed in sync**

Run: `diff -ru content src/slay_the_spire/data/content`
Expected: no unexpected differences beyond packaging metadata

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/test_single_act_smoke.py content src/slay_the_spire/data/content
git commit -m "test: cover sts2 random map shop and rest flow"
```
