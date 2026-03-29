from __future__ import annotations

from slay_the_spire.domain.effects.effect_resolver import resolve_effect_queue, resolve_next_effect
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


def test_effects_append_to_queue_tail_in_order():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3)],
        effect_queue=[
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=3),
            noop_effect(reason="existing"),
        ],
    )

    resolve_next_effect(state)

    assert [effect["type"] for effect in state.effect_queue] == [
        EFFECT_NOOP,
        EFFECT_EMIT_HOOK,
    ]
    assert [effect.get("hook_name") for effect in state.effect_queue[1:]] == ["on_enemy_defeated"]


def test_resolver_never_recurses_synchronously():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3), make_enemy("enemy-2", 10)],
        effect_queue=[
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=3),
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


def test_dead_targets_become_noop_effects():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 1)],
        effect_queue=[
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=2),
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=2),
        ],
    )

    first = resolve_next_effect(state)
    second = resolve_next_effect(state)

    assert first["type"] == "damage"
    assert second["type"] == EFFECT_NOOP
    assert state.enemies[0].hp == 0


def test_on_enemy_defeated_enqueues_before_on_combat_end():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 4)],
        effect_queue=[
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=4),
        ],
    )

    resolve_next_effect(state)

    assert [effect["hook_name"] for effect in state.effect_queue] == ["on_enemy_defeated"]


def test_on_combat_end_is_enqueued_only_after_defeat_hook_resolves():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 4)],
        effect_queue=[
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=4),
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

    assert [effect["type"] for effect in state.effect_queue] == [EFFECT_NOOP, EFFECT_EMIT_HOOK]
    assert state.effect_queue[0]["reason"] == "defeat-follow-up"
    assert state.effect_queue[1]["hook_name"] == "on_combat_end"


def test_on_combat_end_fires_once_even_if_multiple_enemies_die():
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 2), make_enemy("enemy-2", 2)],
        effect_queue=[
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=2),
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-2", amount=2),
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


def test_gain_energy_effect_increases_combat_energy() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 3)],
        energy=3,
        effect_queue=[{"type": "gain_energy", "amount": 1}],
    )

    resolved = resolve_effect_queue(state)

    assert resolved == [{"type": "gain_energy", "amount": 1, "result": {"gained_energy": 1}}]
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
        effect_queue=[{"type": "strength", "source_instance_id": "enemy-1", "amount": 3}],
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
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=4),
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
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=4),
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
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=2),
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=2),
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
            damage_effect(source_instance_id="enemy-1", target_instance_id="player-1", amount=4),
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
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=5),
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


def test_damage_effect_applies_negative_strength_and_floors_at_zero() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[
            damage_effect(source_instance_id="player-1", target_instance_id="enemy-1", amount=6),
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


def test_lose_hp_effect_reduces_player_hp_without_touching_block() -> None:
    state = make_combat_state(
        enemies=[make_enemy("enemy-1", 10)],
        effect_queue=[{"type": "lose_hp", "target_instance_id": "player-1", "amount": 3}],
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
