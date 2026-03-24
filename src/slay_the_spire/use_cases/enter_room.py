from __future__ import annotations

from collections.abc import Mapping

from slay_the_spire.content.registries import ActDef
from slay_the_spire.domain.combat.turn_flow import start_turn
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort

_SUPPORTED_ROOM_TYPES = {"combat", "elite", "event", "boss"}


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


def _act_def_from_registry(act_state: ActState, registry: ContentProviderPort) -> ActDef:
    return registry.acts().get(act_state.act_id)


def _room_type_for_node(act_state: ActState, node_id: str, registry: ContentProviderPort) -> str:
    act_def = _act_def_from_registry(act_state, registry)
    for raw_node in act_def.nodes:
        node = _require_mapping(raw_node, "act node")
        if _require_str(node.get("id"), "node.id") != node_id:
            continue
        room_type = node.get("room_type")
        if room_type is None:
            raise ValueError("room_type is required for act nodes")
        room_type = _require_str(room_type, "node.room_type")
        if room_type not in _SUPPORTED_ROOM_TYPES:
            raise ValueError(f"unsupported room_type: {room_type}")
        return room_type
    raise ValueError(f"node {node_id} not found in act {act_state.act_id}")


def _build_card_instance_ids(card_ids: list[str]) -> list[str]:
    return [f"{card_id}#{index}" for index, card_id in enumerate(card_ids, start=1)]


def _build_enemy_state(enemy_id: str, registry: ContentProviderPort) -> EnemyState:
    enemy_def = registry.enemies().get(enemy_id)
    return EnemyState(
        instance_id="enemy-1",
        enemy_id=enemy_def.id,
        hp=enemy_def.hp,
        max_hp=enemy_def.hp,
        block=0,
        statuses=[],
    )


def _build_combat_state(run_state: RunState, *, enemy_pool_id: str, registry: ContentProviderPort) -> CombatState:
    character = registry.characters().get(run_state.character_id)
    deck_instance_ids = _build_card_instance_ids(character.starter_deck)
    enemy_ids = registry.enemy_ids_for_pool(enemy_pool_id)
    if not enemy_ids:
        raise ValueError(f"enemy pool {enemy_pool_id} must contain at least one enemy")

    state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=deck_instance_ids,
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id=f"player-{run_state.character_id}",
            hp=run_state.current_hp,
            max_hp=run_state.max_hp,
            block=0,
            statuses=[],
        ),
        enemies=[_build_enemy_state(enemy_ids[0], registry)],
        effect_queue=[],
        log=[],
    )
    return start_turn(state)


def enter_room(run_state: RunState, act_state: ActState, node_id: str, registry: ContentProviderPort) -> RoomState:
    current_node = act_state.get_node(node_id)
    room_kind = _room_type_for_node(act_state, current_node.node_id, registry)
    payload: dict[str, object] = {
        "act_id": act_state.act_id,
        "node_id": current_node.node_id,
        "room_kind": room_kind,
        "next_node_ids": list(current_node.next_node_ids),
    }
    if room_kind in {"combat", "elite", "boss"}:
        if room_kind == "combat":
            enemy_pool_id = act_state.enemy_pool_id
        elif room_kind == "elite":
            enemy_pool_id = act_state.elite_pool_id
        else:
            enemy_pool_id = act_state.boss_pool_id
        if enemy_pool_id is None:
            raise ValueError(f"{room_kind} rooms require an enemy pool id")
        payload["enemy_pool_id"] = enemy_pool_id
        payload["combat_state"] = _build_combat_state(
            run_state,
            enemy_pool_id=enemy_pool_id,
            registry=registry,
        ).to_dict()
    elif room_kind == "event":
        payload["event_pool_id"] = act_state.event_pool_id
        if act_state.event_pool_id is None:
            raise ValueError("event rooms require an event pool id")
        event_ids = registry.event_ids_for_pool(act_state.event_pool_id)
        if not event_ids:
            raise ValueError(f"event pool {act_state.event_pool_id} must contain at least one event")
        payload["event_id"] = event_ids[0]
    room_id = f"{act_state.act_id}:{current_node.node_id}"
    return RoomState(
        room_id=room_id,
        room_type=room_kind,
        stage="waiting_input",
        payload=payload,
        is_resolved=False,
        rewards=[],
    )
