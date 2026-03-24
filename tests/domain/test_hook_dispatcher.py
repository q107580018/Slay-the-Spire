from __future__ import annotations

from slay_the_spire.domain.effects.effect_types import noop_effect
from slay_the_spire.domain.hooks.hook_dispatcher import dispatch_hook, serialize_hook_registrations
from slay_the_spire.domain.hooks.hook_types import CATEGORY_PRIORITY, HookRegistration
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState


def make_combat_state() -> CombatState:
    return CombatState(
        schema_version=1,
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=70,
            max_hp=70,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="cultist",
                hp=10,
                max_hp=10,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )


def make_registration(
    *,
    reason: str,
    category: str,
    priority: int,
    source_type: str,
    source_instance_id: str,
    registration_index: int,
) -> HookRegistration:
    return HookRegistration(
        hook_name="on_enemy_defeated",
        category=category,
        priority=priority,
        source_type=source_type,
        source_instance_id=source_instance_id,
        registration_index=registration_index,
        effects=[noop_effect(reason=reason)],
    )


def test_hooks_only_append_new_effects_to_queue_tail():
    state = make_combat_state()
    state.effect_queue.append(noop_effect(reason="existing"))

    dispatch_hook(
        state,
        "on_enemy_defeated",
        [
            make_registration(
                reason="first",
                category="status",
                priority=0,
                source_type="player",
                source_instance_id="player-1",
                registration_index=0,
            ),
            make_registration(
                reason="second",
                category="status",
                priority=1,
                source_type="player",
                source_instance_id="player-1",
                registration_index=1,
            ),
        ],
    )

    assert [effect["reason"] for effect in state.effect_queue] == ["existing", "first", "second"]


def test_hook_category_priority_is_stable():
    state = make_combat_state()
    ordered_categories = sorted(CATEGORY_PRIORITY, key=CATEGORY_PRIORITY.__getitem__)

    dispatch_hook(
        state,
        "on_enemy_defeated",
        [
            make_registration(
                reason=category,
                category=category,
                priority=0,
                source_type="player",
                source_instance_id="player-1",
                registration_index=index,
            )
            for index, category in enumerate(reversed(ordered_categories))
        ],
    )

    assert [effect["reason"] for effect in state.effect_queue] == ordered_categories


def test_equal_priority_hooks_use_source_type_order_before_instance_id():
    state = make_combat_state()

    dispatch_hook(
        state,
        "on_enemy_defeated",
        [
            make_registration(
                reason="enemy",
                category="status",
                priority=0,
                source_type="enemy",
                source_instance_id="a-enemy",
                registration_index=1,
            ),
            make_registration(
                reason="player",
                category="status",
                priority=0,
                source_type="player",
                source_instance_id="z-player",
                registration_index=0,
            ),
        ],
    )

    assert [effect["reason"] for effect in state.effect_queue] == ["player", "enemy"]


def test_equal_priority_hooks_sort_by_instance_id():
    state = make_combat_state()

    dispatch_hook(
        state,
        "on_enemy_defeated",
        [
            make_registration(
                reason="enemy-2",
                category="status",
                priority=0,
                source_type="enemy",
                source_instance_id="enemy-2",
                registration_index=1,
            ),
            make_registration(
                reason="enemy-1",
                category="status",
                priority=0,
                source_type="enemy",
                source_instance_id="enemy-1",
                registration_index=0,
            ),
        ],
    )

    assert [effect["reason"] for effect in state.effect_queue] == ["enemy-1", "enemy-2"]


def test_hook_registration_order_serializes_stably():
    registrations = [
        make_registration(
            reason="second",
            category="status",
            priority=0,
            source_type="enemy",
            source_instance_id="enemy-1",
            registration_index=2,
        ),
        make_registration(
            reason="first",
            category="status",
            priority=0,
            source_type="enemy",
            source_instance_id="enemy-1",
            registration_index=1,
        ),
    ]

    assert serialize_hook_registrations(registrations) == [
        {
            "hook_name": "on_enemy_defeated",
            "category": "status",
            "priority": 0,
            "source_type": "enemy",
            "source_instance_id": "enemy-1",
            "registration_index": 1,
            "effects": [{"type": "noop", "reason": "first"}],
        },
        {
            "hook_name": "on_enemy_defeated",
            "category": "status",
            "priority": 0,
            "source_type": "enemy",
            "source_instance_id": "enemy-1",
            "registration_index": 2,
            "effects": [{"type": "noop", "reason": "second"}],
        },
    ]
