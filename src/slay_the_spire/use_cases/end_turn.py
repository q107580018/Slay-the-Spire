from __future__ import annotations

from collections.abc import Sequence

from slay_the_spire.domain.combat.turn_flow import end_turn as advance_turn
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.cards import CombatActionResult
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.ports.content_provider import ContentProviderPort


def end_turn(
    combat_state: CombatState,
    registry: ContentProviderPort,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
) -> CombatActionResult:
    if combat_state.player.hp <= 0:
        raise ValueError("cannot end turn when player is defeated")

    resolved_effects = advance_turn(
        combat_state,
        registry,
        hook_registrations=hook_registrations,
    )
    return CombatActionResult(
        combat_state=combat_state,
        resolved_effects=resolved_effects,
    )
