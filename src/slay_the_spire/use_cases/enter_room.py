from __future__ import annotations

from collections.abc import Mapping

from slay_the_spire.content.registries import ActDef
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import PlayerCombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort


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
        return _require_str(room_type, "node.room_type")
    raise ValueError(f"node {node_id} not found in act {act_state.act_id}")


def _build_combat_state(run_state: RunState) -> CombatState:
    return CombatState(
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id=f"player-{run_state.character_id}",
            hp=80,
            max_hp=80,
            block=0,
            statuses=[],
        ),
        enemies=[],
        effect_queue=[],
        log=[],
    )


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
        payload["combat_state"] = _build_combat_state(run_state).to_dict()
        if room_kind == "combat":
            payload["enemy_pool_id"] = act_state.enemy_pool_id
        elif room_kind == "elite":
            payload["enemy_pool_id"] = act_state.elite_pool_id
        else:
            payload["enemy_pool_id"] = act_state.boss_pool_id
    elif room_kind == "event":
        payload["event_pool_id"] = act_state.event_pool_id
    room_id = f"{act_state.act_id}:{current_node.node_id}"
    return RoomState(
        room_id=room_id,
        room_type=room_kind,
        stage="waiting_input",
        payload=payload,
        is_resolved=False,
        rewards=[],
    )
