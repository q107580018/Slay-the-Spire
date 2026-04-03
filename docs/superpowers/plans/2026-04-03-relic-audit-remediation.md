# Relic Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix relic drop eligibility, unify relic acquisition paths, repair the highest-priority runtime relic behaviors, and correct audited static relic data so the repository matches its local source material and runtime facts.

**Architecture:** Implement the repair in three phases. First, stop placeholder relics from entering real reward pools and route every relic acquisition through `apply_reward`. Second, fix the already-wired runtime relic behaviors whose lifecycle timing is wrong and generalize replacement-relic handling. Third, correct the audited `content/relics` metadata mismatches, add the missing base-game relic entries, and update README to reflect the actual state of implementation.

**Tech Stack:** Python 3.12, pytest, `uv`, JSON content under `content/`, textual/rich app code under `src/slay_the_spire/`

---

### Task 1: Stop Placeholder Relics From Entering Real Reward Pools

**Files:**
- Modify: `src/slay_the_spire/use_cases/start_run.py:9-36`
- Modify: `src/slay_the_spire/use_cases/opening_flow.py:269-283`
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `tests/use_cases/test_apply_reward.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_start_new_run_excludes_placeholder_relics_from_reward_sequences() -> None:
    provider = _content_provider()

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert "akabeko" not in run_state.relic_sequences["common"]
    assert "anchor" not in run_state.relic_sequences["common"]
    assert "blood_vial" in run_state.relic_sequences["common"]
    assert "ectoplasm" in run_state.relic_sequences["boss"]
    assert "astrolabe" not in run_state.relic_sequences["boss"]


def test_neow_random_relic_selection_excludes_placeholder_relics() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    rng = Random(7)

    picked = {_choose_relic_id(registry=provider, rng=rng, run_state=run_state) for _ in range(20)}

    assert picked
    assert picked <= {"blood_vial"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_start_run.py -k "placeholder or neow_random_relic_selection" -v`
Expected: FAIL because sequence construction and Neow relic selection still include placeholder relics.

- [ ] **Step 3: Write minimal implementation**

```python
_REWARDABLE_RELIC_STATUSES = {"implemented", "partial"}
_RELIC_SEQUENCE_POOL_IDS = ("common", "uncommon", "rare", "shop", "boss")


def _is_rewardable_relic(*, relic, character_id: str, pool_id: str) -> bool:
    if pool_id not in relic.pools:
        return False
    if relic.implementation_status not in _REWARDABLE_RELIC_STATUSES:
        return False
    return not relic.owner_character_ids or character_id in relic.owner_character_ids


def _build_relic_sequences(*, character_id: str, seed: int, registry: ContentProviderPort) -> tuple[dict[str, list[str]], dict[str, int]]:
    sequences: dict[str, list[str]] = {}
    for pool_id in _RELIC_SEQUENCE_POOL_IDS:
        relic_ids = sorted(
            relic.id
            for relic in registry.relics().all()
            if _is_rewardable_relic(relic=relic, character_id=character_id, pool_id=pool_id)
        )
        Random(f"{seed}:{character_id}:{pool_id}").shuffle(relic_ids)
        sequences[pool_id] = relic_ids
    return sequences, {pool_id: 0 for pool_id in _RELIC_SEQUENCE_POOL_IDS}


def _choose_relic_id(*, registry, rng: Random, run_state: RunState) -> str:
    relic_ids = sorted(
        relic.id
        for relic in registry.relics().all()
        if "neow" in relic.pools
        and relic.implementation_status in {"implemented", "partial"}
        and (
            not relic.owner_character_ids
            or run_state.character_id in relic.owner_character_ids
        )
    )
    if not relic_ids:
        raise ValueError(f"no Neow relics available for character: {run_state.character_id}")
    return rng.choice(relic_ids)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_start_run.py -k "placeholder or neow_random_relic_selection" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_start_run.py src/slay_the_spire/use_cases/start_run.py src/slay_the_spire/use_cases/opening_flow.py
git commit -m "fix: exclude placeholder relics from reward pools"
```

### Task 2: Route Shop And Event Relic Rewards Through apply_reward

**Files:**
- Modify: `src/slay_the_spire/use_cases/apply_reward.py:18-58`
- Modify: `src/slay_the_spire/use_cases/shop_action.py:167-195`
- Modify: `src/slay_the_spire/use_cases/event_action.py:40-55`
- Modify: `tests/use_cases/test_shop_and_rest_actions.py`
- Modify: `tests/use_cases/test_event_actions.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_shop_buy_relic_routes_through_apply_reward_replacement_rules() -> None:
    run_state = replace(_run_state(gold=300), relics=["burning_blood"])
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "cards": [],
            "relics": [{"offer_id": "relic-1", "relic_id": "black_blood", "price": 150}],
            "potions": [],
            "remove_price": 75,
        },
        is_resolved=False,
        rewards=[],
    )

    result = shop_action(run_state=run_state, room_state=room_state, action_id="buy_relic:relic-1")

    assert result.run_state.gold == 150
    assert result.run_state.relics == ["black_blood"]


def test_event_reward_relic_routes_through_apply_reward_replacement_rules() -> None:
    room_state = RoomState(
        room_id="act1:test-event",
        room_type="event",
        stage="waiting_input",
        payload={"event_id": "golden_idol", "node_id": "r1c1", "next_node_ids": ["r2c0"]},
        is_resolved=False,
        rewards=[],
    )
    run_state = replace(_run_state(), relics=["burning_blood"])

    result = event_action(
        run_state=run_state,
        room_state=room_state,
        action_id="choice:take_hide",
        registry=_content_provider(),
    )

    assert "golden_idol" in result.run_state.relics
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_shop_and_rest_actions.py tests/use_cases/test_event_actions.py -k "routes_through_apply_reward" -v`
Expected: FAIL because shop and event relic acquisition still append directly to `run_state.relics`.

- [ ] **Step 3: Write minimal implementation**

```python
def _apply_relic_reward(*, run_state: RunState, relic_id: str, registry: ContentProviderPort) -> RunState:
    return apply_reward(run_state=run_state, reward_id=f"relic:{relic_id}", registry=registry)


def _with_added_relic(run_state: RunState, relic_id: str, registry: ContentProviderPort) -> RunState:
    return apply_reward(run_state=run_state, reward_id=f"relic:{relic_id}", registry=registry)


# shop_action.py
updated_run_state = apply_reward(
    run_state=replace(run_state, gold=run_state.gold - price),
    reward_id=f"relic:{relic_id}",
    registry=_content_provider(),
)


# event_action.py
if relic_id is not None:
    updated_run_state = apply_reward(
        run_state=updated_run_state,
        reward_id=f"relic:{relic_id}",
        registry=registry,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_shop_and_rest_actions.py tests/use_cases/test_event_actions.py -k "routes_through_apply_reward" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_shop_and_rest_actions.py tests/use_cases/test_event_actions.py src/slay_the_spire/use_cases/apply_reward.py src/slay_the_spire/use_cases/shop_action.py src/slay_the_spire/use_cases/event_action.py
git commit -m "refactor: unify relic reward application"
```

### Task 3: Generalize Replacement Relics In apply_reward

**Files:**
- Modify: `src/slay_the_spire/use_cases/apply_reward.py:26-43`
- Modify: `tests/use_cases/test_apply_reward.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_apply_reward_replaces_existing_relic_when_replaces_relic_id_matches() -> None:
    run_state = replace(_run_state(), relics=["ring_of_the_snake"])

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:ring_of_the_serpent",
        registry=_content_provider(),
    )

    assert updated.relics == ["ring_of_the_serpent"]


def test_apply_reward_keeps_other_relics_when_replacing_starting_relic() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "golden_idol"])

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:black_blood",
        registry=_content_provider(),
    )

    assert updated.relics == ["golden_idol", "black_blood"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -k "replaces_existing_relic or replacing_starting_relic" -v`
Expected: FAIL because only `black_blood` is special-cased today.

- [ ] **Step 3: Write minimal implementation**

```python
def _apply_relic_acquisition(*, run_state: RunState, relic_id: str, registry: ContentProviderPort) -> RunState:
    relic = registry.relics().get(relic_id)
    relics = list(run_state.relics)

    if relic_id == "circlet":
        return replace(run_state, relics=[*relics, relic_id])

    replaced_relic_id = relic.replaces_relic_id
    if replaced_relic_id is not None:
        relics = [owned for owned in relics if owned != replaced_relic_id]

    if relic_id in relics:
        return replace(run_state, relics=relics)
    return replace(run_state, relics=[*relics, relic_id])


if reward_id.startswith("relic:"):
    relic_id = reward_id.split(":", 1)[1]
    return _apply_relic_acquisition(
        run_state=run_state,
        relic_id=relic_id,
        registry=registry,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -k "replaces_existing_relic or replacing_starting_relic or circlet" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_apply_reward.py src/slay_the_spire/use_cases/apply_reward.py
git commit -m "feat: generalize relic replacement handling"
```

### Task 4: Fix Per-Turn Energy Relic Timing

**Files:**
- Modify: `src/slay_the_spire/domain/hooks/runtime.py:30-52`
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py:462-610`
- Modify: `src/slay_the_spire/use_cases/enter_room.py:160-163`
- Modify: `tests/use_cases/test_start_run.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_ectoplasm_grants_energy_on_second_turn() -> None:
    provider = _content_provider()
    run_state = replace(start_new_run("ironclad", seed=5, registry=provider), relics=["ectoplasm"])
    act_state = generate_act_state("act1", seed=5, registry=provider)
    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    end_turn(combat_state, provider)

    assert combat_state.round_number == 2
    assert combat_state.energy == 4


def test_fusion_hammer_grants_energy_on_second_turn() -> None:
    provider = _content_provider()
    run_state = replace(start_new_run("ironclad", seed=5, registry=provider), relics=["fusion_hammer"])
    act_state = generate_act_state("act1", seed=5, registry=provider)
    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    end_turn(combat_state, provider)

    assert combat_state.energy == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_start_run.py -k "second_turn" -v`
Expected: FAIL because relic energy is currently only granted on `on_combat_start`.

- [ ] **Step 3: Write minimal implementation**

```python
def _start_of_turn_relic_energy(state: CombatState, registrations: Sequence[HookRegistration]) -> None:
    dispatch_hook(state, "on_turn_start", registrations)


def start_turn(
    state: CombatState,
    *,
    hand_size: int = DEFAULT_HAND_SIZE,
    energy_per_turn: int = DEFAULT_ENERGY_PER_TURN,
    registry: ContentProviderPort | None = None,
    resolved_effects: list[JsonDict] | None = None,
    hook_registrations: Sequence[HookRegistration] = (),
) -> CombatState:
    _clear_block_for_turn_start(
        state.player,
        keep_block=_has_player_power(state, "barricade"),
    )
    _clear_temporary_power(state, "flame_barrier")
    state.energy = energy_per_turn
    _start_of_turn_relic_energy(state, hook_registrations)
    _apply_start_turn_powers(state)
    _apply_brutality(state)
    _draw_cards(
        state,
        amount=max(hand_size - len(state.hand), 0),
        registry=registry,
    )
    ...


# content/relics/boss_relics.json
{"id": "ectoplasm", ..., "trigger_hooks": ["on_turn_start"], ...}
{"id": "coffee_dripper", ..., "trigger_hooks": ["on_turn_start"], ...}
{"id": "fusion_hammer", ..., "trigger_hooks": ["on_turn_start"], ...}
{"id": "busted_crown", ..., "trigger_hooks": ["on_turn_start"], ...}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_start_run.py -k "ectoplasm or fusion_hammer" -v`
Expected: PASS with both first-turn and second-turn energy assertions green.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_start_run.py src/slay_the_spire/domain/combat/turn_flow.py src/slay_the_spire/domain/hooks/runtime.py src/slay_the_spire/use_cases/enter_room.py content/relics/boss_relics.json
git commit -m "fix: apply boss energy relics each turn"
```

### Task 5: Add Explicit Combat-End Healing Regression Tests

**Files:**
- Modify: `tests/use_cases/test_enter_room.py`
- Modify: `tests/domain/test_effect_resolver.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_burning_blood_heals_six_after_combat() -> None:
    provider = _content_provider()
    state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(instance_id="player-ironclad", hp=40, max_hp=80, block=0, statuses=[]),
        enemies=[],
        effect_queue=[],
        log=[],
    )
    run_state = _run_state(seed=7, relics=["burning_blood"], current_hp=40, max_hp=80)
    registrations = build_runtime_hook_registrations(run_state, provider)

    dispatch_hook(state, "on_combat_end", registrations)
    resolve_effect_queue(state, hook_registrations=registrations)

    assert state.player.hp == 46


def test_black_blood_heals_twelve_after_combat() -> None:
    provider = _content_provider()
    state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(instance_id="player-ironclad", hp=40, max_hp=80, block=0, statuses=[]),
        enemies=[],
        effect_queue=[],
        log=[],
    )
    run_state = _run_state(seed=7, relics=["black_blood"], current_hp=40, max_hp=80)
    registrations = build_runtime_hook_registrations(run_state, provider)

    dispatch_hook(state, "on_combat_end", registrations)
    resolve_effect_queue(state, hook_registrations=registrations)

    assert state.player.hp == 52
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_enter_room.py tests/domain/test_effect_resolver.py -k "burning_blood_heals or black_blood_heals" -v`
Expected: FAIL because no explicit regression coverage exists yet.

- [ ] **Step 3: Write minimal implementation**

```python
# No production change expected if hooks are already correct.
# Keep the tests as the only change unless they expose a real bug.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_enter_room.py tests/domain/test_effect_resolver.py -k "burning_blood_heals or black_blood_heals" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_enter_room.py tests/domain/test_effect_resolver.py
git commit -m "test: cover combat-end relic healing values"
```

### Task 6: Correct High-Priority Static Relic Metadata And Add Missing Relics

**Files:**
- Modify: `content/relics/event_relics.json`
- Modify: `content/relics/uncommon_relics.json`
- Modify: `content/relics/rare_relics.json`
- Modify: `content/relics/shop_relics.json`
- Modify: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing metadata tests**

```python
@pytest.mark.parametrize(
    ("relic_id", "expected_rarity", "expected_pools", "expected_owner_ids"),
    [
        ("shuriken", "uncommon", ["uncommon", "neow"], []),
        ("the_courier", "uncommon", ["uncommon", "neow"], []),
        ("abacus", "shop", ["shop"], []),
        ("neows_lament", "event", ["event"], []),
    ],
)
def test_audited_relic_metadata_matches_expected_catalog(
    content_root: Path,
    relic_id: str,
    expected_rarity: str,
    expected_pools: list[str],
    expected_owner_ids: list[str],
) -> None:
    provider = StarterContentProvider(content_root)

    relic = provider.relics().get(relic_id)

    assert relic.rarity == expected_rarity
    assert relic.pools == expected_pools
    assert relic.owner_character_ids == expected_owner_ids


@pytest.mark.parametrize("content_root", _content_roots())
def test_missing_audited_relics_are_present(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    assert provider.relics().get("pocketwatch").name == "怀表"
    assert provider.relics().get("twisted_funnel").name == "扭曲漏斗"
    assert provider.relics().get("ninja_scroll").name == "忍术卷轴"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -k "audited_relic_metadata_matches_expected_catalog or missing_audited_relics_are_present" -v`
Expected: FAIL because the metadata is still wrong and the missing relics are not in `content/relics`.

- [ ] **Step 3: Write minimal implementation**

```json
{
  "id": "pocketwatch",
  "name": "怀表",
  "summary": "若你本回合打出不超过 3 张牌，则下回合开始时额外抽 3 张牌",
  "description": "若你在某个回合打出的牌少于等于 3 张，则在你的下个回合开始时额外抽 3 张牌。",
  "rarity": "rare",
  "pools": ["rare"],
  "source_tags": ["standard_pool"],
  "owner_character_ids": [],
  "implementation_status": "placeholder",
  "effect_blueprint": [],
  "trigger_hooks": [],
  "passive_effects": [],
  "can_appear_in_shop": false
}
```

Also apply the audited metadata corrections for the high-priority mismatches:

- `face_of_cleric`
- `gremlin_visage`
- `nloths_gift`
- `ssserpent_head`
- `warped_tongs`
- `cloak_clasp`
- `damaru`
- `melange`
- `thread_and_needle`
- `abacus`
- `gambling_chip`
- `shuriken`
- `runic_capacitor`
- `the_courier`
- `neows_lament`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/content/test_registry_validation.py -k "audited_relic_metadata_matches_expected_catalog or missing_audited_relics_are_present" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add content/relics/event_relics.json content/relics/uncommon_relics.json content/relics/rare_relics.json content/relics/shop_relics.json tests/content/test_registry_validation.py
git commit -m "fix: correct audited relic metadata"
```

### Task 7: Update README To Match Repository Facts

**Files:**
- Modify: `README.md:21-30`

- [ ] **Step 1: Write the failing documentation expectation test surrogate**

```python
# No automated README assertion exists in this repository.
# Use a targeted manual review checklist:
# 1. README must not claim the relic catalog is already complete unless missing relics were added.
# 2. README must not imply all placeholder relics can drop if Task 1 filtered them out.
```

- [ ] **Step 2: Run verification to confirm current README is stale**

Run: `grep -n "原版 1 代基础遗物目录已完整录入到内容层\|运行时效果仍按批次逐步补齐" README.md`
Expected: Matches the stale sentence that no longer reflects audited facts.

- [ ] **Step 3: Write minimal implementation**

```markdown
- 当前原版 1 代遗物目录以 `content/relics/` 为内容真源维护，并与本地原版资料持续校对
- 当前只有一部分遗物具备完整运行时效果；未实现条目会通过实现状态标记，并且不会再进入实际掉落池
```

- [ ] **Step 4: Run verification to confirm README wording is updated**

Run: `grep -n "当前原版 1 代遗物目录以 `content/relics/` 为内容真源维护\|未实现条目会通过实现状态标记，并且不会再进入实际掉落池" README.md`
Expected: Two matches with the new wording.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: align relic status summary with code"
```

### Task 8: Final Verification Sweep

**Files:**
- Modify: none
- Test: `tests/use_cases/test_start_run.py`
- Test: `tests/use_cases/test_apply_reward.py`
- Test: `tests/use_cases/test_shop_and_rest_actions.py`
- Test: `tests/use_cases/test_event_actions.py`
- Test: `tests/use_cases/test_enter_room.py`
- Test: `tests/domain/test_effect_resolver.py`
- Test: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Run the focused verification suite**

Run: `uv run pytest tests/use_cases/test_start_run.py tests/use_cases/test_apply_reward.py tests/use_cases/test_shop_and_rest_actions.py tests/use_cases/test_event_actions.py tests/use_cases/test_enter_room.py tests/domain/test_effect_resolver.py tests/content/test_registry_validation.py -v`
Expected: PASS.

- [ ] **Step 2: Run one broader integration check**

Run: `uv run pytest tests/use_cases tests/content/test_registry_validation.py -v`
Expected: PASS.

- [ ] **Step 3: Review changed files against the approved spec**

Checklist:

```text
1. Placeholder relics no longer enter common/uncommon/rare/shop/boss/neow reward pools.
2. Shop and event relic rewards route through apply_reward.
3. Replacement relic handling is generalized beyond black_blood.
4. Boss energy relics grant energy beyond turn one.
5. Missing audited relics are present in content/relics.
6. README wording matches current behavior.
```

- [ ] **Step 4: Commit any final cleanup if needed**

```bash
git add README.md content/relics src/slay_the_spire tests
git commit -m "test: verify relic audit remediation"
```
