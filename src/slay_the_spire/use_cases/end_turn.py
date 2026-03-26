from __future__ import annotations

from collections.abc import Sequence

from slay_the_spire.domain.combat.turn_flow import end_turn as advance_turn, preview_enemy_move
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.cards import CombatActionResult
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.use_cases.combat_events import build_enemy_turn_events, capture_entity_snapshots
from slay_the_spire.use_cases.combat_log import append_log_entries, describe_enemy_turn


def end_turn(
    combat_state: CombatState,
    registry: ContentProviderPort,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
) -> CombatActionResult:
    if combat_state.player.hp <= 0:
        raise ValueError("cannot end turn when player is defeated")

    snapshots_before = capture_entity_snapshots(combat_state, registry)
    enemy_previews = [
        (
            enemy,
            preview_enemy_move(combat_state, enemy, registry.enemies().get(enemy.enemy_id)),
        )
        for enemy in combat_state.enemies
        if enemy.hp > 0
    ]
    resolved_effects = advance_turn(
        combat_state,
        registry,
        hook_registrations=hook_registrations,
    )
    append_log_entries(
        combat_state,
        describe_enemy_turn(
            events=build_enemy_turn_events(
                enemy_previews=enemy_previews,
                resolved_effects=resolved_effects,
                entities=snapshots_before,
                registry=registry,
            ),
        ),
    )
    return CombatActionResult(
        combat_state=combat_state,
        resolved_effects=resolved_effects,
    )
