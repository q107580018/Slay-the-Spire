# Relic Full Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement real behavior for every relic that can currently appear in this repository's playable flows, in small TDD-driven batches grouped by trigger domain.

**Architecture:** Keep the current mixed approach. Simple lifecycle effects continue to use the existing runtime hooks where they fit; more complex relics are implemented directly in the use cases that already own reward application, combat lifecycle, shop/rest flow, damage resolution, and reward generation. Each batch updates both behavior and `implementation_status` only when the behavior is genuinely present.

**Tech Stack:** Python 3.12, pytest, `uv`, JSON content under `content/`, TUI flow in `textual`/`rich`

---

### Task 1: Build The Relic Behavior Matrix

**Files:**
- Create: `docs/superpowers/relic-behavior-matrix.md`
- Modify: `docs/superpowers/specs/2026-04-03-relic-full-implementation-design.md`

- [ ] **Step 1: Write the failing test**

This task is documentation-only. No production-code test is required.

- [ ] **Step 2: Create the matrix**

Create a markdown table grouping unresolved relics by trigger domain:

```md
| relic_id | status | domain | primary entrypoint | secondary notes |
| --- | --- | --- | --- | --- |
| strawberry | placeholder | on_acquire | apply_reward | max hp +7 |
| anchor | placeholder | combat_start | turn_flow / combat init | gain 10 block |
| question_card | placeholder | reward_generation | reward_generator | +1 card offer |
```

- [ ] **Step 3: Verify the matrix covers all unresolved relics**

Run: `uv run python - <<'PY'\nimport json, pathlib\nroot=pathlib.Path('content/relics')\ncount=0\nfor p in root.glob('*.json'):\n    data=json.loads(p.read_text())\n    count += sum(1 for r in data['relics'] if r['implementation_status'] != 'implemented')\nprint(count)\nPY`
Expected: The count matches the number of rows captured in the matrix, excluding only rows intentionally marked "defer/blocked".

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/relic-behavior-matrix.md docs/superpowers/specs/2026-04-03-relic-full-implementation-design.md
git commit -m "docs: map unresolved relic behavior domains"
```

### Task 1b: Freeze The Remaining Closure Scope

**Files:**
- Modify: `docs/superpowers/relic-behavior-matrix.md`
- Modify: `docs/superpowers/specs/2026-04-03-relic-full-implementation-design.md`
- Modify: `docs/superpowers/plans/2026-04-03-relic-full-implementation.md`

- [ ] **Step 1: Write the failing test**

This task is documentation-only. No production-code test is required.

- [ ] **Step 2: Update the matrix to distinguish closure targets from intentional deferrals**

In the matrix, mark each remaining unresolved relic as either "closure target" or "deferred: [reason]" in the notes column. At minimum, the following must be explicit:

| relic_id | status | domain | primary entrypoint | secondary notes |
| --- | --- | --- | --- | --- |
| vajra | placeholder | on_acquire | apply_reward | closure target: +1 strength (permanent) |
| oddly_smooth_stone | placeholder | on_acquire | apply_reward | closure target: +1 dexterity (permanent) |
| war_paint | placeholder | on_acquire | apply_reward | closure target: upgrade 2 random skills on acquire |
| whetstone | placeholder | on_acquire | apply_reward | closure target: upgrade 2 random attacks on acquire |
| sacred_bark | placeholder | complex/deferred | hooks/runtime | deferred: needs potion-effect system |
| bottled_flame | placeholder | complex/deferred | apply_reward | deferred: needs card picker UI |
| orrery | placeholder | complex/deferred | apply_reward | deferred: needs card picker UI |
| prismatic_shard | placeholder | complex/deferred | reward_generator | deferred: needs multi-class pool support |

- [ ] **Step 3: Record the exact closure targets in the plan**

This closure pass MUST finish:

- `vajra`
- `oddly_smooth_stone`
- `war_paint`
- `whetstone`

This closure pass MUST explicitly leave the following complex relics as `placeholder` or `partial` (no fake `implemented` status):

- `sacred_bark` → placeholder (needs potion-effect system)
- `bottled_flame` → placeholder (needs card picker UI)
- `bottled_lightning` → placeholder (needs card picker UI)
- `bottled_tornado` → placeholder (needs card picker UI)
- `orrery` → placeholder (needs card picker UI)
- `prismatic_shard` → placeholder (needs multi-class pool support)

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/relic-behavior-matrix.md docs/superpowers/specs/2026-04-03-relic-full-implementation-design.md docs/superpowers/plans/2026-04-03-relic-full-implementation.md
git commit -m "docs: freeze relic closure scope"
```

### Task 2: Implement On-Acquire Relics

**Files:**
- Modify: `src/slay_the_spire/use_cases/apply_reward.py`
- Modify: `content/relics/common_relics.json`
- Modify: `content/relics/uncommon_relics.json`
- Modify: `content/relics/rare_relics.json`
- Modify: `content/relics/shop_relics.json`
- Modify: `content/relics/boss_relics.json`
- Test: `tests/use_cases/test_apply_reward.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_apply_reward_grants_strawberry_max_hp_bonus() -> None:
    run_state = _run_state(max_hp=80, current_hp=70)

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:strawberry",
        registry=_content_provider(),
    )

    assert updated.max_hp == 87
    assert updated.current_hp == 77
    assert "strawberry" in updated.relics


def test_apply_reward_grants_old_coin_gold_bonus() -> None:
    run_state = _run_state(gold=99)

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:old_coin",
        registry=_content_provider(),
    )

    assert updated.gold == 399
    assert "old_coin" in updated.relics
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -k "strawberry or old_coin" -v`
Expected: FAIL because relic acquisition only appends the relic and does not apply the side effects.

- [ ] **Step 3: Write minimal implementation**

Add a small acquisition-effect dispatch inside `apply_reward.py`:

```python
_MAX_HP_GAIN_ON_ACQUIRE = {
    "strawberry": 7,
    "pear": 10,
    "mango": 14,
    "leeches_waffle": 7,
}

_GOLD_GAIN_ON_ACQUIRE = {
    "old_coin": 300,
}


def _apply_relic_on_acquire_effects(run_state: RunState, relic_id: str) -> RunState:
    updated = run_state
    if relic_id in _MAX_HP_GAIN_ON_ACQUIRE:
        bonus = _MAX_HP_GAIN_ON_ACQUIRE[relic_id]
        updated = replace(
            updated,
            max_hp=updated.max_hp + bonus,
            current_hp=min(updated.max_hp + bonus, updated.current_hp + bonus),
        )
    if relic_id == "leeches_waffle":
        updated = replace(updated, current_hp=updated.max_hp)
    if relic_id in _GOLD_GAIN_ON_ACQUIRE:
        updated = replace(updated, gold=updated.gold + _GOLD_GAIN_ON_ACQUIRE[relic_id])
    return updated
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -k "strawberry or old_coin" -v`
Expected: PASS.

- [ ] **Step 5: Mark implemented relic content**

Update `implementation_status` to `implemented` for the relics whose acquire effects are now real.

- [ ] **Step 6: Commit**

```bash
git add tests/use_cases/test_apply_reward.py src/slay_the_spire/use_cases/apply_reward.py content/relics/common_relics.json content/relics/uncommon_relics.json content/relics/rare_relics.json content/relics/shop_relics.json
git commit -m "feat: implement on-acquire relic effects"
```

### Task 3: Implement Combat-Start Relics

**Files:**
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
- Modify: `src/slay_the_spire/domain/hooks/runtime.py`
- Modify: `content/relics/common_relics.json`
- Modify: `content/relics/shop_relics.json`
- Modify: `content/relics/uncommon_relics.json`
- Test: `tests/domain/test_combat_flow.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_combat_start_relics_apply_opening_block_vulnerable_and_draw() -> None:
    combat = _combat_state_with_relics(["anchor", "bag_of_marbles", "bag_of_preparation"])

    start_player_turn(combat)

    assert combat.player.block == 10
    assert all(enemy.has_power("vulnerable", 1) for enemy in combat.enemies)
    assert len(combat.hand) == 7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain/test_combat_flow.py -k "combat_start_relics_apply_opening" -v`
Expected: FAIL because these relics do not currently modify the opening combat state.

- [ ] **Step 3: Write minimal implementation**

Implement one combat-start pass that runs once per combat and handles:

```python
if "anchor" in run_state.relics:
    gain_block(player, 10)
if "bag_of_marbles" in run_state.relics:
    for enemy in enemies:
        apply_power(enemy, "vulnerable", 1)
extra_draw = 2 if "bag_of_preparation" in run_state.relics else 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/domain/test_combat_flow.py -k "combat_start_relics_apply_opening" -v`
Expected: PASS.

- [ ] **Step 5: Expand to the rest of the same trigger family**

In the same batch, add tests and minimal implementations for `lantern`, `clockwork_souvenir`, `thread_and_needle`, `twisted_funnel`, `ninja_scroll`.

- [ ] **Step 6: Commit**

```bash
git add tests/domain/test_combat_flow.py src/slay_the_spire/domain/combat/turn_flow.py src/slay_the_spire/domain/hooks/runtime.py content/relics/common_relics.json content/relics/uncommon_relics.json content/relics/shop_relics.json
git commit -m "feat: implement combat-start relics"
```

### Task 4: Implement Turn-Cycle And Counter Relics

**Files:**
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
- Modify: `src/slay_the_spire/domain/models/combat_state.py`
- Modify: `tests/domain/test_combat_flow.py`
- Modify: `content/relics/common_relics.json`
- Modify: `content/relics/rare_relics.json`
- Modify: `content/relics/uncommon_relics.json`

- [ ] **Step 1: Write the failing tests**

```python
def test_happy_flower_grants_energy_every_third_turn() -> None:
    combat = _combat_state_with_relics(["happy_flower"])

    for _ in range(3):
        start_player_turn(combat)
        end_player_turn(combat)

    assert combat.player.energy == combat.player.base_energy + 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain/test_combat_flow.py -k "happy_flower" -v`
Expected: FAIL because turn counters are not yet tracked for relics.

- [ ] **Step 3: Write minimal implementation**

Add the smallest combat-scoped counters needed for:

- `happy_flower`
- `captains_wheel`
- `horn_cleat`
- `stone_calendar`
- `art_of_war`
- `pocketwatch`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/domain/test_combat_flow.py -k "happy_flower or captains_wheel or horn_cleat or stone_calendar or art_of_war or pocketwatch" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/domain/test_combat_flow.py src/slay_the_spire/domain/combat/turn_flow.py src/slay_the_spire/domain/models/combat_state.py content/relics/common_relics.json content/relics/uncommon_relics.json content/relics/rare_relics.json
git commit -m "feat: implement turn-cycle relic counters"
```

### Task 5: Implement Play/Discard/Exhaust/Kill Relics

**Files:**
- Modify: `src/slay_the_spire/use_cases/`
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
- Modify: `tests/use_cases/`
- Modify: `content/relics/common_relics.json`
- Modify: `content/relics/uncommon_relics.json`
- Modify: `content/relics/rare_relics.json`

- [ ] **Step 1: Write the failing tests**

Start with one representative per trigger family:

```python
def test_shuriken_grants_strength_after_three_attacks_in_one_turn() -> None: ...
def test_tingsha_deals_damage_when_player_discards() -> None: ...
def test_charons_ashes_hits_all_enemies_when_card_is_exhausted() -> None: ...
def test_gremlin_horn_draws_and_grants_energy_on_enemy_death() -> None: ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases -k "shuriken or tingsha or charons_ashes or gremlin_horn" -v`
Expected: FAIL because these trigger hooks are not wired.

- [ ] **Step 3: Write minimal implementation**

Add only the counters and callbacks needed for:

- `nunchaku`
- `pen_nib`
- `kunai`
- `shuriken`
- `ornamental_fan`
- `ink_bottle`
- `letter_opener`
- `bird_faced_urn`
- `mummified_hand`
- `orange_pellets`
- `tingsha`
- `tough_bandages`
- `hovering_kite`
- `charons_ashes`
- `dead_branch`
- `gremlin_horn`
- `unceasing_top`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases tests/domain/test_combat_flow.py -k "shuriken or tingsha or charons_ashes or gremlin_horn or nunchaku or pen_nib or ink_bottle" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases tests/domain/test_combat_flow.py src/slay_the_spire/use_cases src/slay_the_spire/domain/combat/turn_flow.py content/relics/common_relics.json content/relics/uncommon_relics.json content/relics/rare_relics.json
git commit -m "feat: implement action-triggered relic effects"
```

### Task 6: Implement Damage-Resolution Relics

**Files:**
- Modify: `src/slay_the_spire/domain/`
- Modify: `tests/domain/`
- Modify: `content/relics/common_relics.json`
- Modify: `content/relics/rare_relics.json`
- Modify: `content/relics/event_relics.json`

- [ ] **Step 1: Write the failing tests**

```python
def test_the_boot_raises_small_attack_damage_to_five() -> None: ...
def test_torii_reduces_small_unblocked_attack_damage_to_one() -> None: ...
def test_tungsten_rod_reduces_hp_loss_by_one() -> None: ...
def test_centennial_puzzle_draws_three_on_first_hp_loss() -> None: ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain -k "the_boot or torii or tungsten_rod or centennial_puzzle" -v`
Expected: FAIL because the damage pipeline does not yet apply these relic-specific adjustments.

- [ ] **Step 3: Write minimal implementation**

Patch the existing damage-resolution pipeline so it can express:

- pre-damage minimum floor (`the_boot`)
- post-block low-damage reduction (`torii`)
- life-loss reduction (`tungsten_rod`)
- first-damage-taken trigger (`centennial_puzzle`, then `self_forming_clay`, `runic_cube`)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/domain -k "the_boot or torii or tungsten_rod or centennial_puzzle or self_forming_clay or runic_cube" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/domain src/slay_the_spire/domain content/relics/common_relics.json content/relics/rare_relics.json content/relics/event_relics.json
git commit -m "feat: implement damage-resolution relic rules"
```

### Task 7: Implement Reward, Shop, Rest, And Map Relics

**Files:**
- Modify: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/use_cases/`
- Modify: `tests/use_cases/`
- Modify: `tests/app/`
- Modify: `content/relics/common_relics.json`
- Modify: `content/relics/uncommon_relics.json`
- Modify: `content/relics/rare_relics.json`
- Modify: `content/relics/shop_relics.json`
- Modify: `content/relics/boss_relics.json`

- [ ] **Step 1: Write the failing tests**

Use one representative per subsystem:

```python
def test_question_card_adds_one_more_card_reward_offer() -> None: ...
def test_membership_card_halves_shop_prices() -> None: ...
def test_smiling_mask_sets_card_remove_price_to_fifty() -> None: ...
def test_regal_pillow_adds_extra_rest_healing() -> None: ...
def test_black_star_adds_extra_relic_after_elite_combat() -> None: ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases tests/app -k "question_card or membership_card or smiling_mask or regal_pillow or black_star" -v`
Expected: FAIL because these non-combat systems ignore relic modifiers today.

- [ ] **Step 3: Write minimal implementation**

Implement the batch in subsystems:

- reward generator: `question_card`, `prayer_wheel`, `busted_crown`, `white_beast_statue`, `sozu`
- shop pricing and stock: `membership_card`, `the_courier`, `smiling_mask`, `meal_ticket`, `maw_bank`
- rest menus and outcomes: `dream_catcher`, `regal_pillow`, `eternal_feather`, `girya`, `peace_pipe`, `shovel`
- map/room flow: `juzu_bracelet`, `tiny_chest`, `matryoshka`, `black_star`, `preserved_insect`, `ssserpent_head`, `wing_boots`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases tests/app -k "question_card or membership_card or smiling_mask or regal_pillow or black_star or white_beast_statue or meal_ticket" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases tests/app src/slay_the_spire/domain/rewards/reward_generator.py src/slay_the_spire/app/session.py src/slay_the_spire/use_cases content/relics/common_relics.json content/relics/uncommon_relics.json content/relics/rare_relics.json content/relics/shop_relics.json content/relics/boss_relics.json
git commit -m "feat: implement non-combat relic systems"
```

### Task 8: Handle Complex Or Partial Relics And Update Docs

**Files:**
- Modify: `content/relics/*.json`
- Modify: `README.md`
- Modify: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing test**

```python
def test_complex_relics_are_marked_partial_only_when_backing_behavior_exists(content_root: Path) -> None:
    provider = create_content_provider(content_root)

    assert provider.relics().get("sacred_bark").implementation_status in {"placeholder", "partial"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -k "complex_relics_are_marked_partial_only_when_backing_behavior_exists" -v`
Expected: FAIL until the content metadata is updated to match the actual implementation boundary.

- [ ] **Step 3: Write minimal implementation**

Review the remaining unresolved relics, then:

- set `implemented` only for relics with real behavior
- set `partial` for relics with intentionally limited but real behavior
- leave the rest as `placeholder`
- update README with the actual coverage statement

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/content/test_registry_validation.py -v`
Expected: PASS.

- [ ] **Step 5: Run broad regression**

Run: `uv run pytest`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add content/relics README.md tests/content/test_registry_validation.py
git commit -m "docs: align relic implementation status with behavior"
```
