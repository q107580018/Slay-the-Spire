from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from typing import Mapping

from slay_the_spire.shared.types import JsonDict

SCHEMA_VERSION = 1


def _require_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    return value


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


def _require_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("data must be a mapping")
    return value


def _require_schema_version(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("schema_version must be an int")
    return value


@dataclass(slots=True, kw_only=True)
class RunState:
    schema_version: ClassVar[int] = SCHEMA_VERSION
    seed: int
    character_id: str
    current_act_id: str | None
    current_hp: int = 80
    max_hp: int = 80

    def __post_init__(self) -> None:
        self.seed = _require_int(self.seed, "seed")
        self.character_id = _require_str(self.character_id, "character_id")
        self.current_hp = _require_int(self.current_hp, "current_hp")
        self.max_hp = _require_int(self.max_hp, "max_hp")
        if self.current_act_id is not None:
            self.current_act_id = _require_str(self.current_act_id, "current_act_id")
            if not self.current_act_id:
                raise ValueError("current_act_id must not be empty")
        if not self.character_id:
            raise ValueError("character_id must not be empty")
        if self.max_hp <= 0:
            raise ValueError("max_hp must be positive")
        if not 0 <= self.current_hp <= self.max_hp:
            raise ValueError("current_hp must be between 0 and max_hp")

    @classmethod
    def new(cls, *, character_id: str, seed: int) -> RunState:
        return cls(seed=seed, character_id=character_id, current_act_id=None)

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "character_id": self.character_id,
            "current_act_id": self.current_act_id,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> RunState:
        data = _require_mapping(data)
        schema_version = _require_schema_version(data.get("schema_version"))
        if schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for RunState")
        current_act_id = data.get("current_act_id")
        if current_act_id is not None and not isinstance(current_act_id, str):
            raise TypeError("current_act_id must be a string or None")
        return cls(
            seed=_require_int(data["seed"], "seed"),
            character_id=_require_str(data["character_id"], "character_id"),
            current_act_id=current_act_id,
            current_hp=_require_int(data.get("current_hp", 80), "current_hp"),
            max_hp=_require_int(data.get("max_hp", 80), "max_hp"),
        )
