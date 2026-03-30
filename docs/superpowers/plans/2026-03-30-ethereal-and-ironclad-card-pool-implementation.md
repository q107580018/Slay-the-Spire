# Ethereal And Ironclad Card Pool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a generic `Ethereal` card rule and ship the first balanced batch of original Ironclad cards so Act 2 runs have a broader, more original-feeling reward pool.

**Architecture:** Extend `CardDef` with a new `ethereal` boolean, resolve that rule exactly once in `end_turn()`, and add only the minimum reusable mechanics required by the chosen first-wave cards: all-enemy vulnerable for `Thunderclap`, block doubling for `Entrench`, enemy-hit retaliation for `Flame Barrier`, and start-of-turn strength gain for `Demon Form`. Keep content mirrored across both card roots and verify the work with targeted TDD slices before running the full suite.

**Tech Stack:** Python 3.12, JSON content files, `pytest`, `uv`, Rich/Textual presentation layers

---

### Task 1: Add `ethereal` to the card schema

**Files:**
- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing schema tests**

Add two tests in `tests/content/test_registry_validation.py`:

```python
def test_card_registry_parses_ethereal_flag() -> None:
    registry = CardRegistry()

    card = registry.register(
        {
            "id": "ghostly_armor",
            "name": "幽魂护甲",
            "cost": 1,
            "rarity": "uncommon",
            "card_type": "skill",
            "ethereal": True,
            "effects": [{"type": "block", "amount": 10}],
        }
    )

    assert card.ethereal is True
```

```python
def test_card_registry_defaults_ethereal_to_false() -> None:
    registry = CardRegistry()

    card = registry.register({"id": "strike", "name": "Strike", "cost": 1, "effects": []})

    assert card.ethereal is False
```

- [ ] **Step 2: Run the schema tests and verify they fail**

Run: `uv run pytest tests/content/test_registry_validation.py::test_card_registry_parses_ethereal_flag tests/content/test_registry_validation.py::test_card_registry_defaults_ethereal_to_false -q`

Expected: FAIL because `CardDef` has no `ethereal` field yet.

- [ ] **Step 3: Add the field with a safe default**

Update `src/slay_the_spire/content/registries.py`:

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
```

And in `_build()`:

```python
            playable=_require_optional_bool(data.get("playable"), "playable", default=True),
            exhausts=_require_optional_bool(data.get("exhausts"), "exhausts", default=False),
            ethereal=_require_optional_bool(data.get("ethereal"), "ethereal", default=False),
```

- [ ] **Step 4: Re-run the schema tests and verify they pass**

Run: `uv run pytest tests/content/test_registry_validation.py::test_card_registry_parses_ethereal_flag tests/content/test_registry_validation.py::test_card_registry_defaults_ethereal_to_false -q`

Expected: PASS.

- [ ] **Step 5: Commit the schema slice**

```bash
git add src/slay_the_spire/content/registries.py tests/content/test_registry_validation.py
git commit -m "feat: add ethereal card field"
```

### Task 2: Resolve `Ethereal` at player end turn

**Files:**
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
- Modify: `tests/domain/test_combat_flow.py`

- [ ] **Step 1: Write the failing end-turn tests**

Add three tests to `tests/domain/test_combat_flow.py`:

```python
def test_end_turn_exhausts_ethereal_cards_left_in_hand() -> None:
    registry = _enemy_registry()
    registry.cards().register(
        {
            "id": "ghostly_armor",
            "name": "幽魂护甲",
            "cost": 1,
            "card_type": "skill",
            "ethereal": True,
            "effects": [{"type": "block", "amount": 10}],
        }
    )
    state = _combat_state()
    state.hand = ["ghostly_armor#1", "strike#1"]

    end_turn(state, registry)

    assert "ghostly_armor#1" in state.exhaust_pile
    assert "ghostly_armor#1" not in state.discard_pile
    assert "strike#1" in state.discard_pile
```

```python
def test_end_turn_keeps_non_ethereal_discard_behavior() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.hand = ["strike#1", "defend#1"]

    end_turn(state, registry)

    assert state.exhaust_pile == []
    assert "strike#1" in state.discard_pile
    assert "defend#1" in state.discard_pile
```

```python
def test_end_turn_burn_damage_happens_before_ethereal_exhaust() -> None:
    registry = _enemy_registry()
    registry.cards().register(
        {
            "id": "ghostly_armor",
            "name": "幽魂护甲",
            "cost": 1,
            "card_type": "skill",
            "ethereal": True,
            "effects": [{"type": "block", "amount": 10}],
        }
    )
    state = _combat_state()
    state.player.hp = 20
    state.hand = ["burn#1", "ghostly_armor#1"]

    resolved = end_turn(state, registry)

    assert [effect["type"] for effect in resolved][:1] == ["damage"]
    assert "burn#1" in state.discard_pile
    assert "ghostly_armor#1" in state.exhaust_pile
```

- [ ] **Step 2: Run the end-turn tests and verify they fail**

Run: `uv run pytest tests/domain/test_combat_flow.py::test_end_turn_exhausts_ethereal_cards_left_in_hand tests/domain/test_combat_flow.py::test_end_turn_keeps_non_ethereal_discard_behavior tests/domain/test_combat_flow.py::test_end_turn_burn_damage_happens_before_ethereal_exhaust -q`

Expected: FAIL because `end_turn()` discards the whole hand today.

- [ ] **Step 3: Implement a single hand-drain helper**

In `src/slay_the_spire/domain/combat/turn_flow.py`, add:

```python
def _move_end_turn_hand_cards(state: CombatState, registry: ContentProviderPort) -> None:
    for card_instance_id in tuple(state.hand):
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        if card_def.ethereal:
            state.exhaust_pile.append(card_instance_id)
        else:
            state.discard_pile.append(card_instance_id)
    state.hand.clear()
```

Then replace:

```python
    state.discard_pile.extend(state.hand)
    state.hand.clear()
```

with:

```python
    _move_end_turn_hand_cards(state, registry)
```

- [ ] **Step 4: Re-run the end-turn tests and verify they pass**

Run: `uv run pytest tests/domain/test_combat_flow.py::test_end_turn_exhausts_ethereal_cards_left_in_hand tests/domain/test_combat_flow.py::test_end_turn_keeps_non_ethereal_discard_behavior tests/domain/test_combat_flow.py::test_end_turn_burn_damage_happens_before_ethereal_exhaust -q`

Expected: PASS.

- [ ] **Step 5: Commit the end-turn slice**

```bash
git add src/slay_the_spire/domain/combat/turn_flow.py tests/domain/test_combat_flow.py
git commit -m "feat: exhaust ethereal cards at end of turn"
```

### Task 3: Add the reusable first-wave combat mechanics

**Files:**
- Modify: `src/slay_the_spire/domain/effects/effect_types.py`
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Modify: `src/slay_the_spire/use_cases/play_card.py`
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
- Modify: `tests/domain/test_effect_resolver.py`
- Modify: `tests/use_cases/test_play_card.py`
- Modify: `tests/domain/test_combat_flow.py`

- [ ] **Step 1: Write the failing tests for the four new reusable behaviors**

Add one test per mechanic:

```python
def test_double_block_effect_doubles_current_block() -> None:
    state = _combat_state()
    state.player.block = 7
    state.effect_queue = [
        {
            "type": "double_block",
            "source_instance_id": state.player.instance_id,
            "target_instance_id": state.player.instance_id,
        }
    ]

    resolved = resolve_effect_queue(state)

    assert resolved[0]["type"] == "double_block"
    assert resolved[0]["result"] == {"previous_block": 7, "doubled_block": 14}
    assert state.player.block == 14
```

```python
def test_play_card_thunderclap_applies_vulnerable_to_all_enemies() -> None:
    state = _combat_state(hand=["thunderclap#1"])
    provider = _provider_with_card(
        card_id="thunderclap",
        effects=[
            {"type": "damage_all_enemies", "amount": 4},
            {"type": "vulnerable_all_enemies", "stacks": 1},
        ],
    )

    play_card(state, "thunderclap#1", None, provider)

    assert all(any(status.status_id == "vulnerable" and status.stacks == 1 for status in enemy.statuses) for enemy in state.enemies)
```

```python
def test_enemy_attack_triggers_flame_barrier_counter_damage() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.active_powers = [{"power_id": "flame_barrier", "amount": 4}]

    resolved = end_turn(state, registry)

    assert any(effect.get("power_id") == "flame_barrier" and effect.get("type") == "damage" for effect in resolved)
```

```python
def test_start_turn_applies_demon_form_strength_gain() -> None:
    state = _combat_state()
    state.active_powers = [{"power_id": "demon_form", "amount": 2}]

    start_turn(state)

    assert any(status.status_id == "strength" and status.stacks == 2 for status in state.player.statuses)
```

- [ ] **Step 2: Run the mechanic tests and verify they fail**

Run:

```bash
uv run pytest \
  tests/domain/test_effect_resolver.py::test_double_block_effect_doubles_current_block \
  tests/use_cases/test_play_card.py::test_play_card_thunderclap_applies_vulnerable_to_all_enemies \
  tests/domain/test_combat_flow.py::test_enemy_attack_triggers_flame_barrier_counter_damage \
  tests/domain/test_combat_flow.py::test_start_turn_applies_demon_form_strength_gain -q
```

Expected: FAIL because none of those mechanics exist yet.

- [ ] **Step 3: Add the minimum shared implementation**

In `src/slay_the_spire/domain/effects/effect_types.py`, add:

```python
EFFECT_VULNERABLE_ALL_ENEMIES = "vulnerable_all_enemies"
EFFECT_DOUBLE_BLOCK = "double_block"
```

In `src/slay_the_spire/use_cases/play_card.py`, expand `_materialize_card_effects()`:

```python
        if effect_type == EFFECT_VULNERABLE_ALL_ENEMIES:
            stacks = int(effect.get("stacks", 0))
            for enemy in combat_state.enemies:
                effects.append(
                    {
                        "type": EFFECT_VULNERABLE,
                        "stacks": stacks,
                        "source_instance_id": source_instance_id,
                        "target_instance_id": enemy.instance_id,
                    }
                )
            continue
```

In `src/slay_the_spire/domain/effects/effect_resolver.py`, add:

```python
    if effect_type == EFFECT_DOUBLE_BLOCK:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        previous_block = max(target.block, 0)
        target.block = previous_block * 2
        return _with_result(effect, previous_block=previous_block, doubled_block=target.block)
```

In `src/slay_the_spire/domain/combat/turn_flow.py`, add start-turn support:

```python
def _apply_start_turn_powers(state: CombatState) -> None:
    for power in state.active_powers:
        if power.get("power_id") != "demon_form":
            continue
        amount = power.get("amount")
        if isinstance(amount, int) and amount > 0:
            state.player.statuses.append(StatusState(status_id="strength", stacks=amount))
```

Call it near the top of `start_turn()` before drawing.

Also add flame-barrier retaliation in the damage-resolution path by enqueuing a reflected damage effect when:

- the current effect is enemy `damage`
- the target is the player
- `state.active_powers` contains `{"power_id": "flame_barrier", "amount": N}`

Use:

```python
state.effect_queue.insert(
    0,
    damage_effect(
        source_instance_id=target.instance_id,
        target_instance_id=source.instance_id,
        amount=flame_barrier_amount,
    ),
)
```

Finally clear the temporary power at the start of the player turn:

```python
    _clear_temporary_power(state, "flame_barrier")
```

inside `start_turn()`.

- [ ] **Step 4: Re-run the mechanic tests and verify they pass**

Run:

```bash
uv run pytest \
  tests/domain/test_effect_resolver.py::test_double_block_effect_doubles_current_block \
  tests/use_cases/test_play_card.py::test_play_card_thunderclap_applies_vulnerable_to_all_enemies \
  tests/domain/test_combat_flow.py::test_enemy_attack_triggers_flame_barrier_counter_damage \
  tests/domain/test_combat_flow.py::test_start_turn_applies_demon_form_strength_gain -q
```

Expected: PASS.

- [ ] **Step 5: Commit the mechanic slice**

```bash
git add src/slay_the_spire/domain/effects/effect_types.py src/slay_the_spire/domain/effects/effect_resolver.py src/slay_the_spire/use_cases/play_card.py src/slay_the_spire/domain/combat/turn_flow.py tests/domain/test_effect_resolver.py tests/use_cases/test_play_card.py tests/domain/test_combat_flow.py
git commit -m "feat: add first-wave ironclad combat mechanics"
```

### Task 4: Add the first-wave Ironclad cards to both content roots

**Files:**
- Modify: `content/cards/ironclad_starter.json`
- Modify: `src/slay_the_spire/data/content/cards/ironclad_starter.json`
- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/use_cases/test_apply_reward.py`

- [ ] **Step 1: Write the failing provider and reward-pool tests**

Extend `tests/content/test_registry_validation.py`:

```python
    assert provider.cards().get("clothesline").name == "晾衣绳"
    assert provider.cards().get("thunderclap").name == "震地"
    assert provider.cards().get("uppercut").name == "升龙拳"
    assert provider.cards().get("flame_barrier").name == "火焰屏障"
    assert provider.cards().get("ghostly_armor").name == "幽魂护甲"
    assert provider.cards().get("ghostly_armor").ethereal is True
    assert provider.cards().get("disarm").name == "缴械"
    assert provider.cards().get("entrench").name == "壁垒"
    assert provider.cards().get("demon_form").name == "恶魔形态"
```

Extend `tests/use_cases/test_apply_reward.py`:

```python
    assert "clothesline" in seen_cards
    assert "thunderclap" in seen_cards
    assert "uppercut" in seen_cards
    assert "flame_barrier" in seen_cards
    assert "ghostly_armor" in seen_cards
    assert "disarm" in seen_cards
    assert "entrench" in seen_cards
    assert "demon_form" in seen_cards
```

- [ ] **Step 2: Run the content and reward tests and verify they fail**

Run:

```bash
uv run pytest \
  tests/content/test_registry_validation.py::test_provider_exposes_registry_accessors \
  tests/use_cases/test_apply_reward.py::test_generate_combat_rewards_samples_from_full_ironclad_reward_pool_in_act1 -q
```

Expected: FAIL because the cards are not in the content yet.

- [ ] **Step 3: Add the exact card records in both JSON files**

Use these effect shapes:

```json
{"id": "clothesline", "effects": [{"type": "damage", "amount": 12}, {"type": "weak", "stacks": 2}]}
{"id": "thunderclap", "effects": [{"type": "damage_all_enemies", "amount": 4}, {"type": "vulnerable_all_enemies", "stacks": 1}]}
{"id": "uppercut", "effects": [{"type": "damage", "amount": 13}, {"type": "weak", "stacks": 1}, {"type": "vulnerable", "stacks": 1}]}
{"id": "flame_barrier", "effects": [{"type": "block", "amount": 12}, {"type": "add_power", "power_id": "flame_barrier", "amount": 4}]}
{"id": "ghostly_armor", "ethereal": true, "effects": [{"type": "block", "amount": 10}]}
{"id": "disarm", "effects": [{"type": "strength", "amount": -2}]}
{"id": "entrench", "effects": [{"type": "double_block"}]}
{"id": "demon_form", "effects": [{"type": "add_power", "power_id": "demon_form", "amount": 2}]}
```

Mirror every base card and upgraded card into:

- `content/cards/ironclad_starter.json`
- `src/slay_the_spire/data/content/cards/ironclad_starter.json`

Use `combat_reward` and `shop` tags on these eight new reward cards.

- [ ] **Step 4: Re-run the content and reward tests and verify they pass**

Run:

```bash
uv run pytest \
  tests/content/test_registry_validation.py::test_provider_exposes_registry_accessors \
  tests/use_cases/test_apply_reward.py::test_generate_combat_rewards_samples_from_full_ironclad_reward_pool_in_act1 -q
```

Expected: PASS.

- [ ] **Step 5: Commit the content slice**

```bash
git add content/cards/ironclad_starter.json src/slay_the_spire/data/content/cards/ironclad_starter.json tests/content/test_registry_validation.py tests/use_cases/test_apply_reward.py
git commit -m "feat: add first-wave ironclad card content"
```

### Task 5: Surface the new effects in inspect and summaries

**Files:**
- Modify: `src/slay_the_spire/adapters/presentation/widgets.py`
- Modify: `src/slay_the_spire/adapters/rich_ui/inspect.py`
- Modify: `tests/adapters/rich_ui/test_inspect.py`

- [ ] **Step 1: Write the failing rendering tests**

Add tests that the card detail and summary layers mention the new rule/mechanics:

```python
def test_render_card_detail_panel_shows_ethereal_keyword() -> None:
    registry = StarterContentProvider(_content_root())

    output = _export(render_card_detail_panel("ghostly_armor#1", registry))

    assert "回合结束时若仍在手牌中，则消耗" in output
```

```python
def test_format_card_detail_lines_show_demon_form_power_text() -> None:
    registry = StarterContentProvider(_content_root())

    lines = format_card_detail_lines("demon_form#1", registry)

    assert "每回合开始时获得 2 层力量" in "\n".join(line.plain for line in lines)
```

- [ ] **Step 2: Run the rendering tests and verify they fail**

Run: `uv run pytest tests/adapters/rich_ui/test_inspect.py::test_render_card_detail_panel_shows_ethereal_keyword tests/adapters/rich_ui/test_inspect.py::test_format_card_detail_lines_show_demon_form_power_text -q`

Expected: FAIL because inspect text does not describe the new rule/powers yet.

- [ ] **Step 3: Update summary labels and inspect detail lines**

In `src/slay_the_spire/adapters/presentation/widgets.py`, extend labels:

```python
_POWER_LABELS.update({
    "flame_barrier": "火焰屏障",
    "demon_form": "恶魔形态",
})
```

And extend `summarize_effect()`:

```python
    if effect_type == "double_block":
        return "格挡翻倍"
    if effect_type == "vulnerable_all_enemies":
        return f"对所有敌人施加 {int(effect.get('stacks', 0))} 易伤"
```

For `add_power`:

```python
        if power_id == "flame_barrier":
            return f"本回合内每次被敌人攻击时反弹 {amount} 伤害"
        if power_id == "demon_form":
            return f"每回合开始时获得 {amount} 层力量"
```

In `src/slay_the_spire/adapters/rich_ui/inspect.py`, append:

```python
    if card_def.ethereal:
        lines.append(Text.assemble(("关键词 ", "summary.label"), "Ethereal（回合结束时若仍在手牌中，则消耗）"))
```

- [ ] **Step 4: Re-run the rendering tests and verify they pass**

Run: `uv run pytest tests/adapters/rich_ui/test_inspect.py::test_render_card_detail_panel_shows_ethereal_keyword tests/adapters/rich_ui/test_inspect.py::test_format_card_detail_lines_show_demon_form_power_text -q`

Expected: PASS.

- [ ] **Step 5: Commit the rendering slice**

```bash
git add src/slay_the_spire/adapters/presentation/widgets.py src/slay_the_spire/adapters/rich_ui/inspect.py tests/adapters/rich_ui/test_inspect.py
git commit -m "feat: show ethereal and new power text"
```

### Task 6: Verify parity, update README, and run final regression

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Modify: `README.md`

- [ ] **Step 1: Add a failing content-parity test**

Add:

```python
def test_ironclad_card_file_stays_in_sync_between_content_roots() -> None:
    root, packaged = _content_roots()
    assert (root / "cards" / "ironclad_starter.json").read_text(encoding="utf-8") == (
        packaged / "cards" / "ironclad_starter.json"
    ).read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the parity test and verify it passes after mirroring**

Run: `uv run pytest tests/content/test_registry_validation.py::test_ironclad_card_file_stays_in_sync_between_content_roots -q`

Expected: PASS.

- [ ] **Step 3: Update README**

Add one short section describing:

- Ironclad now has an expanded first-wave original card pool
- `Ghostly Armor` uses the generic `Ethereal` rule
- The packaged content file is kept in sync with the editable root content file

- [ ] **Step 4: Run the focused regression suite**

Run:

```bash
uv run pytest \
  tests/content/test_registry_validation.py \
  tests/domain/test_effect_resolver.py \
  tests/domain/test_combat_flow.py \
  tests/use_cases/test_play_card.py \
  tests/use_cases/test_apply_reward.py \
  tests/adapters/rich_ui/test_inspect.py -q
```

Expected: PASS.

- [ ] **Step 5: Run the full suite and create the finishing commit**

Run: `uv run pytest`

Expected: PASS.

Then:

```bash
git add README.md tests/content/test_registry_validation.py
git commit -m "feat: add ethereal rule and ironclad card expansion"
```

- [ ] **Step 6: Record the intentionally deferred cards in the final handoff**

Note that `heavy_blade` and `power_through` remain out of scope because they still need additional generic mechanics beyond this pass.
