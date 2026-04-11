from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path
from random import Random

import pytest

from slay_the_spire.app.cli import main
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.hooks.runtime import build_runtime_hook_registrations
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.use_cases import opening_flow
from slay_the_spire.use_cases.end_turn import end_turn
from slay_the_spire.use_cases.enter_room import enter_room
from slay_the_spire.use_cases.start_run import start_new_run


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


class _CountingProvider:
    def __init__(self, delegate: StarterContentProvider) -> None:
        self._delegate = delegate
        self.characters_calls = 0

    def characters(self):
        self.characters_calls += 1
        return self._delegate.characters()

    def cards(self):
        return self._delegate.cards()

    def enemies(self):
        return self._delegate.enemies()

    def encounters(self):
        return self._delegate.encounters()

    def relics(self):
        return self._delegate.relics()

    def potions(self):
        return self._delegate.potions()

    def events(self):
        return self._delegate.events()

    def acts(self):
        return self._delegate.acts()

    def enemy_ids_for_pool(self, pool_id: str):
        return self._delegate.enemy_ids_for_pool(pool_id)

    def enemy_pool_entries(self, pool_id: str):
        return self._delegate.enemy_pool_entries(pool_id)

    def encounter_pool_entries(self, pool_id: str):
        return self._delegate.encounter_pool_entries(pool_id)

    def event_ids_for_pool(self, pool_id: str):
        return self._delegate.event_ids_for_pool(pool_id)

    def event_pool_entries(self, pool_id: str):
        return self._delegate.event_pool_entries(pool_id)

    def potion_ids_for_pool(self, pool_id: str):
        return self._delegate.potion_ids_for_pool(pool_id)


def _node_id_for_room_type(act_state, room_type: str) -> str:
    for node in act_state.nodes:
        if node.room_type == room_type:
            return node.node_id
    raise AssertionError(f"room_type {room_type} not found")


def test_main_returns_zero_for_stub_argv() -> None:
    assert main(["--help"]) == 0


def test_start_new_run_populates_gold_deck_relics_and_empty_potions() -> None:
    provider = _content_provider()

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert isinstance(run_state, RunState)
    assert run_state.seed == 7
    assert run_state.character_id == "ironclad"
    assert run_state.current_act_id == "act1"
    assert run_state.gold == 99
    assert run_state.deck == [
        "strike#1",
        "strike#2",
        "strike#3",
        "strike#4",
        "strike#5",
        "defend#6",
        "defend#7",
        "defend#8",
        "defend#9",
        "bash#10",
    ]
    assert run_state.relics == ["burning_blood"]
    assert run_state.potions == []


def test_start_new_run_initializes_relic_sequences() -> None:
    provider = _content_provider()

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert set(run_state.relic_sequences) == {
        "common",
        "uncommon",
        "rare",
        "shop",
        "boss",
    }
    assert set(run_state.relic_sequence_positions) == {
        "common",
        "uncommon",
        "rare",
        "shop",
        "boss",
    }
    assert all(
        position == 0 for position in run_state.relic_sequence_positions.values()
    )
    assert all(
        isinstance(run_state.relic_sequences[pool], list)
        for pool in run_state.relic_sequences
    )
    assert run_state.relic_sequences["shop"]
    assert run_state.relic_sequences["boss"]


def test_start_new_run_builds_relic_sequences_from_pool_membership() -> None:
    provider = _content_provider()

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert "akabeko" in run_state.relic_sequences["common"]
    assert "anchor" in run_state.relic_sequences["common"]
    assert "blood_vial" in run_state.relic_sequences["common"]
    assert "clockwork_souvenir" in run_state.relic_sequences["shop"]
    assert "cauldron" in run_state.relic_sequences["shop"]
    assert "ectoplasm" in run_state.relic_sequences["boss"]
    assert "astrolabe" in run_state.relic_sequences["boss"]


def test_start_new_run_auto_includes_new_relic_entries_by_pool(tmp_path: Path) -> None:
    content_root = Path(__file__).resolve().parents[2] / "content"
    copied_root = tmp_path / "content"
    shutil.copytree(content_root, copied_root)

    common_relics_path = copied_root / "relics" / "common_relics.json"
    common_payload = json.loads(common_relics_path.read_text(encoding="utf-8"))
    common_payload["relics"].append(
        {
            "id": "test_auto_common_relic",
            "name": "测试公共遗物",
            "summary": "测试公共池自动纳入",
            "description": "只要属于公共池，就应自动进入公共遗物序列。",
            "rarity": "common",
            "pools": ["common"],
            "source_tags": ["test"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
            "effect_blueprint": [],
            "trigger_hooks": [],
            "passive_effects": [],
            "can_appear_in_shop": False,
        }
    )
    common_relics_path.write_text(
        json.dumps(common_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    boss_relics_path = copied_root / "relics" / "boss_relics.json"
    boss_payload = json.loads(boss_relics_path.read_text(encoding="utf-8"))
    boss_payload["relics"].append(
        {
            "id": "test_auto_boss_relic",
            "name": "测试首领遗物",
            "summary": "测试首领池自动纳入",
            "description": "只要属于首领池，就应自动进入首领遗物序列。",
            "rarity": "boss",
            "pools": ["boss"],
            "source_tags": ["boss_relic"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
            "effect_blueprint": [],
            "trigger_hooks": [],
            "passive_effects": [],
            "can_appear_in_shop": False,
        }
    )
    boss_relics_path.write_text(
        json.dumps(boss_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    provider = StarterContentProvider(copied_root)

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert "test_auto_common_relic" in run_state.relic_sequences["common"]
    assert "test_auto_boss_relic" in run_state.relic_sequences["boss"]


def test_neow_random_relic_selection_uses_neow_pool_membership(tmp_path: Path) -> None:
    content_root = Path(__file__).resolve().parents[2] / "content"
    copied_root = tmp_path / "content"
    shutil.copytree(content_root, copied_root)

    common_relics_path = copied_root / "relics" / "common_relics.json"
    common_payload = json.loads(common_relics_path.read_text(encoding="utf-8"))
    common_payload["relics"].append(
        {
            "id": "zz_test_auto_neow_relic",
            "name": "测试 Neow 遗物",
            "summary": "测试 Neow 池自动纳入",
            "description": "只要属于 Neow 池，就应自动进入 Neow 遗物随机池。",
            "rarity": "common",
            "pools": ["common", "neow"],
            "source_tags": ["test"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
            "effect_blueprint": [],
            "trigger_hooks": [],
            "passive_effects": [],
            "can_appear_in_shop": False,
        }
    )
    common_relics_path.write_text(
        json.dumps(common_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    provider = StarterContentProvider(copied_root)
    run_state = start_new_run("ironclad", seed=7, registry=provider)

    class _PickLastRng:
        def choice(self, values):
            return values[-1]

    relic_id = opening_flow._choose_relic_id(
        registry=provider, rng=_PickLastRng(), run_state=run_state
    )

    assert relic_id == "zz_test_auto_neow_relic"


def test_start_new_run_rejects_unknown_character() -> None:
    provider = _content_provider()

    with pytest.raises(KeyError):
        start_new_run("missing", seed=7, registry=provider)


def test_start_new_run_loads_character_definitions_through_provider_contract() -> None:
    provider = _CountingProvider(_content_provider())

    run_state = start_new_run("ironclad", seed=7, registry=provider)

    assert run_state.current_act_id == "act1"
    assert provider.characters_calls >= 1


def test_enter_room_marks_selected_node_visited_immediately() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)
    target_node_id = act_state.reachable_node_ids[0]

    room_state = enter_room(
        run_state, act_state, node_id=target_node_id, registry=provider
    )

    assert isinstance(room_state, RoomState)
    assert act_state.current_node_id == target_node_id
    assert target_node_id in act_state.visited_node_ids


@pytest.mark.parametrize("room_type", ["shop", "rest"])
def test_enter_room_supports_shop_and_rest_room_types(room_type: str) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)
    node_id = _node_id_for_room_type(act_state, room_type)

    room_state = enter_room(run_state, act_state, node_id=node_id, registry=provider)

    assert room_state.room_type == room_type
    assert room_state.stage == "waiting_input"
    assert room_state.payload["node_id"] == node_id
    if room_type == "shop":
        assert "cards" in room_state.payload
        assert "relics" in room_state.payload
        assert "potions" in room_state.payload
        assert room_state.payload["remove_price"] == 75
    else:
        assert room_state.payload["actions"] == ["rest", "smith"]


def test_enter_room_shop_payload_excludes_curse_cards_and_event_only_relics() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)
    node_id = _node_id_for_room_type(act_state, "shop")

    room_state = enter_room(run_state, act_state, node_id=node_id, registry=provider)

    offered_cards = [item["card_id"] for item in room_state.payload["cards"]]
    offered_relics = [item["relic_id"] for item in room_state.payload["relics"]]

    assert all(
        "shop" in provider.cards().get(card_id).acquisition_tags
        for card_id in offered_cards
    )
    assert "doubt" not in offered_cards
    assert "injury" not in offered_cards
    assert "burn" not in offered_cards
    assert "golden_idol" not in offered_relics


def test_enter_room_shop_payload_uses_shop_pool_sequence() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    expected_relic_id = run_state.relic_sequences["shop"][0]
    act_state = generate_act_state("act1", seed=7, registry=provider)
    node_id = _node_id_for_room_type(act_state, "shop")

    room_state = enter_room(run_state, act_state, node_id=node_id, registry=provider)

    offered_relics = [item["relic_id"] for item in room_state.payload["relics"]]

    assert offered_relics == [expected_relic_id]
    assert run_state.relic_sequence_positions["shop"] == 1
    assert all(
        "shop" in provider.relics().get(relic_id).pools for relic_id in offered_relics
    )


def test_enter_room_shop_payload_is_stable_for_unresolved_reentry() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)
    node_id = _node_id_for_room_type(act_state, "shop")

    first_room = enter_room(run_state, act_state, node_id=node_id, registry=provider)
    second_room = enter_room(run_state, act_state, node_id=node_id, registry=provider)

    assert first_room.payload["relics"] == second_room.payload["relics"]
    assert run_state.relic_sequence_positions["shop"] == 1


def test_enter_room_builds_playable_combat_state_for_combat_nodes() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.energy == 3
    assert combat_state.round_number == 1
    assert len(combat_state.hand) == 5
    assert len(combat_state.draw_pile) == 5
    assert sorted([*combat_state.hand, *combat_state.draw_pile]) == sorted(
        run_state.deck
    )
    assert combat_state.hand != [
        "strike#1",
        "strike#2",
        "strike#3",
        "strike#4",
        "strike#5",
    ]
    assert len(combat_state.enemies) >= 1


def test_enter_room_shuffles_opening_hand_deterministically_for_same_room_seed() -> (
    None
):
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    first_act_state = generate_act_state("act1", seed=7, registry=provider)
    second_act_state = generate_act_state("act1", seed=7, registry=provider)

    first_room_state = enter_room(
        run_state, first_act_state, node_id="start", registry=provider
    )
    second_room_state = enter_room(
        run_state, second_act_state, node_id="start", registry=provider
    )
    first_combat_state = CombatState.from_dict(first_room_state.payload["combat_state"])
    second_combat_state = CombatState.from_dict(
        second_room_state.payload["combat_state"]
    )

    assert first_combat_state.hand == second_combat_state.hand
    assert first_combat_state.draw_pile == second_combat_state.draw_pile


def test_enter_room_applies_ectoplasm_energy_on_combat_start() -> None:
    provider = _content_provider()
    run_state = replace(
        start_new_run("ironclad", seed=5, registry=provider), relics=["ectoplasm"]
    )
    act_state = generate_act_state("act1", seed=5, registry=provider)

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.energy == 4


def test_enter_room_applies_fusion_hammer_energy_on_combat_start() -> None:
    provider = _content_provider()
    run_state = replace(
        start_new_run("ironclad", seed=5, registry=provider), relics=["fusion_hammer"]
    )
    act_state = generate_act_state("act1", seed=5, registry=provider)

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.energy == 4


def test_ectoplasm_grants_energy_on_second_turn() -> None:
    provider = _content_provider()
    run_state = replace(
        start_new_run("ironclad", seed=5, registry=provider), relics=["ectoplasm"]
    )
    act_state = generate_act_state("act1", seed=5, registry=provider)

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])
    registrations = build_runtime_hook_registrations(run_state, provider)

    end_turn(combat_state, provider, hook_registrations=registrations)

    assert combat_state.round_number == 2
    assert combat_state.energy == 4


def test_fusion_hammer_grants_energy_on_second_turn() -> None:
    provider = _content_provider()
    run_state = replace(
        start_new_run("ironclad", seed=5, registry=provider), relics=["fusion_hammer"]
    )
    act_state = generate_act_state("act1", seed=5, registry=provider)

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])
    registrations = build_runtime_hook_registrations(run_state, provider)

    end_turn(combat_state, provider, hook_registrations=registrations)

    assert combat_state.round_number == 2
    assert combat_state.energy == 4


def test_enter_room_samples_enemy_from_pool_deterministically() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=3, registry=provider)
    act_state = generate_act_state("act1", seed=3, registry=provider)

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert combat_state.energy == 3
    assert combat_state.round_number == 1
    assert room_state.payload["encounter_id"] in {
        "single_red_louse",
        "single_green_louse",
        "pair_louses",
        "cultist",
        "single_jaw_worm",
        "double_slime",
    }
    assert len(combat_state.enemies) >= 1


def test_enter_room_can_sample_new_basic_enemy_from_pool() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=23, registry=provider)
    act_state = generate_act_state("act1", seed=23, registry=provider)

    room_state = enter_room(run_state, act_state, node_id="start", registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert room_state.payload["encounter_id"] in {
        "single_red_louse",
        "single_green_louse",
        "pair_louses",
        "cultist",
        "single_jaw_worm",
        "double_slime",
    }
    assert len(combat_state.enemies) >= 1


def test_enter_act2_combat_room_uses_act2_basic_encounters() -> None:
    provider = _content_provider()
    run_state = replace(
        start_new_run("ironclad", seed=17, registry=provider), current_act_id="act2"
    )
    act_state = generate_act_state("act2", seed=17, registry=provider)
    node_id = _node_id_for_room_type(act_state, "combat")

    room_state = enter_room(run_state, act_state, node_id=node_id, registry=provider)
    combat_state = CombatState.from_dict(room_state.payload["combat_state"])

    assert room_state.payload["encounter_id"] in {
        "chosen_plus_byrd",
        "double_chosen",
        "spheric_guardian_plus_slaver",
        "triple_byrd",
    }
    assert len(combat_state.enemies) >= 2


def test_enter_act2_elite_room_uses_act2_elite_encounters() -> None:
    provider = _content_provider()
    run_state = replace(
        start_new_run("ironclad", seed=19, registry=provider), current_act_id="act2"
    )
    act_state = generate_act_state("act2", seed=19, registry=provider)
    node_id = _node_id_for_room_type(act_state, "elite")

    room_state = enter_room(run_state, act_state, node_id=node_id, registry=provider)

    assert room_state.payload["encounter_id"] in {
        "book_of_stabbing",
        "gremlin_leader",
        "slavers",
    }


def test_enter_act2_boss_room_uses_act2_boss_encounters() -> None:
    provider = _content_provider()
    run_state = replace(
        start_new_run("ironclad", seed=29, registry=provider), current_act_id="act2"
    )
    act_state = generate_act_state("act2", seed=29, registry=provider)
    node_id = _node_id_for_room_type(act_state, "boss")

    room_state = enter_room(run_state, act_state, node_id=node_id, registry=provider)

    assert room_state.payload["encounter_id"] in {
        "bronze_automaton",
        "champ",
        "the_collector",
    }


def test_enter_room_does_not_mutate_act_state_when_combat_setup_fails() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    act_state = generate_act_state("act1", seed=7, registry=provider)
    target_node_id = next(
        node.node_id
        for node in act_state.nodes
        if node.room_type == "combat" and node.node_id != act_state.current_node_id
    )
    original_current_node_id = act_state.current_node_id
    original_visited_node_ids = list(act_state.visited_node_ids)
    act_state.enemy_pool_id = None

    with pytest.raises(ValueError, match="combat rooms require an enemy pool id"):
        enter_room(run_state, act_state, node_id=target_node_id, registry=provider)

    assert act_state.current_node_id == original_current_node_id
    assert act_state.visited_node_ids == original_visited_node_ids
    assert target_node_id not in act_state.visited_node_ids


@pytest.mark.guardrail
def test_start_new_run_excludes_placeholder_relics_from_random_sequences() -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=7, registry=provider)
    offenders = [
        f"{pool_id}:{relic_id}"
        for pool_id, relic_ids in run_state.relic_sequences.items()
        for relic_id in relic_ids
        if provider.relics().get(relic_id).implementation_status == "placeholder"
    ]
    assert not offenders, "placeholder relics in random pools:\n" + "\n".join(
        offenders[:50]
    )


@pytest.mark.guardrail
def test_neow_excludes_placeholder_relics_from_random_pool(tmp_path: Path) -> None:
    content_root = Path(__file__).resolve().parents[2] / "content"
    copied_root = tmp_path / "content"
    shutil.copytree(content_root, copied_root)

    common_relics_path = copied_root / "relics" / "common_relics.json"
    common_payload = json.loads(common_relics_path.read_text(encoding="utf-8"))
    common_payload["relics"].extend(
        [
            {
                "id": "zz_test_neow_placeholder_relic",
                "name": "测试 Neow 占位遗物",
                "summary": "占位遗物不应进入 Neow 随机池",
                "description": "placeholder 遗物应被排除。",
                "rarity": "common",
                "pools": ["common", "neow"],
                "source_tags": ["test"],
                "owner_character_ids": [],
                "implementation_status": "placeholder",
                "effect_blueprint": [],
                "trigger_hooks": [],
                "passive_effects": [],
                "can_appear_in_shop": False,
            },
            {
                "id": "zy_test_neow_implemented_relic",
                "name": "测试 Neow 已实现遗物",
                "summary": "已实现遗物应进入 Neow 随机池",
                "description": "implemented 遗物应进入池。",
                "rarity": "common",
                "pools": ["common", "neow"],
                "source_tags": ["test"],
                "owner_character_ids": [],
                "implementation_status": "implemented",
                "effect_blueprint": [],
                "trigger_hooks": [],
                "passive_effects": [],
                "can_appear_in_shop": False,
            },
        ]
    )
    common_relics_path.write_text(
        json.dumps(common_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    provider = StarterContentProvider(copied_root)
    run_state = start_new_run("ironclad", seed=7, registry=provider)

    class _PickLastRng:
        def choice(self, values):
            return values[-1]

    relic_id = opening_flow._choose_relic_id(
        registry=provider, rng=_PickLastRng(), run_state=run_state
    )

    assert relic_id == "zy_test_neow_implemented_relic"
