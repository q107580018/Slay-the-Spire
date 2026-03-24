from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.shared.types import JsonDict

SCHEMA_VERSION = 1


def _copy_statuses(statuses: list[StatusState]) -> list[StatusState]:
    return list(statuses)


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
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for PlayerCombatState")
        if data.get("kind") != "player":
            raise ValueError("player combat state must have kind=player")
        statuses = [StatusState.from_dict(item) for item in data.get("statuses", [])]
        return cls(
            schema_version=SCHEMA_VERSION,
            instance_id=str(data["instance_id"]),
            hp=int(data["hp"]),
            max_hp=int(data["max_hp"]),
            block=int(data["block"]),
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
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for EnemyState")
        if data.get("kind") != "enemy":
            raise ValueError("enemy combat state must have kind=enemy")
        statuses = [StatusState.from_dict(item) for item in data.get("statuses", [])]
        return cls(
            schema_version=SCHEMA_VERSION,
            instance_id=str(data["instance_id"]),
            enemy_id=str(data["enemy_id"]),
            hp=int(data["hp"]),
            max_hp=int(data["max_hp"]),
            block=int(data["block"]),
            statuses=statuses,
        )
