from __future__ import annotations

from collections.abc import Mapping

from slay_the_spire.content.registries import ActDef
from slay_the_spire.domain.models.act_state import ActNodeState, ActState
from slay_the_spire.ports.content_provider import ContentProviderPort


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


def _require_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list")
    return value


def _act_def_from_registry(act_id: str, registry: ContentProviderPort) -> ActDef:
    return registry.acts().get(act_id)


def _build_node_state(raw_node: Mapping[str, object]) -> ActNodeState:
    node_id = _require_str(raw_node.get("id"), "node.id")
    next_nodes = raw_node.get("next")
    if next_nodes is None:
        next_nodes = raw_node.get("next_node_ids", [])
    next_node_ids = [_require_str(item, "node.next item") for item in _require_list(next_nodes, "node.next")]
    return ActNodeState(node_id=node_id, next_node_ids=next_node_ids)


def _starting_node_id(nodes: list[ActNodeState]) -> str:
    for node in nodes:
        if node.node_id == "start":
            return node.node_id
    raise ValueError("act must define a start node")


def generate_act_state(act_id: str, seed: int, registry: ContentProviderPort) -> ActState:
    del seed
    act_def = _act_def_from_registry(act_id, registry)
    nodes = [_build_node_state(_require_mapping(node, "act node")) for node in act_def.nodes]
    if not nodes:
        raise ValueError(f"act {act_id} must define at least one node")
    return ActState(
        act_id=act_def.id,
        current_node_id=_starting_node_id(nodes),
        nodes=nodes,
        visited_node_ids=[],
        enemy_pool_id=act_def.enemy_pool_id,
        elite_pool_id=act_def.elite_pool_id,
        boss_pool_id=act_def.boss_pool_id,
        event_pool_id=act_def.event_pool_id,
    )
