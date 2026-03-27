from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from slay_the_spire.adapters.rich_ui.widgets import card_label
from slay_the_spire.adapters.rich_ui.widgets import active_power_label
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.entities import EnemyState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.types import JsonDict


@dataclass(slots=True, frozen=True)
class EntitySnapshot:
    name: str
    kind: str


@dataclass(slots=True, frozen=True)
class CombatEvent:
    event_type: str
    actor_name: str
    target_name: str | None = None
    card_name: str | None = None
    amount: int = 0
    blocked: int = 0
    actual_damage: int = 0
    status_id: str | None = None
    stacks: int = 0
    count: int = 0


def capture_entity_snapshots(
    combat_state: CombatState,
    registry: ContentProviderPort,
) -> dict[str, EntitySnapshot]:
    snapshots: dict[str, EntitySnapshot] = {
        combat_state.player.instance_id: EntitySnapshot(
            name="你",
            kind="player",
        )
    }
    for enemy in combat_state.enemies:
        enemy_def = registry.enemies().get(enemy.enemy_id)
        snapshots[enemy.instance_id] = EntitySnapshot(
            name=enemy_def.name,
            kind="enemy",
        )
    return snapshots


def build_player_action_events(
    *,
    card_name: str,
    resolved_effects: Sequence[JsonDict],
    entities: Mapping[str, EntitySnapshot],
    registry: ContentProviderPort | None = None,
) -> list[CombatEvent]:
    events = [CombatEvent(event_type="card_played", actor_name="你", card_name=card_name)]
    for effect in resolved_effects:
        effect_type = effect.get("type")
        result = _result_mapping(effect)
        if effect_type == "damage":
            target_name = _target_name(entities, effect)
            if target_name is None:
                continue
            events.append(
                CombatEvent(
                    event_type="damage",
                    actor_name="你",
                    target_name=target_name,
                    amount=_result_int(result, "applied_amount"),
                    blocked=_result_int(result, "blocked"),
                    actual_damage=_result_int(result, "actual_damage"),
                )
            )
            continue
        if effect_type == "block":
            events.append(
                CombatEvent(
                    event_type="block_gained",
                    actor_name="你",
                    amount=_result_int(result, "gained_block"),
                )
            )
            continue
        if effect_type == "draw":
            events.append(
                CombatEvent(
                    event_type="draw",
                    actor_name="你",
                    amount=_result_int(result, "drawn_count"),
                )
            )
            continue
        if effect_type == "gain_energy":
            events.append(
                CombatEvent(
                    event_type="gain_energy",
                    actor_name="你",
                    amount=_result_int(result, "gained_energy"),
                )
            )
            continue
        if effect_type == "add_power":
            power_id = effect.get("power_id")
            if power_id == "inflame":
                events.append(
                    CombatEvent(
                        event_type="gain_strength",
                        actor_name="你",
                        amount=_result_int(result, "amount"),
                    )
                )
            continue
        if effect_type == "lose_hp":
            events.append(
                CombatEvent(
                    event_type="lose_hp",
                    actor_name="你",
                    amount=_result_int(result, "actual_hp_lost"),
                )
            )
            continue
        if effect_type == "create_card_copy":
            if effect.get("zone") != "discard_pile":
                continue
            events.append(
                CombatEvent(
                    event_type="add_card_to_discard",
                    actor_name="你",
                    card_name=_card_name(effect.get("card_id"), registry) if registry is not None else str(effect.get("card_id")),
                    count=1,
                )
            )
            continue
        if effect_type == "vulnerable":
            target_name = _target_name(entities, effect)
            if target_name is None:
                continue
            events.append(
                CombatEvent(
                    event_type="status_applied",
                    actor_name="你",
                    target_name=target_name,
                    status_id="vulnerable",
                    stacks=_result_int(result, "applied_stacks"),
                )
            )
            continue
        if effect_type == "weak":
            target_name = _target_name(entities, effect)
            if target_name is None:
                continue
            events.append(
                CombatEvent(
                    event_type="status_applied",
                    actor_name="你",
                    target_name=target_name,
                    status_id="weak",
                    stacks=_result_int(result, "applied_stacks"),
                )
            )
            continue
        if effect_type in {"exhaust_random_hand", "exhaust_target_card"}:
            events.append(
                CombatEvent(
                    event_type="exhaust_card",
                    actor_name="你",
                    count=len(result.get("exhausted_cards", [])) if isinstance(result.get("exhausted_cards"), list) else 0,
                )
            )
            continue
        if effect_type == "upgrade_target_card":
            upgraded_to = result.get("upgraded_to")
            events.append(
                CombatEvent(
                    event_type="upgrade_card",
                    actor_name="你",
                    count=1 if isinstance(upgraded_to, str) else 0,
                )
            )
            continue
        if effect_type == "upgrade_all_hand":
            upgraded_cards = result.get("upgraded_cards")
            events.append(
                CombatEvent(
                    event_type="upgrade_card",
                    actor_name="你",
                    count=len(upgraded_cards) if isinstance(upgraded_cards, list) else 0,
                )
            )
    return events


def build_enemy_turn_events(
    *,
    enemy_previews: Sequence[tuple[EnemyState, Mapping[str, object] | None]],
    resolved_effects: Sequence[JsonDict],
    entities: Mapping[str, EntitySnapshot],
    registry: ContentProviderPort,
) -> list[CombatEvent]:
    events: list[CombatEvent] = []
    for enemy, preview in enemy_previews:
        snapshot = entities.get(enemy.instance_id)
        if snapshot is None:
            continue
        if preview is not None and preview.get("move") == "sleep":
            events.append(
                CombatEvent(
                    event_type="sleep",
                    actor_name=snapshot.name,
                    amount=_safe_int(preview.get("sleep_turns")),
                )
            )

    for effect in resolved_effects:
        source_id = effect.get("source_instance_id")
        effect_type = effect.get("type")
        result = _result_mapping(effect)
        source_snapshot = entities.get(source_id) if isinstance(source_id, str) else None
        if effect_type == "damage":
            target_name = _target_name(entities, effect)
            if target_name is None:
                continue
            actor_name = _effect_actor_name(
                source_id=source_id,
                source_snapshot=source_snapshot,
                registry=registry,
            )
            if actor_name is None:
                continue
            events.append(
                CombatEvent(
                    event_type="damage",
                    actor_name=actor_name,
                    target_name=target_name,
                    amount=_result_int(result, "applied_amount"),
                    blocked=_result_int(result, "blocked"),
                    actual_damage=_result_int(result, "actual_damage"),
                )
            )
            continue
        if source_snapshot is None or source_snapshot.kind != "enemy":
            continue
        if effect_type == "block":
            events.append(
                CombatEvent(
                    event_type="block_gained",
                    actor_name=source_snapshot.name,
                    amount=_result_int(result, "gained_block"),
                )
            )
            continue
        if effect_type == "vulnerable":
            target_name = _target_name(entities, effect)
            if target_name is None:
                continue
            events.append(
                CombatEvent(
                    event_type="status_applied",
                    actor_name=source_snapshot.name,
                    target_name=target_name,
                    status_id="vulnerable",
                    stacks=_result_int(result, "applied_stacks"),
                )
            )
            continue
        if effect_type == "weak":
            target_name = _target_name(entities, effect)
            if target_name is None:
                continue
            events.append(
                CombatEvent(
                    event_type="status_applied",
                    actor_name=source_snapshot.name,
                    target_name=target_name,
                    status_id="weak",
                    stacks=_result_int(result, "applied_stacks"),
                )
            )
            continue
        if effect_type == "add_card_to_discard":
            events.append(
                CombatEvent(
                    event_type="add_card_to_discard",
                    actor_name=source_snapshot.name,
                    card_name=_card_name(effect.get("card_id"), registry),
                    count=_safe_int(effect.get("count")) or 1,
                )
            )
    return events


def build_active_power_events(
    *,
    resolved_effects: Sequence[JsonDict],
    entities: Mapping[str, EntitySnapshot],
) -> list[CombatEvent]:
    events: list[CombatEvent] = []
    for effect in resolved_effects:
        if effect.get("trigger") != "end_turn_power":
            continue
        power_id = effect.get("power_id")
        if not isinstance(power_id, str):
            continue
        result = _result_mapping(effect)
        effect_type = effect.get("type")
        actor_name = active_power_label(power_id)
        if effect_type == "block":
            amount = _result_int(result, "gained_block")
            if amount > 0:
                events.append(
                    CombatEvent(
                        event_type="active_power_triggered",
                        actor_name=actor_name,
                        amount=amount,
                    )
                )
            continue
        if effect_type == "damage":
            target_name = _target_name(entities, effect)
            if target_name is None:
                continue
            events.append(
                CombatEvent(
                    event_type="active_power_triggered",
                    actor_name=actor_name,
                    target_name=target_name,
                    amount=_result_int(result, "applied_amount"),
                    blocked=_result_int(result, "blocked"),
                    actual_damage=_result_int(result, "actual_damage"),
                )
            )
            continue
        if effect_type == "lose_hp":
            hp_lost = _result_int(result, "actual_hp_lost")
            if hp_lost > 0:
                events.append(
                    CombatEvent(
                        event_type="active_power_triggered",
                        actor_name=actor_name,
                        actual_damage=hp_lost,
                    )
                )
            continue
    return events


def _effect_actor_name(
    *,
    source_id: object,
    source_snapshot: EntitySnapshot | None,
    registry: ContentProviderPort,
) -> str | None:
    if source_snapshot is not None and source_snapshot.kind == "enemy":
        return source_snapshot.name
    if not isinstance(source_id, str):
        return None
    try:
        return _card_name(card_id_from_instance_id(source_id), registry)
    except (TypeError, ValueError):
        return None


def _card_name(card_id: object, registry: ContentProviderPort) -> str:
    if not isinstance(card_id, str):
        return str(card_id)
    try:
        return registry.cards().get(card_id).name
    except KeyError:
        return card_label(card_id)


def _target_name(entities: Mapping[str, EntitySnapshot], effect: Mapping[str, object]) -> str | None:
    target_id = effect.get("target_instance_id")
    if not isinstance(target_id, str):
        return None
    target_snapshot = entities.get(target_id)
    if target_snapshot is None:
        return None
    return target_snapshot.name


def _result_mapping(effect: Mapping[str, object]) -> Mapping[str, object]:
    result = effect.get("result")
    if not isinstance(result, Mapping):
        return {}
    return result


def _result_int(result: Mapping[str, object], key: str) -> int:
    return _safe_int(result.get(key))


def _safe_int(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0
