from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from slay_the_spire.adapters.presentation.widgets import summarize_effect
from slay_the_spire.domain.effects.effect_resolver import resolve_effect_queue
from slay_the_spire.domain.effects.effect_types import copy_effect
from slay_the_spire.domain.hooks.hook_types import HookRegistration
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.types import JsonDict
from slay_the_spire.use_cases.combat_log import append_log_entries


@dataclass(slots=True, frozen=True)
class PotionUseResult:
    combat_state: CombatState
    resolved_effects: list[JsonDict]
    message: str | None = None


def _target_name(combat_state: CombatState, target_id: str | None, registry: ContentProviderPort) -> str | None:
    if target_id is None:
        return None
    if combat_state.player.instance_id == target_id:
        return "你"
    for enemy in combat_state.enemies:
        if enemy.instance_id == target_id:
            return registry.enemies().get(enemy.enemy_id).name
    return None


def _result_int(result: object, key: str) -> int:
    if not isinstance(result, dict):
        return 0
    value = result.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0


def _describe_damage_use(*, potion_name: str, target_name: str, effect: JsonDict) -> str:
    result = effect.get("result")
    actual_damage = _result_int(result, "actual_damage")
    blocked = _result_int(result, "blocked")
    line = f"你使用 {potion_name}，对 {target_name} 造成 {actual_damage} 伤害"
    if blocked > 0:
        line += f"，格挡抵消 {blocked}"
        line += f"，实际受到 {actual_damage}"
    return f"{line}。"


def _describe_self_use(*, potion_name: str, summary: str) -> str:
    return f"你使用 {potion_name}，{summary}。"


def _describe_potion_use(
    *,
    potion_name: str,
    effect_type: str,
    effect: JsonDict,
    combat_state: CombatState,
    registry: ContentProviderPort,
    target_id: str | None,
) -> str:
    if effect_type == "damage":
        target_name = _target_name(combat_state, target_id, registry)
        if target_name is None:
            target_name = "目标"
        return _describe_damage_use(potion_name=potion_name, target_name=target_name, effect=effect)
    if effect_type == "block":
        gained_block = _result_int(effect.get("result"), "gained_block")
        return _describe_self_use(potion_name=potion_name, summary=f"获得 {gained_block} 格挡")
    if effect_type == "strength":
        applied_stacks = _result_int(effect.get("result"), "applied_stacks")
        return _describe_self_use(potion_name=potion_name, summary=f"获得 {applied_stacks} 层力量")
    if effect_type == "heal":
        actual_healed = _result_int(effect.get("result"), "actual_healed")
        return _describe_self_use(potion_name=potion_name, summary=f"回复 {actual_healed} 点生命")
    return _describe_self_use(
        potion_name=potion_name,
        summary=f"触发了 {summarize_effect(effect)}",
    )


def _resolve_target_id(
    *,
    potion_target: str,
    combat_state: CombatState,
    target_id: str | None,
) -> str:
    if potion_target == "enemy":
        if target_id is None:
            raise ValueError("target is required for enemy-targeted potions")
        return target_id
    if potion_target == "self":
        if target_id is not None and target_id != combat_state.player.instance_id:
            raise ValueError("self-targeted potions can only target the player")
        return combat_state.player.instance_id
    if potion_target == "any":
        return target_id or combat_state.player.instance_id
    raise ValueError(f"unsupported potion target: {potion_target}")


def use_potion(
    combat_state: CombatState,
    potion_id: str,
    target_id: str | None,
    registry: ContentProviderPort,
    *,
    hook_registrations: Sequence[HookRegistration] = (),
) -> PotionUseResult:
    potion_def = registry.potions().get(potion_id)
    potion_effect = copy_effect(potion_def.effect)
    effect_type = potion_effect.get("type")
    if not isinstance(effect_type, str):
        raise TypeError("potion effect type must be a string")
    if potion_def.timing != "in_combat":
        raise ValueError("该药水当前不可在战斗中使用。")

    if effect_type not in {"damage", "block", "strength", "heal"}:
        raise ValueError(f"unsupported potion effect: {effect_type}")

    potion_effect["source_instance_id"] = combat_state.player.instance_id
    potion_effect["target_instance_id"] = _resolve_target_id(
        potion_target=potion_def.target,
        combat_state=combat_state,
        target_id=target_id,
    )
    combat_state.effect_queue.append(potion_effect)
    resolved_effects = resolve_effect_queue(combat_state, hook_registrations=hook_registrations)
    message = _describe_potion_use(
        potion_name=potion_def.name,
        effect_type=effect_type,
        effect=resolved_effects[0] if resolved_effects else potion_effect,
        combat_state=combat_state,
        registry=registry,
        target_id=target_id,
    )
    append_log_entries(combat_state, [message])
    return PotionUseResult(
        combat_state=combat_state,
        resolved_effects=resolved_effects,
        message=message,
    )
