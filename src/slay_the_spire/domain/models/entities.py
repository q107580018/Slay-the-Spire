from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.shared.types import JsonDict

SCHEMA_VERSION = 1


def _require_schema_version(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("schema_version must be an int")
    return value


def _copy_statuses(statuses: list[StatusState]) -> list[StatusState]:
    return list(statuses)


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _require_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list")
    return value


def _require_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
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
class PlayerCombatState:
    schema_version: int = SCHEMA_VERSION
    instance_id: str
    hp: int
    max_hp: int
    block: int
    statuses: list[StatusState] = field(default_factory=list)
    kind: str = field(init=False, default="player")

    def __post_init__(self) -> None:
        self.schema_version = _require_schema_version(self.schema_version)
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for PlayerCombatState")
        if not self.instance_id:
            raise ValueError("instance_id must not be empty")
        if self.max_hp <= 0:
            raise ValueError("max_hp must be positive")
        if not 0 <= self.hp <= self.max_hp:
            raise ValueError("hp must be between 0 and max_hp")
        if self.block < 0:
            raise ValueError("block must be non-negative")
        self.statuses = _copy_statuses(self.statuses)
        for status in self.statuses:
            if not isinstance(status, StatusState):
                raise TypeError("statuses must contain StatusState instances")

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "instance_id": self.instance_id,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "block": self.block,
            "statuses": [status.to_dict() for status in self.statuses],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> PlayerCombatState:
        data = _require_mapping_data(data)
        schema_version = _require_schema_version(data.get("schema_version"))
        if schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for PlayerCombatState")
        if data.get("kind") != "player":
            raise ValueError("player combat state must have kind=player")
        statuses_raw = _require_list(data.get("statuses", []), "statuses")
        statuses = [StatusState.from_dict(_require_mapping(item, "statuses item")) for item in statuses_raw]
        return cls(
            schema_version=SCHEMA_VERSION,
            instance_id=_require_str(data["instance_id"], "instance_id"),
            hp=_require_int(data["hp"], "hp"),
            max_hp=_require_int(data["max_hp"], "max_hp"),
            block=_require_int(data["block"], "block"),
            statuses=statuses,
        )


@dataclass(slots=True, kw_only=True)
class EnemyState:
    schema_version: int = SCHEMA_VERSION
    instance_id: str
    enemy_id: str
    hp: int
    max_hp: int
    block: int
    statuses: list[StatusState] = field(default_factory=list)
    kind: str = field(init=False, default="enemy")

    def __post_init__(self) -> None:
        self.schema_version = _require_schema_version(self.schema_version)
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for EnemyState")
        if not self.instance_id:
            raise ValueError("instance_id must not be empty")
        if not self.enemy_id:
            raise ValueError("enemy_id must not be empty")
        if self.max_hp <= 0:
            raise ValueError("max_hp must be positive")
        if not 0 <= self.hp <= self.max_hp:
            raise ValueError("hp must be between 0 and max_hp")
        if self.block < 0:
            raise ValueError("block must be non-negative")
        self.statuses = _copy_statuses(self.statuses)
        for status in self.statuses:
            if not isinstance(status, StatusState):
                raise TypeError("statuses must contain StatusState instances")

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "instance_id": self.instance_id,
            "enemy_id": self.enemy_id,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "block": self.block,
            "statuses": [status.to_dict() for status in self.statuses],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> EnemyState:
        data = _require_mapping_data(data)
        schema_version = _require_schema_version(data.get("schema_version"))
        if schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for EnemyState")
        if data.get("kind") != "enemy":
            raise ValueError("enemy combat state must have kind=enemy")
        statuses_raw = _require_list(data.get("statuses", []), "statuses")
        statuses = [StatusState.from_dict(_require_mapping(item, "statuses item")) for item in statuses_raw]
        return cls(
            schema_version=SCHEMA_VERSION,
            instance_id=_require_str(data["instance_id"], "instance_id"),
            enemy_id=_require_str(data["enemy_id"], "enemy_id"),
            hp=_require_int(data["hp"], "hp"),
            max_hp=_require_int(data["max_hp"], "max_hp"),
            block=_require_int(data["block"], "block"),
            statuses=statuses,
        )
