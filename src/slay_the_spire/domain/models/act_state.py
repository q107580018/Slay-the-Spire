from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from slay_the_spire.shared.types import JsonDict

SCHEMA_VERSION = 1


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _require_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list")
    return value


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


def _require_mapping_data(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("data must be a mapping")
    return value


@dataclass(slots=True, kw_only=True)
class ActNodeState:
    schema_version: int = SCHEMA_VERSION
    node_id: str
    next_node_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for ActNodeState")
        if not self.node_id:
            raise ValueError("node_id must not be empty")
        self.next_node_ids = list(self.next_node_ids)
        if len(set(self.next_node_ids)) != len(self.next_node_ids):
            raise ValueError("next_node_ids must be unique")

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "node_id": self.node_id,
            "next_node_ids": list(self.next_node_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ActNodeState:
        data = _require_mapping_data(data)
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for ActNodeState")
        next_node_ids = _require_list(data.get("next_node_ids", []), "next_node_ids")
        return cls(
            schema_version=SCHEMA_VERSION,
            node_id=_require_str(data["node_id"], "node_id"),
            next_node_ids=[_require_str(item, "next_node_ids item") for item in next_node_ids],
        )


@dataclass(slots=True, kw_only=True)
class ActState:
    schema_version: int = SCHEMA_VERSION
    act_id: str
    current_node_id: str
    nodes: list[ActNodeState] = field(default_factory=list)
    visited_node_ids: list[str] = field(default_factory=list)
    enemy_pool_id: str | None = None
    elite_pool_id: str | None = None
    boss_pool_id: str | None = None
    event_pool_id: str | None = None
    _node_by_id: dict[str, ActNodeState] = field(init=False, repr=False, compare=False, default_factory=dict)

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for ActState")
        if not self.act_id:
            raise ValueError("act_id must not be empty")
        if not self.current_node_id:
            raise ValueError("current_node_id must not be empty")
        self.visited_node_ids = list(self.visited_node_ids)
        self._refresh_node_index()
        if self.current_node_id not in self._node_by_id:
            raise ValueError("current_node_id must exist in nodes")
        invalid_visited = [node_id for node_id in self.visited_node_ids if node_id not in self._node_by_id]
        if invalid_visited:
            raise ValueError("visited_node_ids must exist in nodes")

    def _refresh_node_index(self) -> None:
        self._node_by_id.clear()
        for node in self.nodes:
            if not isinstance(node, ActNodeState):
                raise TypeError("nodes must contain ActNodeState instances")
            if node.node_id in self._node_by_id:
                raise ValueError("duplicate node_id found in ActState")
            self._node_by_id[node.node_id] = node

    def get_node(self, node_id: str) -> ActNodeState:
        return self._node_by_id[node_id]

    @property
    def reachable_node_ids(self) -> list[str]:
        return list(self.get_node(self.current_node_id).next_node_ids)

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "act_id": self.act_id,
            "current_node_id": self.current_node_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "visited_node_ids": list(self.visited_node_ids),
            "enemy_pool_id": self.enemy_pool_id,
            "elite_pool_id": self.elite_pool_id,
            "boss_pool_id": self.boss_pool_id,
            "event_pool_id": self.event_pool_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> ActState:
        data = _require_mapping_data(data)
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for ActState")
        nodes_raw = _require_list(data.get("nodes", []), "nodes")
        visited_node_ids = _require_list(data.get("visited_node_ids", []), "visited_node_ids")
        return cls(
            schema_version=SCHEMA_VERSION,
            act_id=_require_str(data["act_id"], "act_id"),
            current_node_id=_require_str(data["current_node_id"], "current_node_id"),
            nodes=[ActNodeState.from_dict(_require_mapping(item, "nodes item")) for item in nodes_raw],
            visited_node_ids=[_require_str(item, "visited_node_ids item") for item in visited_node_ids],
            enemy_pool_id=None if data.get("enemy_pool_id") is None else _require_str(data["enemy_pool_id"], "enemy_pool_id"),
            elite_pool_id=None if data.get("elite_pool_id") is None else _require_str(data["elite_pool_id"], "elite_pool_id"),
            boss_pool_id=None if data.get("boss_pool_id") is None else _require_str(data["boss_pool_id"], "boss_pool_id"),
            event_pool_id=None if data.get("event_pool_id") is None else _require_str(data["event_pool_id"], "event_pool_id"),
        )
