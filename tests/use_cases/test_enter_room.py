from __future__ import annotations

from pathlib import Path

import pytest

from slay_the_spire.content.catalog import WeightedPoolEntry
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.act_state import ActNodeState, ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.use_cases.enter_room import _TREASURE_RELIC_CANDIDATE_IDS, enter_room


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


def _run_state(
    *,
    seed: int,
    seen_event_ids: list[str] | None = None,
    relics: list[str] | None = None,
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
    )


def _act_state(*, node_id: str, room_type: str, next_node_ids: list[str] | None = None) -> ActState:
    resolved_next_node_ids = [] if next_node_ids is None else list(next_node_ids)
    return ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=[node_id]),
            ActNodeState(node_id=node_id, row=1, col=0, room_type=room_type, next_node_ids=resolved_next_node_ids),
            *[
                ActNodeState(node_id=next_node_id, row=2, col=index, room_type="combat", next_node_ids=[])
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
                ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=["r1c0"]),
                ActNodeState(node_id="r1c0", row=1, col=0, room_type="combat", next_node_ids=["r2c0"]),
                ActNodeState(node_id="r2c0", row=2, col=0, room_type="combat", next_node_ids=["r3c0"]),
                ActNodeState(node_id="r3c0", row=3, col=0, room_type="combat", next_node_ids=[]),
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
    assert all("shop" in provider.cards().get(card_id).acquisition_tags for card_id in offered_cards)
    assert "burn" not in offered_cards
    assert "doubt" not in offered_cards
    assert "injury" not in offered_cards


def test_enter_room_does_not_fallback_to_enemy_pool_when_encounter_pool_is_missing() -> None:
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
                    ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=["r1c0"]),
                    ActNodeState(node_id="r1c0", row=1, col=0, room_type="combat", next_node_ids=["r2c0"]),
                    ActNodeState(node_id="r2c0", row=2, col=0, room_type="combat", next_node_ids=["r3c0"]),
                    ActNodeState(node_id="r3c0", row=3, col=0, room_type="combat", next_node_ids=[]),
                ],
                visited_node_ids=["start", "r1c0", "r2c0"],
                enemy_pool_id="act1_basic",
                elite_pool_id="act1_elites",
                boss_pool_id="act1_bosses",
                event_pool_id="act1_events",
            ),
            "r3c0",
            _SingleEncounterProvider(_content_provider(), encounter_id="single_red_louse"),
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


def test_enter_treasure_room_generates_deterministic_relic_payload_and_keeps_next_nodes() -> None:
    first_room = enter_room(
        _run_state(seed=13),
        _act_state(node_id="r1c0", room_type="treasure", next_node_ids=["r2c0", "r2c1"]),
        "r1c0",
        _content_provider(),
    )
    second_room = enter_room(
        _run_state(seed=13),
        _act_state(node_id="r1c0", room_type="treasure", next_node_ids=["r2c0", "r2c1"]),
        "r1c0",
        _content_provider(),
    )

    assert first_room.room_type == "treasure"
    assert first_room.payload["next_node_ids"] == ["r2c0", "r2c1"]
    assert first_room.payload["treasure_relic_id"] == second_room.payload["treasure_relic_id"]


def test_enter_treasure_room_skips_owned_relics_from_candidate_pool() -> None:
    room_state = enter_room(
        _run_state(seed=13, relics=["burning_blood", "golden_idol"]),
        _act_state(node_id="r1c0", room_type="treasure"),
        "r1c0",
        _content_provider(),
    )

    assert room_state.payload["treasure_relic_id"] not in {"burning_blood", "golden_idol"}


def test_enter_combat_room_applies_blood_vial_on_combat_start() -> None:
    room_state = enter_room(
        _run_state(seed=7, relics=["burning_blood", "blood_vial"], current_hp=70, max_hp=80),
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


def test_treasure_candidate_pool_matches_content_boundary_assumptions() -> None:
    registry = _content_provider()

    assert len(_TREASURE_RELIC_CANDIDATE_IDS) == len(set(_TREASURE_RELIC_CANDIDATE_IDS))
    for relic_id in _TREASURE_RELIC_CANDIDATE_IDS:
        relic = registry.relics().get(relic_id)
        assert relic.id == relic_id
        assert relic.can_appear_in_shop is False
