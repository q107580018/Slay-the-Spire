from __future__ import annotations

from pathlib import Path

import pytest

from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.content.registries import CardRegistry, EnemyRegistry
from slay_the_spire.domain.hooks.runtime import build_runtime_hook_registrations
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.use_cases.play_card import play_card


class _Provider:
    def __init__(self) -> None:
        self._cards = CardRegistry()
        self._enemies = EnemyRegistry()
        self.cards_calls = 0

    def characters(self):
        raise NotImplementedError

    def cards(self) -> CardRegistry:
        self.cards_calls += 1
        return self._cards

    def enemies(self) -> EnemyRegistry:
        return self._enemies

    def relics(self):
        raise NotImplementedError

    def events(self):
        raise NotImplementedError

    def acts(self):
        raise NotImplementedError


def _combat_state(
    *,
    hand: list[str] | None = None,
    energy: int = 3,
    enemy_hps: list[int] | None = None,
    enemy_ids: list[str] | None = None,
) -> CombatState:
    enemy_hps = enemy_hps or [10]
    enemy_ids = enemy_ids or ["training_dummy"] * len(enemy_hps)
    return CombatState(
        round_number=1,
        energy=energy,
        hand=list(hand or ["custom_strike#1"]),
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
                instance_id=f"enemy-{index}",
                enemy_id=enemy_ids[index - 1],
                hp=hp,
                max_hp=hp,
                block=0,
                statuses=[],
            )
            for index, hp in enumerate(enemy_hps, start=1)
        ],
        effect_queue=[],
        log=[],
    )


def _provider_with_card(
    *,
    card_id: str = "custom_strike",
    cost: int = 1,
    effects: list[dict[str, object]] | None = None,
    card_type: str | None = None,
) -> _Provider:
    provider = _Provider()
    provider.cards().register(
        {
            "id": card_id,
            "name": "Custom Strike",
            "cost": cost,
            "effects": effects or [{"type": "damage", "amount": 4}],
            "card_type": (
                card_type
                if card_type is not None
                else ("skill" if card_id.startswith("skill_") else "attack")
            ),
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
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
    return provider


def _relic_hook_registrations(*relic_ids: str):
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")
    run_state = RunState(
        seed=7,
        character_id="ironclad",
        current_act_id="act1",
        relics=list(relic_ids),
    )
    return provider, build_runtime_hook_registrations(run_state, provider)


def test_playing_skill_grants_strength_to_gremlin_nob() -> None:
    state = _combat_state(
        hand=["skill_guard#1"],
        enemy_ids=["gremlin_nob"],
        enemy_hps=[40],
    )
    provider = _provider_with_card(
        card_id="skill_guard", cost=1, effects=[{"type": "block", "amount": 5}]
    )

    result = play_card(state, "skill_guard#1", None, provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == [
        "strength",
        "block",
    ]
    assert state.enemies[0].statuses == [StatusState(status_id="strength", stacks=2)]


def test_play_card_rejects_card_not_in_hand() -> None:
    state = _combat_state(hand=["custom_strike#1"])
    provider = _provider_with_card()

    with pytest.raises(ValueError, match="not in hand"):
        play_card(state, "custom_strike#2", "enemy-1", provider)


def test_play_card_rejects_insufficient_energy() -> None:
    state = _combat_state(energy=0)
    provider = _provider_with_card(cost=1)

    with pytest.raises(ValueError, match="energy"):
        play_card(state, "custom_strike#1", "enemy-1", provider)


def test_play_card_rejects_missing_target_for_targeted_effect() -> None:
    state = _combat_state()
    provider = _provider_with_card(effects=[{"type": "damage", "amount": 4}])
    before = state.to_dict()

    with pytest.raises(ValueError, match="target"):
        play_card(state, "custom_strike#1", None, provider)

    assert state.to_dict() == before


def test_play_card_failure_does_not_increment_turn_counters() -> None:
    state = _combat_state(hand=["broken_card#1"])
    provider = _provider_with_card(
        card_id="broken_card",
        effects=[{"type": "unsupported_effect"}],
        card_type="attack",
    )

    with pytest.raises(ValueError, match="unsupported effect type"):
        play_card(state, "broken_card#1", "enemy-1", provider)

    assert state.cards_played_this_turn == 0
    assert state.attacks_played_this_turn == 0


def test_play_card_failure_does_not_consume_attack_trigger_powers() -> None:
    state = _combat_state(hand=["broken_card#1"])
    state.active_powers = [
        {"power_id": "double_tap", "amount": 1},
        {"power_id": "rage", "amount": 3},
    ]
    provider = _provider_with_card(
        card_id="broken_card",
        effects=[{"type": "unsupported_effect"}],
        card_type="attack",
    )

    with pytest.raises(ValueError, match="unsupported effect type"):
        play_card(state, "broken_card#1", "enemy-1", provider)

    assert state.active_powers == [
        {"power_id": "double_tap", "amount": 1},
        {"power_id": "rage", "amount": 3},
    ]


def test_play_card_failure_does_not_pollute_action_relic_runtime_state() -> None:
    state = _combat_state(hand=["broken_power#1", "bash#2"], energy=1)
    state.card_play_data = {
        "relic:ink_bottle": 9,
        "relic:nunchaku": 9,
        "relic:pen_nib": 9,
        "relic:letter_opener": 2,
        "relic:hovering_kite:discarded": 1,
    }
    state.temporary_costs = {"bash#2": 2}
    provider = _Provider()
    provider.cards().register(
        {
            "id": "broken_power",
            "name": "Broken Power",
            "cost": 1,
            "card_type": "power",
            "effects": [{"type": "unsupported_effect"}],
        }
    )
    provider.cards().register(
        {
            "id": "bash",
            "name": "Bash",
            "cost": 2,
            "effects": [{"type": "damage", "amount": 8}],
            "card_type": "attack",
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )
    _, hook_registrations = _relic_hook_registrations(
        "ink_bottle",
        "pen_nib",
        "orange_pellets",
        "mummified_hand",
    )
    before = state.to_dict()

    with pytest.raises(ValueError, match="unsupported effect type"):
        play_card(
            state,
            "broken_power#1",
            None,
            provider,
            hook_registrations=hook_registrations,
        )

    assert state.to_dict() == before


def test_play_card_failure_restores_debuffs_cleared_by_orange_pellets() -> None:
    state = _combat_state(hand=["broken_power#1"], energy=1)
    state.card_play_data = {
        "relic:orange_pellets:attack:active": 1,
        "relic:orange_pellets:skill:active": 1,
    }
    state.player.statuses = [
        StatusState(status_id="weak", stacks=1),
        StatusState(status_id="poison", stacks=2),
    ]
    provider = _Provider()
    provider.cards().register(
        {
            "id": "broken_power",
            "name": "Broken Power",
            "cost": 1,
            "card_type": "power",
            "effects": [{"type": "unsupported_effect"}],
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )
    _, hook_registrations = _relic_hook_registrations("orange_pellets")

    with pytest.raises(ValueError, match="unsupported effect type"):
        play_card(
            state,
            "broken_power#1",
            None,
            provider,
            hook_registrations=hook_registrations,
        )

    assert state.player.statuses == [
        StatusState(status_id="weak", stacks=1),
        StatusState(status_id="poison", stacks=2),
    ]


def test_play_card_body_slam_deals_damage_equal_to_player_block() -> None:
    state = _combat_state(hand=["body_slam#1"], enemy_hps=[20])
    state.player.block = 12
    provider = _provider_with_card(
        card_id="body_slam",
        cost=1,
        effects=[{"type": "damage_equal_to_block"}],
        card_type="attack",
    )

    result = play_card(state, "body_slam#1", "enemy-1", provider)

    assert result.combat_state is state
    assert state.enemies[0].hp == 8


def test_play_card_damage_with_strength_multiplier_uses_selected_target() -> None:
    state = _combat_state(hand=["heavy_blade#1"], enemy_hps=[30])
    provider = _provider_with_card(
        card_id="heavy_blade",
        cost=2,
        effects=[
            {"type": "damage_with_strength_multiplier", "base": 14, "multiplier": 3}
        ],
        card_type="attack",
    )

    result = play_card(state, "heavy_blade#1", "enemy-1", provider)

    assert result.combat_state is state
    assert state.enemies[0].hp == 16


def test_play_card_blood_for_blood_uses_damage_taken_as_cost_reduction() -> None:
    state = _combat_state(hand=["blood_for_blood#1"], energy=2)
    state.times_hit_this_combat = 3
    provider = _Provider()
    provider.cards().register(
        {
            "id": "blood_for_blood",
            "name": "Blood for Blood",
            "cost": 4,
            "cost_reducer": "times_hit_this_combat",
            "effects": [{"type": "damage", "amount": 18}],
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
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

    result = play_card(state, "blood_for_blood#1", "enemy-1", provider)

    assert result.combat_state.energy == 1


def test_play_card_temporary_cost_overrides_damage_taken_cost_reduction() -> None:
    state = _combat_state(hand=["blood_for_blood#1"], energy=1)
    state.times_hit_this_combat = 4
    state.temporary_costs = {"blood_for_blood#1": 1}
    provider = _Provider()
    provider.cards().register(
        {
            "id": "blood_for_blood",
            "name": "Blood for Blood",
            "cost": 4,
            "cost_reducer": "times_hit_this_combat",
            "effects": [{"type": "damage", "amount": 18}],
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )

    result = play_card(state, "blood_for_blood#1", "enemy-1", provider)

    assert result.combat_state.energy == 0


def test_play_card_rejects_unknown_card() -> None:
    state = _combat_state(hand=["unknown_card#1"])
    provider = _Provider()

    with pytest.raises(KeyError):
        play_card(state, "unknown_card#1", "enemy-1", provider)


def test_play_card_second_wind_resolves_through_registry_and_exhausts_only_non_attacks() -> (
    None
):
    state = _combat_state(hand=["second_wind#1", "defend#2", "strike#3"], energy=3)
    provider = _Provider()
    provider.cards().register(
        {
            "id": "second_wind",
            "name": "Second Wind",
            "cost": 1,
            "card_type": "skill",
            "effects": [
                {"type": "exhaust_all_non_attacks_gain_block", "amount_per_card": 5}
            ],
        }
    )
    provider.cards().register(
        {
            "id": "defend",
            "name": "Defend",
            "cost": 1,
            "card_type": "skill",
            "effects": [{"type": "block", "amount": 5}],
        }
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "Strike",
            "cost": 1,
            "card_type": "attack",
            "effects": [{"type": "damage", "amount": 6}],
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )

    result = play_card(state, "second_wind#1", None, provider)

    assert [effect["type"] for effect in result.resolved_effects] == [
        "exhaust_all_non_attacks_gain_block"
    ]
    assert state.hand == ["strike#3"]
    assert state.exhaust_pile == ["defend#2"]
    assert state.player.block == 5


def test_play_card_self_exhaust_triggers_on_exhaust_effects() -> None:
    state = _combat_state(hand=["sentinel_skill#1"], energy=3)
    provider = _Provider()
    provider.cards().register(
        {
            "id": "sentinel_skill",
            "name": "Sentinel Skill",
            "cost": 1,
            "card_type": "skill",
            "exhausts": True,
            "effects": [],
            "on_exhaust_effects": [{"type": "gain_energy", "amount": 2}],
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )

    result = play_card(state, "sentinel_skill#1", None, provider)

    assert [effect["type"] for effect in result.resolved_effects] == ["gain_energy"]
    assert state.energy == 4
    assert state.exhaust_pile == ["sentinel_skill#1"]


def test_play_card_self_exhaust_queues_on_exhaust_after_normal_effects() -> None:
    state = _combat_state(hand=["exhausting_signal#1"], energy=3)
    provider = _Provider()
    provider.cards().register(
        {
            "id": "exhausting_signal",
            "name": "Exhausting Signal",
            "cost": 1,
            "card_type": "skill",
            "exhausts": True,
            "effects": [{"type": "block", "amount": 4}],
            "on_exhaust_effects": [{"type": "gain_energy", "amount": 2}],
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )

    result = play_card(state, "exhausting_signal#1", None, provider)

    assert [effect["type"] for effect in result.resolved_effects] == [
        "block",
        "gain_energy",
    ]
    assert state.player.block == 4
    assert state.energy == 4


def test_play_card_rejects_invalid_card_instance_id_format() -> None:
    state = _combat_state(hand=["registry_card"])
    provider = _provider_with_card(card_id="registry_card")
    before = state.to_dict()

    with pytest.raises(ValueError, match="card_instance_id"):
        play_card(state, "registry_card", "enemy-1", provider)

    assert state.to_dict() == before


def test_play_card_applies_negative_player_strength_to_damage_effects() -> None:
    state = _combat_state(hand=["custom_strike#1"])
    state.player.statuses.append(StatusState(status_id="strength", stacks=-2))
    provider = _provider_with_card()

    result = play_card(state, "custom_strike#1", "enemy-1", provider)

    assert result.resolved_effects[0]["result"]["applied_amount"] == 2


def test_play_card_applies_negative_player_dexterity_to_block_effects() -> None:
    state = _combat_state(hand=["skill_guard#1"])
    state.player.statuses.append(StatusState(status_id="dexterity", stacks=-2))
    provider = _provider_with_card(
        card_id="skill_guard", cost=1, effects=[{"type": "block", "amount": 5}]
    )

    result = play_card(state, "skill_guard#1", None, provider)

    assert result.resolved_effects[0]["result"]["gained_block"] == 3


def test_play_card_defaults_draw_target_to_player() -> None:
    state = _combat_state(hand=["draw_card#1"])
    state.draw_pile = ["bonus_card#1"]
    provider = _provider_with_card(
        card_id="draw_card", effects=[{"type": "draw", "amount": 1}]
    )

    result = play_card(state, "draw_card#1", None, provider)

    assert [effect["type"] for effect in result.resolved_effects] == ["draw"]
    assert state.hand == ["bonus_card#1"]
    assert state.discard_pile == ["draw_card#1"]


def test_play_card_creates_a_new_anger_copy_in_discard_pile() -> None:
    state = _combat_state(hand=["anger#1"], energy=3)
    provider = _provider_with_card(
        card_id="anger",
        cost=0,
        effects=[
            {"type": "damage", "amount": 6},
            {"type": "create_card_copy", "card_id": "anger", "zone": "discard_pile"},
        ],
    )

    result = play_card(state, "anger#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == [
        "damage",
        "create_card_copy",
    ]
    assert state.energy == 3
    assert state.hand == []
    assert state.discard_pile == ["anger#2", "anger#1"]
    assert state.enemies[0].hp == 4
    assert state.log == [
        "你打出 Custom Strike，对 Training Dummy 造成 6 伤害，并向弃牌堆加入 1 张Custom Strike。"
    ]


def test_play_card_uses_registry_to_resolve_card_definition() -> None:
    state = _combat_state(hand=["registry_card#9"])
    provider = _provider_with_card(
        card_id="registry_card", effects=[{"type": "damage", "amount": 7}]
    )

    result = play_card(state, "registry_card#9", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage"]
    assert state.energy == 2
    assert state.hand == []
    assert state.discard_pile == ["registry_card#9"]
    assert state.enemies[0].hp == 3
    assert provider.cards_calls >= 2


def test_play_card_applies_player_strength_to_damage_effects() -> None:
    state = _combat_state(hand=["custom_strike#1"])
    state.player.statuses.append(StatusState(status_id="strength", stacks=2))
    provider = _provider_with_card(effects=[{"type": "damage", "amount": 4}])

    result = play_card(state, "custom_strike#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage"]
    assert result.resolved_effects[0]["result"] == {
        "applied_amount": 6,
        "blocked": 0,
        "actual_damage": 6,
        "target_defeated": False,
    }
    assert state.enemies[0].hp == 4


def test_play_card_rampage_tracks_card_instance_and_scales_damage() -> None:
    state = _combat_state(hand=["rampage_plus#1"], energy=3, enemy_hps=[50])
    provider = _provider_with_card(
        card_id="rampage_plus",
        effects=[{"type": "rampage_damage", "amount": 8, "increment": 8}],
    )

    first = play_card(state, "rampage_plus#1", "enemy-1", provider)

    state.discard_pile.remove("rampage_plus#1")
    state.hand.append("rampage_plus#1")
    second = play_card(state, "rampage_plus#1", "enemy-1", provider)

    assert first.resolved_effects[0]["type"] == "rampage_damage"
    assert first.resolved_effects[0]["result"]["applied_amount"] == 8
    assert second.resolved_effects[0]["type"] == "rampage_damage"
    assert second.resolved_effects[0]["result"]["applied_amount"] == 16
    assert state.card_play_data == {"rampage_plus#1": 2}
    assert state.enemies[0].hp == 26
    assert state.log == [
        "你打出 Custom Strike，对 Training Dummy 造成 8 伤害。",
        "你打出 Custom Strike，对 Training Dummy 造成 16 伤害。",
    ]


def test_inflame_adds_strength_via_power_play() -> None:
    state = _combat_state(hand=["inflame#1"])
    provider = _provider_with_card(
        card_id="inflame",
        effects=[{"type": "add_power", "power_id": "inflame", "amount": 2}],
        card_type="power",
    )

    result = play_card(state, "inflame#1", None, provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["add_power"]
    assert state.active_powers == [{"power_id": "inflame", "amount": 2}]
    assert state.player.statuses == [StatusState(status_id="strength", stacks=2)]
    assert state.discard_pile == []
    assert state.exhaust_pile == []


def test_play_card_applies_vulnerable_status_effects() -> None:
    state = _combat_state(hand=["bash#1"], energy=2)
    provider = _provider_with_card(
        card_id="bash",
        cost=2,
        effects=[
            {"type": "damage", "amount": 8},
            {"type": "vulnerable", "stacks": 2},
        ],
    )

    result = play_card(state, "bash#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == [
        "damage",
        "vulnerable",
    ]
    assert state.enemies[0].hp == 2
    assert len(state.enemies[0].statuses) == 1
    assert state.enemies[0].statuses[0].status_id == "vulnerable"
    assert state.enemies[0].statuses[0].stacks == 2
    assert state.log == [
        "你打出 Custom Strike，对 Training Dummy 造成 8 伤害，并施加 2 层易伤。"
    ]


def test_play_card_can_apply_vulnerable_to_self_without_target() -> None:
    state = _combat_state(hand=["berserk#1"])
    provider = _provider_with_card(
        card_id="berserk",
        card_type="power",
        effects=[
            {"type": "vulnerable", "stacks": 2, "target_instance_id": "self"},
            {"type": "add_power", "power_id": "berserk", "amount": 1},
        ],
    )

    result = play_card(state, "berserk#1", None, provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == [
        "vulnerable",
        "add_power",
    ]
    assert state.player.hp == 40
    assert state.player.statuses == [StatusState(status_id="vulnerable", stacks=2)]
    assert state.active_powers == [{"power_id": "berserk", "amount": 1}]
    assert state.log == ["你打出 Custom Strike，获得 2 层易伤。"]


def test_play_card_dropkick_hits_vulnerable_enemy_and_grants_energy_and_draw() -> None:
    state = _combat_state(hand=["dropkick#1"], enemy_hps=[20])
    state.energy = 1
    state.hand = ["dropkick#1"]
    state.draw_pile = ["strike#2", "defend#2"]
    state.enemies[0].statuses.append(StatusState(status_id="vulnerable", stacks=1))
    provider = _provider_with_card(
        card_id="dropkick",
        effects=[{"type": "dropkick_effect", "amount": 5}],
    )

    result = play_card(state, "dropkick#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["dropkick_effect"]
    assert state.enemies[0].hp == 13
    assert state.energy == 1
    assert state.hand == ["strike#2"]


def test_play_card_dropkick_only_deals_damage_when_enemy_not_vulnerable() -> None:
    state = _combat_state(hand=["dropkick#1"], enemy_hps=[20])
    state.energy = 1
    state.hand = ["dropkick#1"]
    state.draw_pile = ["strike#2", "defend#2"]
    provider = _provider_with_card(
        card_id="dropkick",
        effects=[{"type": "dropkick_effect", "amount": 5}],
    )

    result = play_card(state, "dropkick#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["dropkick_effect"]
    assert state.enemies[0].hp == 15
    assert state.energy == 0
    assert state.hand == []


def test_play_card_disarm_applies_negative_strength_to_target_enemy() -> None:
    state = _combat_state(hand=["disarm#1"])
    provider = _provider_with_card(
        card_id="disarm",
        effects=[{"type": "strength", "amount": -2}],
    )

    result = play_card(state, "disarm#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["strength"]
    assert state.player.statuses == []
    assert state.enemies[0].statuses == [StatusState(status_id="strength", stacks=-2)]


def test_play_card_damage_is_reduced_while_player_is_weak() -> None:
    state = _combat_state(hand=["custom_strike#1"])
    state.player.statuses.append(StatusState(status_id="weak", stacks=1))
    provider = _provider_with_card(effects=[{"type": "damage", "amount": 6}])

    result = play_card(state, "custom_strike#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage"]
    assert state.enemies[0].hp == 6
    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 4 伤害。"]


def test_play_card_rejects_unplayable_cards() -> None:
    state = _combat_state(hand=["doubt#1"])
    provider = _Provider()
    provider.cards().register(
        {
            "id": "doubt",
            "name": "疑虑",
            "cost": -1,
            "playable": False,
            "effects": [],
        }
    )

    with pytest.raises(ValueError, match="无法打出"):
        play_card(state, "doubt#1", None, provider)


def test_play_card_appends_damage_log_entry() -> None:
    state = _combat_state(hand=["custom_strike#1"])
    provider = _provider_with_card(effects=[{"type": "damage", "amount": 4}])

    play_card(state, "custom_strike#1", "enemy-1", provider)

    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 4 伤害。"]


def test_play_card_appends_block_log_entry() -> None:
    state = _combat_state(hand=["guard#1"])
    provider = _provider_with_card(
        card_id="guard", effects=[{"type": "block", "amount": 5}]
    )

    play_card(state, "guard#1", None, provider)

    assert state.log == ["你打出 Custom Strike，获得 5 格挡。"]


def test_play_card_logs_juggernaut_damage_as_triggered_power() -> None:
    state = _combat_state(hand=["guard#1"], enemy_hps=[20])
    state.active_powers = [{"power_id": "juggernaut", "amount": 7}]
    provider = _provider_with_card(
        card_id="guard", effects=[{"type": "block", "amount": 5}]
    )

    result = play_card(state, "guard#1", None, provider)

    assert [effect["type"] for effect in result.resolved_effects] == ["block", "damage"]
    assert state.log == [
        "你打出 Custom Strike，获得 5 格挡。",
        "势不可当触发，对 Training Dummy 造成 7 伤害。",
    ]


def test_play_card_all_enemy_attack_hits_all_enemies_without_target() -> None:
    state = _combat_state(hand=["cleave#1"], enemy_hps=[20, 20])
    provider = _provider_with_card(
        card_id="cleave",
        effects=[{"type": "damage_all_enemies", "amount": 8}],
    )

    result = play_card(state, "cleave#1", None, provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == [
        "damage",
        "damage",
    ]
    assert [enemy.hp for enemy in state.enemies] == [12, 12]
    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 16 伤害。"]


def test_play_card_thunderclap_applies_vulnerable_to_all_enemies() -> None:
    state = _combat_state(hand=["thunderclap#1"], enemy_hps=[10, 10])
    provider = _provider_with_card(
        card_id="thunderclap",
        effects=[
            {"type": "damage_all_enemies", "amount": 4},
            {"type": "vulnerable_all_enemies", "stacks": 1},
        ],
    )

    play_card(state, "thunderclap#1", None, provider)

    assert all(
        any(
            status.status_id == "vulnerable" and status.stacks == 1
            for status in enemy.statuses
        )
        for enemy in state.enemies
    )


def test_play_card_x_cost_whirlwind_spends_all_energy_and_hits_all_enemies() -> None:
    state = _combat_state(hand=["whirlwind#1"], energy=3, enemy_hps=[20, 20])
    provider = _provider_with_card(
        card_id="whirlwind",
        cost=-1,
        effects=[{"type": "damage_all_enemies_x_times", "amount": 5}],
    )

    result = play_card(state, "whirlwind#1", None, provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == [
        "damage",
        "damage",
        "damage",
        "damage",
        "damage",
        "damage",
    ]
    assert state.energy == 0
    assert [enemy.hp for enemy in state.enemies] == [5, 5]
    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 30 伤害。"]


def test_play_card_x_cost_whirlwind_applies_strength_to_each_hit() -> None:
    state = _combat_state(hand=["whirlwind#1"], energy=2, enemy_hps=[20, 20])
    state.player.statuses.append(StatusState(status_id="strength", stacks=2))
    provider = _provider_with_card(
        card_id="whirlwind",
        cost=-1,
        effects=[{"type": "damage_all_enemies_x_times", "amount": 5}],
    )

    result = play_card(state, "whirlwind#1", None, provider)

    assert result.combat_state is state
    assert [enemy.hp for enemy in state.enemies] == [6, 6]
    assert all(
        effect["result"]["applied_amount"] == 7 for effect in result.resolved_effects
    )
    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 28 伤害。"]


def test_play_card_draw_log_uses_refilled_discard_cards() -> None:
    state = _combat_state(hand=["pommel_strike_plus#1"])
    state.draw_pile = ["bonus_a#1"]
    state.discard_pile = ["bonus_b#1"]
    provider = _provider_with_card(
        card_id="pommel_strike_plus",
        effects=[
            {"type": "damage", "amount": 10},
            {"type": "draw", "amount": 2},
        ],
    )

    play_card(state, "pommel_strike_plus#1", "enemy-1", provider)

    assert state.hand == ["bonus_a#1", "bonus_b#1"]
    assert state.draw_pile == []
    assert state.discard_pile == ["pommel_strike_plus#1"]
    assert state.log == [
        "你打出 Custom Strike，对 Training Dummy 造成 10 伤害，并抽 2 张牌。"
    ]


def test_play_card_perfected_strike_uses_bonus_per_strike_and_logs_actual_damage() -> (
    None
):
    state = _combat_state(hand=["perfected_strike#1", "strike#2"], enemy_hps=[20])
    state.draw_pile = ["wild_strike#3"]
    state.discard_pile = ["pommel_strike#4"]
    state.exhaust_pile = ["twin_strike#5"]
    provider = _Provider()
    provider.cards().register(
        {
            "id": "perfected_strike",
            "name": "完美打击",
            "cost": 2,
            "effects": [
                {"type": "damage_per_strike_in_deck", "base": 6, "bonus_per_strike": 2}
            ],
            "card_type": "attack",
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 20,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )

    result = play_card(state, "perfected_strike#1", "enemy-1", provider)

    assert result.resolved_effects[0]["result"]["applied_amount"] == 16
    assert state.enemies[0].hp == 4
    assert state.log == ["你打出 完美打击，对 Training Dummy 造成 16 伤害。"]


def test_play_card_shrug_it_off_does_not_draw_itself_when_refilling_discard() -> None:
    state = _combat_state(hand=["shrug_it_off_plus#1"])
    state.draw_pile = []
    state.discard_pile = ["bonus_b#1"]
    provider = _provider_with_card(
        card_id="shrug_it_off_plus",
        cost=1,
        card_type="skill",
        effects=[
            {"type": "block", "amount": 11},
            {"type": "draw", "amount": 1},
        ],
    )

    play_card(state, "shrug_it_off_plus#1", None, provider)

    assert state.hand == ["bonus_b#1"]
    assert state.draw_pile == []
    assert state.discard_pile == ["shrug_it_off_plus#1"]


def test_play_card_bloodletting_gains_energy_and_loses_hp() -> None:
    state = _combat_state(hand=["bloodletting#1"], energy=1)
    provider = _provider_with_card(
        card_id="bloodletting",
        cost=0,
        effects=[
            {"type": "gain_energy", "amount": 2},
            {"type": "lose_hp", "amount": 3},
        ],
    )

    result = play_card(state, "bloodletting#1", None, provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == [
        "gain_energy",
        "lose_hp",
    ]
    assert state.energy == 3
    assert state.player.hp == 37
    assert state.log == ["你打出 Custom Strike，获得 2 点能量，并失去 3 点生命。"]


def test_play_card_battle_trance_draws_and_blocks_later_draw_effects() -> None:
    state = _combat_state(hand=["battle_trance#1", "draw_card#2"])
    state.draw_pile = ["bonus_card#1"]
    provider = _provider_with_card(
        card_id="battle_trance",
        cost=0,
        card_type="power",
        effects=[
            {"type": "draw", "amount": 1},
            {"type": "add_power", "power_id": "battle_trance", "amount": 1},
        ],
    )
    provider.cards().register(
        {
            "id": "draw_card",
            "name": "Draw Card",
            "cost": 0,
            "effects": [{"type": "draw", "amount": 1}],
        }
    )

    first_result = play_card(state, "battle_trance#1", None, provider)
    second_result = play_card(state, "draw_card#2", None, provider)

    assert [effect["type"] for effect in first_result.resolved_effects] == [
        "draw",
        "add_power",
    ]
    assert [effect["type"] for effect in second_result.resolved_effects] == ["draw"]
    assert state.hand == ["bonus_card#1"]
    assert state.discard_pile == ["draw_card#2"]
    assert state.exhaust_pile == []
    assert state.active_powers == [{"power_id": "battle_trance", "amount": 1}]


def test_play_card_true_grit_plus_can_target_a_hand_card_to_exhaust() -> None:
    state = _combat_state(hand=["true_grit_plus#1", "strike#2"])
    provider = _provider_with_card(
        card_id="true_grit_plus",
        cost=1,
        effects=[
            {"type": "block", "amount": 9},
            {"type": "exhaust_target_card"},
        ],
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "Strike",
            "cost": 1,
            "effects": [{"type": "damage", "amount": 6}],
        }
    )

    result = play_card(state, "true_grit_plus#1", "strike#2", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == [
        "block",
        "exhaust_target_card",
    ]
    assert state.hand == []
    assert state.discard_pile == ["true_grit_plus#1"]
    assert state.exhaust_pile == ["strike#2"]
    assert state.player.block == 9
    assert state.log == ["你打出 Custom Strike，获得 9 格挡，并消耗 1 张手牌。"]


def test_play_card_armaments_plus_upgrades_all_remaining_hand_cards() -> None:
    state = _combat_state(hand=["armaments_plus#1", "strike#2", "defend#3"])
    provider = _provider_with_card(
        card_id="armaments_plus",
        cost=1,
        effects=[
            {"type": "block", "amount": 5},
            {"type": "upgrade_all_hand"},
        ],
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "Strike",
            "cost": 1,
            "upgrades_to": "strike_plus",
            "effects": [{"type": "damage", "amount": 6}],
        }
    )
    provider.cards().register(
        {
            "id": "strike_plus",
            "name": "Strike+",
            "cost": 1,
            "effects": [{"type": "damage", "amount": 9}],
        }
    )
    provider.cards().register(
        {
            "id": "defend",
            "name": "Defend",
            "cost": 1,
            "upgrades_to": "defend_plus",
            "effects": [{"type": "block", "amount": 5}],
        }
    )
    provider.cards().register(
        {
            "id": "defend_plus",
            "name": "Defend+",
            "cost": 1,
            "effects": [{"type": "block", "amount": 8}],
        }
    )

    result = play_card(state, "armaments_plus#1", None, provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == [
        "block",
        "upgrade_all_hand",
    ]
    assert state.hand == ["strike_plus#2", "defend_plus#3"]
    assert state.discard_pile == ["armaments_plus#1"]
    assert state.player.block == 5


def test_play_card_clash_rejects_non_attack_cards_in_hand() -> None:
    state = _combat_state(hand=["clash#1", "defend#2"])
    provider = _Provider()
    provider.cards().register(
        {
            "id": "clash",
            "name": "Clash",
            "cost": 0,
            "play_condition": "all_attacks_in_hand",
            "effects": [{"type": "damage", "amount": 14}],
        }
    )
    provider.cards().register(
        {
            "id": "defend",
            "name": "Defend",
            "cost": 1,
            "card_type": "skill",
            "effects": [{"type": "block", "amount": 5}],
        }
    )

    with pytest.raises(ValueError, match="非攻击牌"):
        play_card(state, "clash#1", "enemy-1", provider)


def test_play_card_headbutt_moves_discard_target_to_top_of_draw_pile() -> None:
    state = _combat_state(hand=["headbutt#1"], enemy_hps=[20])
    state.discard_pile = ["bash#9"]
    provider = _Provider()
    provider.cards().register(
        {
            "id": "headbutt",
            "name": "头槌",
            "cost": 1,
            "effects": [
                {"type": "damage", "amount": 9},
                {"type": "put_top_of_deck_from_discard"},
            ],
            "card_type": "attack",
        }
    )
    provider.cards().register(
        {
            "id": "bash",
            "name": "Bash",
            "cost": 2,
            "effects": [{"type": "damage", "amount": 8}],
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 20,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )

    result = play_card(
        state,
        "headbutt#1",
        {"enemy": "enemy-1", "discard": "bash#9"},
        provider,
    )

    assert state.draw_pile[0] == "bash#9"
    assert state.enemies[0].hp == 11


def test_play_card_warcry_moves_selected_hand_card_to_top_of_draw_pile() -> None:
    state = _combat_state(hand=["warcry#1", "strike#2"])
    state.draw_pile = ["defend#3"]
    provider = _Provider()
    provider.cards().register(
        {
            "id": "warcry",
            "name": "战吼",
            "cost": 0,
            "exhausts": True,
            "effects": [
                {"type": "draw", "amount": 1},
                {"type": "put_top_of_deck_from_hand"},
            ],
            "card_type": "skill",
        }
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "打击",
            "cost": 1,
            "effects": [{"type": "damage", "amount": 6}],
            "card_type": "attack",
        }
    )
    provider.cards().register(
        {
            "id": "defend",
            "name": "防御",
            "cost": 1,
            "effects": [{"type": "block", "amount": 5}],
            "card_type": "skill",
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 20,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )

    play_card(state, "warcry#1", {"hand": "strike#2"}, provider)

    assert state.draw_pile == ["strike#2"]
    assert state.hand == ["defend#3"]
    assert state.exhaust_pile == ["warcry#1"]


def test_play_card_double_tap_replays_next_attack_effects_once() -> None:
    state = _combat_state(hand=["strike#1"], enemy_hps=[20])
    state.active_powers = [{"power_id": "double_tap", "amount": 1}]
    provider = _provider_with_card(
        card_id="strike", effects=[{"type": "damage", "amount": 6}]
    )

    result = play_card(state, "strike#1", "enemy-1", provider)

    assert [effect["type"] for effect in result.resolved_effects] == [
        "damage",
        "damage",
    ]
    assert state.enemies[0].hp == 8
    assert state.active_powers == []


def test_play_card_rage_grants_block_after_attack() -> None:
    state = _combat_state(hand=["strike#1"])
    state.active_powers = [{"power_id": "rage", "amount": 3}]
    provider = _provider_with_card(
        card_id="strike", effects=[{"type": "damage", "amount": 6}]
    )

    play_card(state, "strike#1", "enemy-1", provider)

    assert state.player.block == 3


def test_play_card_rupture_grants_strength_when_self_damage_via_card_effect() -> None:
    state = _combat_state(hand=["bloodletting#1"], energy=3)
    state.active_powers = [{"power_id": "rupture", "amount": 1}]
    provider = _provider_with_card(
        card_id="bloodletting",
        cost=0,
        effects=[
            {"type": "gain_energy", "amount": 2},
            {"type": "lose_hp", "amount": 3},
        ],
    )

    play_card(state, "bloodletting#1", None, provider)

    strength_stacks = next(
        (s.stacks for s in state.player.statuses if s.status_id == "strength"), 0
    )
    assert strength_stacks == 1


def test_play_card_spot_weakness_grants_strength_when_enemy_intends_attack() -> None:
    state = _combat_state(hand=["spot_weakness#1"])
    state.enemies[0].current_move = {
        "name": "攻击",
        "effects": [{"type": "damage", "amount": 10}],
    }
    provider = _provider_with_card(
        card_id="spot_weakness",
        effects=[{"type": "spot_weakness_strength", "amount": 3}],
    )

    play_card(state, "spot_weakness#1", "enemy-1", provider)

    strength_stacks = next(
        (s.stacks for s in state.player.statuses if s.status_id == "strength"), 0
    )
    assert strength_stacks == 3
    assert state.log == ["你打出 Custom Strike，获得 3 层力量。"]


def test_play_card_spot_weakness_grants_strength_from_enemy_move_table() -> None:
    state = _combat_state(
        hand=["spot_weakness#1"],
        enemy_ids=["attacking_dummy"],
    )
    provider = _provider_with_card(
        card_id="spot_weakness",
        effects=[{"type": "spot_weakness_strength", "amount": 3}],
    )
    provider.enemies().register(
        {
            "id": "attacking_dummy",
            "name": "Attacking Dummy",
            "hp": 10,
            "move_table": [
                {
                    "move": "slam",
                    "effects": [{"type": "damage", "amount": 10}],
                }
            ],
            "intent_policy": "scripted",
        }
    )

    play_card(state, "spot_weakness#1", "enemy-1", provider)

    strength_stacks = next(
        (s.stacks for s in state.player.statuses if s.status_id == "strength"), 0
    )
    assert strength_stacks == 3


def test_play_card_spot_weakness_grants_strength_for_hexaghost_divider_intent() -> None:
    state = _combat_state(
        hand=["spot_weakness#1"],
        enemy_ids=["hexaghost"],
        enemy_hps=[250],
    )
    provider = _provider_with_card(
        card_id="spot_weakness",
        effects=[{"type": "spot_weakness_strength", "amount": 3}],
    )
    provider.enemies().register(
        {
            "id": "hexaghost",
            "name": "六火幽魂",
            "hp": 250,
            "move_table": [
                {"move": "divider", "effects": [], "once": True},
                {"move": "sear", "effects": [{"type": "damage", "amount": 6}]},
            ],
            "intent_policy": "scripted",
        }
    )

    play_card(state, "spot_weakness#1", "enemy-1", provider)

    strength_stacks = next(
        (s.stacks for s in state.player.statuses if s.status_id == "strength"), 0
    )
    assert strength_stacks == 3


def test_play_card_spot_weakness_does_not_grant_strength_when_enemy_defends() -> None:
    state = _combat_state(hand=["spot_weakness#1"])
    state.enemies[0].current_move = {
        "name": "防御",
        "effects": [{"type": "block", "amount": 10}],
    }
    provider = _provider_with_card(
        card_id="spot_weakness",
        effects=[{"type": "spot_weakness_strength", "amount": 3}],
    )

    play_card(state, "spot_weakness#1", "enemy-1", provider)

    strength_stacks = next(
        (s.stacks for s in state.player.statuses if s.status_id == "strength"), 0
    )
    assert strength_stacks == 0


def test_play_card_feed_kills_enemy_and_increases_max_hp() -> None:
    state = _combat_state(hand=["feed#1"], enemy_hps=[10])
    provider = _provider_with_card(
        card_id="feed",
        cost=1,
        effects=[{"type": "damage_on_kill_gain_max_hp", "amount": 10, "hp_gain": 3}],
    )

    play_card(state, "feed#1", "enemy-1", provider)

    assert state.enemies[0].hp <= 0
    assert state.player.max_hp == 43


def test_play_card_headbutt_logs_damage_and_move_to_draw_pile() -> None:
    state = _combat_state(hand=["headbutt#1"], enemy_hps=[20])
    state.discard_pile = ["bash#9"]
    provider = _provider_with_card(
        card_id="headbutt",
        effects=[
            {"type": "damage", "amount": 9},
            {"type": "put_top_of_deck_from_discard"},
        ],
    )
    provider.cards().register(
        {
            "id": "bash",
            "name": "痛击",
            "cost": 2,
            "effects": [{"type": "damage", "amount": 8}],
        }
    )

    play_card(state, "headbutt#1", {"enemy": "enemy-1", "discard": "bash#9"}, provider)

    assert any("将 1 张弃牌放回牌堆顶" in entry for entry in state.log)


def test_play_card_exhume_logs_exhaust_retrieval() -> None:
    state = _combat_state(hand=["exhume#1"])
    state.exhaust_pile = ["strike#9"]
    provider = _provider_with_card(
        card_id="exhume",
        cost=1,
        effects=[{"type": "select_from_exhaust_to_hand"}],
        card_type="skill",
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "打击",
            "cost": 1,
            "effects": [{"type": "damage", "amount": 6}],
        }
    )

    play_card(state, "exhume#1", {"exhaust": "strike#9"}, provider)

    assert any("从消耗堆" in entry for entry in state.log)


def test_play_card_iron_wave_gains_block_and_deals_damage() -> None:
    state = _combat_state(hand=["iron_wave#1"])
    provider = _provider_with_card(
        card_id="iron_wave",
        effects=[{"type": "block", "amount": 5}, {"type": "damage", "amount": 5}],
    )

    play_card(state, "iron_wave#1", "enemy-1", provider)

    assert state.player.block == 5
    assert state.enemies[0].hp == 5


def test_play_card_limit_break_doubles_strength() -> None:
    state = _combat_state(hand=["limit_break#1"])
    state.player.statuses.append(StatusState(status_id="strength", stacks=3))
    provider = _provider_with_card(
        card_id="limit_break", effects=[{"type": "double_strength"}], card_type="skill"
    )

    play_card(state, "limit_break#1", None, provider)

    assert state.player.statuses == [StatusState(status_id="strength", stacks=6)]


def test_play_card_reaper_deals_damage_to_all_enemies_and_heals() -> None:
    state = _combat_state(hand=["reaper#1"], enemy_hps=[10, 10])
    state.player.hp = 30
    provider = _provider_with_card(
        card_id="reaper",
        effects=[{"type": "damage_lifesteal_all_enemies", "amount": 4}],
    )

    play_card(state, "reaper#1", None, provider)

    assert state.enemies[0].hp == 6
    assert state.enemies[1].hp == 6
    assert state.player.hp == 38


def test_play_card_fiend_fire_exhausts_hand_and_deals_damage_per_card() -> None:
    state = _combat_state(
        hand=["fiend_fire#1", "strike#2", "defend#3"], energy=3, enemy_hps=[100]
    )
    provider = _provider_with_card(
        card_id="fiend_fire",
        effects=[
            {"type": "exhaust_all_in_hand_damage", "amount_per_card": 7},
        ],
        card_type="attack",
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "打击",
            "cost": 1,
            "card_type": "attack",
            "effects": [{"type": "damage", "amount": 6}],
        }
    )
    provider.cards().register(
        {
            "id": "defend",
            "name": "防御",
            "cost": 1,
            "card_type": "skill",
            "effects": [{"type": "block", "amount": 5}],
        }
    )

    play_card(state, "fiend_fire#1", "enemy-1", provider)

    assert "strike#2" in state.exhaust_pile
    assert "defend#3" in state.exhaust_pile
    assert state.hand == []
    assert state.enemies[0].hp == 86


def test_play_card_fiend_fire_appends_damage_log_entry() -> None:
    state = _combat_state(
        hand=["fiend_fire#1", "strike#2", "defend#3"], energy=3, enemy_hps=[100]
    )
    provider = _provider_with_card(
        card_id="fiend_fire",
        effects=[{"type": "exhaust_all_in_hand_damage", "amount_per_card": 7}],
        card_type="attack",
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "打击",
            "cost": 1,
            "card_type": "attack",
            "effects": [{"type": "damage", "amount": 6}],
        }
    )
    provider.cards().register(
        {
            "id": "defend",
            "name": "防御",
            "cost": 1,
            "card_type": "skill",
            "effects": [{"type": "block", "amount": 5}],
        }
    )

    play_card(state, "fiend_fire#1", "enemy-1", provider)

    assert state.log == [
        "你打出 Custom Strike，对 Training Dummy 造成 14 伤害，并消耗 2 张手牌。"
    ]


def test_play_card_corruption_adds_power_and_skills_cost_zero() -> None:
    state = _combat_state(hand=["corruption#1"])
    provider = _provider_with_card(
        card_id="corruption",
        effects=[
            {
                "type": "add_power",
                "power_id": "corruption",
                "amount": 1,
            }
        ],
        card_type="power",
    )

    play_card(state, "corruption#1", None, provider)

    assert any(p.get("power_id") == "corruption" for p in state.active_powers)
    assert state.exhaust_pile == []
    assert state.discard_pile == []


def test_play_card_corruption_allows_zero_cost_skill_play() -> None:
    state = _combat_state(hand=["defend#1"], energy=0)
    state.active_powers = [{"power_id": "corruption", "amount": 1}]
    provider = _provider_with_card(
        card_id="defend",
        cost=2,
        effects=[{"type": "block", "amount": 5}],
        card_type="skill",
    )

    result = play_card(state, "defend#1", None, provider)

    assert result.combat_state.energy == 0
    assert state.exhaust_pile == ["defend#1"]
    assert state.discard_pile == []


def test_play_card_corruption_overrides_temporary_skill_cost() -> None:
    state = _combat_state(hand=["defend#1"], energy=0)
    state.active_powers = [{"power_id": "corruption", "amount": 1}]
    state.temporary_costs = {"defend#1": 2}
    provider = _provider_with_card(
        card_id="defend",
        cost=1,
        effects=[{"type": "block", "amount": 5}],
        card_type="skill",
    )

    result = play_card(state, "defend#1", None, provider)

    assert result.combat_state.energy == 0
    assert state.exhaust_pile == ["defend#1"]


def test_play_card_corruption_does_not_change_attack_cost_or_destination() -> None:
    state = _combat_state(hand=["strike#1"], energy=1)
    state.active_powers = [{"power_id": "corruption", "amount": 1}]
    provider = _provider_with_card(
        card_id="strike",
        cost=1,
        effects=[{"type": "damage", "amount": 6}],
        card_type="attack",
    )

    result = play_card(state, "strike#1", "enemy-1", provider)

    assert result.combat_state.energy == 0
    assert state.exhaust_pile == []
    assert state.discard_pile == ["strike#1"]


def test_shuriken_grants_strength_after_three_attacks_in_one_turn() -> None:
    state = _combat_state(
        hand=["strike#1", "strike#2", "strike#3"],
        energy=3,
        enemy_hps=[30],
    )
    provider = _provider_with_card(
        card_id="strike", effects=[{"type": "damage", "amount": 4}]
    )
    _, hook_registrations = _relic_hook_registrations("shuriken")

    play_card(
        state, "strike#1", "enemy-1", provider, hook_registrations=hook_registrations
    )
    play_card(
        state, "strike#2", "enemy-1", provider, hook_registrations=hook_registrations
    )
    play_card(
        state, "strike#3", "enemy-1", provider, hook_registrations=hook_registrations
    )

    assert state.player.statuses == [StatusState(status_id="strength", stacks=1)]


def test_tingsha_deals_damage_when_player_discards() -> None:
    state = _combat_state(hand=["prepared#1", "strike#2"], enemy_hps=[10])
    provider = _provider_with_card(
        card_id="prepared",
        cost=0,
        effects=[{"type": "discard_target_card"}],
        card_type="skill",
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "Strike",
            "cost": 1,
            "effects": [{"type": "damage", "amount": 6}],
            "card_type": "attack",
        }
    )
    _, hook_registrations = _relic_hook_registrations("tingsha")

    play_card(
        state,
        "prepared#1",
        "strike#2",
        provider,
        hook_registrations=hook_registrations,
    )

    assert state.enemies[0].hp == 7
    assert state.discard_pile == ["strike#2", "prepared#1"]


def test_charons_ashes_hits_all_enemies_when_card_is_exhausted() -> None:
    state = _combat_state(hand=["sentinel_skill#1"], energy=3, enemy_hps=[10, 10])
    provider = _Provider()
    provider.cards().register(
        {
            "id": "sentinel_skill",
            "name": "Sentinel Skill",
            "cost": 1,
            "card_type": "skill",
            "exhausts": True,
            "effects": [],
            "on_exhaust_effects": [{"type": "gain_energy", "amount": 2}],
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )
    _, hook_registrations = _relic_hook_registrations("charons_ashes")

    play_card(
        state, "sentinel_skill#1", None, provider, hook_registrations=hook_registrations
    )

    assert [enemy.hp for enemy in state.enemies] == [7, 7]


def test_gremlin_horn_draws_and_grants_energy_on_enemy_death() -> None:
    state = _combat_state(hand=["strike#1"], energy=1, enemy_hps=[4, 10])
    state.draw_pile = ["bonus_card#1"]
    provider = _provider_with_card(
        card_id="strike", effects=[{"type": "damage", "amount": 4}]
    )
    _, hook_registrations = _relic_hook_registrations("gremlin_horn")

    play_card(
        state, "strike#1", "enemy-1", provider, hook_registrations=hook_registrations
    )

    assert state.energy == 1
    assert state.hand == ["bonus_card#1"]


def test_nunchaku_grants_energy_after_tenth_attack() -> None:
    state = _combat_state(hand=["strike#1"], energy=0, enemy_hps=[20])
    state.card_play_data["relic:nunchaku"] = 9
    provider = _provider_with_card(
        card_id="strike",
        cost=0,
        effects=[{"type": "damage", "amount": 4}],
    )
    _, hook_registrations = _relic_hook_registrations("nunchaku")

    play_card(
        state, "strike#1", "enemy-1", provider, hook_registrations=hook_registrations
    )

    assert state.energy == 1
    assert state.card_play_data["relic:nunchaku"] == 0


def test_pen_nib_doubles_damage_on_tenth_attack() -> None:
    state = _combat_state(hand=["strike#1"], energy=1, enemy_hps=[20])
    state.card_play_data["relic:pen_nib"] = 9
    provider = _provider_with_card(
        card_id="strike", effects=[{"type": "damage", "amount": 6}]
    )
    _, hook_registrations = _relic_hook_registrations("pen_nib")

    play_card(
        state, "strike#1", "enemy-1", provider, hook_registrations=hook_registrations
    )

    assert state.enemies[0].hp == 8
    assert state.card_play_data["relic:pen_nib"] == 0


def test_ink_bottle_draws_after_tenth_card_played() -> None:
    state = _combat_state(hand=["skill_guard#1"], energy=1, enemy_hps=[20])
    state.draw_pile = ["bonus_card#1"]
    state.card_play_data["relic:ink_bottle"] = 9
    provider = _provider_with_card(
        card_id="skill_guard",
        cost=1,
        effects=[{"type": "block", "amount": 5}],
        card_type="skill",
    )
    _, hook_registrations = _relic_hook_registrations("ink_bottle")

    play_card(
        state, "skill_guard#1", None, provider, hook_registrations=hook_registrations
    )

    assert state.hand == ["bonus_card#1"]
    assert state.card_play_data["relic:ink_bottle"] == 0


def test_hovering_kite_grants_energy_next_turn_after_discard() -> None:
    state = _combat_state(hand=["prepared#1", "strike#2"], energy=0, enemy_hps=[10])
    provider = _provider_with_card(
        card_id="prepared",
        cost=0,
        effects=[{"type": "discard_target_card"}],
        card_type="skill",
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "Strike",
            "cost": 1,
            "effects": [{"type": "damage", "amount": 6}],
            "card_type": "attack",
        }
    )
    _, hook_registrations = _relic_hook_registrations("hovering_kite")

    play_card(
        state, "prepared#1", "strike#2", provider, hook_registrations=hook_registrations
    )
    state.round_number = 2

    from slay_the_spire.domain.combat.turn_flow import start_turn

    start_turn(state, registry=provider, hook_registrations=hook_registrations)

    assert state.energy == 4


def test_kunai_grants_dexterity_after_three_attacks_in_one_turn() -> None:
    state = _combat_state(
        hand=["strike#1", "strike#2", "strike#3"],
        energy=3,
        enemy_hps=[30],
    )
    provider = _provider_with_card(
        card_id="strike", effects=[{"type": "damage", "amount": 4}]
    )
    _, hook_registrations = _relic_hook_registrations("kunai")

    play_card(
        state, "strike#1", "enemy-1", provider, hook_registrations=hook_registrations
    )
    play_card(
        state, "strike#2", "enemy-1", provider, hook_registrations=hook_registrations
    )
    play_card(
        state, "strike#3", "enemy-1", provider, hook_registrations=hook_registrations
    )

    assert state.player.statuses == [StatusState(status_id="dexterity", stacks=1)]


def test_ornamental_fan_grants_block_after_three_attacks_in_one_turn() -> None:
    state = _combat_state(
        hand=["strike#1", "strike#2", "strike#3"],
        energy=3,
        enemy_hps=[30],
    )
    provider = _provider_with_card(
        card_id="strike", effects=[{"type": "damage", "amount": 4}]
    )
    _, hook_registrations = _relic_hook_registrations("ornamental_fan")

    play_card(
        state, "strike#1", "enemy-1", provider, hook_registrations=hook_registrations
    )
    play_card(
        state, "strike#2", "enemy-1", provider, hook_registrations=hook_registrations
    )
    play_card(
        state, "strike#3", "enemy-1", provider, hook_registrations=hook_registrations
    )

    assert state.player.block == 4


def test_letter_opener_hits_all_enemies_after_three_skills_in_one_turn() -> None:
    state = _combat_state(
        hand=["guard#1", "guard#2", "guard#3"],
        energy=3,
        enemy_hps=[20, 20],
    )
    provider = _provider_with_card(
        card_id="guard",
        cost=1,
        effects=[{"type": "block", "amount": 5}],
        card_type="skill",
    )
    _, hook_registrations = _relic_hook_registrations("letter_opener")

    play_card(state, "guard#1", None, provider, hook_registrations=hook_registrations)
    play_card(state, "guard#2", None, provider, hook_registrations=hook_registrations)
    play_card(state, "guard#3", None, provider, hook_registrations=hook_registrations)

    assert [enemy.hp for enemy in state.enemies] == [15, 15]


def test_bird_faced_urn_heals_when_power_is_played() -> None:
    state = _combat_state(hand=["inflame#1"], energy=1)
    state.player.hp = 30
    provider = _provider_with_card(
        card_id="inflame",
        effects=[{"type": "add_power", "power_id": "inflame", "amount": 2}],
        card_type="power",
    )
    _, hook_registrations = _relic_hook_registrations("bird_faced_urn")

    play_card(state, "inflame#1", None, provider, hook_registrations=hook_registrations)

    assert state.player.hp == 32


def test_mummified_hand_uses_stable_random_target_selection() -> None:
    state = _combat_state(hand=["inflame#1", "bash#2", "strike#3"], energy=2)
    provider = _provider_with_card(
        card_id="inflame",
        effects=[{"type": "add_power", "power_id": "inflame", "amount": 2}],
        card_type="power",
    )
    provider.cards().register(
        {
            "id": "bash",
            "name": "Bash",
            "cost": 2,
            "effects": [{"type": "damage", "amount": 8}],
            "card_type": "attack",
        }
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "Strike",
            "cost": 2,
            "effects": [{"type": "damage", "amount": 6}],
            "card_type": "attack",
        }
    )
    _, hook_registrations = _relic_hook_registrations("mummified_hand")

    play_card(state, "inflame#1", None, provider, hook_registrations=hook_registrations)

    assert state.temporary_costs == {"strike#3": 0}


def test_orange_pellets_clears_player_debuffs_after_attack_skill_and_power() -> None:
    state = _combat_state(hand=["strike#1", "guard#2", "inflame#3"], energy=3)
    state.player.statuses = [
        StatusState(status_id="weak", stacks=1),
        StatusState(status_id="vulnerable", stacks=1),
        StatusState(status_id="frail", stacks=1),
        StatusState(status_id="poison", stacks=2),
    ]
    provider = _provider_with_card(
        card_id="strike", effects=[{"type": "damage", "amount": 4}]
    )
    provider.cards().register(
        {
            "id": "guard",
            "name": "Guard",
            "cost": 1,
            "effects": [{"type": "block", "amount": 5}],
            "card_type": "skill",
        }
    )
    provider.cards().register(
        {
            "id": "inflame",
            "name": "Inflame",
            "cost": 1,
            "effects": [{"type": "add_power", "power_id": "inflame", "amount": 2}],
            "card_type": "power",
        }
    )
    _, hook_registrations = _relic_hook_registrations("orange_pellets")

    play_card(
        state, "strike#1", "enemy-1", provider, hook_registrations=hook_registrations
    )
    play_card(state, "guard#2", None, provider, hook_registrations=hook_registrations)
    play_card(state, "inflame#3", None, provider, hook_registrations=hook_registrations)

    assert state.player.statuses == [StatusState(status_id="strength", stacks=2)]


def test_tough_bandages_grants_block_when_player_discards() -> None:
    state = _combat_state(hand=["prepared#1", "strike#2"], energy=0, enemy_hps=[10])
    provider = _provider_with_card(
        card_id="prepared",
        cost=0,
        effects=[{"type": "discard_target_card"}],
        card_type="skill",
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "Strike",
            "cost": 1,
            "effects": [{"type": "damage", "amount": 6}],
            "card_type": "attack",
        }
    )
    _, hook_registrations = _relic_hook_registrations("tough_bandages")

    play_card(
        state, "prepared#1", "strike#2", provider, hook_registrations=hook_registrations
    )

    assert state.player.block == 3


def test_dead_branch_adds_stable_random_card_to_hand_when_card_is_exhausted() -> None:
    state = _combat_state(hand=["sentinel_skill#1"], energy=3, enemy_hps=[10])
    provider = _Provider()
    provider.cards().register(
        {
            "id": "sentinel_skill",
            "name": "Sentinel Skill",
            "cost": 1,
            "card_type": "skill",
            "exhausts": True,
            "effects": [],
            "on_exhaust_effects": [{"type": "gain_energy", "amount": 2}],
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )
    provider.cards().register(
        {
            "id": "anger",
            "name": "Anger",
            "cost": 0,
            "effects": [{"type": "damage", "amount": 6}],
            "card_type": "attack",
        }
    )
    provider.cards().register(
        {
            "id": "bash",
            "name": "Bash",
            "cost": 2,
            "effects": [{"type": "damage", "amount": 8}],
            "card_type": "attack",
        }
    )
    provider.cards().register(
        {
            "id": "body_slam",
            "name": "Body Slam",
            "cost": 1,
            "effects": [{"type": "damage_equal_to_block"}],
            "card_type": "attack",
        }
    )
    _, hook_registrations = _relic_hook_registrations("dead_branch")

    play_card(
        state, "sentinel_skill#1", None, provider, hook_registrations=hook_registrations
    )

    assert state.hand == ["bash#1"]


def test_play_card_infernal_blade_adds_zero_cost_attack_to_hand() -> None:
    state = _combat_state(hand=["infernal_blade#1"], energy=1, enemy_hps=[10])
    provider = _Provider()
    provider.cards().register(
        {
            "id": "infernal_blade",
            "name": "地狱之刃",
            "cost": 1,
            "card_type": "skill",
            "exhausts": True,
            "effects": [{"type": "add_random_attack_zero_cost_to_hand"}],
        }
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "Strike",
            "cost": 1,
            "effects": [{"type": "damage", "amount": 6}],
            "card_type": "attack",
        }
    )
    provider.cards().register(
        {
            "id": "reaper",
            "name": "Reaper",
            "cost": 2,
            "effects": [{"type": "damage_lifesteal_all_enemies", "amount": 4}],
            "card_type": "attack",
        }
    )
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )

    play_card(state, "infernal_blade#1", None, provider)

    assert state.energy == 0
    assert state.hand == ["strike#1"]
    assert state.temporary_costs == {"strike#1": 0}
    assert state.exhaust_pile == ["infernal_blade#1"]


def test_unceasing_top_draws_when_hand_becomes_empty() -> None:
    state = _combat_state(hand=["strike#1"], energy=0, enemy_hps=[10])
    state.draw_pile = ["bonus_card#1"]
    provider = _provider_with_card(
        card_id="strike",
        cost=0,
        effects=[{"type": "damage", "amount": 4}],
    )
    _, hook_registrations = _relic_hook_registrations("unceasing_top")

    play_card(
        state, "strike#1", "enemy-1", provider, hook_registrations=hook_registrations
    )

    assert state.hand == ["bonus_card#1"]
