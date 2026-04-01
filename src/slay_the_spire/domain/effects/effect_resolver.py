from __future__ import annotations

import random
from collections.abc import Sequence

from slay_the_spire.domain.effects.effect_types import (
    EFFECT_ADD_CARD_TO_DISCARD,
    EFFECT_ADD_CARD_TO_DRAW_PILE,
    EFFECT_ADD_CARDS_TO_HAND,
    EFFECT_ADD_POWER,
    EFFECT_BLOCK,
    EFFECT_COPY_CARD_TO_HAND,
    EFFECT_CREATE_CARD_COPY,
    EFFECT_DAMAGE,
    EFFECT_DAMAGE_EQUAL_TO_BLOCK,
    EFFECT_DAMAGE_LIFESTEAL_ALL_ENEMIES,
    EFFECT_DAMAGE_PER_STRIKE_IN_DECK,
    EFFECT_DAMAGE_WITH_STRENGTH_MULTIPLIER,
    EFFECT_DEXTERITY,
    EFFECT_DOUBLE_BLOCK,
    EFFECT_DOUBLE_STRENGTH,
    EFFECT_DRAW,
    EFFECT_EMIT_HOOK,
    EFFECT_EXHAUST_ALL_IN_HAND,
    EFFECT_EXHAUST_ALL_NON_ATTACKS_GAIN_BLOCK,
    EFFECT_EXHAUST_ALL_NON_ATTACKS_IN_HAND,
    EFFECT_EXHAUST_RANDOM_HAND,
    EFFECT_EXHAUST_TARGET_CARD,
    EFFECT_GAIN_ENERGY,
    EFFECT_HEAL,
    EFFECT_LOSE_HP,
    EFFECT_DAMAGE_ON_KILL_GAIN_MAX_HP,
    EFFECT_NOOP,
    EFFECT_PUT_TOP_OF_DECK_FROM_DISCARD,
    EFFECT_RAMPAGE_DAMAGE,
    EFFECT_SELECT_FROM_EXHAUST_TO_HAND,
    EFFECT_SPOT_WEAKNESS_STRENGTH,
    EFFECT_STRENGTH,
    EFFECT_UPGRADE_ALL_HAND,
    EFFECT_UPGRADE_TARGET_CARD,
    EFFECT_VULNERABLE,
    EFFECT_WEAK,
    copy_effect,
    damage_effect,
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


def _get_target(
    state: CombatState, instance_id: object
) -> PlayerCombatState | EnemyState | None:
    if not isinstance(instance_id, str):
        return None
    try:
        return state.get_entity(instance_id)
    except KeyError:
        return None


def _is_dead(target: PlayerCombatState | EnemyState | None) -> bool:
    return target is None or target.hp <= 0


def _damage_target(
    target: PlayerCombatState | EnemyState, amount: int
) -> tuple[int, int]:
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
    return any(
        status.status_id == "weak" and status.stacks > 0 for status in source.statuses
    )


def _status_total(entity: PlayerCombatState | EnemyState | None, status_id: str) -> int:
    if entity is None:
        return 0
    return sum(
        status.stacks for status in entity.statuses if status.status_id == status_id
    )


def _strength_bonus(source: PlayerCombatState | EnemyState | None) -> int:
    return _status_total(source, "strength")


def _dexterity_bonus(source: PlayerCombatState | EnemyState | None) -> int:
    return _status_total(source, "dexterity")


def _damage_amount(
    source: PlayerCombatState | EnemyState | None,
    target: PlayerCombatState | EnemyState,
    base_amount: int,
    *,
    strength_bonus: int | None = None,
) -> int:
    amount = max(base_amount, 0)
    amount += _strength_bonus(source) if strength_bonus is None else strength_bonus
    amount = max(amount, 0)
    if _is_weak(source):
        amount = (amount * 3) // 4
    if _vulnerable_bonus(target):
        amount += amount // 2
    return max(amount, 0)


def _heal_target(target: PlayerCombatState | EnemyState, amount: int) -> int:
    healed = min(target.max_hp - target.hp, max(amount, 0))
    target.hp = min(target.max_hp, target.hp + max(amount, 0))
    return healed


def _lose_hp_target(target: PlayerCombatState | EnemyState, amount: int) -> int:
    hp_lost = min(target.hp, max(amount, 0))
    target.hp = max(target.hp - max(amount, 0), 0)
    return hp_lost


def _with_result(effect: JsonDict, **result: JsonValue) -> JsonDict:
    resolved = copy_effect(effect)
    resolved["result"] = result
    return resolved


def _next_card_instance_id(state: CombatState, card_id: str) -> str:
    highest_suffix = 0
    for card_instance_id in [
        *state.hand,
        *state.draw_pile,
        *state.discard_pile,
        *state.exhaust_pile,
        *state._cards_in_limbo,
    ]:
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


def _append_card_to_zone(
    state: CombatState, *, zone: str, card_instance_id: str
) -> None:
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


def _add_cards_to_zone(
    state: CombatState, *, zone: str, card_id: str, count: int
) -> list[str]:
    created_cards: list[str] = []
    for _ in range(max(count, 0)):
        card_instance_id = _next_card_instance_id(state, card_id)
        _append_card_to_zone(state, zone=zone, card_instance_id=card_instance_id)
        created_cards.append(card_instance_id)
    return created_cards


def _is_strike_like_card(card_instance_id: str) -> bool:
    try:
        card_id = card_id_from_instance_id(card_instance_id)
    except (TypeError, ValueError):
        return False
    return "strike" in card_id


def _resolve_damage_effect(
    state: CombatState,
    effect: JsonDict,
    *,
    base_amount: int,
    strength_bonus: int | None = None,
    extra_result: JsonDict | None = None,
) -> JsonDict:
    target = _get_target(state, effect.get("target_instance_id"))
    if _is_dead(target):
        return noop_effect(reason="dead_target")
    was_alive = target.hp > 0
    source = _get_target(state, effect.get("source_instance_id"))
    if isinstance(source, EnemyState) and isinstance(target, PlayerCombatState):
        flame_barrier_amount = _flame_barrier_amount(state)
        if flame_barrier_amount > 0:
            reflected_damage = damage_effect(
                source_instance_id=target.instance_id,
                target_instance_id=source.instance_id,
                amount=flame_barrier_amount,
            )
            reflected_damage["power_id"] = "flame_barrier"
            state.effect_queue.insert(0, reflected_damage)
    applied_amount = _damage_amount(
        source,
        target,
        base_amount,
        strength_bonus=strength_bonus,
    )
    blocked, actual_damage = _damage_target(target, applied_amount)
    if (
        isinstance(source, EnemyState)
        and isinstance(target, PlayerCombatState)
        and actual_damage > 0
    ):
        state.times_hit_this_combat += 1
    target_defeated = isinstance(target, EnemyState) and was_alive and target.hp == 0
    if target_defeated:
        state.effect_queue.append(
            emit_hook_effect(
                hook_name="on_enemy_defeated",
                payload={"target_instance_id": target.instance_id},
            )
        )
    result: JsonDict = {
        "applied_amount": applied_amount,
        "blocked": blocked,
        "actual_damage": actual_damage,
        "target_defeated": target_defeated,
    }
    if extra_result:
        result.update(extra_result)
    return _with_result(effect, **result)


def _remove_card_from_zones(state: CombatState, card_instance_id: str) -> bool:
    for zone in (state.hand, state.draw_pile, state.discard_pile, state.exhaust_pile):
        if card_instance_id in zone:
            zone.remove(card_instance_id)
            return True
    return False


def _replace_card_in_zones(
    state: CombatState, from_card_instance_id: str, to_card_instance_id: str
) -> bool:
    for zone in (state.hand, state.draw_pile, state.discard_pile, state.exhaust_pile):
        for index, current in enumerate(zone):
            if current == from_card_instance_id:
                zone[index] = to_card_instance_id
                return True
    return False


def _get_card_definition(registry: object | None, card_instance_id: str):
    if registry is None:
        raise ValueError("registry is required to classify exhausted cards")
    cards = getattr(registry, "cards", None)
    if not callable(cards):
        raise ValueError("registry must expose cards() for exhausted card lookup")
    return cards().get(card_id_from_instance_id(card_instance_id))


def _queue_on_exhaust_effects(
    state: CombatState,
    *,
    card_instance_id: str,
    registry: object | None,
) -> list[JsonDict]:
    queued_effects: list[JsonDict] = []
    if registry is not None:
        card_def = _get_card_definition(registry, card_instance_id)
        for raw_effect in card_def.on_exhaust_effects:
            queued_effect = copy_effect(raw_effect)
            queued_effect.setdefault("source_instance_id", card_instance_id)
            queued_effect.setdefault("target_instance_id", state.player.instance_id)
            queued_effects.append(queued_effect)
    for power in state.active_powers:
        power_id = power.get("power_id")
        raw_amount = power.get("amount")
        amount = raw_amount if isinstance(raw_amount, int) else 0
        if power_id == "dark_embrace" and amount > 0:
            queued_effects.append(
                {
                    "type": EFFECT_DRAW,
                    "source_instance_id": state.player.instance_id,
                    "target_instance_id": state.player.instance_id,
                    "amount": amount,
                    "power_id": power_id,
                    "trigger": "on_exhaust",
                }
            )
        if power_id == "feel_no_pain" and amount > 0:
            queued_effects.append(
                {
                    "type": EFFECT_BLOCK,
                    "source_instance_id": state.player.instance_id,
                    "target_instance_id": state.player.instance_id,
                    "amount": amount,
                    "power_id": power_id,
                    "trigger": "on_exhaust",
                }
            )
    return queued_effects


def _draw_trigger_effects(
    state: CombatState,
    *,
    drawn_card_instance_id: str,
    registry: object | None,
) -> list[JsonDict]:
    if registry is None:
        return []
    try:
        card_def = _get_card_definition(registry, drawn_card_instance_id)
    except (LookupError, TypeError, ValueError):
        return []
    if card_def.card_type not in {"status", "curse"}:
        return []
    queued_effects: list[JsonDict] = []
    for power in state.active_powers:
        power_id = power.get("power_id")
        raw_amount = power.get("amount")
        amount = raw_amount if isinstance(raw_amount, int) else 0
        if power_id == "evolve" and amount > 0:
            queued_effects.append(
                {
                    "type": EFFECT_DRAW,
                    "source_instance_id": state.player.instance_id,
                    "target_instance_id": state.player.instance_id,
                    "amount": amount,
                    "power_id": power_id,
                    "trigger": "on_draw",
                }
            )
        if power_id == "fire_breathing" and amount > 0:
            for enemy in state.enemies:
                if enemy.hp <= 0:
                    continue
                queued_effects.append(
                    damage_effect(
                        source_instance_id=state.player.instance_id,
                        target_instance_id=enemy.instance_id,
                        amount=amount,
                    )
                )
                queued_effects[-1]["power_id"] = power_id
                queued_effects[-1]["trigger"] = "on_draw"
    return queued_effects


def _enqueue_on_exhaust_effects(
    state: CombatState,
    *,
    card_instance_id: str,
    registry: object | None,
    queue_position: str = "front",
) -> list[JsonDict]:
    if queue_position not in {"front", "back"}:
        raise ValueError("queue_position must be 'front' or 'back'")
    queued_effects = _queue_on_exhaust_effects(
        state,
        card_instance_id=card_instance_id,
        registry=registry,
    )
    if queue_position == "front":
        state.effect_queue[0:0] = queued_effects
    else:
        state.effect_queue.extend(queued_effects)
    return queued_effects


def _move_cards_to_exhaust(
    state: CombatState,
    card_instance_ids: Sequence[str],
    *,
    registry: object | None,
    queue_position: str = "front",
) -> list[str]:
    exhausted_cards: list[str] = []
    queued_effects: list[JsonDict] = []
    for card_instance_id in card_instance_ids:
        if not _remove_card_from_zones(state, card_instance_id):
            continue
        state.exhaust_pile.append(card_instance_id)
        exhausted_cards.append(card_instance_id)
        queued_effects.extend(
            _queue_on_exhaust_effects(
                state,
                card_instance_id=card_instance_id,
                registry=registry,
            )
        )
    if queued_effects:
        if queue_position == "front":
            state.effect_queue[0:0] = queued_effects
        elif queue_position == "back":
            state.effect_queue.extend(queued_effects)
        else:
            raise ValueError("queue_position must be 'front' or 'back'")
    return exhausted_cards


def _non_attack_hand_cards(state: CombatState, *, registry: object | None) -> list[str]:
    non_attacks: list[str] = []
    for card_instance_id in state.hand:
        if _get_card_definition(registry, card_instance_id).card_type != "attack":
            non_attacks.append(card_instance_id)
    return non_attacks


def _pseudo_random_hand_selection(
    state: CombatState, candidates: list[str], *, count: int
) -> list[str]:
    if count <= 0 or not candidates:
        return []
    ordered = sorted(candidates)
    seed_basis = sum(
        ord(char)
        for item in [
            *state.hand,
            *state.draw_pile,
            *state.discard_pile,
            *state.exhaust_pile,
        ]
        for char in item
    )
    start_index = seed_basis % len(ordered)
    rotated = ordered[start_index:] + ordered[:start_index]
    return rotated[: min(count, len(rotated))]


def refill_draw_pile_from_discard(state: CombatState) -> bool:
    if not state.discard_pile:
        return False
    seed_basis = sum(
        ord(char)
        for item in [
            *state.hand,
            *state.draw_pile,
            *state.discard_pile,
            *state.exhaust_pile,
        ]
        for char in item
    )
    reshuffled = list(state.discard_pile)
    random.Random(seed_basis).shuffle(reshuffled)
    state.draw_pile.extend(reshuffled)
    state.discard_pile.clear()
    return True


def _draw_cards(
    state: CombatState, *, amount: int, registry: object | None = None
) -> tuple[int, list[str]]:
    for power in state.active_powers:
        if power.get("power_id") == "battle_trance":
            raw_amount = power.get("amount")
            if isinstance(raw_amount, int) and raw_amount > 0:
                return 0, []
    drawn_count = 0
    drawn_cards: list[str] = []
    queued_effects: list[JsonDict] = []
    for _ in range(max(amount, 0)):
        if not state.draw_pile:
            if not refill_draw_pile_from_discard(state):
                break
        drawn_card_instance_id = state.draw_pile.pop(0)
        state.hand.append(drawn_card_instance_id)
        drawn_cards.append(drawn_card_instance_id)
        queued_effects.extend(
            _draw_trigger_effects(
                state,
                drawn_card_instance_id=drawn_card_instance_id,
                registry=registry,
            )
        )
        drawn_count += 1
    if queued_effects:
        state.effect_queue[0:0] = queued_effects
    return drawn_count, drawn_cards


def _first_living_enemy(state: CombatState) -> EnemyState | None:
    for enemy in state.enemies:
        if enemy.hp > 0:
            return enemy
    return None


def _apply_status(
    target: PlayerCombatState | EnemyState,
    *,
    status_id: str,
    stacks: int,
) -> None:
    if stacks == 0:
        return
    for index, status in enumerate(target.statuses):
        if status.status_id != status_id:
            continue
        next_stacks = status.stacks + stacks
        if next_stacks == 0:
            target.statuses.pop(index)
        else:
            target.statuses[index] = StatusState(
                status_id=status_id, stacks=next_stacks
            )
        return
    target.statuses.append(StatusState(status_id=status_id, stacks=stacks))


def _append_or_increase_power(
    state: CombatState,
    *,
    power_id: str,
    amount: int,
    self_damage: int | None,
) -> JsonDict:
    normalized_amount = max(amount, 0)
    normalized_self_damage = max(self_damage, 0) if self_damage is not None else None
    for power in state.active_powers:
        if power.get("power_id") != power_id:
            continue
        raw_existing_amount = power.get("amount")
        existing_amount = (
            raw_existing_amount if isinstance(raw_existing_amount, int) else 0
        )
        power["amount"] = existing_amount + normalized_amount
        if normalized_self_damage is not None:
            power["self_damage"] = normalized_self_damage
        return power

    next_power: JsonDict = {
        "power_id": power_id,
        "amount": normalized_amount,
    }
    if normalized_self_damage is not None:
        next_power["self_damage"] = normalized_self_damage
    state.active_powers.append(next_power)
    return next_power


def _flame_barrier_amount(state: CombatState) -> int:
    for power in state.active_powers:
        if power.get("power_id") != "flame_barrier":
            continue
        raw_amount = power.get("amount")
        if isinstance(raw_amount, int) and raw_amount > 0:
            return raw_amount
    return 0


def _has_pending_hook(state: CombatState, hook_name: str) -> bool:
    for effect in state.effect_queue:
        if (
            effect.get("type") == EFFECT_EMIT_HOOK
            and effect.get("hook_name") == hook_name
        ):
            return True
    return False


def _maybe_enqueue_combat_end(
    state: CombatState, *, payload: JsonDict | None = None
) -> None:
    if all(enemy.hp == 0 for enemy in state.enemies) and not _has_pending_hook(
        state, "on_combat_end"
    ):
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
    registry: object | None = None,
) -> JsonDict:
    effect = state.effect_queue.pop(0)
    effect_type = effect.get("type")

    if effect_type == EFFECT_DAMAGE:
        return _resolve_damage_effect(
            state,
            effect,
            base_amount=int(effect.get("amount", 0)),
        )

    if effect_type == EFFECT_DAMAGE_EQUAL_TO_BLOCK:
        source = _get_target(state, effect.get("source_instance_id"))
        base_amount = source.block if source is not None else 0
        return _resolve_damage_effect(state, effect, base_amount=base_amount)

    if effect_type == EFFECT_DAMAGE_WITH_STRENGTH_MULTIPLIER:
        source = _get_target(state, effect.get("source_instance_id"))
        multiplier = int(effect.get("multiplier", 1))
        return _resolve_damage_effect(
            state,
            effect,
            base_amount=int(effect.get("base", 0)),
            strength_bonus=_strength_bonus(source) * multiplier,
        )

    if effect_type == EFFECT_DAMAGE_PER_STRIKE_IN_DECK:
        excluded_card_instance_id = effect.get("excluding_card_instance_id")
        strike_count = sum(
            1
            for card_instance_id in [
                *state.hand,
                *state.draw_pile,
                *state.discard_pile,
                *state.exhaust_pile,
            ]
            if card_instance_id != excluded_card_instance_id
            and _is_strike_like_card(card_instance_id)
        )
        return _resolve_damage_effect(
            state,
            effect,
            base_amount=int(effect.get("base", 0))
            + int(effect.get("amount_per_strike", 0)) * strike_count,
            extra_result={"strike_count": strike_count},
        )

    if effect_type == EFFECT_RAMPAGE_DAMAGE:
        base_amount = int(effect.get("amount", 0))
        increment = int(effect.get("increment", 5))
        card_instance_id = effect.get("card_instance_id")
        play_count_before = (
            state.card_play_data.get(card_instance_id, 0)
            if isinstance(card_instance_id, str)
            else 0
        )
        resolved = _resolve_damage_effect(
            state,
            effect,
            base_amount=base_amount + increment * play_count_before,
            extra_result={
                "play_count_before": play_count_before,
                "play_count_after": (
                    play_count_before + 1
                    if isinstance(card_instance_id, str)
                    else play_count_before
                ),
            },
        )
        if isinstance(card_instance_id, str):
            state.card_play_data[card_instance_id] = play_count_before + 1
        return resolved

    if effect_type == EFFECT_BLOCK:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        source = _get_target(state, effect.get("source_instance_id"))
        gained_block = max(int(effect.get("amount", 0)) + _dexterity_bonus(source), 0)
        target.block += gained_block
        if (
            isinstance(target, PlayerCombatState)
            and target.instance_id == state.player.instance_id
            and gained_block > 0
        ):
            for power in state.active_powers:
                if power.get("power_id") != "juggernaut":
                    continue
                raw_amount = power.get("amount")
                amount = raw_amount if isinstance(raw_amount, int) else 0
                if amount <= 0:
                    continue
                enemy = _first_living_enemy(state)
                if enemy is None:
                    break
                juggernaut_damage = damage_effect(
                    source_instance_id=state.player.instance_id,
                    target_instance_id=enemy.instance_id,
                    amount=amount,
                )
                juggernaut_damage["power_id"] = "juggernaut"
                juggernaut_damage["trigger"] = "on_gain_block"
                state.effect_queue.insert(0, juggernaut_damage)
                break
        return _with_result(effect, gained_block=gained_block)

    if effect_type == EFFECT_DOUBLE_BLOCK:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        previous_block = max(target.block, 0)
        target.block = previous_block * 2
        return _with_result(
            effect,
            previous_block=previous_block,
            doubled_block=target.block,
        )

    if effect_type == EFFECT_STRENGTH:
        target_instance_id = effect.get("target_instance_id")
        if target_instance_id is None:
            target_instance_id = effect.get("source_instance_id")
        target = _get_target(state, target_instance_id)
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        applied_stacks = int(effect.get("amount", 0))
        _apply_status(
            target,
            status_id="strength",
            stacks=applied_stacks,
        )
        return _with_result(effect, applied_stacks=applied_stacks)

    if effect_type == EFFECT_DEXTERITY:
        target_instance_id = effect.get("target_instance_id")
        if target_instance_id is None:
            target_instance_id = effect.get("source_instance_id")
        target = _get_target(state, target_instance_id)
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        applied_stacks = int(effect.get("amount", 0))
        _apply_status(
            target,
            status_id="dexterity",
            stacks=applied_stacks,
        )
        return _with_result(effect, applied_stacks=applied_stacks)

    if effect_type == EFFECT_HEAL:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        healed = _heal_target(target, int(effect.get("amount", 0)))
        return _with_result(effect, actual_healed=healed)

    if effect_type == EFFECT_LOSE_HP:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        hp_lost = _lose_hp_target(target, int(effect.get("amount", 0)))
        return _with_result(effect, actual_hp_lost=hp_lost)

    if effect_type == EFFECT_DRAW:
        target = _get_target(state, effect.get("target_instance_id"))
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        draw_count, _drawn_cards = _draw_cards(
            state,
            amount=int(effect.get("amount", 0)),
            registry=registry,
        )
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
        _add_cards_to_zone(state, zone="discard_pile", card_id=card_id, count=count)
        return effect

    if effect_type == EFFECT_ADD_CARD_TO_DRAW_PILE:
        card_id = effect.get("card_id")
        if not isinstance(card_id, str):
            raise TypeError("card_id must be a string")
        _add_cards_to_zone(
            state,
            zone="draw_pile",
            card_id=card_id,
            count=int(effect.get("count", 1)),
        )
        return effect

    if effect_type == EFFECT_ADD_CARDS_TO_HAND:
        card_id = effect.get("card_id")
        if not isinstance(card_id, str):
            raise TypeError("card_id must be a string")
        _add_cards_to_zone(
            state,
            zone="hand",
            card_id=card_id,
            count=int(effect.get("count", 1)),
        )
        return effect

    if effect_type == EFFECT_EXHAUST_ALL_NON_ATTACKS_GAIN_BLOCK:
        source = _get_target(state, effect.get("source_instance_id"))
        if _is_dead(source):
            return noop_effect(reason="dead_target")
        exhausted_cards = _move_cards_to_exhaust(
            state,
            _non_attack_hand_cards(state, registry=registry),
            registry=registry,
        )
        gained_block = max(
            len(exhausted_cards) * int(effect.get("amount_per_card", 0))
            + _dexterity_bonus(source),
            0,
        )
        source.block += gained_block
        return _with_result(
            effect,
            exhausted_cards=exhausted_cards,
            exhausted_count=len(exhausted_cards),
            gained_block=gained_block,
        )

    if effect_type == EFFECT_EXHAUST_ALL_NON_ATTACKS_IN_HAND:
        exhausted_cards = _move_cards_to_exhaust(
            state,
            _non_attack_hand_cards(state, registry=registry),
            registry=registry,
        )
        return _with_result(
            effect,
            exhausted_cards=exhausted_cards,
            exhausted_count=len(exhausted_cards),
        )

    if effect_type == EFFECT_EXHAUST_ALL_IN_HAND:
        exhausted_cards = _move_cards_to_exhaust(
            state,
            list(state.hand),
            registry=registry,
        )
        return _with_result(
            effect,
            exhausted_cards=exhausted_cards,
            exhausted_count=len(exhausted_cards),
        )

    if effect_type == EFFECT_EXHAUST_RANDOM_HAND:
        count = max(int(effect.get("count", 1)), 0)
        selected_cards = _pseudo_random_hand_selection(
            state, list(state.hand), count=count
        )
        exhausted_cards = _move_cards_to_exhaust(
            state, selected_cards, registry=registry
        )
        return _with_result(effect, exhausted_cards=exhausted_cards)

    if effect_type == EFFECT_EXHAUST_TARGET_CARD:
        card_instance_id = effect.get("target_card_instance_id")
        if not isinstance(card_instance_id, str):
            raise TypeError("target_card_instance_id must be a string")
        exhausted_cards = _move_cards_to_exhaust(
            state, [card_instance_id], registry=registry
        )
        if not exhausted_cards:
            return noop_effect(reason="missing_target_card")
        return _with_result(effect, exhausted_cards=exhausted_cards)

    if effect_type == EFFECT_UPGRADE_TARGET_CARD:
        target_card_instance_id = effect.get("target_card_instance_id")
        upgraded_card_id = effect.get("upgraded_card_id")
        if not isinstance(target_card_instance_id, str):
            raise TypeError("target_card_instance_id must be a string")
        if not isinstance(upgraded_card_id, str):
            raise TypeError("upgraded_card_id must be a string")
        _old_card_id, suffix = target_card_instance_id.split("#", 1)
        upgraded_card_instance_id = f"{upgraded_card_id}#{suffix}"
        if not _replace_card_in_zones(
            state, target_card_instance_id, upgraded_card_instance_id
        ):
            return noop_effect(reason="missing_target_card")
        return _with_result(
            effect,
            upgraded_from=target_card_instance_id,
            upgraded_to=upgraded_card_instance_id,
        )

    if effect_type == EFFECT_UPGRADE_ALL_HAND:
        upgrades = effect.get("upgrades")
        if not isinstance(upgrades, dict):
            raise TypeError("upgrades must be a mapping")
        upgraded_cards: list[JsonDict] = []
        for index, card_instance_id in enumerate(list(state.hand)):
            try:
                card_id = card_id_from_instance_id(card_instance_id)
            except (TypeError, ValueError):
                continue
            upgraded_card_id = upgrades.get(card_id)
            if not isinstance(upgraded_card_id, str):
                continue
            _old_card_id, suffix = card_instance_id.split("#", 1)
            upgraded_card_instance_id = f"{upgraded_card_id}#{suffix}"
            state.hand[index] = upgraded_card_instance_id
            upgraded_cards.append(
                {"from": card_instance_id, "to": upgraded_card_instance_id}
            )
        return _with_result(effect, upgraded_cards=upgraded_cards)

    if effect_type == EFFECT_ADD_POWER:
        power_id = effect.get("power_id")
        if not isinstance(power_id, str):
            raise TypeError("power_id must be a string")
        amount = max(int(effect.get("amount", 0)), 0)
        raw_self_damage = effect.get("self_damage")
        if raw_self_damage is not None and not isinstance(raw_self_damage, int):
            raise TypeError("self_damage must be an int")
        merged_power = _append_or_increase_power(
            state,
            power_id=power_id,
            amount=amount,
            self_damage=raw_self_damage if isinstance(raw_self_damage, int) else None,
        )
        if power_id == "inflame" and amount > 0:
            _apply_status(
                state.player,
                status_id="strength",
                stacks=amount,
            )
        return _with_result(
            effect,
            power_id=power_id,
            amount=amount,
            total_amount=int(merged_power.get("amount", amount)),
        )

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

    if effect_type == EFFECT_PUT_TOP_OF_DECK_FROM_DISCARD:
        target_card = effect.get("target_card_instance_id")
        if isinstance(target_card, str) and target_card in state.discard_pile:
            state.discard_pile.remove(target_card)
            state.draw_pile.insert(0, target_card)
            return {**effect, "result": {"moved": target_card}}
        return {**effect, "result": {"moved": None}}

    if effect_type == EFFECT_NOOP:
        return effect

    if effect_type == EFFECT_SPOT_WEAKNESS_STRENGTH:
        target_instance_id = effect.get("target_instance_id")
        enemy = next(
            (
                e
                for e in state.enemies
                if e.instance_id == target_instance_id and e.hp > 0
            ),
            None,
        )
        amount = int(effect.get("amount", 3))
        enemy_intends_damage = False
        if enemy is not None:
            current_move = getattr(enemy, "current_move", None)
            if isinstance(current_move, dict):
                move_effects = current_move.get("effects", [])
                enemy_intends_damage = any(
                    str(me.get("type", "")) == EFFECT_DAMAGE for me in move_effects
                )
        if enemy_intends_damage:
            _apply_status(state.player, status_id="strength", stacks=amount)
            return {**effect, "result": {"strength_gained": amount}}
        return {**effect, "result": {"strength_gained": 0}}

    if effect_type == EFFECT_DAMAGE_ON_KILL_GAIN_MAX_HP:
        target_instance_id = effect.get("target_instance_id")
        source_instance_id = effect.get("source_instance_id")
        amount = int(effect.get("amount", 0))
        hp_gain = int(effect.get("hp_gain", 3))
        target = _get_target(state, target_instance_id)
        if _is_dead(target):
            return noop_effect(reason="dead_target")
        _blocked, actual_damage = _damage_target(
            target,
            _damage_amount(_get_target(state, source_instance_id), target, amount),
        )
        killed = target.hp <= 0
        if killed:
            state.player.max_hp += hp_gain
            state.player.hp = min(state.player.hp + hp_gain, state.player.max_hp)
        return {
            **effect,
            "result": {
                "applied_amount": actual_damage,
                "target_defeated": killed,
                "hp_gain": hp_gain if killed else 0,
            },
        }

    if effect_type == EFFECT_SELECT_FROM_EXHAUST_TO_HAND:
        target_card = effect.get("target_card_instance_id")
        if isinstance(target_card, str) and target_card in state.exhaust_pile:
            state.exhaust_pile.remove(target_card)
            state.hand.append(target_card)
            return {**effect, "result": {"moved": target_card}}
        return {**effect, "result": {"moved": None}}

    if effect_type == EFFECT_COPY_CARD_TO_HAND:
        source_card = effect.get("source_card_instance_id")
        if isinstance(source_card, str):
            card_id = source_card.split("#")[0]
            new_instance_id = _next_card_instance_id(state, card_id)
            state.hand.append(new_instance_id)
            return {**effect, "result": {"created": new_instance_id}}
        return {**effect, "result": {"created": None}}

    if effect_type == EFFECT_DOUBLE_STRENGTH:
        source_instance_id = effect.get("source_instance_id")
        source = _get_target(state, source_instance_id)
        if source is None:
            return noop_effect(reason="missing_source")
        current = next(
            (s.stacks for s in source.statuses if s.status_id == "strength"), 0
        )
        _apply_status(source, status_id="strength", stacks=current)
        return {
            **effect,
            "result": {"doubled_from": current, "doubled_to": current * 2},
        }

    if effect_type == EFFECT_DAMAGE_LIFESTEAL_ALL_ENEMIES:
        source = _get_target(state, effect.get("source_instance_id"))
        base_amount = int(effect.get("amount", 0))
        total_healed = 0
        results: list[JsonDict] = []
        for enemy in state.enemies:
            if enemy.hp <= 0:
                continue
            applied_amount = _damage_amount(source, enemy, base_amount)
            blocked, actual_damage = _damage_target(enemy, applied_amount)
            total_healed += actual_damage
            results.append(
                {
                    "target_instance_id": enemy.instance_id,
                    "applied_amount": applied_amount,
                    "blocked": blocked,
                    "actual_damage": actual_damage,
                    "target_defeated": enemy.hp == 0,
                }
            )
            if enemy.hp == 0:
                state.effect_queue.append(
                    emit_hook_effect(
                        hook_name="on_enemy_defeated",
                        payload={"target_instance_id": enemy.instance_id},
                    )
                )
        healed = _heal_target(state.player, total_healed)
        return _with_result(effect, hits=results, total_healed=healed)

    raise ValueError(f"unsupported effect type: {effect_type}")


def resolve_effect_queue(
    state: CombatState,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
    registry: object | None = None,
) -> list[JsonDict]:
    resolved: list[JsonDict] = []
    while state.effect_queue:
        resolved.append(
            resolve_next_effect(
                state,
                hook_registrations=hook_registrations,
                registry=registry,
            )
        )
    return resolved
