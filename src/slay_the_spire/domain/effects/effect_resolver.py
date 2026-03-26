from __future__ import annotations

from collections.abc import Sequence

from slay_the_spire.domain.effects.effect_types import (
    EFFECT_ADD_CARD_TO_DISCARD,
    EFFECT_BLOCK,
    EFFECT_CREATE_CARD_COPY,
    EFFECT_DAMAGE,
    EFFECT_DRAW,
    EFFECT_EMIT_HOOK,
    EFFECT_GAIN_ENERGY,
    EFFECT_HEAL,
    EFFECT_NOOP,
    EFFECT_VULNERABLE,
    EFFECT_WEAK,
    copy_effect,
    emit_hook_effect,
    noop_effect,
)
from slay_the_spire.domain.hooks.hook_dispatcher import dispatch_hook
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.shared.types import JsonDict, JsonValue


def _get_target(state: CombatState, instance_id: object) -> PlayerCombatState | EnemyState | None:
    if not isinstance(instance_id, str):
        return None
    try:
        return state.get_entity(instance_id)
    except KeyError:
        return None


def _is_dead(target: PlayerCombatState | EnemyState | None) -> bool:
    return target is None or target.hp <= 0


def _damage_target(target: PlayerCombatState | EnemyState, amount: int) -> tuple[int, int]:
    remaining = max(amount, 0)
    blocked = min(target.block, remaining)
    target.block -= blocked
    remaining -= blocked
    actual_damage = min(target.hp, remaining)
    if remaining > 0:
        target.hp = max(target.hp - remaining, 0)
    return blocked, actual_damage


def _vulnerable_bonus(target: PlayerCombatState | EnemyState) -> int:
    for status in target.statuses:
        if status.status_id == "vulnerable" and status.stacks > 0:
            return 1
    return 0


def _is_weak(source: PlayerCombatState | EnemyState | None) -> bool:
    if source is None:
        return False
    return any(status.status_id == "weak" and status.stacks > 0 for status in source.statuses)


def _damage_amount(
    source: PlayerCombatState | EnemyState | None,
    target: PlayerCombatState | EnemyState,
    base_amount: int,
) -> int:
    amount = max(base_amount, 0)
    if _is_weak(source):
        amount = (amount * 3) // 4
    if _vulnerable_bonus(target):
        amount += amount // 2
    return amount


def _heal_target(target: PlayerCombatState | EnemyState, amount: int) -> int:
    healed = min(target.max_hp - target.hp, max(amount, 0))
    target.hp = min(target.max_hp, target.hp + max(amount, 0))
    return healed


def _with_result(effect: JsonDict, **result: JsonValue) -> JsonDict:
    resolved = copy_effect(effect)
    resolved["result"] = result
    return resolved


def _next_card_instance_id(state: CombatState, card_id: str) -> str:
    highest_suffix = 0
    for card_instance_id in [*state.hand, *state.draw_pile, *state.discard_pile, *state.exhaust_pile]:
        try:
            existing_card_id = card_id_from_instance_id(card_instance_id)
        except (TypeError, ValueError):
            continue
        if existing_card_id != card_id:
            continue
        _existing_card_id, suffix = card_instance_id.split("#", 1)
        if suffix.isdigit():
            highest_suffix = max(highest_suffix, int(suffix))
    return f"{card_id}#{highest_suffix + 1}"


def _append_card_to_zone(state: CombatState, *, zone: str, card_instance_id: str) -> None:
    if zone == "hand":
        state.hand.append(card_instance_id)
        return
    if zone == "draw_pile":
        state.draw_pile.append(card_instance_id)
        return
    if zone == "discard_pile":
        state.discard_pile.append(card_instance_id)
        return
    if zone == "exhaust_pile":
        state.exhaust_pile.append(card_instance_id)
        return
    raise ValueError(f"unsupported card copy zone: {zone}")


def _draw_cards(state: CombatState, *, amount: int) -> int:
    drawn_count = 0
    for _ in range(max(amount, 0)):
        if not state.draw_pile:
            if not state.discard_pile:
                break
            state.draw_pile.extend(state.discard_pile)
            state.discard_pile.clear()
        state.hand.append(state.draw_pile.pop(0))
        drawn_count += 1
    return drawn_count


def _apply_status(
    target: PlayerCombatState | EnemyState,
    *,
    status_id: str,
    stacks: int,
) -> None:
    normalized_stacks = max(stacks, 0)
    if normalized_stacks == 0:
        return
    for status in target.statuses:
        if status.status_id == status_id:
            status.stacks += normalized_stacks
            return
    target.statuses.append(StatusState(status_id=status_id, stacks=normalized_stacks))


def _has_pending_hook(state: CombatState, hook_name: str) -> bool:
    for effect in state.effect_queue:
        if effect.get("type") == EFFECT_EMIT_HOOK and effect.get("hook_name") == hook_name:
            return True
    return False


def _maybe_enqueue_combat_end(state: CombatState, *, payload: JsonDict | None = None) -> None:
    if all(enemy.hp == 0 for enemy in state.enemies) and not _has_pending_hook(state, "on_combat_end"):
        state.effect_queue.append(
            emit_hook_effect(
                hook_name="on_combat_end",
                payload=payload or {},
            )
        )


def resolve_next_effect(
    state: CombatState,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
) -> JsonDict:
    effect = state.effect_queue.pop(0)
    effect_type = effect.get("type")

    if effect_type == EFFECT_DAMAGE:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        was_alive = target.hp > 0
        source = _get_target(state, effect.get("source_instance_id"))
        applied_amount = _damage_amount(source, target, int(effect.get("amount", 0)))
        blocked, actual_damage = _damage_target(target, applied_amount)
        target_defeated = isinstance(target, EnemyState) and was_alive and target.hp == 0
        if target_defeated:
            state.effect_queue.append(
                emit_hook_effect(
                    hook_name="on_enemy_defeated",
                    payload={"target_instance_id": target.instance_id},
                )
            )
        return _with_result(
            effect,
            applied_amount=applied_amount,
            blocked=blocked,
            actual_damage=actual_damage,
            target_defeated=target_defeated,
        )

    if effect_type == EFFECT_BLOCK:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        gained_block = max(int(effect.get("amount", 0)), 0)
        target.block += gained_block
        return _with_result(effect, gained_block=gained_block)

    if effect_type == EFFECT_HEAL:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        healed = _heal_target(target, int(effect.get("amount", 0)))
        return _with_result(effect, actual_healed=healed)

    if effect_type == EFFECT_DRAW:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        draw_count = _draw_cards(state, amount=int(effect.get("amount", 0)))
        return _with_result(effect, drawn_count=draw_count)

    if effect_type == EFFECT_GAIN_ENERGY:
        gained_energy = max(int(effect.get("amount", 0)), 0)
        state.energy += gained_energy
        return _with_result(effect, gained_energy=gained_energy)

    if effect_type == EFFECT_VULNERABLE:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        applied_stacks = max(int(effect.get("stacks", 0)), 0)
        _apply_status(
            target,
            status_id="vulnerable",
            stacks=applied_stacks,
        )
        return _with_result(effect, applied_stacks=applied_stacks)

    if effect_type == EFFECT_WEAK:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        applied_stacks = max(int(effect.get("stacks", 0)), 0)
        _apply_status(
            target,
            status_id="weak",
            stacks=applied_stacks,
        )
        return _with_result(effect, applied_stacks=applied_stacks)

    if effect_type == EFFECT_CREATE_CARD_COPY:
        card_id = effect.get("card_id")
        zone = effect.get("zone", "discard_pile")
        if not isinstance(card_id, str):
            raise TypeError("card_id must be a string")
        if not isinstance(zone, str):
            raise TypeError("zone must be a string")
        card_instance_id = _next_card_instance_id(state, card_id)
        _append_card_to_zone(
            state,
            zone=zone,
            card_instance_id=card_instance_id,
        )
        return _with_result(effect, created_card_instance_id=card_instance_id)

    if effect_type == EFFECT_ADD_CARD_TO_DISCARD:
        card_id = effect.get("card_id")
        if not isinstance(card_id, str):
            raise TypeError("card_id must be a string")
        count = max(int(effect.get("count", 1)), 0)
        for _ in range(count):
            state.discard_pile.append(_next_card_instance_id(state, card_id))
        return effect

    if effect_type == EFFECT_EMIT_HOOK:
        hook_name = effect.get("hook_name")
        if not isinstance(hook_name, str):
            raise TypeError("hook_name must be a string")
        payload = effect.get("payload")
        if payload is not None and not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")
        dispatch_hook(
            state,
            hook_name,
            hook_registrations,
            payload=payload if isinstance(payload, dict) else None,
        )
        if hook_name == "on_enemy_defeated":
            _maybe_enqueue_combat_end(
                state,
                payload=payload if isinstance(payload, dict) else None,
            )
        return effect

    if effect_type == EFFECT_NOOP:
        return effect

    raise ValueError(f"unsupported effect type: {effect_type}")


def resolve_effect_queue(
    state: CombatState,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
) -> list[JsonDict]:
    resolved: list[JsonDict] = []
    while state.effect_queue:
        resolved.append(resolve_next_effect(state, hook_registrations=hook_registrations))
    return resolved
