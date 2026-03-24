from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from slay_the_spire.shared.types import JsonDict

SCHEMA_VERSION = 1


def _require_schema_version(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("schema_version must be an int")
    return value


@dataclass(slots=True, kw_only=True)
class StatusState:
    schema_version: int = SCHEMA_VERSION
    status_id: str
    stacks: int
    duration: int | None = None

    def __post_init__(self) -> None:
        self.schema_version = _require_schema_version(self.schema_version)
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for StatusState")
        if not isinstance(self.status_id, str):
            raise TypeError("status_id must be a string")
        if not self.status_id:
            raise ValueError("status_id must not be empty")
        if self.stacks <= 0:
            raise ValueError("stacks must be positive")
        if self.duration is not None and self.duration <= 0:
            raise ValueError("duration must be positive when provided")

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "status_id": self.status_id,
            "stacks": self.stacks,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> StatusState:
        if not isinstance(data, Mapping):
            raise TypeError("data must be a mapping")
        schema_version = _require_schema_version(data.get("schema_version"))
        if schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for StatusState")
        if not isinstance(data.get("status_id"), str):
            raise TypeError("status_id must be a string")
        if not isinstance(data.get("stacks"), int) or isinstance(data.get("stacks"), bool):
            raise TypeError("stacks must be an int")
        duration = data.get("duration")
        if duration is not None and (not isinstance(duration, int) or isinstance(duration, bool)):
            raise TypeError("duration must be an int or None")
        return cls(
            schema_version=SCHEMA_VERSION,
            status_id=data["status_id"],
            stacks=data["stacks"],
            duration=duration,
        )
