from __future__ import annotations

from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import PlayerCombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort


def _node_room_kind(node_id: str) -> str:
    if node_id == "start":
        return "start"
    if "boss" in node_id:
        return "boss"
    if "elite" in node_id:
        return "elite"
    if "event" in node_id:
        return "event"
    return "combat"


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
    room_kind = _node_room_kind(current_node.node_id)
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
