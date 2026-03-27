from __future__ import annotations

from collections.abc import Sequence

from slay_the_spire.domain.combat.turn_flow import resolve_player_actions
from slay_the_spire.domain.effects.effect_types import (
    EFFECT_DAMAGE,
    EFFECT_DAMAGE_ALL_ENEMIES_X_TIMES,
    EFFECT_EXHAUST_TARGET_CARD,
    EFFECT_UPGRADE_TARGET_CARD,
    EFFECT_UPGRADE_ALL_HAND,
    EFFECT_VULNERABLE,
    EFFECT_WEAK,
    copy_effect,
)
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.cards import CombatActionResult, card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.content.registries import CardDef
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.types import JsonDict
from slay_the_spire.use_cases.combat_events import build_player_action_events, capture_entity_snapshots
from slay_the_spire.use_cases.combat_log import append_log_entries, describe_player_action

_TARGETED_EFFECT_TYPES = {EFFECT_DAMAGE, EFFECT_VULNERABLE, EFFECT_WEAK}
_HAND_TARGETED_EFFECT_TYPES = {EFFECT_EXHAUST_TARGET_CARD, EFFECT_UPGRADE_TARGET_CARD}


def _materialize_card_effects(
    raw_effects: Sequence[JsonDict],
    *,
    combat_state: CombatState,
    card_instance_id: str,
    registry: ContentProviderPort,
    source_instance_id: str,
    target_id: str | None,
    energy_spent: int,
) -> list[JsonDict]:
    effects: list[JsonDict] = []
    for raw_effect in raw_effects:
        effect = copy_effect(raw_effect)
        effect_type = effect.get("type")
        if not isinstance(effect_type, str):
            raise TypeError("card effect type must be a string")
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
                        }
                    )
            continue
        if "source_instance_id" not in effect:
            effect["source_instance_id"] = source_instance_id
        if effect_type in _TARGETED_EFFECT_TYPES:
            if target_id is None:
                raise ValueError("target is required for targeted cards")
            effect["target_instance_id"] = target_id
        elif effect_type in _HAND_TARGETED_EFFECT_TYPES:
            if target_id is None:
                raise ValueError("target is required for targeted cards")
            if target_id == card_instance_id:
                raise ValueError("不能将当前打出的牌作为目标。")
            if target_id not in combat_state.hand:
                raise ValueError("target card is not in hand")
            effect["target_card_instance_id"] = target_id
            if effect_type == EFFECT_UPGRADE_TARGET_CARD:
                target_card_def = registry.cards().get(card_id_from_instance_id(target_id))
                if target_card_def.upgrades_to is None:
                    raise ValueError("所选卡牌无法升级。")
                effect["upgraded_card_id"] = target_card_def.upgrades_to
        elif effect_type == EFFECT_UPGRADE_ALL_HAND:
            upgrades: dict[str, str] = {}
            for hand_card_instance_id in combat_state.hand:
                if hand_card_instance_id == card_instance_id:
                    continue
                hand_card_def = registry.cards().get(card_id_from_instance_id(hand_card_instance_id))
                if hand_card_def.upgrades_to is not None:
                    upgrades[card_id_from_instance_id(hand_card_instance_id)] = hand_card_def.upgrades_to
            effect["upgrades"] = upgrades
        elif effect_type in {"block", "draw", "lose_hp"} and "target_instance_id" not in effect:
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
) -> CombatActionResult:
    if card_instance_id not in combat_state.hand:
        raise ValueError(f"card {card_instance_id} is not in hand")

    card_id = card_id_from_instance_id(card_instance_id)
    card_def = registry.cards().get(card_id)
    if not getattr(card_def, "playable", True):
        raise ValueError("这张牌无法打出。")
    if card_def.cost >= 0 and combat_state.energy < card_def.cost:
        raise ValueError("not enough energy to play card")
    energy_spent = combat_state.energy if card_def.cost == -1 else card_def.cost

    materialized_effects = _materialize_card_effects(
        card_def.effects,
        combat_state=combat_state,
        card_instance_id=card_instance_id,
        registry=registry,
        source_instance_id=combat_state.player.instance_id,
        target_id=target_id,
        energy_spent=energy_spent,
    )
    snapshots_before = capture_entity_snapshots(combat_state, registry)

    combat_state.energy -= energy_spent
    combat_state.hand.remove(card_instance_id)
    if getattr(card_def, "exhausts", False):
        combat_state.exhaust_pile.append(card_instance_id)
    else:
        combat_state.discard_pile.append(card_instance_id)
    combat_state.effect_queue.extend(materialized_effects)
    resolved_effects = resolve_player_actions(
        combat_state,
        hook_registrations=hook_registrations,
    )
    append_log_entries(
        combat_state,
        describe_player_action(
            events=build_player_action_events(
                card_name=card_def.name,
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
