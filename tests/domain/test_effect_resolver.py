from __future__ import annotations

import pytest

from slay_the_spire.content.registries import CardRegistry
from slay_the_spire.domain.effects.effect_resolver import (
    resolve_effect_queue,
    resolve_next_effect,
)
from slay_the_spire.domain.effects import effect_types
from slay_the_spire.domain.effects.effect_types import (
    EFFECT_EMIT_HOOK,
    EFFECT_NOOP,
    draw_effect,
    damage_effect,
    noop_effect,
)
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.statuses import StatusState


class _CardProvider:
    def __init__(self) -> None:
        self._cards = CardRegistry()

    def cards(self) -> CardRegistry:
        return self._cards


def make_combat_state(
    *,
    enemies: list[EnemyState],
    energy: int = 3,
    effect_queue: list[dict[str, object]] | None = None,
) -> CombatState:
    return CombatState(
        schema_version=1,
        round_number=1,
        energy=energy,
        hand=[],
        draw_pile=["strike-1", "defend-1"],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=70,
            max_hp=70,
            block=0,
            statuses=[],
        ),
        enemies=enemies,
        effect_queue=list(effect_queue or []),
        log=[],
    )


def make_enemy(instance_id: str, hp: int) -> EnemyState:
    return EnemyState(
        instance_id=instance_id,
        enemy_id="cultist",
        hp=hp,
        max_hp=max(hp, 1),
        block=0,
        statuses=[],
    )


def _register_test_card(
    provider: _CardProvider,
    *,
    card_id: str,
    card_type: str,
    on_exhaust_effects: list[dict[str, object]] | None = None,
) -> None:
    provider.cards().register(
        {
            "id": card_id,
            "name": card_id,
            "cost": 1,
            "effects": [],
            "card_type": card_type,
            "on_exhaust_effects": on_exhaust_effects or [],
        }
    )


def test_full_ironclad_effect_types_are_declared() -> None:
    assert (
        effect_types.EFFECT_DAMAGE_WITH_STRENGTH_MULTIPLIER
        == "damage_with_strength_multiplier"
    )
    assert effect_types.EFFECT_DAMAGE_PER_STRIKE_IN_DECK == "damage_per_strike_in_deck"
    assert effect_types.EFFECT_DAMAGE_EQUAL_TO_BLOCK == "damage_equal_to_block"
    assert effect_types.EFFECT_WEAK_ALL_ENEMIES == "weak_all_enemies"
    assert effect_types.EFFECT_ADD_CARD_TO_DRAW_PILE == "add_card_to_draw_pile"
    assert effect_types.EFFECT_ADD_CARDS_TO_HAND == "add_cards_to_hand"
    assert (
        effect_types.EFFECT_EXHAUST_ALL_NON_ATTACKS_GAIN_BLOCK
        == "exhaust_all_non_attacks_gain_block"
    )
    assert (
        effect_types.EFFECT_EXHAUST_ALL_NON_ATTACKS_IN_HAND
        == "exhaust_all_non_attacks_in_hand"
    )
    assert effect_types.EFFECT_EXHAUST_ALL_IN_HAND == "exhaust_all_in_hand"
    assert (
        effect_types.EFFECT_EXHAUST_ALL_IN_HAND_DAMAGE == "exhaust_all_in_hand_damage"
    )
    assert effect_types.EFFECT_DOUBLE_STRENGTH == "double_strength"
    assert (
        effect_types.EFFECT_DAMAGE_LIFESTEAL_ALL_ENEMIES
        == "damage_lifesteal_all_enemies"
    )
    assert (
        effect_types.EFFECT_SELECT_FROM_EXHAUST_TO_HAND == "select_from_exhaust_to_hand"
    )
    assert (
        effect_types.EFFECT_PUT_TOP_OF_DECK_FROM_DISCARD
        == "put_top_of_deck_from_discard"
    )
    assert effect_types.EFFECT_PUT_TOP_OF_DECK_FROM_HAND == "put_top_of_deck_from_hand"
    assert effect_types.EFFECT_PLAY_TOP_OF_DECK == "play_top_of_deck"
    assert (
        effect_types.EFFECT_ADD_RANDOM_ATTACK_ZERO_COST_TO_HAND
        == "add_random_attack_zero_cost_to_hand"
    )
    assert effect_types.EFFECT_COPY_CARD_TO_HAND == "copy_card_to_hand"
    assert (
        effect_types.EFFECT_DAMAGE_ON_KILL_GAIN_MAX_HP == "damage_on_kill_gain_max_hp"
    )
    assert effect_types.EFFECT_SPOT_WEAKNESS_STRENGTH == "spot_weakness_strength"
    assert effect_types.EFFECT_DROPKICK_EFFECT == "dropkick_effect"
    assert effect_types.EFFECT_RAMPAGE_DAMAGE == "rampage_damage"


@pytest.mark.guardrail
def test_effects_append_to_queue_tail_in_order():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3)],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=3
            ),
            noop_effect(reason="existing"),
        ],
    )

    resolve_next_effect(state)

    assert [effect["type"] for effect in state.effect_queue] == [
        EFFECT_NOOP,
        EFFECT_EMIT_HOOK,
    ]
    assert [effect.get("hook_name") for effect in state.effect_queue[1:]] == [
        "on_enemy_defeated"
    ]


@pytest.mark.guardrail
def test_resolver_never_recurses_synchronously():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3), make_enemy("enemy-2", 10)],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=3
            ),
        ],
    )

    registrations = [
        HookRegistration(
            hook_name="on_enemy_defeated",
            category="status",
            priority=0,
            source_type="player",
            source_instance_id="player-1",
            registration_index=0,
            effects=[noop_effect(reason="hook-follow-up")],
        ),
    ]

    resolve_next_effect(state, hook_registrations=registrations)

    assert state.player.block == 0
    assert len(state.effect_queue) == 1
    assert state.effect_queue[0]["type"] == EFFECT_EMIT_HOOK
    assert state.effect_queue[0]["hook_name"] == "on_enemy_defeated"


@pytest.mark.guardrail
def test_dead_targets_become_noop_effects():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 1)],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=2
            ),
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=2
            ),
        ],
    )

    first = resolve_next_effect(state)
    second = resolve_next_effect(state)

    assert first["type"] == "damage"
    assert second["type"] == EFFECT_NOOP
    assert state.enemies[0].hp == 0


@pytest.mark.guardrail
def test_on_enemy_defeated_enqueues_before_on_combat_end():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 4)],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=4
            ),
        ],
    )

    resolve_next_effect(state)

    assert [effect["hook_name"] for effect in state.effect_queue] == [
        "on_enemy_defeated"
    ]


@pytest.mark.guardrail
def test_on_combat_end_is_enqueued_only_after_defeat_hook_resolves():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 4)],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=4
            ),
            noop_effect(reason="existing-tail"),
        ],
    )
    registrations = [
        HookRegistration(
            hook_name="on_enemy_defeated",
            category="status",
            priority=0,
            source_type="player",
            source_instance_id="player-1",
            registration_index=0,
            effects=[noop_effect(reason="defeat-follow-up")],
        ),
    ]

    resolve_next_effect(state)
    resolve_next_effect(state)
    resolve_next_effect(state, hook_registrations=registrations)

    assert [effect["type"] for effect in state.effect_queue] == [
        EFFECT_NOOP,
        EFFECT_EMIT_HOOK,
    ]
    assert state.effect_queue[0]["reason"] == "defeat-follow-up"
    assert state.effect_queue[1]["hook_name"] == "on_combat_end"


@pytest.mark.guardrail
def test_on_combat_end_fires_once_even_if_multiple_enemies_die():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 2), make_enemy("enemy-2", 2)],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=2
            ),
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-2", amount=2
            ),
        ],
    )

    resolve_next_effect(state)
    resolve_next_effect(state)

    assert [effect.get("hook_name") for effect in state.effect_queue] == [
        "on_enemy_defeated",
        "on_enemy_defeated",
    ]

    resolve_next_effect(state)
    resolve_next_effect(state)

    assert [effect.get("hook_name") for effect in state.effect_queue] == [
        "on_combat_end",
    ]


def test_add_card_to_discard_creates_new_instance_ids() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3)],
        effect_queue=[
            {
                "type": "add_card_to_discard",
                "card_id": "burn",
                "count": 2,
            }
        ],
    )

    resolved = resolve_effect_queue(state)

    assert [effect["type"] for effect in resolved] == ["add_card_to_discard"]
    assert state.discard_pile == ["burn#1", "burn#2"]


def test_damage_equal_to_block_uses_current_player_block() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 30)],
        effect_queue=[
            {
                "type": "damage_equal_to_block",
                "source_instance_id": "player-1",
                "target_instance_id": "enemy-1",
            }
        ],
    )
    state.player.block = 11

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "damage_equal_to_block"
    assert resolved["result"] == {
        "applied_amount": 11,
        "blocked": 0,
        "actual_damage": 11,
        "target_defeated": False,
    }
    assert state.enemies[0].hp == 19


def test_damage_with_strength_multiplier_uses_scaled_strength() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 30)],
        effect_queue=[
            {
                "type": "damage_with_strength_multiplier",
                "source_instance_id": "player-1",
                "target_instance_id": "enemy-1",
                "base": 14,
                "multiplier": 3,
            }
        ],
    )
    state.player.statuses.append(StatusState(status_id="strength", stacks=2))

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "damage_with_strength_multiplier"
    assert resolved["result"] == {
        "applied_amount": 20,
        "blocked": 0,
        "actual_damage": 20,
        "target_defeated": False,
    }
    assert state.enemies[0].hp == 10


def test_damage_per_strike_in_deck_counts_strike_cards_in_all_zones() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 40)],
        effect_queue=[
            {
                "type": "damage_per_strike_in_deck",
                "source_instance_id": "player-1",
                "target_instance_id": "enemy-1",
                "base": 6,
                "bonus_per_strike": 2,
            }
        ],
    )
    state.hand = ["strike#1", "perfected_strike#5"]
    state.draw_pile = ["wild_strike#2", "defend#3"]
    state.discard_pile = ["pommel_strike#4"]
    state.exhaust_pile = ["twin_strike#6", "bash#7"]

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "damage_per_strike_in_deck"
    assert resolved["result"] == {
        "applied_amount": 16,
        "blocked": 0,
        "actual_damage": 16,
        "target_defeated": False,
        "strike_count": 5,
    }
    assert state.enemies[0].hp == 24


def test_damage_per_strike_in_deck_counts_other_perfected_strike_copies() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 50)],
        effect_queue=[
            {
                "type": "damage_per_strike_in_deck",
                "source_instance_id": "player-1",
                "target_instance_id": "enemy-1",
                "base": 6,
                "bonus_per_strike": 2,
            }
        ],
    )
    state.hand = ["perfected_strike#5", "strike#1"]
    state.draw_pile = ["perfected_strike#8", "wild_strike#2"]
    state.discard_pile = ["pommel_strike#4"]
    state.exhaust_pile = ["twin_strike#6", "bash#7"]

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "damage_per_strike_in_deck"
    assert resolved["result"] == {
        "applied_amount": 18,
        "blocked": 0,
        "actual_damage": 18,
        "target_defeated": False,
        "strike_count": 6,
    }
    assert state.enemies[0].hp == 32


def test_rampage_damage_scales_with_per_card_play_counter() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 50)],
        effect_queue=[
            {
                "type": "rampage_damage",
                "source_instance_id": "player-1",
                "target_instance_id": "enemy-1",
                "card_instance_id": "rampage_plus#1",
                "amount": 8,
                "increment": 8,
            },
            {
                "type": "rampage_damage",
                "source_instance_id": "player-1",
                "target_instance_id": "enemy-1",
                "card_instance_id": "rampage_plus#1",
                "amount": 8,
                "increment": 8,
            },
        ],
    )

    first = resolve_next_effect(state)
    second = resolve_next_effect(state)

    assert first["type"] == "rampage_damage"
    assert first["result"] == {
        "applied_amount": 8,
        "blocked": 0,
        "actual_damage": 8,
        "target_defeated": False,
        "play_count_before": 0,
        "play_count_after": 1,
    }
    assert second["type"] == "rampage_damage"
    assert second["result"] == {
        "applied_amount": 16,
        "blocked": 0,
        "actual_damage": 16,
        "target_defeated": False,
        "play_count_before": 1,
        "play_count_after": 2,
    }
    assert state.enemies[0].hp == 26
    assert state.card_play_data["rampage_plus#1"] == 2


def test_add_card_to_draw_pile_creates_new_cards() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3)],
        effect_queue=[
            {
                "type": "add_card_to_draw_pile",
                "card_id": "wound",
                "count": 2,
            }
        ],
    )

    resolved = resolve_effect_queue(state)

    assert [effect["type"] for effect in resolved] == ["add_card_to_draw_pile"]
    assert state.draw_pile[-2:] == ["wound#1", "wound#2"]


def test_add_cards_to_hand_creates_new_cards() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3)],
        effect_queue=[
            {
                "type": "add_cards_to_hand",
                "card_id": "wound",
                "count": 2,
            }
        ],
    )

    resolved = resolve_effect_queue(state)

    assert [effect["type"] for effect in resolved] == ["add_cards_to_hand"]
    assert state.hand == ["wound#1", "wound#2"]


def test_add_random_attack_zero_cost_to_hand_excludes_lifesteal_attacks() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3)],
        effect_queue=[{"type": "add_random_attack_zero_cost_to_hand"}],
    )
    provider = _CardProvider()
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

    resolved = resolve_next_effect(state, registry=provider)

    assert resolved == {
        "type": "add_random_attack_zero_cost_to_hand",
        "result": {"created_card_instance_id": "strike#1"},
    }
    assert state.hand == ["strike#1"]
    assert state.temporary_costs == {"strike#1": 0}


def test_gain_energy_effect_increases_combat_energy() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3)],
        energy=3,
        effect_queue=[{"type": "gain_energy", "amount": 1}],
    )

    resolved = resolve_effect_queue(state)

    assert resolved == [
        {"type": "gain_energy", "amount": 1, "result": {"gained_energy": 1}}
    ]
    assert state.energy == 4


def test_add_power_effect_appends_active_power_and_applies_inflame_strength() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3)],
        effect_queue=[{"type": "add_power", "power_id": "inflame", "amount": 2}],
    )

    resolved = resolve_effect_queue(state)

    assert resolved == [
        {
            "type": "add_power",
            "power_id": "inflame",
            "amount": 2,
            "result": {"power_id": "inflame", "amount": 2, "total_amount": 2},
        }
    ]
    assert state.active_powers == [{"power_id": "inflame", "amount": 2}]
    assert state.player.statuses == [StatusState(status_id="strength", stacks=2)]


def test_strength_effect_defaults_to_source_target_when_target_is_missing() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3)],
        effect_queue=[
            {"type": "strength", "source_instance_id": "enemy-1", "amount": 3}
        ],
    )

    resolved = resolve_next_effect(state)

    assert resolved == {
        "type": "strength",
        "source_instance_id": "enemy-1",
        "amount": 3,
        "result": {"applied_stacks": 3},
    }
    assert state.enemies[0].statuses == [StatusState(status_id="strength", stacks=3)]


def test_damage_effect_reports_structured_resolution_details():
    enemy = make_enemy("enemy-1", 10)
    enemy.block = 2
    enemy.statuses.append(StatusState(status_id="vulnerable", stacks=1))
    state = make_combat_state(
        enemies=[enemy],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=4
            ),
        ],
    )

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "damage"
    assert resolved["result"] == {
        "applied_amount": 6,
        "blocked": 2,
        "actual_damage": 4,
        "target_defeated": False,
    }


def test_damage_effect_applies_source_strength_to_player_damage() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=4
            ),
        ],
    )
    state.player.statuses.append(StatusState(status_id="strength", stacks=2))

    resolved = resolve_next_effect(state)

    assert resolved["result"] == {
        "applied_amount": 6,
        "blocked": 0,
        "actual_damage": 6,
        "target_defeated": False,
    }
    assert state.enemies[0].hp == 4


def test_damage_effect_applies_strength_to_each_damage_hit() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 20)],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=2
            ),
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=2
            ),
        ],
    )
    state.player.statuses.append(StatusState(status_id="strength", stacks=2))

    resolved = resolve_effect_queue(state)

    assert [effect["result"]["applied_amount"] for effect in resolved] == [4, 4]
    assert [effect["result"]["actual_damage"] for effect in resolved] == [4, 4]
    assert state.enemies[0].hp == 12


def test_damage_effect_applies_enemy_strength_to_player_damage() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            damage_effect(
                source_instance_id="enemy-1", target_instance_id="player-1", amount=4
            ),
        ],
    )
    state.enemies[0].statuses.append(StatusState(status_id="strength", stacks=2))

    resolved = resolve_next_effect(state)

    assert resolved["result"] == {
        "applied_amount": 6,
        "blocked": 0,
        "actual_damage": 6,
        "target_defeated": False,
    }
    assert state.player.hp == 64


def test_damage_effect_keeps_strength_weak_and_vulnerable_order_semantics() -> None:
    enemy = make_enemy("enemy-1", 20)
    enemy.statuses.append(StatusState(status_id="vulnerable", stacks=1))
    state = make_combat_state(
        enemies=[enemy],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=5
            ),
        ],
    )
    state.player.statuses.append(StatusState(status_id="strength", stacks=1))
    state.player.statuses.append(StatusState(status_id="weak", stacks=1))

    resolved = resolve_next_effect(state)

    assert resolved["result"] == {
        "applied_amount": 6,
        "blocked": 0,
        "actual_damage": 6,
        "target_defeated": False,
    }
    assert state.enemies[0].hp == 14


def test_strength_effect_allows_negative_stacks_on_player() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "strength",
                "source_instance_id": "enemy-1",
                "target_instance_id": "player-1",
                "amount": -2,
            }
        ],
    )

    resolved = resolve_effect_queue(state)

    assert resolved == [
        {
            "type": "strength",
            "source_instance_id": "enemy-1",
            "target_instance_id": "player-1",
            "amount": -2,
            "result": {"applied_stacks": -2},
        }
    ]
    assert state.player.statuses == [StatusState(status_id="strength", stacks=-2)]


def test_strength_effect_removes_status_when_negative_stacks_cancel_to_zero() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "strength",
                "source_instance_id": "enemy-1",
                "target_instance_id": "player-1",
                "amount": -2,
            }
        ],
    )
    state.player.statuses.append(StatusState(status_id="strength", stacks=2))

    resolved = resolve_effect_queue(state)

    assert resolved[0]["result"] == {"applied_stacks": -2}
    assert state.player.statuses == []


def test_dexterity_effect_applies_negative_stacks_on_player() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "dexterity",
                "source_instance_id": "enemy-1",
                "target_instance_id": "player-1",
                "amount": -2,
            }
        ],
    )

    resolved = resolve_effect_queue(state)

    assert resolved == [
        {
            "type": "dexterity",
            "source_instance_id": "enemy-1",
            "target_instance_id": "player-1",
            "amount": -2,
            "result": {"applied_stacks": -2},
        }
    ]
    assert state.player.statuses == [StatusState(status_id="dexterity", stacks=-2)]


def test_dexterity_effect_removes_status_when_negative_stacks_cancel_to_zero() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "dexterity",
                "source_instance_id": "enemy-1",
                "target_instance_id": "player-1",
                "amount": -2,
            }
        ],
    )
    state.player.statuses.append(StatusState(status_id="dexterity", stacks=2))

    resolved = resolve_effect_queue(state)

    assert resolved[0]["result"] == {"applied_stacks": -2}
    assert state.player.statuses == []


def test_block_effect_applies_player_dexterity_and_floors_at_zero() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "block",
                "source_instance_id": "player-1",
                "target_instance_id": "player-1",
                "amount": 5,
            }
        ],
    )
    state.player.statuses.append(StatusState(status_id="dexterity", stacks=-7))

    resolved = resolve_effect_queue(state)

    assert resolved[0]["result"] == {"gained_block": 0}
    assert state.player.block == 0


def test_block_effect_triggers_juggernaut_damage() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 20), make_enemy("enemy-2", 20)],
        effect_queue=[
            {
                "type": "block",
                "source_instance_id": "player-1",
                "target_instance_id": "player-1",
                "amount": 5,
            }
        ],
    )
    state.active_powers.append({"power_id": "juggernaut", "amount": 7})

    resolved = resolve_effect_queue(state)

    assert [effect["type"] for effect in resolved] == ["block", "damage"]
    assert resolved[0]["result"] == {"gained_block": 5}
    assert resolved[1]["power_id"] == "juggernaut"
    assert resolved[1]["target_instance_id"] == "enemy-1"
    assert state.player.block == 5
    assert state.enemies[0].hp == 13
    assert state.enemies[1].hp == 20


def test_juggernaut_damage_does_not_scale_with_strength() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 20)],
        effect_queue=[
            {
                "type": "block",
                "source_instance_id": "player-1",
                "target_instance_id": "player-1",
                "amount": 5,
            }
        ],
    )
    state.player.statuses.append(StatusState(status_id="strength", stacks=3))
    state.active_powers.append({"power_id": "juggernaut", "amount": 7})

    resolve_effect_queue(state)

    assert state.enemies[0].hp == 13


def test_double_block_effect_doubles_current_block() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "double_block",
                "source_instance_id": "player-1",
                "target_instance_id": "player-1",
            }
        ],
    )
    state.player.block = 7

    resolved = resolve_effect_queue(state)

    assert resolved[0]["type"] == "double_block"
    assert resolved[0]["result"] == {"previous_block": 7, "doubled_block": 14}
    assert state.player.block == 14


def test_damage_effect_applies_negative_strength_and_floors_at_zero() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            damage_effect(
                source_instance_id="player-1", target_instance_id="enemy-1", amount=6
            ),
        ],
    )
    state.player.statuses.append(StatusState(status_id="strength", stacks=-8))

    resolved = resolve_effect_queue(state)

    assert resolved[0]["result"]["applied_amount"] == 0
    assert resolved[0]["result"]["actual_damage"] == 0
    assert state.enemies[0].hp == 10


def test_draw_effect_refills_from_discard_pile_when_draw_pile_runs_out():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[draw_effect(target_instance_id="player-1", amount=2)],
    )
    state.hand = []
    state.draw_pile = ["pommel_a#1"]
    state.discard_pile = ["pommel_b#1"]

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "draw"
    assert resolved["result"] == {"drawn_count": 2}
    assert state.hand == ["pommel_a#1", "pommel_b#1"]
    assert state.draw_pile == []
    assert state.discard_pile == []


def test_draw_effect_shuffles_discard_pile_when_refilling_draw_pile() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[draw_effect(target_instance_id="player-1", amount=2)],
    )
    state.hand = []
    state.draw_pile = ["pommel_a#1"]
    state.discard_pile = [
        "pommel_b#1",
        "pommel_c#1",
        "pommel_d#1",
        "pommel_e#1",
    ]

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "draw"
    assert resolved["result"] == {"drawn_count": 2}
    assert state.hand == ["pommel_a#1", "pommel_d#1"]
    assert state.draw_pile == ["pommel_c#1", "pommel_e#1", "pommel_b#1"]
    assert state.discard_pile == []


def test_lose_hp_effect_reduces_player_hp_without_touching_block() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {"type": "lose_hp", "target_instance_id": "player-1", "amount": 3}
        ],
    )
    state.player.block = 9

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "lose_hp"
    assert resolved["result"] == {"actual_hp_lost": 3}
    assert state.player.hp == 67
    assert state.player.block == 9


def test_exhaust_random_hand_effect_moves_a_remaining_hand_card_to_exhaust() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[{"type": "exhaust_random_hand", "count": 1}],
    )
    state.hand = ["true_grit_plus#1", "strike#2", "defend#3"]

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "exhaust_random_hand"
    exhausted_cards = resolved["result"]["exhausted_cards"]
    assert len(exhausted_cards) == 1
    assert exhausted_cards[0] in {"true_grit_plus#1", "strike#2", "defend#3"}
    assert len(state.hand) == 2
    assert exhausted_cards[0] not in state.hand
    assert state.exhaust_pile == exhausted_cards


def test_exhaust_all_non_attacks_gain_block_moves_cards_and_grants_block() -> None:
    provider = _CardProvider()
    _register_test_card(provider, card_id="defend", card_type="skill")
    _register_test_card(provider, card_id="ghostly_armor", card_type="skill")
    _register_test_card(provider, card_id="strike", card_type="attack")
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "exhaust_all_non_attacks_gain_block",
                "source_instance_id": "player-1",
                "amount_per_card": 5,
            }
        ],
    )
    state.hand = ["defend#1", "ghostly_armor#1", "strike#1"]

    resolved = resolve_next_effect(state, registry=provider)

    assert resolved["type"] == "exhaust_all_non_attacks_gain_block"
    assert resolved["result"] == {
        "exhausted_cards": ["defend#1", "ghostly_armor#1"],
        "exhausted_count": 2,
        "gained_block": 10,
    }
    assert state.hand == ["strike#1"]
    assert state.exhaust_pile == ["defend#1", "ghostly_armor#1"]
    assert state.player.block == 10


def test_exhaust_all_non_attacks_gain_block_triggers_juggernaut_damage() -> None:
    provider = _CardProvider()
    _register_test_card(provider, card_id="defend", card_type="skill")
    _register_test_card(provider, card_id="strike", card_type="attack")
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 20)],
        effect_queue=[
            {
                "type": "exhaust_all_non_attacks_gain_block",
                "source_instance_id": "player-1",
                "amount_per_card": 5,
            }
        ],
    )
    state.active_powers.append({"power_id": "juggernaut", "amount": 7})
    state.hand = ["defend#1", "strike#1"]

    resolved = resolve_effect_queue(state, registry=provider)

    assert [effect["type"] for effect in resolved] == [
        "exhaust_all_non_attacks_gain_block",
        "damage",
    ]
    assert resolved[1]["power_id"] == "juggernaut"
    assert resolved[1]["target_instance_id"] == "enemy-1"
    assert state.player.block == 5
    assert state.enemies[0].hp == 13


def test_exhaust_all_non_attacks_in_hand_moves_only_non_attacks() -> None:
    provider = _CardProvider()
    _register_test_card(provider, card_id="defend", card_type="skill")
    _register_test_card(provider, card_id="ghostly_armor", card_type="skill")
    _register_test_card(provider, card_id="strike", card_type="attack")
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[{"type": "exhaust_all_non_attacks_in_hand"}],
    )
    state.hand = ["defend#1", "ghostly_armor#1", "strike#1"]

    resolved = resolve_next_effect(state, registry=provider)

    assert resolved["type"] == "exhaust_all_non_attacks_in_hand"
    assert resolved["result"] == {
        "exhausted_cards": ["defend#1", "ghostly_armor#1"],
        "exhausted_count": 2,
    }
    assert state.hand == ["strike#1"]
    assert state.exhaust_pile == ["defend#1", "ghostly_armor#1"]


def test_exhaust_all_in_hand_moves_all_cards_and_reports_count() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[{"type": "exhaust_all_in_hand"}],
    )
    state.hand = ["defend#1", "ghostly_armor#1", "strike#1"]

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "exhaust_all_in_hand"
    assert resolved["result"] == {
        "exhausted_cards": ["defend#1", "ghostly_armor#1", "strike#1"],
        "exhausted_count": 3,
    }
    assert state.hand == []
    assert state.exhaust_pile == ["defend#1", "ghostly_armor#1", "strike#1"]


def test_exhaust_all_in_hand_damage_scales_damage_by_exhausted_count() -> None:
    provider = _CardProvider()
    _register_test_card(provider, card_id="defend", card_type="skill")
    _register_test_card(provider, card_id="strike", card_type="attack")
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 30)],
        effect_queue=[
            {
                "type": "exhaust_all_in_hand_damage",
                "source_instance_id": "player-1",
                "target_instance_id": "enemy-1",
                "amount_per_card": 7,
            }
        ],
    )
    state.hand = ["defend#1", "strike#1"]

    resolved = resolve_next_effect(state, registry=provider)

    assert resolved["type"] == "exhaust_all_in_hand_damage"
    assert resolved["result"] == {
        "exhausted_cards": ["defend#1", "strike#1"],
        "exhausted_count": 2,
        "base_amount": 14,
        "applied_amount": 14,
        "blocked": 0,
        "actual_damage": 14,
        "target_defeated": False,
    }
    assert state.hand == []
    assert state.exhaust_pile == ["defend#1", "strike#1"]
    assert state.enemies[0].hp == 16


def test_on_exhaust_effects_trigger_when_card_is_exhausted() -> None:
    provider = _CardProvider()
    _register_test_card(
        provider,
        card_id="sentinel",
        card_type="skill",
        on_exhaust_effects=[{"type": "gain_energy", "amount": 2}],
    )
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {"type": "exhaust_target_card", "target_card_instance_id": "sentinel#1"}
        ],
        energy=3,
    )
    state.hand = ["sentinel#1"]

    resolved = resolve_effect_queue(state, registry=provider)

    assert [effect["type"] for effect in resolved] == [
        "exhaust_target_card",
        "gain_energy",
    ]
    assert resolved[1]["source_instance_id"] == "sentinel#1"
    assert resolved[1]["target_instance_id"] == "player-1"
    assert state.hand == []
    assert state.exhaust_pile == ["sentinel#1"]
    assert state.energy == 5


def test_exhaust_effects_trigger_dark_embrace_and_feel_no_pain() -> None:
    provider = _CardProvider()
    _register_test_card(provider, card_id="defend", card_type="skill")
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {"type": "exhaust_target_card", "target_card_instance_id": "defend#1"}
        ],
    )
    state.hand = ["defend#1"]
    state.active_powers.extend(
        [
            {"power_id": "dark_embrace", "amount": 1},
            {"power_id": "feel_no_pain", "amount": 4},
        ]
    )

    resolved = resolve_effect_queue(state, registry=provider)

    assert [effect["type"] for effect in resolved] == [
        "exhaust_target_card",
        "draw",
        "block",
    ]
    assert resolved[1]["power_id"] == "dark_embrace"
    assert resolved[1]["target_instance_id"] == "player-1"
    assert resolved[1]["amount"] == 1
    assert resolved[2]["power_id"] == "feel_no_pain"
    assert resolved[2]["target_instance_id"] == "player-1"
    assert resolved[2]["amount"] == 4
    assert state.exhaust_pile == ["defend#1"]
    assert state.player.block == 4
    assert len(state.hand) == 1


def test_exhaust_all_in_hand_preserves_cross_card_on_exhaust_order() -> None:
    provider = _CardProvider()
    _register_test_card(
        provider,
        card_id="skill_a",
        card_type="skill",
        on_exhaust_effects=[{"type": "gain_energy", "amount": 1, "label": "A"}],
    )
    _register_test_card(
        provider,
        card_id="skill_b",
        card_type="skill",
        on_exhaust_effects=[{"type": "gain_energy", "amount": 1, "label": "B"}],
    )
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[{"type": "exhaust_all_in_hand"}],
        energy=3,
    )
    state.hand = ["skill_a#1", "skill_b#1"]

    resolved = resolve_effect_queue(state, registry=provider)

    assert [effect["type"] for effect in resolved] == [
        "exhaust_all_in_hand",
        "gain_energy",
        "gain_energy",
    ]
    assert [effect["source_instance_id"] for effect in resolved[1:]] == [
        "skill_a#1",
        "skill_b#1",
    ]


def test_upgrade_target_card_effect_rewrites_card_instance_id_in_hand() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "upgrade_target_card",
                "target_card_instance_id": "bash#3",
                "upgraded_card_id": "bash_plus",
            }
        ],
    )
    state.hand = ["bash#3", "defend#4"]

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "upgrade_target_card"
    assert resolved["result"] == {
        "upgraded_from": "bash#3",
        "upgraded_to": "bash_plus#3",
    }
    assert state.hand == ["bash_plus#3", "defend#4"]


def test_upgrade_all_hand_effect_upgrades_every_upgradeable_card_in_hand() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            {
                "type": "upgrade_all_hand",
                "upgrades": {
                    "strike": "strike_plus",
                    "defend": "defend_plus",
                    "bash": "bash_plus",
                },
            }
        ],
    )
    state.hand = ["strike#1", "defend#2", "burn#3"]

    resolved = resolve_next_effect(state)

    assert resolved["type"] == "upgrade_all_hand"
    assert resolved["result"]["upgraded_cards"] == [
        {"from": "strike#1", "to": "strike_plus#1"},
        {"from": "defend#2", "to": "defend_plus#2"},
    ]
    assert state.hand == ["strike_plus#1", "defend_plus#2", "burn#3"]


def test_enemy_damage_increments_times_hit_this_combat() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            damage_effect(
                source_instance_id="enemy-1", target_instance_id="player-1", amount=5
            )
        ],
    )

    resolve_next_effect(state)

    assert state.times_hit_this_combat == 1
