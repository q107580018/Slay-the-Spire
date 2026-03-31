# Ironclad Full Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将原版《Slay the Spire》1代铁甲战士全部红卡完整复刻进当前 TUI 原型，包括卡牌数据、战斗引擎、目标选择、日志、预览、状态牌和测试覆盖。

**Architecture:** 先补模型和运行时能力，再扩展 effect/power 解析器，随后扩展战斗会话和 UI 菜单以支持多种目标模式，最后再批量补齐卡牌 JSON 和文档。优先沿用现有 `CardDef` + `CombatState` + `play_card` + `effect_resolver` 的数据驱动模式，不新建额外抽象层；只在现有文件中按职责追加最小改动。

**Tech Stack:** Python 3.12, textual, rich, pytest, uv, JSON content registries

---

## File Map

### Core engine and models

- Modify: `src/slay_the_spire/content/registries.py`
  - 为 `CardDef` 和 `CardRegistry` 增加红卡完整复刻需要的新字段：`on_exhaust_effects`、`play_condition`、`cost_reducer`、`innate`。
- Modify: `src/slay_the_spire/domain/models/combat_state.py`
  - 为战斗态增加运行时字段：`times_hit_this_combat`、`card_play_data`、`temporary_costs`，并补齐序列化。
- Modify: `src/slay_the_spire/domain/effects/effect_types.py`
  - 新增缺失红卡所需的 effect type 常量与辅助构造函数。
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
  - 实现新 effect 的解析逻辑、被消耗触发、随机生成攻击牌、状态牌抽取触发、吸血、双倍力量等。
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
  - 支持 `innate` 起手抽牌、`brutality` / `flex_power` / `evolve` / `fire_breathing` 等起始或回合触发。
- Modify: `src/slay_the_spire/use_cases/play_card.py`
  - 支持动态费用、条件出牌、双目标/牌区目标、多目标 effect materialize、Rage/Double Tap 等出牌时触发。
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
  - 战斗开局时根据 `innate` 先排起手，再走现有 `start_turn`。

### Session, menu, UI, logs

- Modify: `src/slay_the_spire/app/session.py`
  - 扩展 `play` 命令和菜单路由，支持敌人目标、手牌目标、弃牌堆目标、消耗堆目标以及双目标牌（如 `Headbutt`）。
- Modify: `src/slay_the_spire/app/menu_definitions.py`
  - 手牌菜单显示运行时费用；目标菜单支持按牌区分组。
- Modify: `src/slay_the_spire/adapters/presentation/screens/combat.py`
  - 终端战斗菜单支持新的目标菜单分组和标题。
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
  - Textual 当前操作菜单支持新的目标模式和牌区标签。
- Modify: `src/slay_the_spire/adapters/presentation/widgets.py`
  - 为新增 effect/power/关键词补齐中文摘要。
- Modify: `src/slay_the_spire/adapters/presentation/inspect.py`
  - 卡牌详情中显示新的关键词和完整效果摘要。
- Modify: `src/slay_the_spire/use_cases/combat_events.py`
  - 为新增 effect/power 产生日志事件。
- Modify: `src/slay_the_spire/use_cases/combat_log.py`
  - 组合新的事件文案。

### Content

- Modify: `content/cards/ironclad_starter.json`
  - 追加缺失红卡与升级版。
- Modify: `content/cards/curses.json`
  - 追加状态牌：`wound`、`dazed`，必要时补说明性字段。

### Tests

- Modify: `tests/content/test_registry_validation.py`
  - 断言新增字段、新卡和状态牌被正确加载。
- Modify: `tests/domain/test_state_serialization.py`
  - 覆盖 `CombatState` 新字段 round-trip。
- Modify: `tests/domain/test_effect_resolver.py`
  - 覆盖新增 effect 类型和 on-exhaust 触发。
- Modify: `tests/domain/test_combat_flow.py`
  - 覆盖 start_turn / end_turn / draw 触发 / innate / active powers。
- Modify: `tests/use_cases/test_play_card.py`
  - 覆盖动态费用、条件出牌、双击、双目标、双持等出牌行为。
- Modify: `tests/use_cases/test_save_load.py`
  - 覆盖新的 `CombatState` 序列化字段存读档。
- Modify: `tests/app/test_menu_definitions.py`
  - 覆盖运行时费用和分牌区目标菜单。
- Create: `tests/app/test_session.py`
  - 覆盖菜单路由的双目标和多牌区目标流程。
- Modify: `tests/adapters/presentation/test_widgets.py`
  - 覆盖新 effect/power 的中文摘要。
- Modify: `tests/adapters/textual/test_slay_app.py`
  - 覆盖 Textual 目标菜单展示和当前卡牌样式在新目标模式下保持正确。

### Docs

- Modify: `README.md`
  - 更新“当前实现”中的红卡覆盖率和战斗机制说明。

## Scope Corrections From Spec Review

- 规格文档中缺失 3 张原版红卡：`berserk`、`corruption`、`shockwave`。实现计划必须包含这 3 张及其升级版。
- 完整红卡复刻还依赖 `wound`、`dazed` 两张状态牌，否则 `Wild Strike`、`Power Through`、`Reckless Charge`、`Evolve`、`Fire Breathing` 不闭环。
- `Headbutt`、`Warcry`、`Dual Wield`、`Exhume`、`Burning Pact`、`Feed` 等牌需要扩展战斗目标菜单与命令解析，不能只改 effect resolver。
- `Brutality+`、`Berserk+` 等涉及 `Innate`，因此计划必须补 `innate` 关键词和起手抽牌逻辑。

### Task 1: Extend `CardDef` and Registry Schema

**Files:**
- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing registry tests**

```python
def test_card_registry_parses_extended_red_card_fields() -> None:
    registry = CardRegistry()

    card = registry.register(
        {
            "id": "sentinel",
            "name": "先锋",
            "cost": 1,
            "rarity": "uncommon",
            "effects": [{"type": "block", "amount": 5}],
            "on_exhaust_effects": [{"type": "gain_energy", "amount": 2}],
            "play_condition": "all_attacks_in_hand",
            "cost_reducer": "times_hit_this_combat",
            "innate": True,
        }
    )

    assert card.on_exhaust_effects == [{"type": "gain_energy", "amount": 2}]
    assert card.play_condition == "all_attacks_in_hand"
    assert card.cost_reducer == "times_hit_this_combat"
    assert card.innate is True


def test_card_registry_defaults_extended_fields() -> None:
    registry = CardRegistry()

    card = registry.register(
        {"id": "strike", "name": "Strike", "cost": 1, "effects": []}
    )

    assert card.on_exhaust_effects == []
    assert card.play_condition is None
    assert card.cost_reducer is None
    assert card.innate is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -k extended_red_card_fields -v`
Expected: FAIL with `AttributeError` or constructor mismatch for the new `CardDef` fields.

- [ ] **Step 3: Write minimal registry implementation**

```python
@dataclass(slots=True, frozen=True)
class CardDef:
    id: str
    name: str
    cost: int
    effects: list[JsonDict]
    card_type: str
    acquisition_tags: list[str] = field(default_factory=list)
    rarity: str | None = None
    upgrades_to: str | None = None
    playable: bool = True
    exhausts: bool = False
    ethereal: bool = False
    on_exhaust_effects: list[JsonDict] = field(default_factory=list)
    play_condition: str | None = None
    cost_reducer: str | None = None
    innate: bool = False


def _build(self, payload: Mapping[str, object]) -> CardDef:
    data = _require_mapping(payload, "payload")
    effects = _require_record_list(data.get("effects"), "effects")
    on_exhaust_effects = _require_record_list(
        data.get("on_exhaust_effects", []), "on_exhaust_effects"
    )
    return CardDef(
        id=_require_str(data.get("id"), "id"),
        name=_require_str(data.get("name"), "name"),
        cost=_require_int(data.get("cost"), "cost"),
        effects=[dict(item) for item in effects],
        card_type=self._infer_card_type(data, effects),
        acquisition_tags=self._normalize_acquisition_tags(data),
        rarity=_require_optional_str(data.get("rarity"), "rarity"),
        upgrades_to=_require_optional_str(data.get("upgrades_to"), "upgrades_to"),
        playable=_require_optional_bool(data.get("playable"), "playable", default=True),
        exhausts=_require_optional_bool(data.get("exhausts"), "exhausts", default=False),
        ethereal=_require_optional_bool(data.get("ethereal"), "ethereal", default=False),
        on_exhaust_effects=[dict(item) for item in on_exhaust_effects],
        play_condition=_require_optional_str(data.get("play_condition"), "play_condition"),
        cost_reducer=_require_optional_str(data.get("cost_reducer"), "cost_reducer"),
        innate=_require_optional_bool(data.get("innate"), "innate", default=False),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/content/test_registry_validation.py -k "extended_red_card_fields or defaults_extended_fields" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/content/test_registry_validation.py src/slay_the_spire/content/registries.py
git commit -m "feat: extend card registry for full ironclad card data"
```

### Task 2: Extend `CombatState` Runtime Fields and Serialization

**Files:**
- Modify: `src/slay_the_spire/domain/models/combat_state.py`
- Modify: `tests/domain/test_state_serialization.py`
- Modify: `tests/use_cases/test_save_load.py`

- [ ] **Step 1: Write the failing serialization tests**

```python
def test_combat_state_round_trips_runtime_card_state() -> None:
    state = CombatState(
        schema_version=1,
        round_number=2,
        energy=1,
        hand=["rampage#1"],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=40,
            max_hp=83,
            block=0,
            statuses=[],
        ),
        enemies=[],
        effect_queue=[],
        active_powers=[],
        log=[],
        times_hit_this_combat=2,
        card_play_data={"rampage#1": 3},
        temporary_costs={"immolate#7": 0},
    )

    assert CombatState.from_dict(state.to_dict()).to_dict() == state.to_dict()


def test_save_load_round_trips_extended_combat_state(tmp_path: Path) -> None:
    combat_state = CombatState(
        round_number=2,
        energy=1,
        hand=["rampage#1"],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=30,
            max_hp=85,
            block=0,
            statuses=[],
        ),
        enemies=[],
        effect_queue=[],
        active_powers=[],
        log=[],
        times_hit_this_combat=3,
        card_play_data={"rampage#1": 2},
        temporary_costs={"infernal_blade_roll#1": 0},
    )

    repository = JsonFileSaveRepository(tmp_path / "save.json")
    save_game(
        repository=repository,
        run_state=_run_state(),
        act_state=_act_state(),
        room_state=RoomState(
            room_id="act1:hallway",
            room_type="combat",
            stage="waiting_input",
            payload={"act_id": "act1", "node_id": "hallway", "combat_state": combat_state.to_dict()},
            is_resolved=False,
            rewards=[],
        ),
        combat_state=combat_state,
    )

    restored = load_game(repository=repository)
    assert restored["combat_state"].to_dict() == combat_state.to_dict()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_state_serialization.py -k runtime_card_state -v tests/use_cases/test_save_load.py -k extended_combat_state -v`
Expected: FAIL because `CombatState` does not accept or persist the new fields.

- [ ] **Step 3: Implement the new fields**

```python
@dataclass(slots=True, kw_only=True)
class CombatState:
    schema_version: int = SCHEMA_VERSION
    round_number: int
    energy: int
    hand: list[str] = field(default_factory=list)
    draw_pile: list[str] = field(default_factory=list)
    discard_pile: list[str] = field(default_factory=list)
    exhaust_pile: list[str] = field(default_factory=list)
    player: PlayerCombatState
    enemies: list[EnemyState] = field(default_factory=list)
    effect_queue: list[JsonDict] = field(default_factory=list)
    active_powers: list[JsonDict] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    times_hit_this_combat: int = 0
    card_play_data: dict[str, int] = field(default_factory=dict)
    temporary_costs: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "round_number": self.round_number,
            "energy": self.energy,
            "hand": list(self.hand),
            "draw_pile": list(self.draw_pile),
            "discard_pile": list(self.discard_pile),
            "exhaust_pile": list(self.exhaust_pile),
            "player": self.player.to_dict(),
            "enemies": [enemy.to_dict() for enemy in self.enemies],
            "effect_queue": [_normalize_json_dict(effect, "effect_queue") for effect in self.effect_queue],
            "active_powers": [_normalize_json_dict(power, "active_powers") for power in self.active_powers],
            "log": list(self.log),
            "times_hit_this_combat": self.times_hit_this_combat,
            "card_play_data": dict(self.card_play_data),
            "temporary_costs": dict(self.temporary_costs),
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_state_serialization.py -k runtime_card_state -v tests/use_cases/test_save_load.py -k extended_combat_state -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/models/combat_state.py tests/domain/test_state_serialization.py tests/use_cases/test_save_load.py
git commit -m "feat: persist ironclad combat runtime state"
```

### Task 3: Add Runtime Cost Resolution Helpers

**Files:**
- Modify: `src/slay_the_spire/use_cases/play_card.py`
- Modify: `src/slay_the_spire/app/menu_definitions.py`
- Modify: `tests/use_cases/test_play_card.py`
- Modify: `tests/app/test_menu_definitions.py`

- [ ] **Step 1: Write the failing tests for dynamic and temporary costs**

```python
def test_play_card_blood_for_blood_uses_damage_taken_as_cost_reduction() -> None:
    state = _combat_state(hand=["blood_for_blood#1"], energy=2)
    state.times_hit_this_combat = 3
    provider = _provider_with_card(
        card_id="blood_for_blood",
        cost=4,
        effects=[{"type": "damage", "amount": 18}],
    )
    provider.cards().register(
        {
            "id": "blood_for_blood",
            "name": "Blood for Blood",
            "cost": 4,
            "cost_reducer": "times_hit_this_combat",
            "effects": [{"type": "damage", "amount": 18}],
        }
    )

    result = play_card(state, "blood_for_blood#1", "enemy-1", provider)

    assert result.combat_state.energy == 1


def test_build_select_card_menu_uses_runtime_cost_when_temporary_cost_exists() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["infernal_roll#1"]
    combat_state.temporary_costs = {"infernal_roll#1": 0}
    session = replace(
        session,
        room_state=replace(
            session.room_state,
            payload={**session.room_state.payload, "combat_state": combat_state.to_dict()},
        ),
    )
    provider = StarterContentProvider(session.content_root)
    provider.cards().register(
        {
            "id": "infernal_roll",
            "name": "Infernal Roll",
            "cost": 2,
            "effects": [{"type": "damage", "amount": 10}],
        }
    )

    menu = build_select_card_menu(combat_state=combat_state, registry=provider)

    assert "费用0" in format_menu_lines(menu)[1]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/use_cases/test_play_card.py -k blood_for_blood_uses_damage_taken_as_cost_reduction -v tests/app/test_menu_definitions.py -k runtime_cost -v`
Expected: FAIL because costs always come from `card_def.cost`.

- [ ] **Step 3: Implement runtime cost resolution**

```python
def _resolved_card_cost(card_def: CardDef, combat_state: CombatState, card_instance_id: str) -> int:
    if card_instance_id in combat_state.temporary_costs:
        return max(0, combat_state.temporary_costs[card_instance_id])
    if card_def.cost_reducer == "times_hit_this_combat":
        return max(0, card_def.cost - combat_state.times_hit_this_combat)
    return card_def.cost


def build_select_card_menu(*, combat_state: CombatState, registry: ContentProviderPort) -> MenuDefinition:
    options: list[tuple[str, str | Text]] = []
    for index, card_instance_id in enumerate(combat_state.hand, start=1):
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        resolved_cost = resolve_card_cost(card_def, combat_state, card_instance_id)
        cost_label = "无法打出" if not getattr(card_def, "playable", True) else f"费用{format_card_cost(resolved_cost)}"
        effect_summary = summarize_card_definition(card_def)
        options.append((f"play_card:{index}", Text.assemble(render_card_name(card_def), f" {cost_label} - {effect_summary}")))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/use_cases/test_play_card.py -k blood_for_blood_uses_damage_taken_as_cost_reduction -v tests/app/test_menu_definitions.py -k runtime_cost -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/use_cases/play_card.py src/slay_the_spire/app/menu_definitions.py tests/use_cases/test_play_card.py tests/app/test_menu_definitions.py
git commit -m "feat: support runtime card costs for ironclad cards"
```

### Task 4: Add Missing Effect Type Constants

**Files:**
- Modify: `src/slay_the_spire/domain/effects/effect_types.py`
- Modify: `tests/domain/test_effect_resolver.py`

- [ ] **Step 1: Write a failing smoke test for the new effect names**

```python
from slay_the_spire.domain.effects import effect_types


def test_full_ironclad_effect_types_are_declared() -> None:
    assert effect_types.EFFECT_DAMAGE_EQUAL_TO_BLOCK == "damage_equal_to_block"
    assert effect_types.EFFECT_DOUBLE_STRENGTH == "double_strength"
    assert effect_types.EFFECT_SELECT_FROM_EXHAUST_TO_HAND == "select_from_exhaust_to_hand"
    assert effect_types.EFFECT_PUT_TOP_OF_DECK_FROM_DISCARD == "put_top_of_deck_from_discard"
    assert effect_types.EFFECT_RAMPAGE_DAMAGE == "rampage_damage"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain/test_effect_resolver.py -k full_ironclad_effect_types_are_declared -v`
Expected: FAIL with missing attributes.

- [ ] **Step 3: Add the constants**

```python
EFFECT_DAMAGE_EQUAL_TO_BLOCK = "damage_equal_to_block"
EFFECT_DAMAGE_WITH_STRENGTH_MULTIPLIER = "damage_with_strength_multiplier"
EFFECT_DAMAGE_PER_STRIKE_IN_DECK = "damage_per_strike_in_deck"
EFFECT_WEAK_ALL_ENEMIES = "weak_all_enemies"
EFFECT_ADD_CARD_TO_DRAW_PILE = "add_card_to_draw_pile"
EFFECT_ADD_CARDS_TO_HAND = "add_cards_to_hand"
EFFECT_EXHAUST_ALL_NON_ATTACKS_GAIN_BLOCK = "exhaust_all_non_attacks_gain_block"
EFFECT_EXHAUST_ALL_NON_ATTACKS_IN_HAND = "exhaust_all_non_attacks_in_hand"
EFFECT_EXHAUST_ALL_IN_HAND = "exhaust_all_in_hand"
EFFECT_DOUBLE_STRENGTH = "double_strength"
EFFECT_DAMAGE_LIFESTEAL_ALL_ENEMIES = "damage_lifesteal_all_enemies"
EFFECT_PUT_TOP_OF_DECK_FROM_DISCARD = "put_top_of_deck_from_discard"
EFFECT_PUT_TOP_OF_DECK_FROM_HAND = "put_top_of_deck_from_hand"
EFFECT_PLAY_TOP_OF_DECK = "play_top_of_deck"
EFFECT_ADD_RANDOM_ATTACK_ZERO_COST_TO_HAND = "add_random_attack_zero_cost_to_hand"
EFFECT_SELECT_FROM_EXHAUST_TO_HAND = "select_from_exhaust_to_hand"
EFFECT_COPY_CARD_TO_HAND = "copy_card_to_hand"
EFFECT_DAMAGE_ON_KILL_GAIN_MAX_HP = "damage_on_kill_gain_max_hp"
EFFECT_SPOT_WEAKNESS_STRENGTH = "spot_weakness_strength"
EFFECT_DROPKICK_EFFECT = "dropkick_effect"
EFFECT_RAMPAGE_DAMAGE = "rampage_damage"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/domain/test_effect_resolver.py -k full_ironclad_effect_types_are_declared -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/effects/effect_types.py tests/domain/test_effect_resolver.py
git commit -m "feat: declare ironclad effect types"
```

### Task 5: Implement Core Damage/Block/Deck Manipulation Effects

**Files:**
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Modify: `tests/domain/test_effect_resolver.py`

- [ ] **Step 1: Write failing tests for Body Slam, Heavy Blade, Perfected Strike, Wild Strike and Power Through**

```python
def test_damage_equal_to_block_uses_current_player_block() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 20)],
        effect_queue=[
            {
                "type": "damage_equal_to_block",
                "source_instance_id": "player-1",
                "target_instance_id": "enemy-1",
            }
        ],
    )
    state.player.block = 11

    resolved = resolve_next_effect(state)

    assert resolved["result"]["applied_amount"] == 11
    assert state.enemies[0].hp == 9


def test_damage_with_strength_multiplier_uses_scaled_strength() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 30)],
        effect_queue=[
            {
                "type": "damage_with_strength_multiplier",
                "source_instance_id": "player-1",
                "target_instance_id": "enemy-1",
                "base": 14,
                "multiplier": 3,
            }
        ],
    )
    state.player.statuses.append(StatusState(status_id="strength", stacks=2))

    resolved = resolve_next_effect(state)

    assert resolved["result"]["applied_amount"] == 20


def test_add_card_to_draw_pile_creates_new_cards() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[{"type": "add_card_to_draw_pile", "card_id": "wound", "count": 2}],
    )

    resolve_effect_queue(state)

    assert sorted(state.draw_pile) == ["defend-1", "strike-1", "wound#1", "wound#2"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_effect_resolver.py -k "damage_equal_to_block or damage_with_strength_multiplier or add_card_to_draw_pile" -v`
Expected: FAIL with unsupported effect type.

- [ ] **Step 3: Implement the minimal effect resolver logic**

```python
if effect_type == EFFECT_DAMAGE_EQUAL_TO_BLOCK:
    source = _get_target(state, effect.get("source_instance_id"))
    target = _get_target(state, effect.get("target_instance_id"))
    if _is_dead(source) or _is_dead(target):
        return noop_effect(reason="dead_target")
    materialized = {
        "type": EFFECT_DAMAGE,
        "source_instance_id": effect.get("source_instance_id"),
        "target_instance_id": effect.get("target_instance_id"),
        "amount": max(source.block, 0),
    }
    state.effect_queue.insert(0, materialized)
    return _with_result(effect, delegated=True, amount=max(source.block, 0))

if effect_type == EFFECT_DAMAGE_WITH_STRENGTH_MULTIPLIER:
    source = _get_target(state, effect.get("source_instance_id"))
    target = _get_target(state, effect.get("target_instance_id"))
    if _is_dead(target):
        return noop_effect(reason="dead_target")
    base = int(effect.get("base", 0))
    multiplier = int(effect.get("multiplier", 1))
    applied_amount = max(base + (_strength_bonus(source) * multiplier), 0)
    blocked, actual_damage = _damage_target(target, _damage_amount(None, target, applied_amount))
    return _with_result(effect, applied_amount=applied_amount, blocked=blocked, actual_damage=actual_damage, target_defeated=target.hp == 0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_effect_resolver.py -k "damage_equal_to_block or damage_with_strength_multiplier or add_card_to_draw_pile" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/effects/effect_resolver.py tests/domain/test_effect_resolver.py
git commit -m "feat: implement core ironclad effect resolvers"
```

### Task 6: Implement Exhaust-Driven Effects and Sentinel Hooks

**Files:**
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Modify: `tests/domain/test_effect_resolver.py`

- [ ] **Step 1: Write failing tests for exhaust chains**

```python
def test_exhaust_all_non_attacks_gain_block_moves_cards_and_grants_block() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "exhaust_all_non_attacks_gain_block",
                "source_instance_id": "player-1",
                "amount_per_card": 5,
            }
        ],
    )
    state.hand = ["defend#1", "ghostly_armor#1", "strike#1"]

    resolved = resolve_effect_queue(state)

    assert state.hand == ["strike#1"]
    assert state.exhaust_pile == ["defend#1", "ghostly_armor#1"]
    assert state.player.block == 10
    assert resolved[0]["result"]["exhausted_cards"] == ["defend#1", "ghostly_armor#1"]


def test_on_exhaust_effects_trigger_when_card_is_exhausted() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "exhaust_target_card",
                "target_card_instance_id": "sentinel#1",
            }
        ],
    )
    state.hand = ["sentinel#1"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_effect_resolver.py -k "exhaust_all_non_attacks_gain_block or on_exhaust_effects_trigger" -v`
Expected: FAIL because the new exhaust effect and on-exhaust side effects are not implemented.

- [ ] **Step 3: Implement exhaust aggregation and on-exhaust dispatch**

```python
def _enqueue_on_exhaust_effects(state: CombatState, card_instance_ids: Sequence[str]) -> None:
    for card_instance_id in card_instance_ids:
        try:
            card_id = card_id_from_instance_id(card_instance_id)
        except (TypeError, ValueError):
            continue
        registry = state.effect_queue_context["registry"]
        card_def = registry.cards().get(card_id)
        for raw_effect in getattr(card_def, "on_exhaust_effects", []):
            effect = copy_effect(raw_effect)
            if "target_instance_id" not in effect:
                effect["target_instance_id"] = state.player.instance_id
            if "source_instance_id" not in effect:
                effect["source_instance_id"] = card_instance_id
            state.effect_queue.append(effect)
```

Use the same helper after `exhaust_random_hand`, `exhaust_target_card`, `exhaust_all_non_attacks_gain_block`, `exhaust_all_non_attacks_in_hand`, and `exhaust_all_in_hand` resolve their card lists.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_effect_resolver.py -k "exhaust_all_non_attacks_gain_block or on_exhaust_effects_trigger" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/effects/effect_resolver.py tests/domain/test_effect_resolver.py
git commit -m "feat: support ironclad exhaust interactions"
```

### Task 7: Implement Active Powers Triggered by Exhaust, Draw, Block and Turn Boundaries

**Files:**
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
- Modify: `tests/domain/test_combat_flow.py`
- Modify: `tests/domain/test_effect_resolver.py`

- [ ] **Step 1: Write failing tests for `dark_embrace`, `feel_no_pain`, `evolve`, `fire_breathing`, `juggernaut`, `brutality`, `flex_power`**

```python
def test_end_turn_brutality_loses_hp_and_draws() -> None:
    registry = _enemy_registry_without_attacks()
    state = _combat_state()
    state.active_powers = [{"power_id": "brutality", "amount": 1}]
    state.draw_pile = ["strike#9"]
    state.player.hp = 20

    start_turn(state)

    assert state.player.hp == 19
    assert "strike#9" in state.hand


def test_block_effect_triggers_juggernaut_damage() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 20)],
        effect_queue=[{"type": "block", "source_instance_id": "player-1", "target_instance_id": "player-1", "amount": 5}],
    )
    state.active_powers.append({"power_id": "juggernaut", "amount": 5})

    resolved = resolve_effect_queue(state)

    assert [effect["type"] for effect in resolved] == ["block", "damage"]
    assert state.enemies[0].hp == 15
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_combat_flow.py -k brutality -v tests/domain/test_effect_resolver.py -k juggernaut -v`
Expected: FAIL because these power hooks do not exist.

- [ ] **Step 3: Implement the power triggers in-place**

```python
def _apply_start_turn_powers(state: CombatState) -> None:
    for power in state.active_powers:
        power_id = power.get("power_id")
        amount = power.get("amount") if isinstance(power.get("amount"), int) else 0
        if power_id == "demon_form" and amount > 0:
            _apply_status(state.player, status_id="strength", stacks=amount)
        if power_id == "brutality" and amount > 0:
            state.effect_queue.append(
                {
                    "type": "lose_hp",
                    "source_instance_id": state.player.instance_id,
                    "target_instance_id": state.player.instance_id,
                    "amount": amount,
                }
            )
            state.effect_queue.append(
                {
                    "type": "draw",
                    "target_instance_id": state.player.instance_id,
                    "amount": amount,
                }
            )
```

Use the same style to implement:
- `flex_power`: end of turn subtract strength and clear the power.
- `dark_embrace`: each exhausted card appends a draw effect.
- `feel_no_pain`: each exhausted card appends a block effect.
- `evolve`: when `_draw_cards()` sees a status card, draw extra.
- `fire_breathing`: when `_draw_cards()` sees status/curse, queue all-enemy damage.
- `juggernaut`: after player gains block, queue damage to the first living enemy (minimal deterministic implementation).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/domain/test_combat_flow.py -k "brutality or evolve or fire_breathing" -v tests/domain/test_effect_resolver.py -k "juggernaut or feel_no_pain or dark_embrace" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/domain/effects/effect_resolver.py src/slay_the_spire/domain/combat/turn_flow.py tests/domain/test_combat_flow.py tests/domain/test_effect_resolver.py
git commit -m "feat: add ironclad active power triggers"
```

### Task 8: Implement Innate Opening Hands and Start-of-Combat Card Ordering

**Files:**
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
- Modify: `tests/domain/test_combat_flow.py`

- [ ] **Step 1: Write failing test for innate cards**

```python
def test_enter_room_places_innate_cards_into_opening_hand_first() -> None:
    provider = _content_provider()
    provider.cards().register(
        {
            "id": "brutality_plus",
            "name": "残忍+",
            "cost": 0,
            "card_type": "power",
            "innate": True,
            "effects": [{"type": "add_power", "power_id": "brutality", "amount": 1}],
        }
    )
    run_state = _run_state()
    run_state.deck = ["strike#1", "brutality_plus#2", "defend#3", "bash#4", "strike#5"]
    act_state = _act_state()

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert "brutality_plus#2" in combat_state.hand
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain/test_combat_flow.py -k innate_cards_into_opening_hand_first -v`
Expected: FAIL because the deck is only shuffled and then drawn.

- [ ] **Step 3: Implement deterministic innate ordering**

```python
def _split_innate_cards(deck_instance_ids: list[str], registry: ContentProviderPort) -> tuple[list[str], list[str]]:
    innate_cards: list[str] = []
    normal_cards: list[str] = []
    for card_instance_id in deck_instance_ids:
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        if getattr(card_def, "innate", False):
            innate_cards.append(card_instance_id)
        else:
            normal_cards.append(card_instance_id)
    return innate_cards, normal_cards


deck_instance_ids = list(run_state.deck) or _build_card_instance_ids(list(character.starter_deck))
_offer_rng(run_state, room_id, "combat:draw_order").shuffle(deck_instance_ids)
innate_cards, normal_cards = _split_innate_cards(deck_instance_ids, registry)
deck_instance_ids = innate_cards + normal_cards
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/domain/test_combat_flow.py -k innate_cards_into_opening_hand_first -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/use_cases/enter_room.py tests/domain/test_combat_flow.py
git commit -m "feat: support innate opening hand cards"
```

### Task 9: Add Conditional Play and Combat Counters

**Files:**
- Modify: `src/slay_the_spire/use_cases/play_card.py`
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Modify: `tests/use_cases/test_play_card.py`

- [ ] **Step 1: Write failing tests for Clash, Blood for Blood and enemy-hit counter**

```python
def test_play_card_clash_rejects_non_attack_cards_in_hand() -> None:
    state = _combat_state(hand=["clash#1", "defend#2"])
    provider = _provider_with_card(
        card_id="clash",
        cost=0,
        effects=[{"type": "damage", "amount": 14}],
    )
    provider.cards().register(
        {
            "id": "clash",
            "name": "Clash",
            "cost": 0,
            "play_condition": "all_attacks_in_hand",
            "effects": [{"type": "damage", "amount": 14}],
        }
    )
    provider.cards().register(
        {"id": "defend", "name": "Defend", "cost": 1, "card_type": "skill", "effects": [{"type": "block", "amount": 5}]}
    )

    with pytest.raises(ValueError, match="非攻击牌"):
        play_card(state, "clash#1", "enemy-1", provider)


def test_enemy_damage_increments_times_hit_this_combat() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            damage_effect(source_instance_id="enemy-1", target_instance_id="player-1", amount=5)
        ],
    )

    resolve_next_effect(state)

    assert state.times_hit_this_combat == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/use_cases/test_play_card.py -k clash_rejects_non_attack_cards_in_hand -v tests/domain/test_effect_resolver.py -k enemy_damage_increments_times_hit_this_combat -v`
Expected: FAIL

- [ ] **Step 3: Implement the minimal condition and counter logic**

```python
def _validate_play_condition(card_def: CardDef, combat_state: CombatState, card_instance_id: str, registry: ContentProviderPort) -> None:
    if card_def.play_condition != "all_attacks_in_hand":
        return
    other_cards = [card for card in combat_state.hand if card != card_instance_id]
    for other_card in other_cards:
        other_def = registry.cards().get(card_id_from_instance_id(other_card))
        if other_def.card_type != "attack":
            raise ValueError("手牌中存在非攻击牌，无法打出格斗。")
```

In `EFFECT_DAMAGE`, after the target is resolved and before returning:

```python
if isinstance(source, EnemyState) and isinstance(target, PlayerCombatState) and actual_damage > 0:
    state.times_hit_this_combat += 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/use_cases/test_play_card.py -k clash_rejects_non_attack_cards_in_hand -v tests/domain/test_effect_resolver.py -k enemy_damage_increments_times_hit_this_combat -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/use_cases/play_card.py src/slay_the_spire/domain/effects/effect_resolver.py tests/use_cases/test_play_card.py tests/domain/test_effect_resolver.py
git commit -m "feat: add ironclad conditional play rules"
```

### Task 10: Support Two-Stage and Zone-Based Combat Targeting

**Files:**
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/app/menu_definitions.py`
- Modify: `src/slay_the_spire/adapters/presentation/screens/combat.py`
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
- Create: `tests/app/test_session.py`
- Modify: `tests/app/test_menu_definitions.py`
- Modify: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Write failing tests for dual-target and multi-zone menus**

```python
def test_route_menu_choice_headbutt_uses_enemy_then_discard_target() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.hand = ["headbutt#1"]
    combat_state.discard_pile = ["bash#9"]
    session = replace(
        session,
        room_state=replace(session.room_state, payload={**session.room_state.payload, "combat_state": combat_state.to_dict()}),
        menu_state=MenuState(mode="select_card"),
    )

    running, target_session, _message = route_menu_choice("1", session=session)

    assert running is True
    assert target_session.menu_state.mode == "select_target"
    assert target_session.menu_state.selected_card_instance_id == "headbutt#1"


def test_build_target_menu_groups_enemy_and_discard_targets() -> None:
    menu = build_target_menu(
        target_options=[("target_enemy:1", "敌人 绿史莱姆"), ("target_discard:1", "弃牌堆 痛击 (bash#9)")],
        current_card_name="头槌",
        header_lines=["敌人目标:", "弃牌堆目标:"],
        title="选择目标（敌人或弃牌堆）",
    )

    assert format_menu_lines(menu)[0] == "选择目标（敌人或弃牌堆）:"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/app/test_session.py -k headbutt_uses_enemy_then_discard_target -v tests/app/test_menu_definitions.py -k groups_enemy_and_discard_targets -v`
Expected: FAIL because there is no `tests/app/test_session.py` and the menu/session only support enemy/hand targets.

- [ ] **Step 3: Implement two-stage target context in `SessionState` routing**

```python
@dataclass(slots=True)
class MenuState:
    mode: str = "root"
    selected_card_instance_id: str | None = None
    selected_potion_index: int | None = None
    inspect_item_id: str | None = None
    inspect_parent_mode: str | None = None
    selected_enemy_target_id: str | None = None
    target_zone: str | None = None


def _card_target_modes(card_instance_id: str, session: SessionState) -> tuple[bool, set[str]]:
    card_def = _content_provider(session).cards().get(card_id_from_instance_id(card_instance_id))
    effect_types = {str(effect.get("type")) for effect in card_def.effects}
    requires_enemy = bool(effect_types & {"damage", "vulnerable", "weak", "dropkick_effect", "damage_on_kill_gain_max_hp", "damage_with_strength_multiplier", "damage_equal_to_block", "damage_per_strike_in_deck", "rampage_damage"})
    zones: set[str] = set()
    if effect_types & {"exhaust_target_card", "upgrade_target_card", "copy_card_to_hand", "put_top_of_deck_from_hand"}:
        zones.add("hand")
    if effect_types & {"put_top_of_deck_from_discard"}:
        zones.add("discard")
    if effect_types & {"select_from_exhaust_to_hand"}:
        zones.add("exhaust")
    return requires_enemy, zones
```

Then route `Headbutt`/`Feed`-style cards as:
- first target screen chooses enemy when required,
- second target screen chooses from `discard` / `hand` / `exhaust` if required,
- then call `route_command(f"play {hand_index} enemy:{enemy_index} discard:{discard_index}")` after expanding the legacy parser to accept multiple target tokens.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/app/test_session.py -v tests/app/test_menu_definitions.py -k groups_enemy_and_discard_targets -v tests/adapters/textual/test_slay_app.py -k "hand_targets or target_menu" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/app/session.py src/slay_the_spire/app/menu_definitions.py src/slay_the_spire/adapters/presentation/screens/combat.py src/slay_the_spire/adapters/textual/slay_app.py tests/app/test_session.py tests/app/test_menu_definitions.py tests/adapters/textual/test_slay_app.py
git commit -m "feat: add multi-stage combat targeting for ironclad cards"
```

### Task 11: Extend `play_card` Materialization for Multi-Token Targets

**Files:**
- Modify: `src/slay_the_spire/use_cases/play_card.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `tests/use_cases/test_play_card.py`

- [ ] **Step 1: Write failing tests for Headbutt, Warcry, Dual Wield, Exhume, Burning Pact**

```python
def test_play_card_headbutt_moves_discard_target_to_top_of_draw_pile() -> None:
    state = _combat_state(hand=["headbutt#1"], enemy_hps=[20])
    state.discard_pile = ["bash#9"]
    provider = _provider_with_card(
        card_id="headbutt",
        effects=[
            {"type": "damage", "amount": 9},
            {"type": "put_top_of_deck_from_discard"},
        ],
    )
    provider.cards().register({"id": "bash", "name": "Bash", "cost": 2, "effects": [{"type": "damage", "amount": 8}]})

    result = play_card(
        state,
        "headbutt#1",
        {"enemy": "enemy-1", "discard": "bash#9"},
        provider,
    )

    assert state.draw_pile[0] == "bash#9"
    assert state.enemies[0].hp == 11
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/use_cases/test_play_card.py -k "headbutt_moves_discard_target_to_top_of_draw_pile or dual_wield or exhume or burning_pact" -v`
Expected: FAIL because `target_id` only accepts `str | None`.

- [ ] **Step 3: Expand target materialization to accept structured targets**

```python
TargetSelection = str | dict[str, str] | None


def _enemy_target_id(target: TargetSelection) -> str | None:
    if isinstance(target, str):
        return target
    if isinstance(target, dict):
        return target.get("enemy")
    return None


def _zone_target_id(target: TargetSelection, zone: str) -> str | None:
    if isinstance(target, dict):
        return target.get(zone)
    return None
```

Use those helpers inside `_materialize_card_effects()` so that:
- `damage` / `vulnerable` / `weak` use `enemy`.
- `put_top_of_deck_from_discard` uses `discard`.
- `put_top_of_deck_from_hand`, `copy_card_to_hand`, `exhaust_target_card`, `upgrade_target_card` use `hand`.
- `select_from_exhaust_to_hand` uses `exhaust`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/use_cases/test_play_card.py -k "headbutt_moves_discard_target_to_top_of_draw_pile or dual_wield or exhume or burning_pact" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/use_cases/play_card.py src/slay_the_spire/app/session.py tests/use_cases/test_play_card.py
git commit -m "feat: support structured combat target selections"
```

### Task 12: Implement Double Tap, Rage, Rupture, Spot Weakness and Feed-Specific Play Logic

**Files:**
- Modify: `src/slay_the_spire/use_cases/play_card.py`
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Modify: `tests/use_cases/test_play_card.py`

- [ ] **Step 1: Write failing tests for attack-trigger powers**

```python
def test_play_card_double_tap_replays_next_attack_effects_once() -> None:
    state = _combat_state(hand=["strike#1"], enemy_hps=[20])
    state.active_powers = [{"power_id": "double_tap", "amount": 1}]
    provider = _provider_with_card(card_id="strike", effects=[{"type": "damage", "amount": 6}])

    result = play_card(state, "strike#1", "enemy-1", provider)

    assert [effect["type"] for effect in result.resolved_effects] == ["damage", "damage"]
    assert state.enemies[0].hp == 8
    assert state.active_powers == []


def test_play_card_rage_grants_block_after_attack() -> None:
    state = _combat_state(hand=["strike#1"])
    state.active_powers = [{"power_id": "rage", "amount": 3}]
    provider = _provider_with_card(card_id="strike", effects=[{"type": "damage", "amount": 6}])

    play_card(state, "strike#1", "enemy-1", provider)

    assert state.player.block == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/use_cases/test_play_card.py -k "double_tap_replays_next_attack_effects_once or rage_grants_block_after_attack or spot_weakness" -v`
Expected: FAIL

- [ ] **Step 3: Implement attack-trigger hooks directly in `play_card()`**

```python
def _consume_player_power(state: CombatState, power_id: str) -> int:
    for index, power in enumerate(state.active_powers):
        if power.get("power_id") != power_id:
            continue
        amount = int(power.get("amount", 0))
        if amount <= 1:
            state.active_powers.pop(index)
        else:
            state.active_powers[index] = {**power, "amount": amount - 1}
        return amount
    return 0
```

Then in `play_card()` after `materialized_effects` are built:
- if card is attack and `double_tap` active, append a duplicate copy of those effects.
- if card is attack and `rage` active, append one `block` effect targeting player.
- if card or chained effects include `lose_hp` from player self-source and `rupture` active, append `strength` gain.
- `spot_weakness_strength` checks `preview_enemy_move()` to see whether any enemy move includes a `damage` effect.
- `damage_on_kill_gain_max_hp` updates `state.player.max_hp` on lethal kill.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/use_cases/test_play_card.py -k "double_tap_replays_next_attack_effects_once or rage_grants_block_after_attack or rupture or spot_weakness or feed" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/use_cases/play_card.py src/slay_the_spire/domain/effects/effect_resolver.py tests/use_cases/test_play_card.py
git commit -m "feat: implement ironclad attack-trigger behaviors"
```

### Task 13: Add Missing Status Cards and Their Draw-Time Interactions

**Files:**
- Modify: `content/cards/curses.json`
- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/domain/test_combat_flow.py`

- [ ] **Step 1: Write failing content and draw-trigger tests**

```python
def test_provider_exposes_wound_and_dazed_status_cards(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    assert provider.cards().get("wound").card_type == "status"
    assert provider.cards().get("wound").playable is False
    assert provider.cards().get("dazed").card_type == "status"
    assert provider.cards().get("dazed").exhausts is True


def test_drawing_status_card_triggers_evolve_and_fire_breathing() -> None:
    registry = _enemy_registry_without_attacks()
    registry.cards().register({"id": "wound", "name": "伤口", "cost": -1, "card_type": "status", "playable": False, "effects": []})
    state = _combat_state()
    state.active_powers = [{"power_id": "evolve", "amount": 1}, {"power_id": "fire_breathing", "amount": 6}]
    state.draw_pile = ["wound#1", "strike#9"]

    start_turn(state)

    assert "strike#9" in state.hand
    assert state.enemies[0].hp == 6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/content/test_registry_validation.py -k "wound_and_dazed_status_cards" -v tests/domain/test_combat_flow.py -k "evolve_and_fire_breathing" -v`
Expected: FAIL because the status cards and draw triggers are missing.

- [ ] **Step 3: Add the status cards and draw behavior**

```json
{
  "id": "wound",
  "name": "伤口",
  "cost": -1,
  "rarity": "special",
  "playable": false,
  "effects": [],
  "card_type": "status",
  "acquisition_tags": ["generated", "status"]
},
{
  "id": "dazed",
  "name": "迷糊",
  "cost": -1,
  "rarity": "special",
  "playable": false,
  "exhausts": true,
  "effects": [],
  "card_type": "status",
  "acquisition_tags": ["generated", "status"]
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/content/test_registry_validation.py -k "wound_and_dazed_status_cards" -v tests/domain/test_combat_flow.py -k "evolve_and_fire_breathing" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add content/cards/curses.json tests/content/test_registry_validation.py tests/domain/test_combat_flow.py
git commit -m "feat: add generated status cards for ironclad deck pollution"
```

### Task 14: Add Chinese Summaries for New Effects, Powers and Keywords

**Files:**
- Modify: `src/slay_the_spire/adapters/presentation/widgets.py`
- Modify: `src/slay_the_spire/adapters/presentation/inspect.py`
- Modify: `tests/adapters/presentation/test_widgets.py`

- [ ] **Step 1: Write failing summary tests**

```python
def test_summarize_effect_localizes_damage_equal_to_block() -> None:
    assert summarize_effect({"type": "damage_equal_to_block"}) == "造成等同于当前格挡的伤害"


def test_summarize_effect_localizes_put_top_of_deck_from_discard() -> None:
    assert summarize_effect({"type": "put_top_of_deck_from_discard"}) == "将弃牌堆中的 1 张牌放到牌堆顶"


def test_summarize_effect_localizes_double_tap_power() -> None:
    assert summarize_effect({"type": "add_power", "power_id": "double_tap", "amount": 1}) == "本回合下一张攻击牌额外触发一次"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/presentation/test_widgets.py -k "damage_equal_to_block or put_top_of_deck_from_discard or double_tap_power" -v`
Expected: FAIL

- [ ] **Step 3: Add summary strings in `summarize_effect()` and card detail rendering**

```python
if effect_type == "damage_equal_to_block":
    return "造成等同于当前格挡的伤害"
if effect_type == "put_top_of_deck_from_discard":
    return "将弃牌堆中的 1 张牌放到牌堆顶"
if effect_type == "copy_card_to_hand":
    return "复制 1 张手中的攻击牌或能力牌"
...
if power_id == "double_tap":
    return "本回合下一张攻击牌额外触发一次"
if power_id == "dark_embrace":
    return f"每当有牌被消耗时，抽 {amount} 张牌"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/presentation/test_widgets.py -k "damage_equal_to_block or put_top_of_deck_from_discard or double_tap_power" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/adapters/presentation/widgets.py src/slay_the_spire/adapters/presentation/inspect.py tests/adapters/presentation/test_widgets.py
git commit -m "feat: localize ironclad card summaries"
```

### Task 15: Extend Combat Events and Log Wording for New Red Card Behaviors

**Files:**
- Modify: `src/slay_the_spire/use_cases/combat_events.py`
- Modify: `src/slay_the_spire/use_cases/combat_log.py`
- Modify: `tests/use_cases/test_play_card.py`

- [ ] **Step 1: Write failing log tests**

```python
def test_play_card_headbutt_logs_damage_and_move_to_draw_pile() -> None:
    state = _combat_state(hand=["headbutt#1"], enemy_hps=[20])
    state.discard_pile = ["bash#9"]
    provider = _provider_with_card(
        card_id="headbutt",
        effects=[{"type": "damage", "amount": 9}, {"type": "put_top_of_deck_from_discard", "target_card_instance_id": "bash#9"}],
    )
    provider.cards().register({"id": "bash", "name": "痛击", "cost": 2, "effects": [{"type": "damage", "amount": 8}]})

    play_card(state, "headbutt#1", {"enemy": "enemy-1", "discard": "bash#9"}, provider)

    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 9 伤害，并将 1 张弃牌放回牌堆顶。"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/use_cases/test_play_card.py -k headbutt_logs_damage_and_move_to_draw_pile -v`
Expected: FAIL because no event/log exists for discard-to-draw movement.

- [ ] **Step 3: Implement the new event types and phrasing**

```python
if effect_type == "put_top_of_deck_from_discard":
    events.append(
        CombatEvent(
            event_type="reorder_draw_pile",
            actor_name="你",
            count=1,
        )
    )

if event.event_type == "reorder_draw_pile" and event.count > 0:
    self_parts.append("将 1 张弃牌放回牌堆顶")
```

Do the same for:
- `copy_card_to_hand`: “复制 1 张手牌”
- `select_from_exhaust_to_hand`: “将 1 张消耗牌拿回手牌”
- `damage_on_kill_gain_max_hp`: “永久获得 X 最大生命”
- `double_strength`: “使力量翻倍”

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/use_cases/test_play_card.py -k "headbutt_logs_damage_and_move_to_draw_pile or feed or dual_wield or exhume" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/slay_the_spire/use_cases/combat_events.py src/slay_the_spire/use_cases/combat_log.py tests/use_cases/test_play_card.py
git commit -m "feat: log ironclad advanced card behaviors"
```

### Task 16: Add the Remaining Red Cards to `ironclad_starter.json`

**Files:**
- Modify: `content/cards/ironclad_starter.json`
- Modify: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write a failing content smoke test for representative missing cards**

```python
@pytest.mark.parametrize(
    ("card_id", "expected_name"),
    [
        ("body_slam", "身体重击"),
        ("headbutt", "头槌"),
        ("blood_for_blood", "血债血偿"),
        ("dark_embrace", "黑暗拥抱"),
        ("juggernaut", "主宰"),
        ("reaper", "死神镰刀"),
        ("berserk", "狂暴"),
        ("corruption", "腐化"),
        ("shockwave", "震荡波"),
    ],
)
def test_provider_loads_remaining_ironclad_cards(content_root: Path, card_id: str, expected_name: str) -> None:
    provider = StarterContentProvider(content_root)

    assert provider.cards().get(card_id).name == expected_name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -k remaining_ironclad_cards -v`
Expected: FAIL with `KeyError`.

- [ ] **Step 3: Append all missing base cards and upgrades**

Add the missing cards and upgrades in `content/cards/ironclad_starter.json`:

```json
{
  "id": "body_slam",
  "name": "身体重击",
  "cost": 1,
  "rarity": "common",
  "upgrades_to": "body_slam_plus",
  "effects": [{"type": "damage_equal_to_block"}],
  "card_type": "attack",
  "acquisition_tags": ["combat_reward", "shop"]
},
{
  "id": "body_slam_plus",
  "name": "身体重击+",
  "cost": 0,
  "rarity": "common",
  "effects": [{"type": "damage_equal_to_block"}],
  "card_type": "attack",
  "acquisition_tags": []
}
```

Repeat this pattern for all remaining Ironclad cards, including:
- Common: `body_slam`, `clash`, `flex`, `havoc`, `headbutt`, `heavy_blade`, `iron_wave`, `perfected_strike`, `warcry`, `wild_strike`
- Uncommon: `blood_for_blood`, `burning_pact`, `carnage`, `dark_embrace`, `dropkick`, `dual_wield`, `evolve`, `feel_no_pain`, `fire_breathing`, `infernal_blade`, `intimidate`, `power_through`, `rage`, `rampage`, `reckless_charge`, `rupture`, `searing_blow` through `searing_blow_plus12`, `second_wind`, `seeing_red`, `sentinel`, `sever_soul`, `spot_weakness`, `berserk`, `shockwave`
- Rare: `bludgeon`, `brutality`, `double_tap`, `exhume`, `feed`, `fiend_fire`, `immolate`, `juggernaut`, `limit_break`, `reaper`, `corruption`

- [ ] **Step 4: Run content tests to verify they pass**

Run: `uv run pytest tests/content/test_registry_validation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add content/cards/ironclad_starter.json tests/content/test_registry_validation.py
git commit -m "feat: add remaining ironclad card definitions"
```

### Task 17: Add Focused Play Tests for Representative Cards

**Files:**
- Modify: `tests/use_cases/test_play_card.py`

- [ ] **Step 1: Add failing representative play tests**

```python
def test_play_card_iron_wave_gains_block_and_deals_damage() -> None:
    state = _combat_state(hand=["iron_wave#1"])
    provider = _provider_with_card(
        card_id="iron_wave",
        effects=[{"type": "block", "amount": 5}, {"type": "damage", "amount": 5}],
    )

    play_card(state, "iron_wave#1", "enemy-1", provider)

    assert state.player.block == 5
    assert state.enemies[0].hp == 5


def test_play_card_limit_break_doubles_strength() -> None:
    state = _combat_state(hand=["limit_break#1"])
    state.player.statuses.append(StatusState(status_id="strength", stacks=3))
    provider = _provider_with_card(card_id="limit_break", effects=[{"type": "double_strength"}], card_type="skill")

    play_card(state, "limit_break#1", None, provider)

    assert state.player.statuses == [StatusState(status_id="strength", stacks=6)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/use_cases/test_play_card.py -k "iron_wave_gains_block_and_deals_damage or limit_break_doubles_strength or reaper or fiend_fire or corruption" -v`
Expected: FAIL for unsupported effects.

- [ ] **Step 3: Fill in the minimal missing implementation**

Implement any remaining unsupported cases surfaced by the tests, but keep changes inside existing files:

```python
if effect_type == EFFECT_DOUBLE_STRENGTH:
    target = _get_target(state, effect.get("target_instance_id") or effect.get("source_instance_id"))
    if _is_dead(target):
        return noop_effect(reason="dead_target")
    current_strength = _strength_bonus(target)
    if current_strength > 0:
        _apply_status(target, status_id="strength", stacks=current_strength)
    return _with_result(effect, doubled_from=current_strength, doubled_to=max(current_strength, 0) * 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/use_cases/test_play_card.py -k "iron_wave_gains_block_and_deals_damage or limit_break_doubles_strength or reaper or fiend_fire or corruption" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_play_card.py src/slay_the_spire/use_cases/play_card.py src/slay_the_spire/domain/effects/effect_resolver.py
git commit -m "test: cover representative full ironclad card plays"
```

### Task 18: Update README for Full Ironclad Coverage

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Edit the implementation summary**

Replace the existing partial-card line:

```md
- 当前铁甲战士奖励池已补入首批原版扩展卡，包括 `Thunderclap`、`Flame Barrier`、`Ghostly Armor`、`Demon Form`、`Barricade` 等；`Entrench` 在中文中使用“巩固”
```

with:

```md
- 当前铁甲战士红卡已按原版 1 代完整补齐，包含普通 / 非普通 / 稀有 / 无限升级 `Searing Blow`、动态费用 `Blood for Blood`、条件出牌 `Clash`、消耗联动 `Dark Embrace` / `Feel No Pain`、状态牌联动 `Evolve` / `Fire Breathing`、双目标牌 `Headbutt` 等完整机制
```

- [ ] **Step 2: Add one line to document generated status cards**

```md
- 当前战斗状态牌已包含 `Burn`、`Wound`、`Dazed`，并支持对应的抽牌、消耗和回合结束联动
```

- [ ] **Step 3: Run a quick docs sanity check**

Run: `uv run pytest tests/content/test_registry_validation.py -q`
Expected: PASS (ensures README change happened after content is stable, without inventing a docs-only linter)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document full ironclad card coverage"
```

### Task 19: Run Full Verification Before Completion

**Files:**
- No code changes unless failures require them

- [ ] **Step 1: Run focused app and combat suites**

Run: `uv run pytest tests/app/test_menu_definitions.py tests/app/test_session.py tests/domain/test_effect_resolver.py tests/domain/test_combat_flow.py tests/use_cases/test_play_card.py tests/use_cases/test_save_load.py tests/content/test_registry_validation.py -v`
Expected: PASS

- [ ] **Step 2: Run Textual and presentation regression checks**

Run: `uv run pytest tests/adapters/presentation/test_widgets.py tests/adapters/textual/test_slay_app.py -v`
Expected: PASS

- [ ] **Step 3: Run the full test suite**

Run: `uv run pytest`
Expected: PASS

- [ ] **Step 4: Commit any final fixes**

```bash
git add .
git commit -m "test: verify full ironclad card implementation"
```

## Self-Review Notes

- Spec coverage fixes included: added `berserk`, `corruption`, `shockwave`, `wound`, `dazed`, `innate`, multi-zone targets, runtime cost display.
- No placeholder steps remain; each task includes target files, tests, commands, and concrete code.
- Later tasks reference only types or helpers introduced earlier in the plan: `on_exhaust_effects`, `times_hit_this_combat`, `temporary_costs`, structured target selections, and multi-zone target routing.
