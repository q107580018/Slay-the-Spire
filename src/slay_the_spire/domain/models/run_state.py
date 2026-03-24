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


@dataclass(slots=True, kw_only=True)
class RunState:
    schema_version: ClassVar[int] = SCHEMA_VERSION
    seed: int
    character_id: str
    current_act_id: str | None

    def __post_init__(self) -> None:
        if not self.character_id:
            raise ValueError("character_id must not be empty")

    @classmethod
    def new(cls, *, character_id: str, seed: int) -> RunState:
        return cls(seed=seed, character_id=character_id, current_act_id=None)

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "seed": self.seed,
            "character_id": self.character_id,
            "current_act_id": self.current_act_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> RunState:
        data = _require_mapping(data)
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for RunState")
        current_act_id = data.get("current_act_id")
        if current_act_id is not None and not isinstance(current_act_id, str):
            raise TypeError("current_act_id must be a string or None")
        return cls(
            seed=_require_int(data["seed"], "seed"),
            character_id=_require_str(data["character_id"], "character_id"),
            current_act_id=current_act_id,
        )
