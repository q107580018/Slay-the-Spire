from __future__ import annotations

from collections.abc import Sequence

from slay_the_spire.domain.combat.turn_flow import resolve_player_actions
from slay_the_spire.domain.effects.effect_types import EFFECT_DAMAGE, copy_effect
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.types import JsonDict

_TARGETED_EFFECT_TYPES = {EFFECT_DAMAGE}


def _materialize_card_effects(
    raw_effects: Sequence[JsonDict],
    *,
    source_instance_id: str,
    target_id: str | None,
) -> list[JsonDict]:
    effects: list[JsonDict] = []
    for raw_effect in raw_effects:
        effect = copy_effect(raw_effect)
        effect_type = effect.get("type")
        if not isinstance(effect_type, str):
            raise TypeError("card effect type must be a string")
        if "source_instance_id" not in effect:
            effect["source_instance_id"] = source_instance_id
        if effect_type in _TARGETED_EFFECT_TYPES:
            if target_id is None:
                raise ValueError("target is required for targeted cards")
            effect["target_instance_id"] = target_id
        elif effect_type == "block" and "target_instance_id" not in effect:
            effect["target_instance_id"] = source_instance_id
        effects.append(effect)
    return effects


def play_card(
    combat_state: CombatState,
    card_instance_id: str,
    target_id: str | None,
    registry: ContentProviderPort,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
) -> CombatState:
    if card_instance_id not in combat_state.hand:
        raise ValueError(f"card {card_instance_id} is not in hand")

    card_id = card_id_from_instance_id(card_instance_id)
    card_def = registry.cards().get(card_id)
    if combat_state.energy < card_def.cost:
        raise ValueError("not enough energy to play card")

    combat_state.energy -= card_def.cost
    combat_state.hand.remove(card_instance_id)
    combat_state.discard_pile.append(card_instance_id)
    combat_state.effect_queue.extend(
        _materialize_card_effects(
            card_def.effects,
            source_instance_id=combat_state.player.instance_id,
            target_id=target_id,
        )
    )
    resolve_player_actions(
        combat_state,
        hook_registrations=hook_registrations,
    )
    return combat_state
