from __future__ import annotations

from collections.abc import Mapping, Sequence

from slay_the_spire.content.registries import EnemyDef
from slay_the_spire.domain.effects.effect_resolver import resolve_effect_queue
from slay_the_spire.domain.effects.effect_types import copy_effect, damage_effect
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState
from slay_the_spire.domain.models.statuses import StatusState
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


def _status_stacks(enemy: EnemyState, status_id: str) -> int:
    for status in enemy.statuses:
        if status.status_id == status_id:
            return status.stacks
    return 0


def _set_status_stacks(enemy: EnemyState, status_id: str, stacks: int) -> None:
    for index, status in enumerate(enemy.statuses):
        if status.status_id != status_id:
            continue
        if stacks <= 0:
            enemy.statuses.pop(index)
        else:
            enemy.statuses[index] = StatusState(status_id=status_id, stacks=stacks)
        return
    if stacks > 0:
        enemy.statuses.append(StatusState(status_id=status_id, stacks=stacks))


def _sleep_turns(enemy_def: EnemyDef) -> int:
    if not enemy_def.move_table:
        return 0
    first_move = _require_mapping(enemy_def.move_table[0], "move_table item")
    if first_move.get("move") != "sleep":
        return 0
    sleep_turns = first_move.get("sleep_turns", 0)
    if not isinstance(sleep_turns, int):
        raise TypeError("sleep_turns must be an int")
    return max(sleep_turns, 0)


def _is_once_move(move: Mapping[str, object]) -> bool:
    once = move.get("once", False)
    if not isinstance(once, bool):
        raise TypeError("once must be a bool")
    return once


def _active_enemy_move(state: CombatState, enemy_def: EnemyDef) -> Mapping[str, object] | None:
    if not enemy_def.move_table:
        return None

    sleep_turns = _sleep_turns(enemy_def)
    active_moves = enemy_def.move_table[1:] if sleep_turns > 0 else enemy_def.move_table
    if not active_moves:
        return None
    if enemy_def.intent_policy != "scripted":
        return _require_mapping(active_moves[0], "move_table item")

    normalized_round = max(state.round_number - sleep_turns, 1)
    first_move = _require_mapping(active_moves[0], "move_table item")
    if _is_once_move(first_move):
        if normalized_round == 1:
            return first_move
        looping_moves = active_moves[1:]
        if not looping_moves:
            return first_move
        move_index = (normalized_round - 2) % len(looping_moves)
        return _require_mapping(looping_moves[move_index], "move_table item")

    move_index = (normalized_round - 1) % len(active_moves)
    return _require_mapping(active_moves[move_index], "move_table item")


def preview_enemy_move(state: CombatState, enemy: EnemyState, enemy_def: EnemyDef) -> Mapping[str, object] | None:
    if enemy.hp <= 0 or not enemy_def.move_table:
        return None
    sleeping_stacks = _status_stacks(enemy, "sleeping")
    if sleeping_stacks > 0:
        return {"move": "sleep", "sleep_turns": sleeping_stacks}
    return _active_enemy_move(state, enemy_def)


def _select_enemy_move(state: CombatState, enemy: EnemyState, enemy_def: EnemyDef) -> Mapping[str, object] | None:
    preview = preview_enemy_move(state, enemy, enemy_def)
    if preview is None:
        return None
    if preview.get("move") == "sleep":
        _set_status_stacks(enemy, "sleeping", _status_stacks(enemy, "sleeping") - 1)
        return None
    return preview


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


def _divider_damage_per_hit(player_hp: int) -> int:
    if player_hp <= 24:
        return 1
    if player_hp <= 48:
        return 2
    if player_hp <= 72:
        return 3
    return 4


def _burn_end_turn_effects(state: CombatState) -> list[JsonDict]:
    effects: list[JsonDict] = []
    for card_instance_id in state.hand:
        if card_id_from_instance_id(card_instance_id) != "burn":
            continue
        effects.append(
            damage_effect(
                source_instance_id=card_instance_id,
                target_instance_id=state.player.instance_id,
                amount=2,
            )
        )
    return effects


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
        move = _select_enemy_move(state, enemy, enemy_def)
        if move is None:
            continue
        if move.get("move") == "divider":
            divider_damage = _divider_damage_per_hit(state.player.hp)
            state.effect_queue.extend(
                [
                    damage_effect(
                        source_instance_id=enemy.instance_id,
                        target_instance_id=state.player.instance_id,
                        amount=divider_damage,
                    )
                    for _ in range(6)
                ]
            )
            continue
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
    resolved = []
    state.effect_queue.extend(_burn_end_turn_effects(state))
    if state.effect_queue:
        resolved.extend(resolve_effect_queue(state, hook_registrations=hook_registrations))
    state.discard_pile.extend(state.hand)
    state.hand.clear()
    if state.player.hp <= 0:
        return resolved
    resolved.extend(
        run_enemy_turn(
        state,
        registry,
        hook_registrations=hook_registrations,
    )
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
