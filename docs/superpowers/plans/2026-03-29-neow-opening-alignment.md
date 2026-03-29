# Neow Opening Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the opening `Neow` flow with the original game's four-slot rule structure, concrete reward values, and tradeoff constraints while preserving the current Textual opening UX.

**Architecture:** Keep the change centered in `src/slay_the_spire/use_cases/opening_flow.py`, reusing `OpeningState`, session routing, and existing opening menus. Extend the opening state and menu flow only where required for transform and multi-target Neow offers, then update renderer/Textual preview surfaces and docs to match the new semantics.

**Tech Stack:** Python 3.12, `pytest`, `textual`, `rich`, `uv`

---

## File Map

- Modify: `src/slay_the_spire/use_cases/opening_flow.py`
  Responsibility: fixed four-slot Neow generation, reward/cost pools, tradeoff constraints, transform behavior, boss relic swap application.
- Modify: `src/slay_the_spire/app/opening_state.py`
  Responsibility: minimal extra opening state needed for sequential multi-target Neow actions.
- Modify: `src/slay_the_spire/app/session.py`
  Responsibility: route new Neow target modes and preserve current opening-to-active transition.
- Modify: `src/slay_the_spire/adapters/presentation/opening_renderer.py`
  Responsibility: render updated Neow summaries and target panels in Chinese.
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
  Responsibility: hover preview support for new Neow reward kinds and target menu modes.
- Modify: `tests/use_cases/test_opening_flow.py`
  Responsibility: opening-flow generation, reward application, transform, and boss relic swap coverage.
- Modify: `tests/app/test_opening_session.py`
  Responsibility: opening routing and sequential target-selection flow coverage.
- Modify: `tests/adapters/presentation/test_presentation_renderer.py`
  Responsibility: opening renderer text coverage.
- Modify: `tests/adapters/textual/test_slay_app.py`
  Responsibility: Neow hover preview and Textual opening-flow coverage.
- Modify: `README.md`
  Responsibility: describe current Neow structure and intentional omissions.
- Modify: `AGENTS.md`
  Responsibility: keep repo behavior facts aligned with the implemented Neow rules.

### Task 1: Lock Down Four-Slot Neow Generation

**Files:**
- Modify: `tests/use_cases/test_opening_flow.py`
- Modify: `src/slay_the_spire/use_cases/opening_flow.py`

- [ ] **Step 1: Write the failing generation tests**

Add these tests near the top of `tests/use_cases/test_opening_flow.py`:

```python
def test_build_opening_state_generates_fixed_four_slot_neow_offers() -> None:
    provider = _provider()

    opening = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)

    assert [offer.offer_id for offer in opening.neow_offers] == [
        "card-bonus",
        "non-card-bonus",
        "tradeoff-bonus",
        "boss-relic-swap",
    ]
    assert [offer.category for offer in opening.neow_offers] == [
        "card_bonus",
        "non_card_bonus",
        "tradeoff_bonus",
        "boss_relic_swap",
    ]


def test_build_opening_state_always_includes_boss_relic_swap_offer() -> None:
    provider = _provider()

    opening = build_opening_state(seed=11, preferred_character_id="ironclad", registry=provider)
    offer = opening.neow_offers[3]

    assert offer.category == "boss_relic_swap"
    assert offer.reward_kind == "boss_relic_swap"
    assert offer.cost_kind is None
```

- [ ] **Step 2: Run the new tests to verify RED**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "fixed_four_slot or boss_relic_swap_offer" -v`

Expected: FAIL because the current code still generates `free-1`, `free-2`, `tradeoff-1`, and `tradeoff-2`.

- [ ] **Step 3: Write the minimal slot-generation implementation**

Update `src/slay_the_spire/use_cases/opening_flow.py` so `_generate_neow_offers(...)` returns fixed slots:

```python
def _generate_neow_offers(*, seed: int, run_blueprint: RunState, registry) -> list[NeowOffer]:
    character_id = run_blueprint.character_id
    rng = rng_for_room(seed=seed, room_id=f"opening:{character_id}", category="neow")
    return [
        _build_offer("card-bonus", "card_bonus", _pick_card_bonus_reward_kind(rng), registry, rng),
        _build_offer(
            "non-card-bonus",
            "non_card_bonus",
            _pick_non_card_bonus_reward_kind(rng),
            registry,
            rng,
        ),
        _build_tradeoff_offer("tradeoff-bonus", registry=registry, rng=rng),
        _build_offer("boss-relic-swap", "boss_relic_swap", "boss_relic_swap", registry, rng),
    ]
```

Add the picker/helper skeletons in the same file:

```python
def _pick_card_bonus_reward_kind(rng: Random) -> str:
    return rng.choice(["remove_card", "transform_card", "upgrade_card", "rare_card"])


def _pick_non_card_bonus_reward_kind(rng: Random) -> str:
    return rng.choice(["max_hp_gain_small", "common_relic", "gold", "triple_potion"])


def _build_tradeoff_offer(offer_id: str, *, registry, rng: Random) -> NeowOffer:
    reward_kind = rng.choice(
        [
            "remove_two_cards",
            "transform_two_cards",
            "gold_big",
            "rare_card",
            "rare_relic",
            "max_hp_gain_large",
        ]
    )
    cost_kind = rng.choice(["max_hp_loss", "hp_damage", "curse", "gold_loss_all"])
    while (cost_kind, reward_kind) in {
        ("curse", "remove_two_cards"),
        ("gold_loss_all", "gold_big"),
        ("max_hp_loss", "max_hp_gain_large"),
    }:
        reward_kind = rng.choice(
            [
                "remove_two_cards",
                "transform_two_cards",
                "gold_big",
                "rare_card",
                "rare_relic",
                "max_hp_gain_large",
            ]
        )
    return _build_offer(offer_id, "tradeoff_bonus", reward_kind, registry, rng, cost_kind=cost_kind)
```

- [ ] **Step 4: Run the tests to verify GREEN**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "fixed_four_slot or boss_relic_swap_offer" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_opening_flow.py src/slay_the_spire/use_cases/opening_flow.py
git commit -m "test: lock down Neow four-slot structure"
```

### Task 2: Implement Original-Style Reward Values and Tradeoff Constraints

**Files:**
- Modify: `tests/use_cases/test_opening_flow.py`
- Modify: `src/slay_the_spire/use_cases/opening_flow.py`

- [ ] **Step 1: Write the failing value-and-constraint tests**

Append these tests in `tests/use_cases/test_opening_flow.py`:

```python
def test_tradeoff_offer_never_uses_curse_as_reward_kind() -> None:
    provider = _provider()

    for seed in range(1, 30):
        opening = build_opening_state(seed=seed, preferred_character_id="ironclad", registry=provider)
        tradeoff = opening.neow_offers[2]
        assert tradeoff.category == "tradeoff_bonus"
        assert tradeoff.reward_kind != "curse_card"


def test_tradeoff_offer_respects_original_forbidden_pairings() -> None:
    provider = _provider()

    for seed in range(1, 60):
        opening = build_opening_state(seed=seed, preferred_character_id="ironclad", registry=provider)
        tradeoff = opening.neow_offers[2]
        assert (tradeoff.cost_kind, tradeoff.reward_kind) not in {
            ("curse", "remove_two_cards"),
            ("gold_loss_all", "gold_big"),
            ("max_hp_loss", "max_hp_gain_large"),
        }


def test_build_offer_uses_original_ironclad_neow_values() -> None:
    provider = _provider()

    small_hp = opening_flow._build_offer("small-hp", "non_card_bonus", "max_hp_gain_small", provider, Random(0))
    big_hp = opening_flow._build_offer("big-hp", "tradeoff_bonus", "max_hp_gain_large", provider, Random(0), cost_kind="hp_damage")
    gold_free = opening_flow._build_offer("free-gold", "non_card_bonus", "gold", provider, Random(0))
    gold_big = opening_flow._build_offer("big-gold", "tradeoff_bonus", "gold_big", provider, Random(0), cost_kind="hp_damage")

    assert small_hp.reward_payload["amount"] == 8
    assert big_hp.reward_payload["amount"] == 16
    assert gold_free.reward_payload["amount"] == 100
    assert gold_big.reward_payload["amount"] == 250


def test_build_offer_triple_potion_reward_contains_three_potions() -> None:
    provider = _provider()

    offer = opening_flow._build_offer("triple-potion", "non_card_bonus", "triple_potion", provider, Random(0))

    assert len(offer.reward_payload["potion_ids"]) == 3
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "curse_as_reward_kind or forbidden_pairings or original_ironclad_neow_values or triple_potion" -v`

Expected: FAIL because the current reward kinds, values, and potion payloads do not match these expectations.

- [ ] **Step 3: Write the minimal reward/cost payload implementation**

In `src/slay_the_spire/use_cases/opening_flow.py`, replace the old reward/cost branches with explicit kinds and values:

```python
def _build_reward_payload(*, reward_kind: str, registry, rng: Random) -> dict[str, object]:
    if reward_kind == "gold":
        return {"reward_id": "gold:100", "amount": 100}
    if reward_kind == "gold_big":
        return {"reward_id": "gold:250", "amount": 250}
    if reward_kind == "max_hp_gain_small":
        return {"amount": 8}
    if reward_kind == "max_hp_gain_large":
        return {"amount": 16}
    if reward_kind == "common_relic":
        relic_id = _choose_common_relic_id(registry=registry, rng=rng)
        return {"reward_id": f"relic:{relic_id}", "relic_id": relic_id}
    if reward_kind == "rare_relic":
        relic_id = _choose_boss_relic_id(registry=registry, rng=rng)
        return {"reward_id": f"relic:{relic_id}", "relic_id": relic_id}
    if reward_kind == "triple_potion":
        return {"potion_ids": [_choose_potion_id(registry=registry, rng=rng) for _ in range(3)]}
    if reward_kind == "boss_relic_swap":
        relic_id = _choose_boss_relic_id(registry=registry, rng=rng)
        return {"reward_id": f"relic:{relic_id}", "relic_id": relic_id}
    if reward_kind == "rare_card":
        card_id = _choose_rare_card_id(registry=registry, rng=rng)
        return {"reward_id": f"card:{card_id}", "card_id": card_id}
    if reward_kind in {"upgrade_card", "remove_card", "transform_card", "remove_two_cards", "transform_two_cards"}:
        return {"action": reward_kind}
    raise ValueError(f"unsupported reward_kind: {reward_kind}")


def _build_cost_payload(*, reward_kind: str, rng: Random, cost_kind: str | None = None) -> tuple[str | None, dict[str, object]]:
    resolved_cost_kind = cost_kind
    if resolved_cost_kind is None:
        return None, {}
    if resolved_cost_kind == "max_hp_loss":
        return resolved_cost_kind, {"amount": 8}
    if resolved_cost_kind == "hp_damage":
        return resolved_cost_kind, {"formula": "current_hp_30_percent"}
    if resolved_cost_kind == "curse":
        return resolved_cost_kind, {"card_id": "doubt"}
    if resolved_cost_kind == "gold_loss_all":
        return resolved_cost_kind, {"mode": "all"}
    raise ValueError(f"unsupported cost_kind: {resolved_cost_kind}")
```

Update `_build_description(...)` and `_describe_cost(...)` in the same file so menu summaries and stored detail lines match the new reward kinds:

```python
summary_map = {
    "gold": "获得 100 金币",
    "gold_big": "获得 250 金币",
    "common_relic": "获得普通遗物",
    "rare_relic": "获得稀有遗物",
    "triple_potion": "获得 3 瓶药水",
    "rare_card": "获得稀有牌",
    "max_hp_gain_small": "最大生命 +8",
    "max_hp_gain_large": "最大生命 +16",
    "upgrade_card": "升级 1 张牌",
    "remove_card": "移除 1 张牌",
    "transform_card": "变形 1 张牌",
    "remove_two_cards": "移除 2 张牌",
    "transform_two_cards": "变形 2 张牌",
    "boss_relic_swap": "替换起始遗物为随机 Boss 遗物",
}
```

```python
if cost_kind == "max_hp_loss":
    return f"失去 {cost_payload['amount']} 点最大生命"
if cost_kind == "hp_damage":
    return "失去当前生命的 30%"
if cost_kind == "gold_loss_all":
    return "失去全部金币"
if cost_kind == "curse":
    return f"牌组中加入诅咒牌：{cost_payload['card_id']}"
```

Update `_build_offer(...)` to accept `cost_kind: str | None = None` and compute `requires_target` like this:

```python
requires_target_map = {
    "upgrade_card": "upgrade_card",
    "remove_card": "remove_card",
    "transform_card": "transform_card",
    "remove_two_cards": "remove_two_cards",
    "transform_two_cards": "transform_two_cards",
}
requires_target = requires_target_map.get(reward_kind)
```

- [ ] **Step 4: Run the tests to verify GREEN**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "curse_as_reward_kind or forbidden_pairings or original_ironclad_neow_values or triple_potion" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_opening_flow.py src/slay_the_spire/use_cases/opening_flow.py
git commit -m "feat: align Neow reward values and tradeoffs"
```

### Task 3: Apply Non-Target Rewards, Costs, and Boss Relic Swap Correctly

**Files:**
- Modify: `tests/use_cases/test_opening_flow.py`
- Modify: `src/slay_the_spire/use_cases/opening_flow.py`

- [ ] **Step 1: Write the failing application tests**

Add these tests in `tests/use_cases/test_opening_flow.py`:

```python
def test_apply_neow_offer_adds_three_potions_for_non_card_bonus() -> None:
    provider = _provider()
    opening = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("triple-potion", "non_card_bonus", "triple_potion", provider, Random(0))
    opening = replace(opening, neow_offers=[offer])

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider)

    assert updated.run_blueprint is not None
    assert len(updated.run_blueprint.potions) == 3


def test_apply_neow_offer_replaces_burning_blood_with_boss_relic() -> None:
    provider = _provider()
    opening = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("boss-relic-swap", "boss_relic_swap", "boss_relic_swap", provider, Random(0))
    opening = replace(opening, neow_offers=[offer])

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider)

    assert updated.run_blueprint is not None
    assert "burning_blood" not in updated.run_blueprint.relics
    assert str(offer.reward_payload["relic_id"]) in updated.run_blueprint.relics


def test_apply_neow_offer_applies_max_hp_gain_and_loss_with_clamp() -> None:
    provider = _provider()
    opening = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("hp-offer", "tradeoff_bonus", "max_hp_gain_large", provider, Random(0), cost_kind="max_hp_loss")
    opening = replace(opening, neow_offers=[offer])

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider)

    assert updated.run_blueprint is not None
    assert updated.run_blueprint.max_hp == 88
    assert updated.run_blueprint.current_hp == 88


def test_apply_neow_offer_hp_damage_uses_current_hp_formula() -> None:
    provider = _provider()
    opening = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("damage-offer", "tradeoff_bonus", "gold_big", provider, Random(0), cost_kind="hp_damage")
    opening = replace(opening, neow_offers=[offer])

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider)

    assert updated.run_blueprint is not None
    assert updated.run_blueprint.current_hp == 56


def test_apply_neow_offer_gold_loss_all_sets_gold_to_zero_before_reward() -> None:
    provider = _provider()
    opening = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("rare-card-offer", "tradeoff_bonus", "rare_card", provider, Random(0), cost_kind="gold_loss_all")
    opening = replace(opening, neow_offers=[offer])

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider)

    assert updated.run_blueprint is not None
    assert updated.run_blueprint.gold == 0
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "three_potions_for_non_card_bonus or replaces_burning_blood_with_boss_relic or max_hp_gain_and_loss_with_clamp or hp_damage_uses_current_hp_formula or gold_loss_all_sets_gold_to_zero" -v`

Expected: FAIL because the current application logic only supports the old single-potion, old cost semantics, and no boss relic swap branch.

- [ ] **Step 3: Write the minimal reward-application implementation**

In `src/slay_the_spire/use_cases/opening_flow.py`, update `_apply_cost(...)`:

```python
def _apply_cost(run_blueprint: RunState, *, offer: NeowOffer) -> RunState:
    if offer.cost_kind == "max_hp_loss":
        amount = int(offer.cost_payload["amount"])
        next_max_hp = max(1, run_blueprint.max_hp - amount)
        return replace(run_blueprint, max_hp=next_max_hp, current_hp=min(run_blueprint.current_hp, next_max_hp))
    if offer.cost_kind == "hp_damage":
        amount = (run_blueprint.current_hp // 10) * 3
        return replace(run_blueprint, current_hp=max(1, run_blueprint.current_hp - amount))
    if offer.cost_kind == "gold_loss_all":
        return replace(run_blueprint, gold=0)
    if offer.cost_kind == "curse":
        card_id = str(offer.cost_payload["card_id"])
        return replace(run_blueprint, deck=[*run_blueprint.deck, _next_instance_id(run_blueprint.deck, card_id)])
    return run_blueprint
```

Update `_apply_reward(...)` with new branches:

```python
if reward_kind == "triple_potion":
    potion_ids = [str(potion_id) for potion_id in reward_payload["potion_ids"]]
    return replace(run_blueprint, potions=[*run_blueprint.potions, *potion_ids])
if reward_kind in {"max_hp_gain_small", "max_hp_gain_large"}:
    amount = int(reward_payload["amount"])
    return replace(
        run_blueprint,
        max_hp=run_blueprint.max_hp + amount,
        current_hp=run_blueprint.current_hp + amount,
    )
if reward_kind == "common_relic":
    return apply_reward(run_state=run_blueprint, reward_id=str(reward_payload["reward_id"]), registry=registry)
if reward_kind == "rare_relic":
    return apply_reward(run_state=run_blueprint, reward_id=str(reward_payload["reward_id"]), registry=registry)
if reward_kind == "boss_relic_swap":
    relic_id = str(reward_payload["relic_id"])
    relics = [existing for existing in run_blueprint.relics if existing != "burning_blood"]
    if relic_id not in relics:
        relics.append(relic_id)
    return replace(run_blueprint, relics=relics)
```

Add `_choose_common_relic_id(...)` and `_choose_boss_relic_id(...)` helpers using current registry metadata:

```python
def _choose_common_relic_id(*, registry, rng: Random) -> str:
    relic_ids = [
        relic.id
        for relic in registry.relics().all()
        if relic.id not in {"burning_blood", "black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer", "circlet"}
        and relic.replaces_relic_id is None
        and not relic.blocks_gold_gain
        and not relic.disabled_actions
    ]
    return rng.choice(relic_ids)


def _choose_boss_relic_id(*, registry, rng: Random) -> str:
    relic_ids = [
        relic.id
        for relic in registry.relics().all()
        if relic.id in {"black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"}
    ]
    return rng.choice(relic_ids)
```

- [ ] **Step 4: Run the tests to verify GREEN**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "three_potions_for_non_card_bonus or replaces_burning_blood_with_boss_relic or max_hp_gain_and_loss_with_clamp or hp_damage_uses_current_hp_formula or gold_loss_all_sets_gold_to_zero" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_opening_flow.py src/slay_the_spire/use_cases/opening_flow.py
git commit -m "feat: apply Neow relic and value rewards"
```

### Task 4: Add Deterministic Transform Support in Opening Flow

**Files:**
- Modify: `tests/use_cases/test_opening_flow.py`
- Modify: `src/slay_the_spire/use_cases/opening_flow.py`

- [ ] **Step 1: Write the failing transform tests**

Add these tests in `tests/use_cases/test_opening_flow.py`:

```python
def test_apply_neow_offer_requests_target_for_transform_card() -> None:
    provider = _provider()
    opening = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("transform-one", "card_bonus", "transform_card", provider, Random(0))
    opening = replace(opening, neow_offers=[offer])

    pending = apply_neow_offer(opening, offer.offer_id, registry=provider)

    assert pending.pending_neow_offer_id == offer.offer_id


def test_apply_neow_offer_transforms_one_card_deterministically() -> None:
    provider = _provider()
    opening = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("transform-one", "card_bonus", "transform_card", provider, Random(0))
    opening = replace(opening, neow_offers=[offer])
    target_card_instance_id = opening.run_blueprint.deck[0]

    first = apply_neow_offer(opening, offer.offer_id, registry=provider, target_card_instance_id=target_card_instance_id)
    second = apply_neow_offer(opening, offer.offer_id, registry=provider, target_card_instance_id=target_card_instance_id)

    assert first.run_blueprint is not None
    assert second.run_blueprint is not None
    assert first.run_blueprint.deck == second.run_blueprint.deck
    assert target_card_instance_id not in first.run_blueprint.deck


def test_transformed_card_is_not_curse_status_or_same_base_id() -> None:
    provider = _provider()
    opening = build_opening_state(seed=7, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("transform-one", "card_bonus", "transform_card", provider, Random(0))
    opening = replace(opening, neow_offers=[offer])
    target_card_instance_id = opening.run_blueprint.deck[0]
    target_card_id = target_card_instance_id.split("#", 1)[0]

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider, target_card_instance_id=target_card_instance_id)

    assert updated.run_blueprint is not None
    replacement_card_id = updated.run_blueprint.deck[0].split("#", 1)[0]
    replacement = provider.cards().get(replacement_card_id)
    assert replacement.card_type not in {"curse", "status"}
    assert replacement_card_id != target_card_id
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "transform_card" -v`

Expected: FAIL because `transform_card` does not exist yet.

- [ ] **Step 3: Write the minimal deterministic transform implementation**

In `src/slay_the_spire/use_cases/opening_flow.py`, add transform helpers:

```python
def _transform_pool(*, registry, excluded_card_id: str) -> list[str]:
    return [
        card.id
        for card in registry.cards().all()
        if card.card_type not in {"curse", "status"}
        and "combat_reward" in card.acquisition_tags
        and card.id != excluded_card_id
    ]


def _transform_card_instance(run_blueprint: RunState, *, registry, target_card_instance_id: str, offer_id: str) -> RunState:
    target_card_id = target_card_instance_id.split("#", 1)[0]
    pool = _transform_pool(registry=registry, excluded_card_id=target_card_id)
    rng = rng_for_room(seed=run_blueprint.seed, room_id=f"opening-transform:{offer_id}", category=target_card_instance_id)
    replacement_card_id = rng.choice(pool)
    replacement_instance_id = _next_instance_id(run_blueprint.deck, replacement_card_id)
    deck = [
        replacement_instance_id if card_instance_id == target_card_instance_id else card_instance_id
        for card_instance_id in run_blueprint.deck
    ]
    return replace(run_blueprint, deck=deck)
```

Then wire `_apply_reward(...)`:

```python
if reward_kind == "transform_card":
    if target_card_instance_id is None:
        return run_blueprint
    return _transform_card_instance(
        run_blueprint,
        registry=registry,
        target_card_instance_id=target_card_instance_id,
        offer_id=offer.offer_id,
    )
```

Update `_validate_target_for_offer(...)` so `transform_card` accepts any card currently in the deck.

- [ ] **Step 4: Run the tests to verify GREEN**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "transform_card" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_opening_flow.py src/slay_the_spire/use_cases/opening_flow.py
git commit -m "feat: add deterministic Neow transform reward"
```

### Task 5: Extend Opening State and Session Routing for Sequential Two-Target Offers

**Files:**
- Modify: `tests/app/test_opening_session.py`
- Modify: `src/slay_the_spire/app/opening_state.py`
- Modify: `src/slay_the_spire/app/session.py`
- Modify: `src/slay_the_spire/use_cases/opening_flow.py`

- [ ] **Step 1: Write the failing session-routing tests**

Add these tests in `tests/app/test_opening_session.py`:

```python
def test_opening_neow_transform_offer_routes_into_target_menu() -> None:
    session, offer = _session_with_targeted_offer(reward_kind="transform_card")

    running, target_session, _message = route_menu_choice("1", session=session)

    assert running is True
    assert target_session.run_phase == "opening"
    assert target_session.menu_state.mode == "opening_neow_transform_card"
    assert target_session.opening_state.pending_neow_offer_id == offer.offer_id


def test_opening_neow_remove_two_cards_stays_in_opening_until_second_pick() -> None:
    session, _offer = _session_with_targeted_offer(reward_kind="remove_two_cards")

    _running, first_target_session, _message = route_menu_choice("1", session=session)
    running, second_target_session, _message = route_menu_choice("1", session=first_target_session)

    assert running is True
    assert second_target_session.run_phase == "opening"
    assert second_target_session.menu_state.mode == "opening_neow_remove_card"
    assert second_target_session.opening_state.pending_neow_offer_id is not None


def test_opening_neow_remove_two_cards_completes_after_second_pick() -> None:
    session, _offer = _session_with_targeted_offer(reward_kind="remove_two_cards")

    _running, first_target_session, _message = route_menu_choice("1", session=session)
    _running, second_target_session, _message = route_menu_choice("1", session=first_target_session)
    running, next_session, _message = route_menu_choice("1", session=second_target_session)

    assert running is True
    assert next_session.run_phase == "active"
    assert next_session.opening_state is None


def test_opening_neow_transform_two_cards_completes_after_second_pick() -> None:
    session, _offer = _session_with_targeted_offer(reward_kind="transform_two_cards")

    _running, first_target_session, _message = route_menu_choice("1", session=session)
    _running, second_target_session, _message = route_menu_choice("1", session=first_target_session)
    running, next_session, _message = route_menu_choice("1", session=second_target_session)

    assert running is True
    assert next_session.run_phase == "active"
    assert next_session.opening_state is None
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `uv run pytest tests/app/test_opening_session.py -k "transform_offer_routes or remove_two_cards or transform_two_cards" -v`

Expected: FAIL because the current menu state only knows upgrade/remove single-target flows.

- [ ] **Step 3: Extend opening state and routing minimally**

In `src/slay_the_spire/app/opening_state.py`, add pending-target memory:

```python
@dataclass(slots=True)
class OpeningState:
    seed: int
    available_character_ids: list[str]
    selected_character_id: str | None
    run_blueprint: RunState | None
    neow_offers: list[NeowOffer] = field(default_factory=list)
    pending_neow_offer_id: str | None = None
    pending_neow_targets: list[str] = field(default_factory=list)
    resolved_neow_offer_ids: list[str] = field(default_factory=list)
```

In `src/slay_the_spire/app/session.py`, extend menu modes and routing. First, update `_route_opening_neow_target_menu(...)` to accept multiple valid target kinds instead of a single string:

```python
def _route_opening_neow_target_menu(
    choice: str,
    session: SessionState,
    *,
    expected_targets: tuple[str, ...],
    action_prefix: str,
) -> tuple[bool, SessionState, str]:
```

Inside the function, replace the exact-match check with:

```python
if offer is None or offer.requires_target not in expected_targets:
    fallback_session = _opening_neow_offer_session(session, opening_state)
    return True, fallback_session, _message_with_render(fallback_session, "Neow 选项已失效，已返回主菜单。")
```

Then extend the menu-mode selection logic:

```python
if offer is not None and offer.requires_target in {"upgrade_card"}:
    next_mode = "opening_neow_upgrade_card"
elif offer is not None and offer.requires_target in {"remove_card", "remove_two_cards"}:
    next_mode = "opening_neow_remove_card"
elif offer is not None and offer.requires_target in {"transform_card", "transform_two_cards"}:
    next_mode = "opening_neow_transform_card"
```

Add a new menu branch in `build_opening_action_menu(...)`:

```python
if session.menu_state.mode == "opening_neow_transform_card":
    return _build_opening_target_card_menu(
        session,
        title="选择要变形的卡牌",
        action_prefix="transform_card",
        upgrade_only=False,
    )
```

Update the main router near the end of `route_menu_choice(...)` to dispatch:

```python
if next_session.menu_state.mode == "opening_neow_upgrade_card":
    return _route_opening_neow_target_menu(
        choice.strip(),
        next_session,
        expected_targets=("upgrade_card",),
        action_prefix="upgrade_card",
    )
if next_session.menu_state.mode == "opening_neow_remove_card":
    return _route_opening_neow_target_menu(
        choice.strip(),
        next_session,
        expected_targets=("remove_card", "remove_two_cards"),
        action_prefix="remove_card",
    )
if next_session.menu_state.mode == "opening_neow_transform_card":
    return _route_opening_neow_target_menu(
        choice.strip(),
        next_session,
        expected_targets=("transform_card", "transform_two_cards"),
        action_prefix="transform_card",
    )
```

In `src/slay_the_spire/use_cases/opening_flow.py`, update `apply_neow_offer(...)` so two-target rewards append the first selected card to `pending_neow_targets`, update the `run_blueprint`, and return to pending mode until enough targets have been chosen.

- [ ] **Step 4: Run the tests to verify GREEN**

Run: `uv run pytest tests/app/test_opening_session.py -k "transform_offer_routes or remove_two_cards or transform_two_cards" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/app/test_opening_session.py src/slay_the_spire/app/opening_state.py src/slay_the_spire/app/session.py src/slay_the_spire/use_cases/opening_flow.py
git commit -m "feat: support multi-step Neow target flows"
```

### Task 6: Finish Two-Target Reward Application and Validation

**Files:**
- Modify: `tests/use_cases/test_opening_flow.py`
- Modify: `src/slay_the_spire/use_cases/opening_flow.py`

- [ ] **Step 1: Write the failing two-target application tests**

Add these tests in `tests/use_cases/test_opening_flow.py`:

```python
def test_apply_neow_offer_remove_two_cards_tracks_first_target_then_finishes() -> None:
    provider = _provider()
    opening = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("remove-two", "tradeoff_bonus", "remove_two_cards", provider, Random(0), cost_kind="hp_damage")
    opening = replace(opening, neow_offers=[offer])
    first_target = opening.run_blueprint.deck[0]
    second_target = opening.run_blueprint.deck[1]

    pending = apply_neow_offer(opening, offer.offer_id, registry=provider, target_card_instance_id=first_target)
    completed = apply_neow_offer(pending, offer.offer_id, registry=provider, target_card_instance_id=second_target)

    assert pending.pending_neow_targets == [first_target]
    assert completed.run_blueprint is not None
    assert first_target not in completed.run_blueprint.deck
    assert second_target not in completed.run_blueprint.deck


def test_apply_neow_offer_transform_two_cards_tracks_first_target_then_finishes() -> None:
    provider = _provider()
    opening = build_opening_state(seed=7, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("transform-two", "tradeoff_bonus", "transform_two_cards", provider, Random(0), cost_kind="hp_damage")
    opening = replace(opening, neow_offers=[offer])
    first_target = opening.run_blueprint.deck[0]
    second_target = opening.run_blueprint.deck[1]

    pending = apply_neow_offer(opening, offer.offer_id, registry=provider, target_card_instance_id=first_target)
    completed = apply_neow_offer(pending, offer.offer_id, registry=provider, target_card_instance_id=second_target)

    assert pending.pending_neow_targets == [first_target]
    assert completed.run_blueprint is not None
    assert len(completed.run_blueprint.deck) == len(opening.run_blueprint.deck)
    assert first_target not in completed.run_blueprint.deck
    assert second_target not in completed.run_blueprint.deck


def test_apply_neow_offer_rejects_duplicate_second_target_for_two_card_rewards() -> None:
    provider = _provider()
    opening = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("remove-two", "tradeoff_bonus", "remove_two_cards", provider, Random(0), cost_kind="hp_damage")
    opening = replace(opening, neow_offers=[offer])
    first_target = opening.run_blueprint.deck[0]

    pending = apply_neow_offer(opening, offer.offer_id, registry=provider, target_card_instance_id=first_target)

    with pytest.raises(ValueError, match="target card is not in deck"):
        apply_neow_offer(pending, offer.offer_id, registry=provider, target_card_instance_id=first_target)
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "remove_two_cards_tracks or transform_two_cards_tracks or duplicate_second_target" -v`

Expected: FAIL because the current apply path does not support sequential multi-target rewards.

- [ ] **Step 3: Implement minimal two-target state transitions**

In `src/slay_the_spire/use_cases/opening_flow.py`, update `apply_neow_offer(...)` and `_apply_reward(...)` so:

```python
if offer.requires_target in {"remove_two_cards", "transform_two_cards"}:
    chosen_targets = [*opening_state.pending_neow_targets]
    if target_card_instance_id is not None:
        chosen_targets.append(target_card_instance_id)
    required_count = 2
    run_blueprint = opening_state.run_blueprint
    if not opening_state.pending_neow_targets:
        run_blueprint = _apply_cost(run_blueprint, offer=offer)
    run_blueprint = _apply_reward(
        run_blueprint,
        offer=offer,
        registry=registry,
        target_card_instance_id=target_card_instance_id,
    )
    if len(chosen_targets) < required_count:
        return replace(
            opening_state,
            run_blueprint=run_blueprint,
            pending_neow_offer_id=offer.offer_id,
            pending_neow_targets=chosen_targets,
        )
```

Make `_apply_reward(...)` treat each target selection as a single remove/transform operation for `remove_two_cards` and `transform_two_cards`, and clear `pending_neow_targets` when the second target resolves.

Update `_validate_target_for_offer(...)` to validate `transform_card`, `remove_two_cards`, and `transform_two_cards` against the current pending `run_blueprint` deck.

- [ ] **Step 4: Run the tests to verify GREEN**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k "remove_two_cards_tracks or transform_two_cards_tracks or duplicate_second_target" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_opening_flow.py src/slay_the_spire/use_cases/opening_flow.py
git commit -m "feat: complete Neow two-card rewards"
```

### Task 7: Update Rich/Textual Opening Rendering for New Neow Semantics

**Files:**
- Modify: `tests/adapters/presentation/test_presentation_renderer.py`
- Modify: `tests/adapters/textual/test_slay_app.py`
- Modify: `src/slay_the_spire/adapters/presentation/opening_renderer.py`
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`

- [ ] **Step 1: Write the failing renderer and hover tests**

Add these tests:

In `tests/adapters/presentation/test_presentation_renderer.py`:

```python
def test_render_session_renderable_shows_boss_relic_swap_copy() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("boss-relic-swap", "boss_relic_swap", "boss_relic_swap", provider, Random(0))
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]), menu_state=MenuState(mode="opening_neow_offer"))

    console = Console(width=100, record=True, force_terminal=False, color_system=None, theme=TERMINAL_THEME)
    console.print(render_session_renderable(session))

    rendered = console.export_text(clear=False)
    assert "替换起始遗物" in rendered


def test_render_session_renderable_shows_triple_potion_count() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("triple-potion", "non_card_bonus", "triple_potion", provider, Random(0))
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]), menu_state=MenuState(mode="opening_neow_offer"))

    console = Console(width=100, record=True, force_terminal=False, color_system=None, theme=TERMINAL_THEME)
    console.print(render_session_renderable(session))

    rendered = console.export_text(clear=False)
    assert "3 瓶药水" in rendered


def test_render_session_renderable_supports_opening_transform_target_menu() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("transform-card", "card_bonus", "transform_card", provider, Random(0))
    session = replace(
        session,
        opening_state=replace(session.opening_state, neow_offers=[offer], pending_neow_offer_id=offer.offer_id),
        menu_state=MenuState(mode="opening_neow_transform_card"),
    )

    console = Console(width=100, record=True, force_terminal=False, color_system=None, theme=TERMINAL_THEME)
    console.print(render_session_renderable(session))

    rendered = console.export_text(clear=False)
    assert "选择要变形的卡牌" in rendered
```

In `tests/adapters/textual/test_slay_app.py`:

```python
def test_hover_preview_shows_boss_relic_swap_details() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("boss-relic-swap", "boss_relic_swap", "boss_relic_swap", provider, Random(0))
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]))

    preview = _hover_preview_renderable(session, f"choose_neow_offer:{offer.offer_id}")

    assert preview is not None
    assert "替换起始遗物" in preview.plain
    assert provider.relics().get(str(offer.reward_payload["relic_id"])).name in preview.plain


def test_hover_preview_shows_triple_potion_offer_details() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("triple-potion", "non_card_bonus", "triple_potion", provider, Random(0))
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]))

    preview = _hover_preview_renderable(session, f"choose_neow_offer:{offer.offer_id}")

    assert preview is not None
    assert "3 瓶药水" in preview.plain


def test_hover_preview_shows_transform_offer_guidance() -> None:
    session = start_new_game_session(seed=5, preferred_character_id="ironclad")
    provider = StarterContentProvider(session.content_root)
    offer = opening_flow._build_offer("transform-card", "card_bonus", "transform_card", provider, Random(0))
    session = replace(session, opening_state=replace(session.opening_state, neow_offers=[offer]))

    preview = _hover_preview_renderable(session, f"choose_neow_offer:{offer.offer_id}")

    assert preview is not None
    assert "变形" in preview.plain
```

- [ ] **Step 2: Run the tests to verify RED**

Run: `uv run pytest tests/adapters/presentation/test_presentation_renderer.py tests/adapters/textual/test_slay_app.py -k "boss_relic_swap_copy or triple_potion_count or boss_relic_swap_details or triple_potion_offer_details or transform_offer_guidance" -v`

Expected: FAIL because the current copy and hover branches still target old reward kinds.

- [ ] **Step 3: Update presentation and hover formatting minimally**

In `src/slay_the_spire/adapters/presentation/opening_renderer.py`, extend `format_neow_offer_detail_lines(...)`:

```python
if offer.reward_kind == "boss_relic_swap":
    relic_id = str(reward_payload["relic_id"])
    details.append(f"替换起始遗物：{registry.relics().get(relic_id).name}")
elif offer.reward_kind == "triple_potion":
    potion_names = [registry.potions().get(str(potion_id)).name for potion_id in reward_payload["potion_ids"]]
    details.append(f"获得 3 瓶药水：{'、'.join(potion_names)}")
elif offer.reward_kind == "max_hp_gain_small":
    details.append(f"最大生命 +{reward_payload['amount']}")
elif offer.reward_kind == "max_hp_gain_large":
    details.append(f"最大生命 +{reward_payload['amount']}")
elif offer.reward_kind == "common_relic":
    relic_id = str(reward_payload["relic_id"])
    details.append(f"获得普通遗物：{registry.relics().get(relic_id).name}")
elif offer.reward_kind == "rare_relic":
    relic_id = str(reward_payload["relic_id"])
    details.append(f"获得稀有遗物：{registry.relics().get(relic_id).name}")
elif offer.reward_kind == "transform_card":
    details.append("选择 1 张牌变形")
elif offer.reward_kind == "remove_two_cards":
    details.append("移除 2 张牌")
elif offer.reward_kind == "transform_two_cards":
    details.append("变形 2 张牌")
```

Also update cost copy:

```python
if offer.cost_kind == "max_hp_loss":
    details.append(f"失去 {offer.cost_payload['amount']} 点最大生命")
elif offer.cost_kind == "hp_damage":
    details.append("失去当前生命的 30%（向下取整到 10 的倍数后再乘以 3）")
elif offer.cost_kind == "gold_loss_all":
    details.append("失去全部金币")
```

In `src/slay_the_spire/adapters/presentation/opening_renderer.py`, also extend `render_opening_screen(...)` with:

```python
elif menu_mode == "opening_neow_transform_card":
    body = _target_card_panel(opening_state, registry=registry, title="选择要变形的卡牌", target_kind="transform_card")
```

In `src/slay_the_spire/adapters/textual/slay_app.py`, extend `_CARD_PREVIEW_MENU_MODES`, `_hover_preview_guidance(...)`, and `_format_neow_offer_hover_lines(...)` for `opening_neow_transform_card`, `boss_relic_swap`, `triple_potion`, `transform_card`, `remove_two_cards`, and `transform_two_cards`.

- [ ] **Step 4: Run the tests to verify GREEN**

Run: `uv run pytest tests/adapters/presentation/test_presentation_renderer.py tests/adapters/textual/test_slay_app.py -k "boss_relic_swap_copy or triple_potion_count or boss_relic_swap_details or triple_potion_offer_details or transform_offer_guidance" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/adapters/presentation/test_presentation_renderer.py tests/adapters/textual/test_slay_app.py src/slay_the_spire/adapters/presentation/opening_renderer.py src/slay_the_spire/adapters/textual/slay_app.py
git commit -m "feat: update Neow opening copy and previews"
```

### Task 8: Update README and AGENTS Facts

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Write the failing documentation diff locally**

Update `README.md` bullets under "当前实现" and the opening notes so they describe:

```md
- 当前 opening 的 `Neow` 采用接近原版的固定四槽结构：卡牌奖励、非卡牌奖励、风险换高收益、替换起始遗物为随机 Boss 遗物
- 当前 `Neow` 已支持升级/移除/变形牌，以及两次连续选择目标的双移除/双变形奖励
- 当前 `Neow` 暂未实现 `Neow's Lament`，部分原版三选一职业牌/无色牌奖励仍使用本项目的最小简化实现
```

Update `AGENTS.md` "当前功能事实" opening bullets to describe the same facts, replacing the outdated line that says opening only has `opening_neow_upgrade_card` and `opening_neow_remove_card` target menus.

- [ ] **Step 2: Verify the doc changes are present**

Run: `uv run pytest tests/use_cases/test_opening_flow.py tests/app/test_opening_session.py tests/adapters/presentation/test_presentation_renderer.py tests/adapters/textual/test_slay_app.py -q`

Expected: PASS. This is the safety check before the docs are committed.

- [ ] **Step 3: Commit**

```bash
git add README.md AGENTS.md
git commit -m "docs: document aligned Neow opening rules"
```

### Task 9: Full Verification

**Files:**
- Modify: none
- Test: `tests/use_cases/test_opening_flow.py`
- Test: `tests/app/test_opening_session.py`
- Test: `tests/adapters/presentation/test_presentation_renderer.py`
- Test: `tests/adapters/textual/test_slay_app.py`

- [ ] **Step 1: Run focused opening verification**

Run: `uv run pytest tests/use_cases/test_opening_flow.py tests/app/test_opening_session.py tests/adapters/presentation/test_presentation_renderer.py tests/adapters/textual/test_slay_app.py -v`

Expected: PASS.

- [ ] **Step 2: Run full project verification**

Run: `uv run pytest`

Expected: PASS.

- [ ] **Step 3: Review git status before handoff**

Run: `git status --short`

Expected: only the intended implementation, tests, docs, and plan/spec files are modified.
