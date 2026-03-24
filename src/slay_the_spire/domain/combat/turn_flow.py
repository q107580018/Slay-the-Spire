from __future__ import annotations

from collections.abc import Mapping, Sequence

from slay_the_spire.domain.effects.effect_resolver import resolve_effect_queue
from slay_the_spire.domain.effects.effect_types import copy_effect
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.types import JsonDict

DEFAULT_ENERGY_PER_TURN = 3
DEFAULT_HAND_SIZE = 5


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _draw_cards(state: CombatState, *, amount: int) -> None:
    for _ in range(max(amount, 0)):
        if not state.draw_pile:
            if not state.discard_pile:
                break
            state.draw_pile.extend(state.discard_pile)
            state.discard_pile.clear()
        state.hand.append(state.draw_pile.pop(0))


def _effects_from_payload(
    payload: Mapping[str, object],
    *,
    source_instance_id: str,
    default_target_id: str | None,
) -> list[JsonDict]:
    if "effects" in payload:
        raw_effects = payload.get("effects")
        if not isinstance(raw_effects, list):
            raise TypeError("effects must be a list")
        effects = [_require_mapping(effect, "effect") for effect in raw_effects]
    else:
        effects = [payload]

    materialized: list[JsonDict] = []
    for raw_effect in effects:
        effect = copy_effect(raw_effect)
        effect_type = effect.get("type")
        if not isinstance(effect_type, str):
            raise TypeError("effect type must be a string")
        if "source_instance_id" not in effect:
            effect["source_instance_id"] = source_instance_id
        if effect_type in {"damage", "block", "draw"} and "target_instance_id" not in effect:
            if default_target_id is None:
                raise ValueError(f"{effect_type} effect requires a target")
            effect["target_instance_id"] = default_target_id
        materialized.append(effect)
    return materialized


def start_turn(
    state: CombatState,
    *,
    hand_size: int = DEFAULT_HAND_SIZE,
    energy_per_turn: int = DEFAULT_ENERGY_PER_TURN,
) -> CombatState:
    state.energy = energy_per_turn
    _draw_cards(state, amount=max(hand_size - len(state.hand), 0))
    return state


def resolve_player_actions(
    state: CombatState,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
) -> list[JsonDict]:
    return resolve_effect_queue(state, hook_registrations=hook_registrations)


def run_enemy_turn(
    state: CombatState,
    registry: ContentProviderPort,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
) -> list[JsonDict]:
    for enemy in state.enemies:
        if enemy.hp <= 0:
            continue
        enemy_def = registry.enemies().get(enemy.enemy_id)
        if not enemy_def.move_table:
            continue
        move = _require_mapping(enemy_def.move_table[0], "move_table item")
        state.effect_queue.extend(
            _effects_from_payload(
                move,
                source_instance_id=enemy.instance_id,
                default_target_id=state.player.instance_id,
            )
        )
    return resolve_effect_queue(state, hook_registrations=hook_registrations)


def end_turn(
    state: CombatState,
    registry: ContentProviderPort,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
    hand_size: int = DEFAULT_HAND_SIZE,
    energy_per_turn: int = DEFAULT_ENERGY_PER_TURN,
) -> list[JsonDict]:
    state.discard_pile.extend(state.hand)
    state.hand.clear()

    resolved = run_enemy_turn(
        state,
        registry,
        hook_registrations=hook_registrations,
    )
    if state.player.hp <= 0:
        return resolved
    state.round_number += 1
    start_turn(
        state,
        hand_size=hand_size,
        energy_per_turn=energy_per_turn,
    )
    return resolved
