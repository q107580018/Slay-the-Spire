from __future__ import annotations

from pathlib import Path

import pytest

from slay_the_spire.content.catalog import WeightedPoolEntry
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.effects.effect_resolver import resolve_effect_queue
from slay_the_spire.domain.hooks.hook_dispatcher import dispatch_hook
from slay_the_spire.domain.hooks.runtime import build_runtime_hook_registrations
from slay_the_spire.domain.models.act_state import ActNodeState, ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import PlayerCombatState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.rewards.reward_generator import generate_combat_rewards
from slay_the_spire.use_cases import enter_room as enter_room_module
from slay_the_spire.use_cases.enter_room import enter_room


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


class _EncounterMissingProvider:
    def __init__(self, delegate: StarterContentProvider) -> None:
        self._delegate = delegate

    def __getattr__(self, name: str):
        return getattr(self._delegate, name)

    def encounter_pool_entries(self, pool_id: str):
        raise KeyError(pool_id)


class _SingleEncounterProvider:
    def __init__(self, delegate: StarterContentProvider, *, encounter_id: str) -> None:
        self._delegate = delegate
        self._encounter_id = encounter_id

    def __getattr__(self, name: str):
        return getattr(self._delegate, name)

    def encounter_pool_entries(self, pool_id: str):
        if pool_id != "act1_basic":
            return self._delegate.encounter_pool_entries(pool_id)
        return tuple(
            entry
            for entry in self._delegate.encounter_pool_entries(pool_id)
            if entry.member_id == self._encounter_id
        )


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


class _RelicRegistryWithLimitedTreasureCandidates:
    def __init__(self, delegate, *, candidate_ids: list[str]) -> None:
        self._delegate = delegate
        self._candidate_ids = candidate_ids

    def all(self):
        return [self._delegate.get(relic_id) for relic_id in self._candidate_ids]

    def get(self, relic_id: str):
        return self._delegate.get(relic_id)


class _LimitedTreasureCandidateProvider:
    def __init__(
        self, delegate: StarterContentProvider, *, candidate_ids: list[str]
    ) -> None:
        self._delegate = delegate
        self._candidate_ids = candidate_ids

    def __getattr__(self, name: str):
        return getattr(self._delegate, name)

    def relics(self):
        return _RelicRegistryWithLimitedTreasureCandidates(
            self._delegate.relics(),
            candidate_ids=self._candidate_ids,
        )


def _run_state(
    *,
    seed: int,
    seen_event_ids: list[str] | None = None,
    relics: list[str] | None = None,
    relic_sequences: dict[str, list[str]] | None = None,
    relic_sequence_positions: dict[str, int] | None = None,
    current_hp: int = 80,
    max_hp: int = 80,
) -> RunState:
    return RunState(
        seed=seed,
        character_id="ironclad",
        current_act_id="act1",
        current_hp=current_hp,
        max_hp=max_hp,
        gold=99,
        deck=[],
        relics=["burning_blood"] if relics is None else relics,
        potions=[],
        card_removal_count=0,
        seen_event_ids=[] if seen_event_ids is None else seen_event_ids,
        relic_sequences={} if relic_sequences is None else relic_sequences,
        relic_sequence_positions=(
            {} if relic_sequence_positions is None else relic_sequence_positions
        ),
    )


def _act_state(
    *, node_id: str, room_type: str, next_node_ids: list[str] | None = None
) -> ActState:
    resolved_next_node_ids = [] if next_node_ids is None else list(next_node_ids)
    return ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(
                node_id="start",
                row=0,
                col=0,
                room_type="combat",
                next_node_ids=[node_id],
            ),
            ActNodeState(
                node_id=node_id,
                row=1,
                col=0,
                room_type=room_type,
                next_node_ids=resolved_next_node_ids,
            ),
            *[
                ActNodeState(
                    node_id=next_node_id,
                    row=2,
                    col=index,
                    room_type="combat",
                    next_node_ids=[],
                )
                for index, next_node_id in enumerate(resolved_next_node_ids)
            ],
        ],
        visited_node_ids=[],
        enemy_pool_id="act1_basic",
        elite_pool_id="act1_elites",
        boss_pool_id="act1_bosses",
        event_pool_id="act1_events",
    )


def test_enter_combat_room_uses_weighted_encounter_pool_entries() -> None:
    room_state = enter_room(
        _run_state(seed=7),
        _act_state(node_id="r1c0", room_type="combat"),
        "r1c0",
        _content_provider(),
    )

    assert room_state.payload["encounter_id"] in {
        "single_red_louse",
        "single_green_louse",
        "pair_louses",
        "cultist",
        "single_jaw_worm",
        "double_slime",
    }

    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.enemies


def test_enter_room_builds_multiple_enemy_states_from_encounter() -> None:
    room_state = enter_room(
        _run_state(seed=37),
        _act_state(node_id="r1c0", room_type="combat"),
        "r1c0",
        _SingleEncounterProvider(_content_provider(), encounter_id="double_slime"),
    )

    assert room_state.payload["encounter_id"] == "double_slime"

    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert len(combat_state.enemies) == 2
    assert [enemy.enemy_id for enemy in combat_state.enemies] == ["slime", "slime"]
    assert all(enemy.instance_id.startswith("enemy-") for enemy in combat_state.enemies)


def test_enter_room_switches_to_late_pool_after_three_prior_combat_rooms() -> None:
    room_state = enter_room(
        _run_state(seed=7),
        ActState(
            act_id="act1",
            current_node_id="r3c0",
            nodes=[
                ActNodeState(
                    node_id="start",
                    row=0,
                    col=0,
                    room_type="combat",
                    next_node_ids=["r1c0"],
                ),
                ActNodeState(
                    node_id="r1c0",
                    row=1,
                    col=0,
                    room_type="combat",
                    next_node_ids=["r2c0"],
                ),
                ActNodeState(
                    node_id="r2c0",
                    row=2,
                    col=0,
                    room_type="combat",
                    next_node_ids=["r3c0"],
                ),
                ActNodeState(
                    node_id="r3c0", row=3, col=0, room_type="combat", next_node_ids=[]
                ),
            ],
            visited_node_ids=["start", "r1c0", "r2c0"],
            enemy_pool_id="act1_basic",
            elite_pool_id="act1_elites",
            boss_pool_id="act1_bosses",
            event_pool_id="act1_events",
        ),
        "r3c0",
        _content_provider(),
    )

    assert room_state.payload["encounter_id"] in {
        "single_slime",
        "single_acid_slime",
        "blue_slaver",
        "red_slaver",
        "looter",
        "fungi_beast",
        "gremlin_gang_no_fat",
        "gremlin_gang_no_mad",
        "gremlin_gang_no_shield",
        "gremlin_gang_no_sneaky",
        "gremlin_gang_no_wizard",
    }


def test_enter_room_shop_cards_come_from_shop_tagged_cards() -> None:
    provider = _content_provider()
    room_state = enter_room(
        _run_state(seed=7),
        _act_state(node_id="shop-1", room_type="shop"),
        "shop-1",
        provider,
    )

    offered_cards = [item["card_id"] for item in room_state.payload["cards"]]

    assert offered_cards
    assert all(
        "shop" in provider.cards().get(card_id).acquisition_tags
        for card_id in offered_cards
    )
    assert "burn" not in offered_cards
    assert "doubt" not in offered_cards
    assert "injury" not in offered_cards


def test_enter_room_does_not_fallback_to_enemy_pool_when_encounter_pool_is_missing() -> (
    None
):
    with pytest.raises(KeyError, match="act1_basic"):
        enter_room(
            _run_state(seed=7),
            _act_state(node_id="r1c0", room_type="combat"),
            "r1c0",
            _EncounterMissingProvider(_content_provider()),
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


def test_enter_room_raises_when_no_encounter_entries_match_combat_count() -> None:
    with pytest.raises(ValueError, match="no encounter entries match combat count"):
        enter_room(
            _run_state(seed=7),
            ActState(
                act_id="act1",
                current_node_id="r3c0",
                nodes=[
                    ActNodeState(
                        node_id="start",
                        row=0,
                        col=0,
                        room_type="combat",
                        next_node_ids=["r1c0"],
                    ),
                    ActNodeState(
                        node_id="r1c0",
                        row=1,
                        col=0,
                        room_type="combat",
                        next_node_ids=["r2c0"],
                    ),
                    ActNodeState(
                        node_id="r2c0",
                        row=2,
                        col=0,
                        room_type="combat",
                        next_node_ids=["r3c0"],
                    ),
                    ActNodeState(
                        node_id="r3c0",
                        row=3,
                        col=0,
                        room_type="combat",
                        next_node_ids=[],
                    ),
                ],
                visited_node_ids=["start", "r1c0", "r2c0"],
                enemy_pool_id="act1_basic",
                elite_pool_id="act1_elites",
                boss_pool_id="act1_bosses",
                event_pool_id="act1_events",
            ),
            "r3c0",
            _SingleEncounterProvider(
                _content_provider(), encounter_id="single_red_louse"
            ),
        )


def test_enter_event_room_uses_weighted_event_pool_entries() -> None:
    room_state = enter_room(
        _run_state(seed=37),
        _act_state(node_id="r1c0", room_type="event"),
        "r1c0",
        _content_provider(),
    )

    assert room_state.payload["event_id"] == "shining_light"


def test_enter_event_room_skips_once_per_run_events_already_seen() -> None:
    room_state = enter_room(
        _run_state(seed=37, seen_event_ids=["shining_light"]),
        _act_state(node_id="r1c0", room_type="event"),
        "r1c0",
        _content_provider(),
    )

    assert room_state.payload["event_id"] == "the_cleric"


def test_enter_treasure_room_generates_deterministic_relic_payload_and_keeps_next_nodes() -> (
    None
):
    first_room = enter_room(
        _run_state(seed=13),
        _act_state(
            node_id="r1c0", room_type="treasure", next_node_ids=["r2c0", "r2c1"]
        ),
        "r1c0",
        _content_provider(),
    )
    second_room = enter_room(
        _run_state(seed=13),
        _act_state(
            node_id="r1c0", room_type="treasure", next_node_ids=["r2c0", "r2c1"]
        ),
        "r1c0",
        _content_provider(),
    )

    assert first_room.room_type == "treasure"
    assert first_room.payload["next_node_ids"] == ["r2c0", "r2c1"]
    assert (
        first_room.payload["treasure_relic_id"]
        == second_room.payload["treasure_relic_id"]
    )


def test_enter_treasure_room_skips_owned_relics_from_candidate_pool() -> None:
    room_state = enter_room(
        _run_state(seed=13, relics=["burning_blood", "golden_idol"]),
        _act_state(node_id="r1c0", room_type="treasure"),
        "r1c0",
        _content_provider(),
    )

    assert room_state.payload["treasure_relic_id"] not in {
        "burning_blood",
        "golden_idol",
    }


def test_enter_treasure_room_uses_rolled_rarity_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        enter_room_module,
        "_roll_treasure_relic_rarity",
        lambda *, room_id, seed: "uncommon",
        raising=False,
    )

    run_state = _run_state(
        seed=13,
        relic_sequences={
            "common": ["anchor"],
            "uncommon": ["oddly_smooth_stone"],
            "rare": ["bird_faced_urn"],
        },
        relic_sequence_positions={"common": 0, "uncommon": 0, "rare": 0},
    )

    room_state = enter_room(
        run_state,
        _act_state(node_id="r1c0", room_type="treasure"),
        "r1c0",
        _content_provider(),
    )

    assert room_state.payload["treasure_relic_id"] == "oddly_smooth_stone"
    assert run_state.relic_sequence_positions == {
        "common": 0,
        "uncommon": 1,
        "rare": 0,
    }


def test_enter_treasure_room_does_not_leak_owner_locked_relics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        enter_room_module,
        "_roll_treasure_relic_rarity",
        lambda *, room_id, seed: "rare",
        raising=False,
    )
    provider = _LimitedTreasureCandidateProvider(
        _content_provider(),
        candidate_ids=["circlet", "emotion_chip"],
    )

    room_state = enter_room(
        _run_state(
            seed=13,
            relic_sequences={
                "common": [],
                "uncommon": [],
                "rare": ["bird_faced_urn"],
            },
            relic_sequence_positions={"common": 0, "uncommon": 0, "rare": 0},
        ),
        _act_state(node_id="r1c0", room_type="treasure"),
        "r1c0",
        provider,
    )

    assert room_state.payload["treasure_relic_id"] == "bird_faced_urn"


def test_enter_treasure_room_is_stable_for_unresolved_reentry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        enter_room_module,
        "_roll_treasure_relic_rarity",
        lambda *, room_id, seed: "uncommon",
        raising=False,
    )
    run_state = _run_state(
        seed=13,
        relic_sequences={
            "common": ["anchor"],
            "uncommon": ["oddly_smooth_stone"],
            "rare": ["bird_faced_urn"],
        },
        relic_sequence_positions={"common": 0, "uncommon": 0, "rare": 0},
    )

    act_state = _act_state(node_id="r1c0", room_type="treasure")

    first_room = enter_room(run_state, act_state, "r1c0", _content_provider())
    second_room = enter_room(run_state, act_state, "r1c0", _content_provider())

    assert first_room.payload["treasure_relic_id"] == "oddly_smooth_stone"
    assert second_room.payload["treasure_relic_id"] == "oddly_smooth_stone"
    assert run_state.relic_sequence_positions == {"common": 0, "uncommon": 1, "rare": 0}


def test_enter_treasure_room_falls_back_to_circlet_when_no_relic_candidates_remain() -> (
    None
):
    room_state = enter_room(
        _run_state(
            seed=13,
            relics=[
                "burning_blood",
                "blood_vial",
                "golden_idol",
                "guarding_totem",
                "circlet",
                "black_blood",
                "ectoplasm",
                "coffee_dripper",
                "fusion_hammer",
            ],
        ),
        _act_state(node_id="r1c0", room_type="treasure"),
        "r1c0",
        _content_provider(),
    )

    assert room_state.payload["treasure_relic_id"] == "circlet"
    assert room_state.is_resolved is False


def test_enter_treasure_room_uses_other_rarity_relics_before_circlet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        enter_room_module,
        "_roll_treasure_relic_rarity",
        lambda *, room_id, seed: "rare",
        raising=False,
    )

    run_state = _run_state(
        seed=13,
        relic_sequences={
            "common": ["anchor"],
            "uncommon": ["oddly_smooth_stone"],
            "rare": [],
        },
        relic_sequence_positions={"common": 0, "uncommon": 0, "rare": 0},
    )

    room_state = enter_room(
        run_state,
        _act_state(node_id="r1c0", room_type="treasure"),
        "r1c0",
        _content_provider(),
    )

    assert room_state.payload["treasure_relic_id"] == "oddly_smooth_stone"
    assert run_state.relic_sequence_positions == {
        "common": 0,
        "uncommon": 1,
        "rare": 0,
    }


def test_black_star_adds_extra_relic_after_elite_combat() -> None:
    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:elite_reward",
        run_state=_run_state(
            seed=13,
            relics=["burning_blood", "black_star"],
            relic_sequences={
                "common": ["anchor", "bag_of_marbles"],
                "uncommon": ["oddly_smooth_stone"],
                "rare": ["bird_faced_urn"],
            },
            relic_sequence_positions={"common": 0, "uncommon": 0, "rare": 0},
        ),
        registry=_content_provider(),
        room_type="elite",
    )

    relic_rewards = [reward for reward in rewards if reward.startswith("relic:")]

    assert len(relic_rewards) == 2


def test_preserved_insect_reduces_elite_enemy_hp_by_quarter() -> None:
    room_state = enter_room(
        _run_state(seed=7, relics=["burning_blood", "preserved_insect"]),
        _act_state(node_id="elite-1", room_type="elite"),
        "elite-1",
        _content_provider(),
    )

    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert all(enemy.hp == enemy.max_hp for enemy in combat_state.enemies)
    assert all(
        enemy.max_hp < _content_provider().enemies().get(enemy.enemy_id).hp
        for enemy in combat_state.enemies
    )


def test_ssserpent_head_adds_fifty_gold_when_entering_event_room() -> None:
    run_state = _run_state(seed=37, relics=["burning_blood", "ssserpent_head"])

    enter_room(
        run_state,
        _act_state(node_id="event-1", room_type="event"),
        "event-1",
        _content_provider(),
    )

    assert run_state.gold == 149


def test_matryoshka_only_affects_next_two_treasure_rooms() -> None:
    run_state = _run_state(
        seed=13,
        relics=["burning_blood", "matryoshka"],
        relic_sequences={
            "common": ["anchor", "bag_of_marbles", "lantern"],
            "uncommon": ["oddly_smooth_stone"],
            "rare": ["bird_faced_urn"],
        },
        relic_sequence_positions={"common": 0, "uncommon": 0, "rare": 0},
    )

    first_room = enter_room(
        run_state,
        _act_state(node_id="r1c0", room_type="treasure"),
        "r1c0",
        _content_provider(),
    )
    second_room = enter_room(
        run_state,
        _act_state(node_id="r2c0", room_type="treasure"),
        "r2c0",
        _content_provider(),
    )
    third_room = enter_room(
        run_state,
        _act_state(node_id="r3c0", room_type="treasure"),
        "r3c0",
        _content_provider(),
    )

    assert first_room.payload["treasure_relic_ids"] == ["anchor", "bag_of_marbles"]
    assert second_room.payload["treasure_relic_ids"] == [
        "lantern",
        "oddly_smooth_stone",
    ]
    assert "treasure_relic_ids" not in third_room.payload
    assert run_state.relic_sequence_positions["matryoshka_chests_opened"] == 2


def test_event_node_resolves_to_combat_room_without_juzu_bracelet() -> None:
    provider = _content_provider()
    room_state = enter_room(
        _run_state(seed=7),
        _act_state(node_id="event-1", room_type="event"),
        "event-1",
        provider,
    )

    assert room_state.payload["room_kind"] == "event"
    assert room_state.payload["resolved_room_kind"] in {"event", "combat", "treasure"}
    if room_state.payload["resolved_room_kind"] == "combat":
        assert room_state.room_type == "combat"
        assert "combat_state" in room_state.payload


def test_juzu_bracelet_prevents_event_node_from_resolving_to_combat() -> None:
    provider = _content_provider()

    for seed in range(1, 50):
        room_state = enter_room(
            _run_state(seed=seed, relics=["burning_blood", "juzu_bracelet"]),
            _act_state(node_id="event-1", room_type="event"),
            "event-1",
            provider,
        )
        assert room_state.payload["resolved_room_kind"] in {"event", "treasure"}


def test_tiny_chest_turns_every_fourth_event_node_into_treasure() -> None:
    provider = _content_provider()
    run_state = _run_state(seed=11, relics=["burning_blood", "tiny_chest"])

    first = enter_room(
        run_state,
        _act_state(node_id="event-1", room_type="event"),
        "event-1",
        provider,
    )
    second = enter_room(
        run_state,
        _act_state(node_id="event-2", room_type="event"),
        "event-2",
        provider,
    )
    third = enter_room(
        run_state,
        _act_state(node_id="event-3", room_type="event"),
        "event-3",
        provider,
    )
    fourth = enter_room(
        run_state,
        _act_state(node_id="event-4", room_type="event"),
        "event-4",
        provider,
    )

    assert first.payload["resolved_room_kind"] in {"event", "combat", "treasure"}
    assert second.payload["resolved_room_kind"] in {"event", "combat", "treasure"}
    assert third.payload["resolved_room_kind"] in {"event", "combat", "treasure"}
    assert fourth.room_type == "treasure"
    assert fourth.payload["resolved_room_kind"] == "treasure"
    assert run_state.relic_sequence_positions["tiny_chest_counter"] == 0


def test_tiny_chest_marks_counter_when_entering_event_room() -> None:
    act_state = _act_state(node_id="event-1", room_type="event")
    run_state = _run_state(seed=37, relics=["burning_blood", "tiny_chest"])

    enter_room(run_state, act_state, "event-1", _content_provider())

    assert act_state.room_payloads["act1:event-1"]["tiny_chest_counter"] == 1


def test_tiny_chest_event_room_reentry_keeps_original_room_payload() -> None:
    act_state = _act_state(
        node_id="event-1", room_type="event", next_node_ids=["r2c0", "r2c1"]
    )
    run_state = _run_state(seed=37, relics=["burning_blood", "tiny_chest"])

    first_room = enter_room(run_state, act_state, "event-1", _content_provider())
    second_room = enter_room(run_state, act_state, "event-1", _content_provider())

    assert first_room.payload["node_id"] == "event-1"
    assert first_room.payload["next_node_ids"] == ["r2c0", "r2c1"]
    assert first_room.payload["resolved_room_kind"] == "event"
    assert "event_id" in first_room.payload
    assert act_state.room_payloads["act1:event-1"] == {
        **first_room.payload,
        "tiny_chest_counter": 1,
    }
    assert second_room.payload == first_room.payload


def test_enter_combat_room_applies_blood_vial_on_combat_start() -> None:
    room_state = enter_room(
        _run_state(
            seed=7, relics=["burning_blood", "blood_vial"], current_hp=70, max_hp=80
        ),
        _act_state(node_id="r1c0", room_type="combat"),
        "r1c0",
        _content_provider(),
    )

    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.player.hp == 72


def test_enter_combat_room_applies_guarding_totem_on_combat_start() -> None:
    room_state = enter_room(
        _run_state(seed=7, relics=["burning_blood", "guarding_totem"]),
        _act_state(node_id="r1c0", room_type="combat"),
        "r1c0",
        _content_provider(),
    )

    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.player.block == 10


def test_enter_combat_room_applies_anchor_only_once() -> None:
    room_state = enter_room(
        _run_state(seed=7, relics=["burning_blood", "anchor"]),
        _act_state(node_id="r1c0", room_type="combat"),
        "r1c0",
        _content_provider(),
    )

    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.player.block == 10


def test_burning_blood_heals_six_after_combat() -> None:
    provider = _content_provider()
    state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-ironclad", hp=40, max_hp=80, block=0, statuses=[]
        ),
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
        player=PlayerCombatState(
            instance_id="player-ironclad", hp=40, max_hp=80, block=0, statuses=[]
        ),
        enemies=[],
        effect_queue=[],
        log=[],
    )
    run_state = _run_state(seed=7, relics=["black_blood"], current_hp=40, max_hp=80)
    registrations = build_runtime_hook_registrations(run_state, provider)

    dispatch_hook(state, "on_combat_end", registrations)
    resolve_effect_queue(state, hook_registrations=registrations)

    assert state.player.hp == 52


def test_enter_room_places_innate_cards_into_opening_hand_first() -> None:
    # seed=42 with 8-card deck places brutality_plus#2 at position 6 after shuffle,
    # so without innate ordering it would NOT be in the opening 5-card hand.
    # brutality_plus is already in the content registry with innate=True.
    provider = _content_provider()
    run_state = RunState(
        seed=42,
        character_id="ironclad",
        current_act_id="act1",
        current_hp=80,
        max_hp=80,
        gold=99,
        deck=[
            "strike#1",
            "brutality_plus#2",
            "defend#3",
            "bash#4",
            "strike#5",
            "defend#6",
            "strike#7",
            "defend#8",
        ],
        relics=["burning_blood"],
        potions=[],
        card_removal_count=0,
        seen_event_ids=[],
    )
    act_state = _act_state(node_id="r1c0", room_type="combat")

    room_state = enter_room(run_state, act_state, "r1c0", provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert "brutality_plus#2" in combat_state.hand
