# Review Findings Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复三条 code review 发现：战斗分层 fail-open、Cultist 开局自我强化、Gremlin Nob 技能惩罚。

**Architecture:** 以最小改动补齐行为与测试。用例层修正分层失败时抛错；战斗流程在敌人效果默认目标上补齐自我力量；出牌用例对 Gremlin Nob 技能触发力量。所有改动配套测试并保持内容 JSON 双路径同步。

**Tech Stack:** Python 3.12, pytest, textual/rich TUI content JSON

---

### Task 1: Combat 分层失败时直接报错

**Files:**
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Test: `tests/use_cases/test_enter_room.py`

- [ ] **Step 1: Write the failing test**

```python
from slay_the_spire.content.catalog import WeightedPoolEntry


class _MisconfiguredEncounterProvider:
    def __init__(self, delegate: StarterContentProvider) -> None:
        self._delegate = delegate

    def __getattr__(self, name: str):
        return getattr(self._delegate, name)

    def encounter_pool_entries(self, pool_id: str):
        if pool_id != "act1_basic":
            return self._delegate.encounter_pool_entries(pool_id)
        return (
            WeightedPoolEntry(
                member_id="single_red_louse",
                weight=1,
                min_combat_count=99,
                max_combat_count=100,
            ),
        )


def test_enter_combat_room_raises_when_no_encounters_match_combat_count() -> None:
    provider = _MisconfiguredEncounterProvider(_content_provider())

    with pytest.raises(ValueError, match="no encounter entries match combat count"):
        enter_room(
            _run_state(seed=7),
            _act_state(node_id="r1c0", room_type="combat"),
            "r1c0",
            provider,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_enter_room.py::test_enter_combat_room_raises_when_no_encounters_match_combat_count -q`
Expected: FAIL with missing ValueError (当前会 fallback 到全池)

- [ ] **Step 3: Write minimal implementation**

```python
    if not eligible_entries:
        raise ValueError(
            f"no encounter entries match combat count {combat_count} for pool {enemy_pool_id}"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_enter_room.py::test_enter_combat_room_raises_when_no_encounters_match_combat_count -q`
Expected: PASS

- [ ] **Step 5: Commit**

Per user instruction “Do not commit”, skip commit.

---

### Task 2: Cultist 开场自我强化（力量）

**Files:**
- Modify: `src/slay_the_spire/domain/combat/turn_flow.py`
- Modify: `content/enemies/act1_basic.json`
- Modify: `src/slay_the_spire/data/content/enemies/act1_basic.json`
- Test: `tests/domain/test_combat_flow.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
from slay_the_spire.content.provider import StarterContentProvider


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def test_cultist_incantation_applies_strength_to_self() -> None:
    registry = _content_provider()
    state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=40,
            max_hp=40,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="cultist",
                hp=48,
                max_hp=48,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )

    resolved = end_turn(state, registry)

    assert any(effect["type"] == "strength" for effect in resolved)
    assert state.enemies[0].statuses == [StatusState(status_id="strength", stacks=2)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/domain/test_combat_flow.py::test_cultist_incantation_applies_strength_to_self -q`
Expected: FAIL (strength effect missing / target missing)

- [ ] **Step 3: Write minimal implementation**

```python
        if effect_type == "strength" and "target_instance_id" not in effect:
            effect["target_instance_id"] = source_instance_id
```

```json
{
  "move": "incantation",
  "once": true,
  "effects": [
    {
      "type": "strength",
      "amount": 2
    }
  ]
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/domain/test_combat_flow.py::test_cultist_incantation_applies_strength_to_self -q`
Expected: PASS

- [ ] **Step 5: Commit**

Per user instruction “Do not commit”, skip commit.

---

### Task 3: Gremlin Nob 技能惩罚

**Files:**
- Modify: `src/slay_the_spire/use_cases/play_card.py`
- Test: `tests/use_cases/test_play_card.py`

- [ ] **Step 1: Write the failing test**

```python
def test_playing_skill_against_gremlin_nob_adds_strength() -> None:
    state = CombatState(
        round_number=1,
        energy=3,
        hand=["guard#1"],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=40,
            max_hp=40,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="gremlin_nob",
                hp=84,
                max_hp=84,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )
    provider = _provider_with_card(
        card_id="guard",
        effects=[{"type": "block", "amount": 5}],
    )
    provider.enemies().register(
        {
            "id": "gremlin_nob",
            "name": "地精头目",
            "hp": 84,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )

    result = play_card(state, "guard#1", None, provider)

    assert any(effect["type"] == "strength" for effect in result.resolved_effects)
    assert state.enemies[0].statuses == [StatusState(status_id="strength", stacks=2)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_play_card.py::test_playing_skill_against_gremlin_nob_adds_strength -q`
Expected: FAIL (strength 未增加)

- [ ] **Step 3: Write minimal implementation**

```python
def _append_gremlin_nob_skill_punish(
    state: CombatState,
    *,
    card_type: str,
) -> list[JsonDict]:
    if card_type != "skill":
        return []
    effects: list[JsonDict] = []
    for enemy in state.enemies:
        if enemy.enemy_id != "gremlin_nob" or enemy.hp <= 0:
            continue
        effects.append(
            {
                "type": EFFECT_STRENGTH,
                "amount": 2,
                "source_instance_id": enemy.instance_id,
                "target_instance_id": enemy.instance_id,
            }
        )
    return effects
```

```python
    materialized_effects = _materialize_card_effects(...)
    materialized_effects.extend(
        _append_gremlin_nob_skill_punish(
            combat_state,
            card_type=card_def.card_type,
        )
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_play_card.py::test_playing_skill_against_gremlin_nob_adds_strength -q`
Expected: PASS

- [ ] **Step 5: Commit**

Per user instruction “Do not commit”, skip commit.

---

### Verification

- [ ] Run targeted: `uv run pytest tests/use_cases/test_enter_room.py tests/domain/test_combat_flow.py tests/use_cases/test_play_card.py -q`
- [ ] Run full suite (if practical): `uv run pytest -q`

