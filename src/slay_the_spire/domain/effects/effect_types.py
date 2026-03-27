from __future__ import annotations

from typing import Mapping

from slay_the_spire.shared.types import JsonDict, JsonValue

EFFECT_DAMAGE = "damage"
EFFECT_BLOCK = "block"
EFFECT_HEAL = "heal"
EFFECT_LOSE_HP = "lose_hp"
EFFECT_DRAW = "draw"
EFFECT_GAIN_ENERGY = "gain_energy"
EFFECT_VULNERABLE = "vulnerable"
EFFECT_WEAK = "weak"
EFFECT_CREATE_CARD_COPY = "create_card_copy"
EFFECT_ADD_CARD_TO_DISCARD = "add_card_to_discard"
EFFECT_EXHAUST_RANDOM_HAND = "exhaust_random_hand"
EFFECT_EXHAUST_TARGET_CARD = "exhaust_target_card"
EFFECT_UPGRADE_TARGET_CARD = "upgrade_target_card"
EFFECT_UPGRADE_ALL_HAND = "upgrade_all_hand"
EFFECT_ADD_POWER = "add_power"
EFFECT_NOOP = "noop"
EFFECT_EMIT_HOOK = "emit_hook"


def _copy_json_value(value: JsonValue) -> JsonValue:
    if isinstance(value, dict):
        return {key: _copy_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy_json_value(item) for item in value]
    return value


def copy_effect(effect: Mapping[str, JsonValue]) -> JsonDict:
    return {key: _copy_json_value(value) for key, value in effect.items()}


def damage_effect(*, target_instance_id: str, amount: int, source_instance_id: str | None = None) -> JsonDict:
    effect: JsonDict = {
        "type": EFFECT_DAMAGE,
        "target_instance_id": target_instance_id,
        "amount": amount,
    }
    if source_instance_id is not None:
        effect["source_instance_id"] = source_instance_id
    return effect


def block_effect(*, target_instance_id: str, amount: int, source_instance_id: str | None = None) -> JsonDict:
    effect: JsonDict = {
        "type": EFFECT_BLOCK,
        "target_instance_id": target_instance_id,
        "amount": amount,
    }
    if source_instance_id is not None:
        effect["source_instance_id"] = source_instance_id
    return effect


def draw_effect(*, target_instance_id: str, amount: int) -> JsonDict:
    return {
        "type": EFFECT_DRAW,
        "target_instance_id": target_instance_id,
        "amount": amount,
    }


def noop_effect(*, reason: str) -> JsonDict:
    return {
        "type": EFFECT_NOOP,
        "reason": reason,
    }


def emit_hook_effect(
    *,
    hook_name: str,
    payload: Mapping[str, JsonValue] | None = None,
) -> JsonDict:
    return {
        "type": EFFECT_EMIT_HOOK,
        "hook_name": hook_name,
        "payload": copy_effect(payload or {}),
    }
