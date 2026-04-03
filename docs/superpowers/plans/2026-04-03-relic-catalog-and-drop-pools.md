# Relic Catalog And Drop Pools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the full Slay the Spire 1 relic catalog in `content/`, extend relic metadata/schema, and replace the current hard-coded relic reward sources with run-persisted relic pool sequences.

**Architecture:** Expand `RelicDef` so content can describe rarity, pools, character restrictions, implementation state, and future effect blueprints while keeping existing executable fields for already-working relics. Add run-level relic sequences to `RunState`, drive shop/treasure/elite/boss/opening relic selection from those sequences, and back the change with content, save/load, renderer, wiki, and regression tests.

**Tech Stack:** Python 3.12, pytest, textual, `uv`, JSON content files under `content/`

---

### Task 1: Extend Relic Schema And Registry Validation

**Files:**
- Modify: `src/slay_the_spire/content/registries.py`
- Modify: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing registry schema tests**

```python
@pytest.mark.parametrize("content_root", _content_roots())
def test_relic_catalog_exposes_new_metadata_fields(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    burning_blood = provider.relics().get("burning_blood")

    assert burning_blood.rarity == "starter"
    assert "starter" in burning_blood.pools
    assert "starting_relic" in burning_blood.source_tags
    assert burning_blood.owner_character_ids == ["ironclad"]
    assert burning_blood.implementation_status == "implemented"
    assert isinstance(burning_blood.effect_blueprint, list)


@pytest.mark.parametrize("content_root", _content_roots())
def test_relic_catalog_rejects_invalid_metadata_enums(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    relic = provider.relics().get("burning_blood")
    assert relic.rarity in {
        "starter",
        "common",
        "uncommon",
        "rare",
        "shop",
        "boss",
        "event",
        "special",
    }
    assert relic.implementation_status in {"implemented", "partial", "placeholder"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -k relic_catalog -v`
Expected: FAIL because `RelicDef` does not expose `rarity`, `pools`, `source_tags`, `owner_character_ids`, `implementation_status`, or `effect_blueprint`.

- [ ] **Step 3: Write minimal registry implementation**

```python
@dataclass(slots=True, frozen=True)
class RelicDef:
    id: str
    name: str
    trigger_hooks: list[str]
    passive_effects: list[JsonDict]
    summary: str | None = None
    description: str | None = None
    replaces_relic_id: str | None = None
    disabled_actions: list[str] = field(default_factory=list)
    blocks_gold_gain: bool = False
    can_appear_in_shop: bool = True
    rarity: str = "special"
    pools: list[str] = field(default_factory=list)
    source_tags: list[str] = field(default_factory=list)
    owner_character_ids: list[str] = field(default_factory=list)
    implementation_status: str = "placeholder"
    effect_blueprint: list[JsonDict] = field(default_factory=list)
    flavor_text: str | None = None


class RelicRegistry(_BaseRegistry[RelicDef]):
    def register(self, data: Mapping[str, object]) -> None:
        rarity = _require_optional_str(data.get("rarity"), "rarity") or "special"
        implementation_status = (
            _require_optional_str(data.get("implementation_status"), "implementation_status")
            or "placeholder"
        )
        if rarity not in _ALLOWED_RELIC_RARITIES:
            raise ValueError(f"unsupported relic rarity: {rarity}")
        if implementation_status not in _ALLOWED_RELIC_IMPLEMENTATION_STATUSES:
            raise ValueError(
                f"unsupported relic implementation_status: {implementation_status}"
            )

        relic = RelicDef(
            id=_require_str(data.get("id"), "id"),
            name=_require_str(data.get("name"), "name"),
            trigger_hooks=_require_optional_str_list(data.get("trigger_hooks"), "trigger_hooks"),
            passive_effects=_require_optional_json_dict_list(data.get("passive_effects"), "passive_effects"),
            summary=_require_optional_str(data.get("summary"), "summary"),
            description=_require_optional_str(data.get("description"), "description"),
            replaces_relic_id=_require_optional_str(data.get("replaces_relic_id"), "replaces_relic_id"),
            disabled_actions=_require_optional_str_list(data.get("disabled_actions"), "disabled_actions"),
            blocks_gold_gain=_require_optional_bool(data.get("blocks_gold_gain"), "blocks_gold_gain") or False,
            can_appear_in_shop=_require_optional_bool(data.get("can_appear_in_shop"), "can_appear_in_shop") or False,
            rarity=rarity,
            pools=_require_optional_str_list(data.get("pools"), "pools"),
            source_tags=_require_optional_str_list(data.get("source_tags"), "source_tags"),
            owner_character_ids=_require_optional_str_list(data.get("owner_character_ids"), "owner_character_ids"),
            implementation_status=implementation_status,
            effect_blueprint=_require_optional_json_dict_list(data.get("effect_blueprint"), "effect_blueprint"),
            flavor_text=_require_optional_str(data.get("flavor_text"), "flavor_text"),
        )
        self._items[relic.id] = relic
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/content/test_registry_validation.py -k relic_catalog -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/content/test_registry_validation.py src/slay_the_spire/content/registries.py
git commit -m "feat: extend relic content schema"
```

### Task 2: Add RunState Relic Sequence Persistence

**Files:**
- Modify: `src/slay_the_spire/domain/models/run_state.py`
- Modify: `src/slay_the_spire/use_cases/start_run.py`
- Modify: `src/slay_the_spire/use_cases/save_game.py`
- Modify: `src/slay_the_spire/use_cases/load_game.py`
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `tests/use_cases/test_save_load.py`
- Modify: `tests/use_cases/test_apply_reward.py`
- Modify: `tests/use_cases/test_enter_room.py`

- [ ] **Step 1: Write the failing run-state and save/load tests**

```python
def test_start_new_run_initializes_relic_sequences() -> None:
    provider = _content_provider()

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert set(run_state.relic_sequences) == {"common", "uncommon", "rare", "shop", "boss"}
    assert set(run_state.relic_sequence_positions) == {"common", "uncommon", "rare", "shop", "boss"}
    assert all(position == 0 for position in run_state.relic_sequence_positions.values())
    assert all(run_state.relic_sequences[pool] for pool in run_state.relic_sequences)


def test_build_save_document_persists_relic_sequence_state() -> None:
    run_state = replace(
        start_new_run("ironclad", seed=7, registry=_content_provider()),
        relic_sequence_positions={"common": 2, "uncommon": 1, "rare": 0, "shop": 0, "boss": 0},
    )

    document = build_save_document(run_state=run_state, act_state=None, room_state=None)

    assert document["run_state"]["relic_sequences"] == run_state.relic_sequences
    assert document["run_state"]["relic_sequence_positions"] == run_state.relic_sequence_positions
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_start_run.py tests/use_cases/test_save_load.py -k relic_sequence -v`
Expected: FAIL because `RunState` has no relic sequence fields and save/load does not persist them.

- [ ] **Step 3: Write minimal implementation**

```python
SCHEMA_VERSION = 2


@dataclass(slots=True, kw_only=True)
class RunState:
    schema_version: ClassVar[int] = SCHEMA_VERSION
    seed: int
    character_id: str
    current_act_id: str | None
    current_hp: int = 80
    max_hp: int = 80
    gold: int = 99
    deck: list[str] = field(default_factory=list)
    relics: list[str] = field(default_factory=list)
    potions: list[str] = field(default_factory=list)
    seen_event_ids: list[str] = field(default_factory=list)
    card_removal_count: int = 0
    rare_card_reward_offset: int = -5
    relic_sequences: dict[str, list[str]] = field(default_factory=dict)
    relic_sequence_positions: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "character_id": self.character_id,
            "current_act_id": self.current_act_id,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "gold": self.gold,
            "deck": list(self.deck),
            "relics": list(self.relics),
            "potions": list(self.potions),
            "seen_event_ids": list(self.seen_event_ids),
            "card_removal_count": self.card_removal_count,
            "rare_card_reward_offset": self.rare_card_reward_offset,
            "relic_sequences": {pool: list(ids) for pool, ids in self.relic_sequences.items()},
            "relic_sequence_positions": dict(self.relic_sequence_positions),
        }


def _build_relic_sequences(*, character_id: str, seed: int, registry: ContentProviderPort) -> tuple[dict[str, list[str]], dict[str, int]]:
    pool_ids = ["common", "uncommon", "rare", "shop", "boss"]
    sequences: dict[str, list[str]] = {}
    for index, pool_id in enumerate(pool_ids, start=1):
        eligible_ids = sorted(
            relic.id
            for relic in registry.relics().all()
            if pool_id in relic.pools and (not relic.owner_character_ids or character_id in relic.owner_character_ids)
        )
        rng = Random(f"{seed}:{character_id}:{pool_id}:{index}")
        rng.shuffle(eligible_ids)
        sequences[pool_id] = eligible_ids
    return sequences, {pool_id: 0 for pool_id in pool_ids}


def start_new_run(character_id: str, seed: int, registry: ContentProviderPort) -> RunState:
    character = registry.characters().get(character_id)
    _ensure_act_loaded(character, registry, seed)
    relic_sequences, relic_sequence_positions = _build_relic_sequences(
        character_id=character.id,
        seed=seed,
        registry=registry,
    )
    return RunState(
        seed=seed,
        character_id=character.id,
        current_act_id=character.starting_act_id,
        current_hp=80,
        max_hp=80,
        gold=99,
        deck=_build_card_instance_ids(list(character.starter_deck)),
        relics=list(character.starter_relic_ids),
        potions=[],
        card_removal_count=0,
        relic_sequences=relic_sequences,
        relic_sequence_positions=relic_sequence_positions,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_start_run.py tests/use_cases/test_save_load.py -k relic_sequence -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_start_run.py tests/use_cases/test_save_load.py src/slay_the_spire/domain/models/run_state.py src/slay_the_spire/use_cases/start_run.py src/slay_the_spire/use_cases/save_game.py src/slay_the_spire/use_cases/load_game.py
git commit -m "feat: persist run relic sequences"
```

### Task 3: Replace Shop And Treasure Relic Selection With Pool-Based Sequences

**Files:**
- Modify: `src/slay_the_spire/use_cases/enter_room.py`
- Modify: `tests/use_cases/test_start_run.py`
- Modify: `tests/use_cases/test_enter_room.py`
- Modify: `tests/use_cases/test_apply_reward.py`

- [ ] **Step 1: Write the failing room entry tests**

```python
def test_enter_room_shop_payload_uses_shop_pool_sequence() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)

    room_state = enter_room(run_state, act_state, node_id=_node_id_for_room_type(act_state, "shop"), registry=provider)

    offered_relics = [item["relic_id"] for item in room_state.payload["relics"]]
    assert offered_relics
    assert all("shop" in provider.relics().get(relic_id).pools for relic_id in offered_relics)


def test_treasure_candidate_pool_uses_relic_rarity_sequences() -> None:
    registry = _content_provider()
    run_state = start_new_run("ironclad", seed=13, registry=registry)
    room_state = enter_room(
        run_state,
        _act_state(node_id="r1c0", room_type="treasure"),
        "r1c0",
        registry,
    )

    treasure_relic_id = room_state.payload["treasure_relic_id"]
    assert registry.relics().get(treasure_relic_id).rarity in {"common", "uncommon", "rare", "special"}
    assert "shop" not in registry.relics().get(treasure_relic_id).pools
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_start_run.py tests/use_cases/test_enter_room.py -k "shop_pool_sequence or treasure_candidate_pool" -v`
Expected: FAIL because shop still uses `can_appear_in_shop` and treasure still uses the non-shop catch-all list.

- [ ] **Step 3: Write minimal implementation**

```python
def _next_relic_from_sequence(*, run_state: RunState, pool_id: str) -> str | None:
    sequence = run_state.relic_sequences.get(pool_id, [])
    position = run_state.relic_sequence_positions.get(pool_id, 0)
    while position < len(sequence):
        relic_id = sequence[position]
        position += 1
        run_state.relic_sequence_positions[pool_id] = position
        if relic_id not in run_state.relics:
            return relic_id
    return None


def _choose_treasure_relic_id(*, run_state: RunState, room_id: str) -> str:
    rarity = _roll_relic_rarity(room_id=room_id, seed=run_state.seed)
    relic_id = _next_relic_from_sequence(run_state=run_state, pool_id=rarity)
    return relic_id or _TREASURE_FALLBACK_RELIC_ID


def _build_shop_payload(run_state: RunState, *, room_id: str, registry: ContentProviderPort) -> dict[str, object]:
    card_ids = [card.id for card in registry.cards().all() if "shop" in card.acquisition_tags]
    potion_ids = [potion.id for potion in registry.potions().all()]
    card_rng = _offer_rng(run_state, room_id, "cards")
    potion_rng = _offer_rng(run_state, room_id, "potions")
    shop_relic_id = _next_relic_from_sequence(run_state=run_state, pool_id="shop") or _TREASURE_FALLBACK_RELIC_ID
    relics = [{"offer_id": "relic-1", "relic_id": shop_relic_id, "price": 150}]
    cards = [
        {"offer_id": f"card-{index}", "card_id": card_id, "price": 60}
        for index, card_id in enumerate(_sample_ids(card_ids, count=3, rng=card_rng), start=1)
    ]
    potions = [
        {"offer_id": f"potion-{index}", "potion_id": potion_id, "price": 60}
        for index, potion_id in enumerate(_sample_ids(potion_ids, count=2, rng=potion_rng), start=1)
    ]
    return {
        "cards": cards,
        "relics": relics,
        "potions": potions,
        "remove_price": 75 + (run_state.card_removal_count * 25),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_start_run.py tests/use_cases/test_enter_room.py -k "shop_pool_sequence or treasure_candidate_pool" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_start_run.py tests/use_cases/test_enter_room.py src/slay_the_spire/use_cases/enter_room.py
git commit -m "feat: drive shop and treasure relics from sequences"
```

### Task 4: Replace Elite And Boss Rewards With Sequence-Based Pools

**Files:**
- Modify: `src/slay_the_spire/domain/rewards/reward_generator.py`
- Modify: `tests/use_cases/test_apply_reward.py`
- Modify: `tests/use_cases/test_room_recovery.py`
- Modify: `tests/e2e/test_single_act_smoke.py`
- Modify: `tests/e2e/test_two_act_smoke.py`
- Modify: `tests/use_cases/test_start_run.py`

- [ ] **Step 1: Write the failing reward generator tests**

```python
def test_generate_boss_rewards_returns_three_unique_boss_pool_relics() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=37, registry=provider)
    rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=run_state,
        registry=provider,
    )

    assert len(rewards["boss_relic_offers"]) == 3
    assert len(set(rewards["boss_relic_offers"])) == 3
    assert all("boss" in provider.relics().get(relic_id).pools for relic_id in rewards["boss_relic_offers"])


def test_generate_combat_rewards_elite_grants_sequence_driven_relic() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=37, registry=provider)
    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:elite_reward",
        run_state=run_state,
        registry=provider,
        room_type="elite",
    )

    relic_rewards = [reward for reward in rewards if reward.startswith("relic:")]
    assert len(relic_rewards) == 1
    relic_id = relic_rewards[0].split(":", 1)[1]
    assert provider.relics().get(relic_id).rarity in {"common", "uncommon", "rare", "special"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -k "boss_pool_relics or elite_grants_sequence_driven_relic" -v`
Expected: FAIL because `_BOSS_RELIC_OFFERS` and `_ELITE_RELIC_OFFERS` are still hard-coded.

- [ ] **Step 3: Write minimal implementation**

```python
def _next_reward_relic(run_state: RunState, *, pool_id: str) -> str | None:
    sequence = run_state.relic_sequences.get(pool_id, [])
    position = run_state.relic_sequence_positions.get(pool_id, 0)
    while position < len(sequence):
        relic_id = sequence[position]
        position += 1
        run_state.relic_sequence_positions[pool_id] = position
        if relic_id not in run_state.relics:
            return relic_id
    return None


def _elite_relic_reward(*, run_state: RunState, registry: ContentProviderPort, seed: int, room_id: str) -> str | None:
    rarity = _roll_relic_rarity(room_id=room_id, seed=seed)
    relic_id = _next_reward_relic(run_state, pool_id=rarity)
    if relic_id is None:
        relic_id = "circlet"
    return f"relic:{relic_id}"


def generate_boss_rewards(*, room_id: str, seed: int, run_state: RunState, registry: ContentProviderPort) -> dict[str, object]:
    offers: list[str] = []
    while len(offers) < 3:
        relic_id = _next_reward_relic(run_state, pool_id="boss") or "circlet"
        if relic_id not in offers:
            offers.append(relic_id)
    return {
        "generated_by": "boss_reward_generator",
        "gold_reward": 90 + (seed % 21),
        "claimed_gold": False,
        "boss_relic_offers": offers,
        "claimed_relic_id": None,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_apply_reward.py -k "boss_pool_relics or elite_grants_sequence_driven_relic" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_apply_reward.py tests/use_cases/test_room_recovery.py tests/e2e/test_single_act_smoke.py tests/e2e/test_two_act_smoke.py src/slay_the_spire/domain/rewards/reward_generator.py
git commit -m "feat: replace relic reward hardcoding with sequences"
```

### Task 5: Move Opening/Neow Random Relics To The New Pool Model

**Files:**
- Modify: `src/slay_the_spire/use_cases/opening_flow.py`
- Modify: `tests/use_cases/test_opening_flow.py`

- [ ] **Step 1: Write the failing opening-flow test**

```python
def test_choose_relic_id_uses_allowed_neow_pool_metadata() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=5, registry=provider)

    relic_id = _choose_relic_id(registry=provider, rng=Random(5), run_state=run_state)

    relic = provider.relics().get(relic_id)
    assert "neow" in relic.pools
    assert not relic.owner_character_ids or run_state.character_id in relic.owner_character_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k allowed_neow_pool_metadata -v`
Expected: FAIL because `_choose_relic_id` still filters by replacement, gold blocking, and disabled actions instead of pool metadata.

- [ ] **Step 3: Write minimal implementation**

```python
def _choose_relic_id(*, registry, rng: Random, run_state: RunState) -> str:
    relic_ids = [
        relic.id
        for relic in registry.relics().all()
        if "neow" in relic.pools
        and (not relic.owner_character_ids or run_state.character_id in relic.owner_character_ids)
    ]
    return rng.choice(sorted(relic_ids))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/use_cases/test_opening_flow.py -k allowed_neow_pool_metadata -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/use_cases/test_opening_flow.py src/slay_the_spire/use_cases/opening_flow.py
git commit -m "feat: align neow relic selection with relic pools"
```

### Task 6: Add Full Relic Content Files And Metadata

**Files:**
- Modify: `content/relics/starter_relics.json`
- Modify: `content/relics/shop_relics.json`
- Modify: `content/relics/boss_relics.json`
- Create: `content/relics/common_relics.json`
- Create: `content/relics/uncommon_relics.json`
- Create: `content/relics/rare_relics.json`
- Create: `content/relics/event_relics.json`
- Create: `content/relics/special_relics.json`
- Modify: `content/characters/ironclad.json`
- Modify: `tests/content/test_registry_validation.py`

- [ ] **Step 1: Write the failing content coverage tests**

```python
@pytest.mark.parametrize("content_root", _content_roots())
def test_relic_catalog_contains_full_base_game_relic_inventory(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    relic_ids = {relic.id for relic in provider.relics().all()}

    assert len(relic_ids) >= 180
    assert {"akabeko", "anchor", "bag_of_preparation", "oddly_smooth_stone", "bird_faced_urn", "burning_blood", "black_blood", "golden_idol", "circlet"}.issubset(relic_ids)


@pytest.mark.parametrize("content_root", _content_roots())
def test_all_relics_have_localized_summary_and_description(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    for relic in provider.relics().all():
        assert relic.name
        assert relic.summary
        assert relic.description
        assert relic.pools
        assert relic.effect_blueprint is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/content/test_registry_validation.py -k "full_base_game_relic_inventory or localized_summary" -v`
Expected: FAIL because only a small subset of relics is present and most entries lack the new metadata.

- [ ] **Step 3: Write minimal content updates**

```json
{
  "relics": [
    {
      "id": "anchor",
      "name": "船锚",
      "summary": "每场战斗开始时获得 10 点格挡。",
      "description": "每场战斗开始时，获得 10 点格挡。",
      "rarity": "common",
      "pools": ["common", "treasure", "elite_reward", "neow"],
      "source_tags": ["elite", "chest", "neow_bonus"],
      "owner_character_ids": [],
      "implementation_status": "placeholder",
      "effect_blueprint": [{"type": "combat_start_block", "amount": 10}],
      "trigger_hooks": [],
      "passive_effects": []
    }
  ]
}
```

Populate every relic file with the same schema, using these conventions:

- `starter_relics.json`: all starter relics, with `owner_character_ids` filled for character-specific starters.
- `common_relics.json`, `uncommon_relics.json`, `rare_relics.json`: all non-boss relics that belong to the standard rarity pools.
- `shop_relics.json`: shop-only relics.
- `boss_relics.json`: boss-only relics.
- `event_relics.json`: event-only relics like `golden_idol` and other event rewards.
- `special_relics.json`: `circlet` and any nonstandard fallback/special relics.
- Set `implementation_status` to `implemented` for already-working relics like `burning_blood`, `black_blood`, `ectoplasm`, `coffee_dripper`, `fusion_hammer`, `frozen_eye`, `blood_vial`, `golden_idol`, `guarding_totem`, and `circlet`.
- Set `implementation_status` to `placeholder` for newly recorded relics whose runtime behavior is not yet wired.

If the starter relic split changes the effective starter relic pool file name, update `content/characters/ironclad.json` so `starter_relic_pool_id` still references a loaded pool.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/content/test_registry_validation.py -k "full_base_game_relic_inventory or localized_summary" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add content/relics/*.json tests/content/test_registry_validation.py
git commit -m "feat: add full base-game relic catalog"
```

### Task 7: Update Inspect, Textual Preview, And Local Wiki Output

**Files:**
- Modify: `src/slay_the_spire/adapters/presentation/inspect.py`
- Modify: `src/slay_the_spire/adapters/textual/slay_app.py`
- Modify: `scripts/generate_local_wiki.py`
- Modify: `tests/adapters/presentation/test_inspect.py`
- Modify: `tests/adapters/textual/test_slay_app.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing renderer and wiki tests**

```python
def test_format_reward_detail_lines_include_relic_metadata_labels() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    relic_lines = format_reward_detail_lines("relic:black_blood", registry)

    assert any("分类" in line.plain for line in relic_lines)
    assert any("实现状态" in line.plain for line in relic_lines)


def test_hover_preview_shows_relic_implementation_status() -> None:
    base = start_session(seed=5)
    session = replace(
        base,
        room_state=replace(
            base.room_state,
            room_type="shop",
            stage="waiting_input",
            is_resolved=False,
            payload={
                "cards": [],
                "relics": [{"offer_id": "relic-1", "relic_id": "black_blood", "price": 150}],
                "potions": [],
                "remove_price": 75,
            },
        ),
        menu_state=replace(base.menu_state, mode="shop_root"),
    )

    preview = _hover_preview_renderable(session, "buy_relic")
    assert "实现状态" in preview.plain
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/adapters/presentation/test_inspect.py tests/adapters/textual/test_slay_app.py -k "relic_metadata_labels or implementation_status" -v`
Expected: FAIL because the renderers do not show rarity/pools/status and the wiki script still groups relics by legacy file names.

- [ ] **Step 3: Write minimal implementation**

```python
def _append_relic_metadata(lines: list[str], relic_def: RelicDef) -> None:
    lines.append(f"分类: {relic_def.rarity}")
    lines.append(f"来源池: {' / '.join(relic_def.pools) if relic_def.pools else '-'}")
    lines.append(f"实现状态: {relic_def.implementation_status}")


def _relic_rules(relic: RelicDef, provider: StarterContentProvider) -> str:
    rules: list[str] = []
    if relic.summary:
        rules.append(f"摘要：{relic.summary}")
    if relic.description:
        rules.append(f"描述：{relic.description}")
    rules.append(f"分类：{relic.rarity}")
    rules.append(f"实现状态：{relic.implementation_status}")
    if relic.pools:
        rules.append(f"掉落池：{' / '.join(relic.pools)}")
    return "；".join(rules)
```

Also update `README.md` with two specific changes:

- In the feature summary, say that relic data now records the full base-game relic catalog even though runtime effects are still being implemented in batches.
- In the local wiki/documentation section, mention that the generated wiki now includes relic rarity/pool/status metadata and still refreshes via `uv run python scripts/generate_local_wiki.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/adapters/presentation/test_inspect.py tests/adapters/textual/test_slay_app.py -k "relic_metadata_labels or implementation_status" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/adapters/presentation/test_inspect.py tests/adapters/textual/test_slay_app.py src/slay_the_spire/adapters/presentation/inspect.py src/slay_the_spire/adapters/textual/slay_app.py scripts/generate_local_wiki.py README.md
git commit -m "docs: expose relic metadata in previews and wiki"
```

### Task 8: Run Full Verification And Regenerate Wiki

**Files:**
- Modify: `docs/local_wiki/cards_and_relics.md`

- [ ] **Step 1: Run the full targeted test suite**

Run: `uv run pytest tests/content/test_registry_validation.py tests/use_cases/test_start_run.py tests/use_cases/test_enter_room.py tests/use_cases/test_apply_reward.py tests/use_cases/test_save_load.py tests/use_cases/test_opening_flow.py tests/adapters/presentation/test_inspect.py tests/adapters/textual/test_slay_app.py tests/e2e/test_single_act_smoke.py tests/e2e/test_two_act_smoke.py -v`
Expected: PASS.

- [ ] **Step 2: Regenerate the local wiki**

Run: `uv run python scripts/generate_local_wiki.py`
Expected: `docs/local_wiki/cards_and_relics.md` updates with the full relic inventory, new categories, and implementation-status details.

- [ ] **Step 3: Run the wiki-related smoke check**

Run: `uv run pytest tests/content/test_registry_validation.py -k relic -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/local_wiki/cards_and_relics.md
git commit -m "chore: regenerate local wiki for relic catalog"
```
