# Relic Closure And Reference Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining relic-implementation closure work, align `implementation_status` with actual behavior, and add full card/relic name-and-summary consistency checks against the local Huiji reference corpus under `docs/reference/sts_huijiwiki/`.

**Architecture:** Treat this as a closure pass, not a new feature branch. First, finish the still-missing low-complexity on-acquire relics so the existing relic plan has no obvious gap. Second, create a reproducible extraction pipeline from `docs/reference/sts_huijiwiki/sts_huiji_baike_entries_clean.json` into audited card/relic expectation fixtures. Third, wire those fixtures into content tests so every card and relic name plus concise summary stays aligned with the local reference corpus. Keep the current game/runtime architecture intact; use test-first changes in content, `apply_reward`, and content-validation tests.

**Tech Stack:** Python 3.12, pytest, `uv`, JSON content under `content/`, local reference corpus under `docs/reference/sts_huijiwiki/`

---

### Task 1: Freeze The Remaining Closure Scope

**Files:**
- Modify: `docs/superpowers/relic-behavior-matrix.md`
- Modify: `docs/superpowers/specs/2026-04-03-relic-full-implementation-design.md`
- Modify: `docs/superpowers/plans/2026-04-03-relic-full-implementation.md`

- [ ] **Step 1: Write the failing test**

This task is documentation-only. No production-code test is required.

- [ ] **Step 2: Update the matrix to distinguish closure targets from intentional deferrals**

Edit the relic matrix so the remaining unresolved relics explicitly show one of these states in the notes column:

```md
| relic_id | status | domain | primary entrypoint | secondary notes |
| --- | --- | --- | --- | --- |
| vajra | placeholder | on_acquire | apply_reward | closure target |
| sacred_bark | placeholder | complex/deferred | hooks/runtime | deferred: needs potion-effect system |
| bottled_flame | placeholder | complex/deferred | apply_reward | deferred: needs card picker UI |
```

- [ ] **Step 3: Record the exact closure targets in the plan**

Update the existing relic full-implementation plan to say that this closure pass must finish:

- `vajra`
- `oddly_smooth_stone`
- `war_paint`
- `whetstone`

and must explicitly leave complex relics such as `sacred_bark`, `bottled_flame`, `orrery`, and `prismatic_shard` in `placeholder` or `partial` based on actual code support.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/relic-behavior-matrix.md docs/superpowers/specs/2026-04-03-relic-full-implementation-design.md docs/superpowers/plans/2026-04-03-relic-full-implementation.md
git commit -m "docs: freeze relic closure scope"
```

### Task 2: Finish The Remaining On-Acquire Relics

**Files:**
- Modify: `src/slay_the_spire/use_cases/apply_reward.py`
- Modify: `tests/use_cases/test_apply_reward.py`
- Modify: `content/relics/common_relics.json`

- [ ] **Step 1: Write the failing tests**

Add these tests to `tests/use_cases/test_apply_reward.py`:

```python
def test_apply_reward_grants_vajra_permanent_strength_bonus() -> None:
    run_state = _run_state()

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:vajra",
        registry=_content_provider(),
    )

    assert "vajra" in updated.relics
    assert updated.relic_sequence_positions["relic:vajra:strength_bonus"] == 1


def test_apply_reward_grants_oddly_smooth_stone_permanent_dexterity_bonus() -> None:
    run_state = _run_state()

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:oddly_smooth_stone",
        registry=_content_provider(),
    )

    assert "oddly_smooth_stone" in updated.relics
    assert updated.relic_sequence_positions["relic:oddly_smooth_stone:dexterity_bonus"] == 1


def test_apply_reward_war_paint_upgrades_two_random_skill_cards() -> None:
    run_state = replace(
        _run_state(),
        deck=["defend#1", "shrug_it_off#1", "bash#1", "armaments#1"],
    )

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:war_paint",
        registry=_content_provider(),
    )

    assert "war_paint" in updated.relics
    upgraded = {card for card in updated.deck if card.endswith("_plus#1")}
    assert upgraded == {"shrug_it_off_plus#1", "armaments_plus#1"}


def test_apply_reward_whetstone_upgrades_two_random_attack_cards() -> None:
    run_state = replace(
        _run_state(),
        deck=["strike#1", "bash#1", "defend#1", "anger#1"],
    )

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:whetstone",
        registry=_content_provider(),
    )

    assert "whetstone" in updated.relics
    upgraded = {card for card in updated.deck if card.endswith("_plus#1")}
    assert upgraded == {"strike_plus#1", "bash_plus#1"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -k "vajra or oddly_smooth_stone or war_paint or whetstone" -v`
Expected: FAIL because only the earlier max-HP / gold on-acquire relics are currently implemented.

- [ ] **Step 3: Write minimal implementation**

Extend `src/slay_the_spire/use_cases/apply_reward.py` with explicit acquire handlers and deterministic upgrade selection:

```python
from slay_the_spire.domain.models.cards import card_id_from_instance_id

_ON_ACQUIRE_RELIC_POSITION_FLAGS = {
    "vajra": ("relic:vajra:strength_bonus", 1),
    "oddly_smooth_stone": ("relic:oddly_smooth_stone:dexterity_bonus", 1),
}


def _upgrade_matching_cards(
    run_state: RunState,
    *,
    registry: ContentProviderPort,
    card_type: str,
    limit: int,
) -> RunState:
    updated_deck = list(run_state.deck)
    upgraded = 0
    for index, instance_id in enumerate(updated_deck):
        card_id = card_id_from_instance_id(instance_id)
        card_def = registry.cards().get(card_id)
        if card_def.card_type != card_type:
            continue
        if not card_def.upgrades_to:
            continue
        updated_deck[index] = instance_id.replace(card_id, card_def.upgrades_to, 1)
        upgraded += 1
        if upgraded == limit:
            break
    return replace(run_state, deck=updated_deck)


def _apply_relic_on_acquire_effects(
    run_state: RunState,
    relic_id: str,
    *,
    registry: ContentProviderPort,
) -> RunState:
    updated = run_state
    if relic_id == "war_paint":
        updated = _upgrade_matching_cards(
            updated, registry=registry, card_type="skill", limit=2
        )
    if relic_id == "whetstone":
        updated = _upgrade_matching_cards(
            updated, registry=registry, card_type="attack", limit=2
        )
    if relic_id in _ON_ACQUIRE_RELIC_POSITION_FLAGS:
        key, value = _ON_ACQUIRE_RELIC_POSITION_FLAGS[relic_id]
        positions = dict(updated.relic_sequence_positions)
        positions[key] = value
        updated = replace(updated, relic_sequence_positions=positions)
    return updated
```

Also update the `apply_reward(...)` call site to pass `registry` into `_apply_relic_on_acquire_effects(...)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -k "vajra or oddly_smooth_stone or war_paint or whetstone" -v`
Expected: PASS.

- [ ] **Step 5: Mark content status as implemented**

Change these relics in `content/relics/common_relics.json`:

```json
"vajra": "implemented",
"oddly_smooth_stone": "implemented",
"war_paint": "implemented",
"whetstone": "implemented"
```

Apply the real JSON edit, not a note.

- [ ] **Step 6: Run the focused regression**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/use_cases/test_apply_reward.py src/slay_the_spire/use_cases/apply_reward.py content/relics/common_relics.json
git commit -m "feat: finish remaining on-acquire relics"
```

### Task 3: Extract Audited Huiji Expectations For Cards And Relics

**Files:**
- Create: `scripts/extract_huiji_card_relic_expectations.py`
- Create: `docs/reference/sts_huijiwiki/card_relic_expectations.json`
- Create: `tests/content/test_huiji_reference_fixture.py`

- [ ] **Step 1: Write the failing fixture test**

Create `tests/content/test_huiji_reference_fixture.py` with:

```python
from __future__ import annotations

import json
from pathlib import Path


def test_card_relic_expectation_fixture_exists_and_is_non_empty() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "reference"
        / "sts_huijiwiki"
        / "card_relic_expectations.json"
    )

    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert payload["cards"]
    assert payload["relics"]
    assert "strike" in payload["cards"]
    assert "burning_blood" in payload["relics"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_huiji_reference_fixture.py -v`
Expected: FAIL because the extracted expectation fixture does not exist yet.

- [ ] **Step 3: Write the extraction script**

Create `scripts/extract_huiji_card_relic_expectations.py`:

```python
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "reference" / "sts_huijiwiki" / "sts_huiji_baike_entries_clean.json"
OUTPUT = ROOT / "docs" / "reference" / "sts_huijiwiki" / "card_relic_expectations.json"


def _normalize_summary(text: str) -> str:
    text = re.sub(r"\\s+", " ", text).strip()
    text = text.replace("。 ", "。")
    return text


def main() -> None:
    entries = json.loads(SOURCE.read_text(encoding="utf-8"))["entries"]
    payload = {"cards": {}, "relics": {}}
    for entry in entries:
        title = str(entry.get("title", "")).strip()
        content = str(entry.get("content_text", "")).strip()
        if not title or not content:
            continue
        if "遗物" in content:
            payload["relics"][title] = {"name": title, "summary": _normalize_summary(content[:120])}
        if "技能" in content or "攻击" in content or "能力" in content or "诅咒" in content:
            payload["cards"][title] = {"name": title, "summary": _normalize_summary(content[:120])}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Generate the fixture**

Run: `uv run python scripts/extract_huiji_card_relic_expectations.py`
Expected: `docs/reference/sts_huijiwiki/card_relic_expectations.json` is created.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/content/test_huiji_reference_fixture.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/extract_huiji_card_relic_expectations.py docs/reference/sts_huijiwiki/card_relic_expectations.json tests/content/test_huiji_reference_fixture.py
git commit -m "test: add huiji reference expectation fixture"
```

### Task 4: Add Full Relic Name-And-Summary Consistency Checks

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing relic audit test**

Add to `tests/content/test_registry_validation.py`:

```python
@pytest.mark.parametrize("content_root", _content_roots())
def test_all_relic_names_and_summaries_match_huiji_reference(content_root: Path) -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "reference"
        / "sts_huijiwiki"
        / "card_relic_expectations.json"
    )
    expectations = json.loads(fixture_path.read_text(encoding="utf-8"))["relics"]
    provider = StarterContentProvider(content_root)

    mismatches: list[str] = []
    for relic in provider.relics().all():
        expected = expectations.get(relic.name)
        if expected is None:
            mismatches.append(f"{relic.id}: missing expectation")
            continue
        if relic.name != expected["name"]:
            mismatches.append(f"{relic.id}: name mismatch")
        if relic.summary != expected["summary"]:
            mismatches.append(f"{relic.id}: summary mismatch")

    assert not mismatches, "\\n".join(mismatches[:20])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -k "all_relic_names_and_summaries_match_huiji_reference" -v`
Expected: FAIL because the raw extracted fixture and current content summaries will not match yet.

- [ ] **Step 3: Refine the fixture into curated audited expectations**

Replace the brittle title-keyed lookup with stable ID-keyed expectations in `docs/reference/sts_huijiwiki/card_relic_expectations.json`. The curated file must look like:

```json
{
  "cards": {
    "strike": {"name": "打击（红）", "summary": "造成 6 点伤害。"},
    "bash": {"name": "痛击", "summary": "造成 8 点伤害。施加 2 层易伤。"}
  },
  "relics": {
    "burning_blood": {"name": "燃烧之血", "summary": "战斗结束后回复 6 点生命。"},
    "black_star": {"name": "黑星", "summary": "精英敌人额外掉落 1 个遗物。"}
  }
}
```

Update the extraction script so it emits this shape, then manually review and correct ambiguous or missing entries by editing the generated JSON in-place.

- [ ] **Step 4: Write minimal test implementation**

Change the relic audit test to compare by content ID:

```python
expected = expectations.get(relic.id)
assert expected is not None, relic.id
assert relic.name == expected["name"]
assert relic.summary == expected["summary"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/content/test_registry_validation.py -k "all_relic_names_and_summaries_match_huiji_reference" -v`
Expected: PASS.

- [ ] **Step 6: Update README**

Add a short line in `README.md` under the reference section and/or content section saying that card and relic Chinese names plus concise summaries are now regression-checked against the local Huiji reference corpus.

- [ ] **Step 7: Commit**

```bash
git add tests/content/test_registry_validation.py docs/reference/sts_huijiwiki/card_relic_expectations.json scripts/extract_huiji_card_relic_expectations.py README.md
git commit -m "test: audit relic names and summaries against huiji reference"
```

### Task 5: Add Full Card Name-And-Summary Consistency Checks

**Files:**
- Modify: `tests/content/test_registry_validation.py`
- Modify: `src/slay_the_spire/adapters/presentation/widgets.py`

- [ ] **Step 1: Write the failing card audit test**

Add to `tests/content/test_registry_validation.py`:

```python
@pytest.mark.parametrize("content_root", _content_roots())
def test_all_card_names_and_summaries_match_huiji_reference(content_root: Path) -> None:
    fixture_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "reference"
        / "sts_huijiwiki"
        / "card_relic_expectations.json"
    )
    expectations = json.loads(fixture_path.read_text(encoding="utf-8"))["cards"]
    provider = StarterContentProvider(content_root)

    mismatches: list[str] = []
    for card in provider.cards().all():
        expected = expectations.get(card.id)
        if expected is None:
            mismatches.append(f"{card.id}: missing expectation")
            continue
        if card.name != expected["name"]:
            mismatches.append(f"{card.id}: name mismatch")
        if summarize_card_definition(card) != expected["summary"]:
            mismatches.append(f"{card.id}: summary mismatch")

    assert not mismatches, "\\n".join(mismatches[:20])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -k "all_card_names_and_summaries_match_huiji_reference" -v`
Expected: FAIL because cards do not store summary text directly and the current presentation summarizer may not normalize wording to the audited reference.

- [ ] **Step 3: Write minimal implementation**

Expose a deterministic card-summary helper in `src/slay_the_spire/adapters/presentation/widgets.py`:

```python
def summarize_card_definition(card_def: CardDef) -> str:
    summary = summarize_card_effects(card_def.effects)
    if card_def.ethereal:
        summary = f"消逝。{summary}"
    if card_def.exhausts:
        summary = f"{summary} 消耗。"
    return summary.strip()
```

Import and use that helper in the test instead of reconstructing summaries ad hoc.

- [ ] **Step 4: Curate the card expectations**

Manually review `docs/reference/sts_huijiwiki/card_relic_expectations.json["cards"]` so the expected `summary` matches the project’s concise one-line card summary style, while remaining faithful to the Huiji wording.

Examples:

```json
"strike": {"name": "打击（红）", "summary": "造成 6 点伤害。"},
"ghostly_armor": {"name": "幽灵铠甲", "summary": "消逝。获得 10 点格挡。"},
"offering": {"name": "祭品", "summary": "失去 6 点生命。获得 2 点能量并抽 3 张牌。消耗。"}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/content/test_registry_validation.py -k "all_card_names_and_summaries_match_huiji_reference" -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/content/test_registry_validation.py src/slay_the_spire/adapters/presentation/widgets.py docs/reference/sts_huijiwiki/card_relic_expectations.json
git commit -m "test: audit card names and summaries against huiji reference"
```

### Task 6: Align Final Status, README, And Full Regression

**Files:**
- Modify: `content/relics/*.json`
- Modify: `README.md`
- Modify: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing status-alignment test**

Extend `test_implementation_status_matches_code_behavior` in `tests/content/test_registry_validation.py`:

```python
def test_closure_targets_are_no_longer_placeholder(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    for relic_id in ["vajra", "oddly_smooth_stone", "war_paint", "whetstone"]:
        assert provider.relics().get(relic_id).implementation_status == "implemented"

    for relic_id in ["sacred_bark", "bottled_flame", "orrery", "prismatic_shard"]:
        assert provider.relics().get(relic_id).implementation_status in {"placeholder", "partial"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -k "closure_targets_are_no_longer_placeholder" -v`
Expected: FAIL until content status is fully aligned.

- [ ] **Step 3: Write minimal implementation**

Update:

- `content/relics/common_relics.json`
- `content/relics/uncommon_relics.json`
- `content/relics/rare_relics.json`
- `content/relics/shop_relics.json`
- `content/relics/boss_relics.json`

so the final statuses match actual code behavior and documented deferrals.

- [ ] **Step 4: Run focused content regression**

Run: `uv run pytest tests/content/test_registry_validation.py -v`
Expected: PASS.

- [ ] **Step 5: Run full regression**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add content/relics README.md tests/content/test_registry_validation.py
git commit -m "docs: close relic plan and enforce huiji content alignment"
```
