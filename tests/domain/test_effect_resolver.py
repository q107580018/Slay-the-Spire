from __future__ import annotations

from slay_the_spire.domain.effects.effect_resolver import resolve_next_effect
from slay_the_spire.domain.effects.effect_types import (
    EFFECT_EMIT_HOOK,
    EFFECT_NOOP,
    damage_effect,
    noop_effect,
)
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState


def make_combat_state(*, enemies: list[EnemyState], effect_queue: list[dict[str, object]] | None = None) -> CombatState:
    return CombatState(
        schema_version=1,
        round_number=1,
        energy=3,
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
