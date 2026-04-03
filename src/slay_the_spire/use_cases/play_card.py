from __future__ import annotations

from collections.abc import Sequence

from slay_the_spire.domain.combat.turn_flow import resolve_player_actions
from slay_the_spire.domain.effects.effect_resolver import _enqueue_on_exhaust_effects
from slay_the_spire.domain.effects.effect_types import (
    EFFECT_DAMAGE,
    EFFECT_DAMAGE_ALL_ENEMIES,
    EFFECT_DAMAGE_ALL_ENEMIES_X_TIMES,
    EFFECT_DAMAGE_EQUAL_TO_BLOCK,
    EFFECT_DAMAGE_WITH_STRENGTH_MULTIPLIER,
    EFFECT_DAMAGE_PER_STRIKE_IN_DECK,
    EFFECT_DROPKICK_EFFECT,
    EFFECT_EXHAUST_ALL_IN_HAND_DAMAGE,
    EFFECT_DAMAGE_ON_KILL_GAIN_MAX_HP,
    EFFECT_EXHAUST_TARGET_CARD,
    EFFECT_PUT_TOP_OF_DECK_FROM_DISCARD,
    EFFECT_PUT_TOP_OF_DECK_FROM_HAND,
    EFFECT_RAMPAGE_DAMAGE,
    EFFECT_SELECT_FROM_EXHAUST_TO_HAND,
    EFFECT_SPOT_WEAKNESS_STRENGTH,
    EFFECT_UPGRADE_TARGET_CARD,
    EFFECT_UPGRADE_ALL_HAND,
    EFFECT_VULNERABLE,
    EFFECT_VULNERABLE_ALL_ENEMIES,
    EFFECT_WEAK,
    copy_effect,
)
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.cards import (
    CombatActionResult,
    card_id_from_instance_id,
)
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.content.registries import CardDef
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.types import JsonDict
from slay_the_spire.use_cases.combat_events import (
    build_player_action_events,
    capture_entity_snapshots,
)
from slay_the_spire.use_cases.combat_log import (
    append_log_entries,
    describe_player_action,
    describe_triggered_active_powers,
)
from slay_the_spire.use_cases.card_runtime_rules import (
    resolve_post_play_destination,
    resolve_runtime_card_cost,
)

TargetSelection = str | dict[str, str] | None

_CARD_DAMAGE_EFFECT_TYPES = {
    EFFECT_DAMAGE,
    EFFECT_DAMAGE_EQUAL_TO_BLOCK,
    EFFECT_DAMAGE_WITH_STRENGTH_MULTIPLIER,
    EFFECT_DAMAGE_PER_STRIKE_IN_DECK,
    EFFECT_DROPKICK_EFFECT,
    EFFECT_RAMPAGE_DAMAGE,
    EFFECT_DAMAGE_ON_KILL_GAIN_MAX_HP,
    "damage_lifesteal_all_enemies",
}

_TARGETED_EFFECT_TYPES = {
    EFFECT_DAMAGE,
    EFFECT_DAMAGE_EQUAL_TO_BLOCK,
    EFFECT_DAMAGE_WITH_STRENGTH_MULTIPLIER,
    EFFECT_DAMAGE_PER_STRIKE_IN_DECK,
    EFFECT_EXHAUST_ALL_IN_HAND_DAMAGE,
    EFFECT_VULNERABLE,
    EFFECT_WEAK,
    EFFECT_SPOT_WEAKNESS_STRENGTH,
    EFFECT_DAMAGE_ON_KILL_GAIN_MAX_HP,
    EFFECT_RAMPAGE_DAMAGE,
    EFFECT_DROPKICK_EFFECT,
    "strength",
}
_HAND_TARGETED_EFFECT_TYPES = {
    EFFECT_EXHAUST_TARGET_CARD,
    EFFECT_UPGRADE_TARGET_CARD,
    EFFECT_PUT_TOP_OF_DECK_FROM_HAND,
}


def _enemy_target_id(target: TargetSelection) -> str | None:
    if isinstance(target, str):
        return target
    if isinstance(target, dict):
        return target.get("enemy")
    return None


def _zone_target_id(target: TargetSelection, zone: str) -> str | None:
    if isinstance(target, dict):
        return target.get(zone)
    return None


def resolve_card_cost(
    card_def: CardDef, combat_state: CombatState, card_instance_id: str
) -> int:
    return resolve_runtime_card_cost(card_def, combat_state, card_instance_id)


def _validate_play_condition(
    card_def: CardDef,
    combat_state: CombatState,
    card_instance_id: str,
    registry: ContentProviderPort,
) -> None:
    if card_def.play_condition != "all_attacks_in_hand":
        return
    other_cards = [card for card in combat_state.hand if card != card_instance_id]
    for other_card in other_cards:
        other_def = registry.cards().get(card_id_from_instance_id(other_card))
        if other_def.card_type != "attack":
            raise ValueError("手牌中存在非攻击牌，无法打出交锋。")


def _consume_player_power(state: CombatState, power_id: str) -> int:
    for index, power in enumerate(state.active_powers):
        if power.get("power_id") != power_id:
            continue
        amount = int(power.get("amount", 0))
        if amount <= 1:
            state.active_powers.pop(index)
        else:
            state.active_powers[index] = {**power, "amount": amount - 1}
        return amount
    return 0


def _materialize_card_effects(
    raw_effects: Sequence[JsonDict],
    *,
    card_type: str,
    combat_state: CombatState,
    card_instance_id: str,
    registry: ContentProviderPort,
    source_instance_id: str,
    target_id: TargetSelection,
    energy_spent: int,
) -> list[JsonDict]:
    resolved_enemy_id = _enemy_target_id(target_id)
    effects: list[JsonDict] = []
    for raw_effect in raw_effects:
        effect = copy_effect(raw_effect)
        effect_type = effect.get("type")
        if not isinstance(effect_type, str):
            raise TypeError("card effect type must be a string")
        if effect_type == EFFECT_DAMAGE_ALL_ENEMIES:
            damage_amount = int(effect.get("amount", 0))
            for enemy in combat_state.enemies:
                effects.append(
                    {
                        "type": EFFECT_DAMAGE,
                        "amount": damage_amount,
                        "source_instance_id": source_instance_id,
                        "target_instance_id": enemy.instance_id,
                        "uses_strength": card_type == "attack",
                    }
                )
            continue
        if effect_type == EFFECT_DAMAGE_ALL_ENEMIES_X_TIMES:
            repeat_count = max(energy_spent, 0)
            damage_amount = int(effect.get("amount", 0))
            for _ in range(repeat_count):
                for enemy in combat_state.enemies:
                        effects.append(
                            {
                                "type": EFFECT_DAMAGE,
                                "amount": damage_amount,
                                "source_instance_id": source_instance_id,
                                "target_instance_id": enemy.instance_id,
                                "uses_strength": card_type == "attack",
                            }
                        )
            continue
        if effect_type == EFFECT_VULNERABLE_ALL_ENEMIES:
            stacks = int(effect.get("stacks", 0))
            for enemy in combat_state.enemies:
                effects.append(
                    {
                        "type": EFFECT_VULNERABLE,
                        "stacks": stacks,
                        "source_instance_id": source_instance_id,
                        "target_instance_id": enemy.instance_id,
                    }
                )
            continue
        if "source_instance_id" not in effect:
            effect["source_instance_id"] = source_instance_id
        if effect.get("target_instance_id") == "self":
            effect["target_instance_id"] = source_instance_id
        if effect_type == EFFECT_RAMPAGE_DAMAGE:
            effect["card_instance_id"] = card_instance_id
        if effect_type in _TARGETED_EFFECT_TYPES:
            if "target_instance_id" in effect:
                pass
            elif resolved_enemy_id is None:
                raise ValueError("target is required for targeted cards")
            else:
                effect["target_instance_id"] = resolved_enemy_id
        elif effect_type in _HAND_TARGETED_EFFECT_TYPES:
            hand_target = _zone_target_id(target_id, "hand") or (
                target_id if isinstance(target_id, str) else None
            )
            if hand_target is None:
                raise ValueError("target is required for targeted cards")
            if hand_target == card_instance_id:
                raise ValueError("不能将当前打出的牌作为目标。")
            if hand_target not in combat_state.hand:
                raise ValueError("target card is not in hand")
            effect["target_card_instance_id"] = hand_target
            if effect_type == EFFECT_UPGRADE_TARGET_CARD:
                target_card_def = registry.cards().get(
                    card_id_from_instance_id(hand_target)
                )
                if target_card_def.upgrades_to is None:
                    raise ValueError("所选卡牌无法升级。")
                effect["upgraded_card_id"] = target_card_def.upgrades_to
        elif effect_type == EFFECT_PUT_TOP_OF_DECK_FROM_DISCARD:
            discard_target = _zone_target_id(target_id, "discard")
            if discard_target is not None:
                effect["target_card_instance_id"] = discard_target
        elif effect_type == EFFECT_SELECT_FROM_EXHAUST_TO_HAND:
            exhaust_target = _zone_target_id(target_id, "exhaust")
            if exhaust_target is not None:
                effect["target_card_instance_id"] = exhaust_target
        elif effect_type == EFFECT_UPGRADE_ALL_HAND:
            upgrades: dict[str, str] = {}
            for hand_card_instance_id in combat_state.hand:
                if hand_card_instance_id == card_instance_id:
                    continue
                hand_card_def = registry.cards().get(
                    card_id_from_instance_id(hand_card_instance_id)
                )
                if hand_card_def.upgrades_to is not None:
                    upgrades[card_id_from_instance_id(hand_card_instance_id)] = (
                        hand_card_def.upgrades_to
                    )
            effect["upgrades"] = upgrades
        elif (
            effect_type in {"block", "draw", "lose_hp", "double_block"}
            and "target_instance_id" not in effect
        ):
            effect["target_instance_id"] = source_instance_id
        if effect_type in _CARD_DAMAGE_EFFECT_TYPES and "uses_strength" not in effect:
            effect["uses_strength"] = card_type == "attack"
        effects.append(effect)
    return effects


def play_card(
    combat_state: CombatState,
    card_instance_id: str,
    target_id: TargetSelection,
    registry: ContentProviderPort,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
) -> CombatActionResult:
    if card_instance_id not in combat_state.hand:
        raise ValueError(f"card {card_instance_id} is not in hand")

    card_id = card_id_from_instance_id(card_instance_id)
    card_def = registry.cards().get(card_id)
    if not getattr(card_def, "playable", True):
        raise ValueError("这张牌无法打出。")
    resolved_cost = resolve_card_cost(card_def, combat_state, card_instance_id)
    if resolved_cost >= 0 and combat_state.energy < resolved_cost:
        raise ValueError("not enough energy to play card")
    _validate_play_condition(card_def, combat_state, card_instance_id, registry)
    energy_spent = combat_state.energy if resolved_cost == -1 else resolved_cost

    materialized_effects = _materialize_card_effects(
        card_def.effects,
        card_type=card_def.card_type,
        combat_state=combat_state,
        card_instance_id=card_instance_id,
        registry=registry,
        source_instance_id=combat_state.player.instance_id,
        target_id=target_id,
        energy_spent=energy_spent,
    )

    punishment_effects: list[JsonDict] = []
    if card_def.card_type == "skill":
        for enemy in combat_state.enemies:
            if enemy.hp <= 0 or enemy.enemy_id != "gremlin_nob":
                continue
            punishment_effects.append(
                {
                    "type": "strength",
                    "amount": 2,
                    "source_instance_id": combat_state.player.instance_id,
                    "target_instance_id": enemy.instance_id,
                }
            )

    # Attack-trigger power hooks: double_tap, rage
    attack_trigger_extras: list[JsonDict] = []
    if card_def.card_type == "attack":
        double_tap_amount = _consume_player_power(combat_state, "double_tap")
        if double_tap_amount > 0:
            attack_trigger_extras.extend(materialized_effects[:])
        rage_amount = _consume_player_power(combat_state, "rage")
        if rage_amount > 0:
            attack_trigger_extras.append(
                {
                    "type": "block",
                    "amount": rage_amount,
                    "source_instance_id": combat_state.player.instance_id,
                    "target_instance_id": combat_state.player.instance_id,
                }
            )

    # Rupture: if any effect causes self-damage (lose_hp targeting player), gain strength
    rupture_extras: list[JsonDict] = []
    rupture_amount = next(
        (
            int(p.get("amount", 0))
            for p in combat_state.active_powers
            if p.get("power_id") == "rupture"
        ),
        0,
    )
    if rupture_amount > 0:
        player_id = combat_state.player.instance_id
        has_self_damage = any(
            str(e.get("type")) == "lose_hp"
            and e.get("target_instance_id", player_id) == player_id
            for e in materialized_effects
        )
        if has_self_damage:
            rupture_extras.append(
                {
                    "type": "strength",
                    "amount": rupture_amount,
                    "source_instance_id": player_id,
                    "target_instance_id": player_id,
                }
            )

    snapshots_before = capture_entity_snapshots(combat_state, registry)

    combat_state.energy -= energy_spent
    combat_state.hand.remove(card_instance_id)
    combat_state._cards_in_limbo.append(card_instance_id)
    combat_state.effect_queue.extend(punishment_effects)
    combat_state.effect_queue.extend(materialized_effects)
    combat_state.effect_queue.extend(attack_trigger_extras)
    combat_state.effect_queue.extend(rupture_extras)
    try:
        resolved_effects = resolve_player_actions(
            combat_state,
            hook_registrations=hook_registrations,
            registry=registry,
        )
    except Exception:
        if card_instance_id in combat_state._cards_in_limbo:
            combat_state._cards_in_limbo.remove(card_instance_id)
        raise
    destination = resolve_post_play_destination(
        card_def, combat_state, card_instance_id
    )
    if destination == "exhaust":
        if card_instance_id in combat_state._cards_in_limbo:
            combat_state._cards_in_limbo.remove(card_instance_id)
        combat_state.exhaust_pile.append(card_instance_id)
        _enqueue_on_exhaust_effects(
            combat_state,
            card_instance_id=card_instance_id,
            registry=registry,
            queue_position="back",
        )
        resolved_effects.extend(
            resolve_player_actions(
                combat_state,
                hook_registrations=hook_registrations,
                registry=registry,
            )
        )
    elif destination == "discard":
        if card_instance_id in combat_state._cards_in_limbo:
            combat_state._cards_in_limbo.remove(card_instance_id)
        combat_state.discard_pile.append(card_instance_id)
    elif card_instance_id in combat_state._cards_in_limbo:
        combat_state._cards_in_limbo.remove(card_instance_id)
    player_action_events = build_player_action_events(
        card_name=card_def.name,
        resolved_effects=resolved_effects,
        entities=snapshots_before,
        registry=registry,
    )
    append_log_entries(
        combat_state,
        [
            *describe_player_action(events=player_action_events),
            *describe_triggered_active_powers(events=player_action_events),
        ],
    )
    return CombatActionResult(
        combat_state=combat_state,
        resolved_effects=resolved_effects,
    )
