# Warrior Archetype Expansion Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand Ironclad's card pool so strength-focused and self-damage-focused runs have enough common paths to resemble the original game more closely.

**Architecture:** Keep the starter deck unchanged and expand only the `ironclad_starter` card pool first. Treat this as a content-first pass: update the source JSON in both content roots, then add only the minimum engine support and tests needed for the first-wave cards to load and play correctly. Defer the higher-complexity cards and mechanics to a later pass so this work stays bounded.

**Tech Stack:** Python 3.12, JSON content files, `pytest`, `uv`

---

### Task 1: Lock the first-wave card list

**Files:**
- Modify: `docs/superpowers/specs/2026-03-28-warrior-archetype-expansion-design.md`
- Modify: `content/cards/ironclad_starter.json`
- Modify: `src/slay_the_spire/data/content/cards/ironclad_starter.json`

- [ ] **Step 1: Write a failing content validation test for the exact first-wave set**

Add assertions in `tests/content/test_registry_validation.py` that the Ironclad starter pool contains the planned first-wave cards and that any cards left for a second pass are not accidentally added yet.

- [ ] **Step 2: Run the targeted test and confirm it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -q`

Expected: FAIL because the new cards are not present yet.

- [ ] **Step 3: Add the planned first-wave cards to both content roots**

Add the low-risk cards first, using the existing content schema and current effect vocabulary wherever possible.

- [ ] **Step 4: Run the targeted test and confirm it passes**

Run: `uv run pytest tests/content/test_registry_validation.py -q`

Expected: PASS for the new card presence assertions.

- [ ] **Step 5: Commit the content-only slice if the repo workflow expects it**

```bash
git add content/cards/ironclad_starter.json src/slay_the_spire/data/content/cards/ironclad_starter.json tests/content/test_registry_validation.py
git commit -m "feat: expand ironclad starter pool"
```

### Task 2: Fill in minimal mechanics for first-wave cards

**Files:**
- Modify: `src/slay_the_spire/domain/effects/effect_types.py`
- Modify: `src/slay_the_spire/domain/effects/effect_resolver.py`
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
- Modify: `src/slay_the_spire/use_cases/combat_events.py`
- Modify: `src/slay_the_spire/adapters/presentation/widgets.py`
- Modify: `tests/domain/test_effect_resolver.py`
- Modify: `tests/domain/test_combat_flow.py`
- Modify: `tests/use_cases/test_combat_events.py`

- [ ] **Step 1: Write failing tests for the minimum mechanics actually introduced**

Cover only the mechanics needed by the first-wave cards, for example:

- a temporary-strength or strength-granting card that already maps to existing `add_power` handling
- a cost/reward self-damage card that already maps to existing `lose_hp` or `gain_energy`
- a block-centric card if it can reuse existing `block` and `draw` logic

Avoid writing tests for second-wave mechanics here; those are intentionally deferred.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/domain/test_effect_resolver.py tests/domain/test_combat_flow.py tests/use_cases/test_combat_events.py -q`

Expected: FAIL on the missing mechanics.

- [ ] **Step 3: Implement the minimal new engine support**

Only add shared behavior that multiple cards need. Keep the implementation generic enough to reuse later, but do not chase full original-game parity in this pass.

- [ ] **Step 4: Re-run the targeted tests**

Run: `uv run pytest tests/domain/test_effect_resolver.py tests/domain/test_combat_flow.py tests/use_cases/test_combat_events.py -q`

Expected: PASS.

### Task 3: Update registry and shop/reward coverage

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `tests/use_cases/test_enter_room.py`
- Modify: `tests/use_cases/test_apply_reward.py`
- Modify: `tests/use_cases/test_shop_and_rest_actions.py`

- [ ] **Step 1: Write tests that prove the new cards can enter the current run flow**

Add assertions that:

- the provider exposes the new cards through the registry
- starter run creation still works unchanged
- shop filtering still excludes curses/status cards and only offers shop-eligible cards
- reward generation can still hand out the expanded pool without breaking existing reward rules

- [ ] **Step 2: Run the targeted use-case tests and confirm failures before implementation**

Run: `uv run pytest tests/use_cases/test_start_run.py tests/use_cases/test_enter_room.py tests/use_cases/test_apply_reward.py tests/use_cases/test_shop_and_rest_actions.py -q`

Expected: FAIL where the new content or mechanics are not yet wired in.

- [ ] **Step 3: Update content tags or registry rules only if the new cards require it**

Prefer keeping the existing acquisition-tag model. Only touch registry logic if a first-wave card truly needs a new supported tag or an existing validation rule is too strict.

- [ ] **Step 4: Re-run the targeted use-case tests**

Run: `uv run pytest tests/use_cases/test_start_run.py tests/use_cases/test_enter_room.py tests/use_cases/test_apply_reward.py tests/use_cases/test_shop_and_rest_actions.py -q`

Expected: PASS.

### Task 4: Verify root/package parity and full regression

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Modify: `tests/e2e/test_single_act_smoke.py`
- Modify: `tests/e2e/test_two_act_smoke.py`

- [ ] **Step 1: Add an explicit root-vs-packaged parity check for the updated card file**

Make the test compare the relevant content JSON files so a later edit cannot drift the packaged content from the source content.

- [ ] **Step 2: Run the parity and smoke tests**

Run: `uv run pytest tests/content/test_registry_validation.py tests/e2e/test_single_act_smoke.py tests/e2e/test_two_act_smoke.py -q`

Expected: PASS.

- [ ] **Step 3: Run the full suite before finishing**

Run: `uv run pytest`

Expected: PASS.

- [ ] **Step 4: Summarize the final card list and note deferred second-wave cards**

Document which cards shipped in this pass and which original-style cards are intentionally deferred for a later, mechanics-heavy expansion.
