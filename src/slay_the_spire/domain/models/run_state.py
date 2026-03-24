from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from typing import Mapping

from slay_the_spire.shared.types import JsonDict

SCHEMA_VERSION = 1


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
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for RunState")
        return cls(
            seed=int(data["seed"]),
            character_id=str(data["character_id"]),
            current_act_id=None if data.get("current_act_id") is None else str(data["current_act_id"]),
        )
