from __future__ import annotations

from collections.abc import Mapping, Sequence

from slay_the_spire.content.registries import EnemyDef
from slay_the_spire.domain.effects.effect_resolver import resolve_effect_queue
from slay_the_spire.domain.effects.effect_types import block_effect, copy_effect, damage_effect
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.types import JsonDict

DEFAULT_ENERGY_PER_TURN = 3
DEFAULT_HAND_SIZE = 5
_TEMPORARY_STATUS_IDS = {"vulnerable", "weak"}


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _draw_cards(state: CombatState, *, amount: int) -> None:
    for power in state.active_powers:
        if power.get("power_id") == "battle_trance":
            raw_amount = power.get("amount")
            if isinstance(raw_amount, int) and raw_amount > 0:
                return
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


def _tick_temporary_statuses(entity: PlayerCombatState | EnemyState) -> None:
    next_statuses: list[StatusState] = []
    for status in entity.statuses:
        if status.status_id not in _TEMPORARY_STATUS_IDS:
            next_statuses.append(status)
            continue
        remaining_stacks = status.stacks - 1
        if remaining_stacks <= 0:
            continue
        next_statuses.append(
            StatusState(
                status_id=status.status_id,
                stacks=remaining_stacks,
                duration=None if status.duration is None else max(status.duration - 1, 1),
            )
        )
    entity.statuses = next_statuses


def _consume_status_stack(entity: PlayerCombatState | EnemyState, status_id: str) -> bool:
    for index, status in enumerate(entity.statuses):
        if status.status_id != status_id:
            continue
        remaining_stacks = status.stacks - 1
        if remaining_stacks <= 0:
            entity.statuses.pop(index)
        else:
            entity.statuses[index] = StatusState(
                status_id=status.status_id,
                stacks=remaining_stacks,
                duration=status.duration,
            )
        return True
    return False


def _clear_block_for_turn_start(entity: PlayerCombatState | EnemyState) -> None:
    if _consume_status_stack(entity, "blur"):
        return
    entity.block = 0


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


def _strength_bonus(entity: PlayerCombatState | EnemyState) -> int:
    return sum(status.stacks for status in entity.statuses if status.status_id == "strength" and status.stacks > 0)


def _adjust_damage_for_strength(effect: Mapping[str, object], strength_bonus: int) -> JsonDict:
    adjusted = copy_effect(effect)
    if adjusted.get("type") != "damage":
        return adjusted
    adjusted["amount"] = max(int(adjusted.get("amount", 0)), 0) + strength_bonus
    return adjusted


def preview_enemy_move_for_display(
    state: CombatState,
    enemy: EnemyState,
    enemy_def: EnemyDef,
) -> Mapping[str, object] | None:
    preview = preview_enemy_move(state, enemy, enemy_def)
    if preview is None:
        return None

    strength_bonus = _strength_bonus(enemy)
    if strength_bonus <= 0:
        return copy_effect(preview)

    adjusted_preview = copy_effect(preview)
    if adjusted_preview.get("move") == "sleep":
        return adjusted_preview

    effects = adjusted_preview.get("effects")
    if isinstance(effects, list):
        adjusted_preview["effects"] = [
            _adjust_damage_for_strength(effect, strength_bonus) if isinstance(effect, Mapping) else effect
            for effect in effects
        ]
        return adjusted_preview

    return _adjust_damage_for_strength(adjusted_preview, strength_bonus)


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
        if effect_type in {"damage", "block", "draw", "vulnerable", "weak"} and "target_instance_id" not in effect:
            if default_target_id is None:
                raise ValueError(f"{effect_type} effect requires a target")
            effect["target_instance_id"] = default_target_id
        if effect_type == "strength" and "target_instance_id" not in effect:
            effect["target_instance_id"] = source_instance_id
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


def _burn_end_turn_effects(hand: Sequence[str], player_instance_id: str) -> list[JsonDict]:
    effects: list[JsonDict] = []
    for card_instance_id in hand:
        if card_id_from_instance_id(card_instance_id) != "burn":
            continue
        effects.append(
            damage_effect(
                source_instance_id=card_instance_id,
                target_instance_id=player_instance_id,
                amount=2,
            )
        )
    return effects


def _post_tick_hand_end_turn_effects(hand: Sequence[str], player_instance_id: str) -> list[JsonDict]:
    effects: list[JsonDict] = []
    for card_instance_id in hand:
        if card_id_from_instance_id(card_instance_id) != "doubt":
            continue
        effects.append(
            {
                "type": "weak",
                "source_instance_id": card_instance_id,
                "target_instance_id": player_instance_id,
                "stacks": 1,
            }
        )
    return effects


def _active_power_end_turn_effects(state: CombatState) -> list[JsonDict]:
    effects: list[JsonDict] = []
    for power in state.active_powers:
        power_id = power.get("power_id")
        if not isinstance(power_id, str):
            continue
        raw_amount = power.get("amount")
        amount = raw_amount if isinstance(raw_amount, int) else 0
        amount = max(amount, 0)
        if power_id == "metallicize" and amount > 0:
            effect = block_effect(
                source_instance_id=state.player.instance_id,
                target_instance_id=state.player.instance_id,
                amount=amount,
            )
            effect["power_id"] = power_id
            effect["trigger"] = "end_turn_power"
            effects.append(effect)
            continue
        if power_id != "combust" or amount <= 0:
            continue
        for enemy in state.enemies:
            if enemy.hp <= 0:
                continue
            effect = damage_effect(
                source_instance_id=state.player.instance_id,
                target_instance_id=enemy.instance_id,
                amount=amount,
            )
            effect["power_id"] = power_id
            effect["trigger"] = "end_turn_power"
            effects.append(effect)
        raw_self_damage = power.get("self_damage", 1)
        self_damage = raw_self_damage if isinstance(raw_self_damage, int) else 0
        self_damage = max(self_damage, 0)
        if self_damage > 0:
            effects.append(
                {
                    "type": "lose_hp",
                    "source_instance_id": state.player.instance_id,
                    "target_instance_id": state.player.instance_id,
                    "amount": self_damage,
                    "power_id": power_id,
                    "trigger": "end_turn_power",
                }
            )
    return effects


def _clear_temporary_power(state: CombatState, power_id: str) -> None:
    state.active_powers = [
        power for power in state.active_powers if power.get("power_id") != power_id
    ]


def start_turn(
    state: CombatState,
    *,
    hand_size: int = DEFAULT_HAND_SIZE,
    energy_per_turn: int = DEFAULT_ENERGY_PER_TURN,
) -> CombatState:
    _clear_block_for_turn_start(state.player)
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
        _clear_block_for_turn_start(enemy)
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
    hand_at_end_turn = tuple(state.hand)
    _clear_temporary_power(state, "battle_trance")
    state.effect_queue.extend(_active_power_end_turn_effects(state))
    state.effect_queue.extend(_burn_end_turn_effects(hand_at_end_turn, state.player.instance_id))
    if state.effect_queue:
        resolved.extend(resolve_effect_queue(state, hook_registrations=hook_registrations))
    state.discard_pile.extend(state.hand)
    state.hand.clear()
    if state.player.hp <= 0:
        return resolved
    _tick_temporary_statuses(state.player)
    state.effect_queue.extend(_post_tick_hand_end_turn_effects(hand_at_end_turn, state.player.instance_id))
    if state.effect_queue:
        resolved.extend(resolve_effect_queue(state, hook_registrations=hook_registrations))
    resolved.extend(
        run_enemy_turn(
        state,
        registry,
        hook_registrations=hook_registrations,
    )
    )
    if state.player.hp <= 0:
        return resolved
    for enemy in state.enemies:
        _tick_temporary_statuses(enemy)
    state.round_number += 1
    start_turn(
        state,
        hand_size=hand_size,
        energy_per_turn=energy_per_turn,
    )
    return resolved
