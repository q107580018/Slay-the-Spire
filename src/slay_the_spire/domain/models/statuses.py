from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from slay_the_spire.shared.types import JsonDict

SCHEMA_VERSION = 1


@dataclass(slots=True, kw_only=True)
class StatusState:
    schema_version: int = SCHEMA_VERSION
    status_id: str
    stacks: int
    duration: int | None = None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for StatusState")
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
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for StatusState")
        return cls(
            schema_version=SCHEMA_VERSION,
            status_id=str(data["status_id"]),
            stacks=int(data["stacks"]),
            duration=None if data.get("duration") is None else int(data["duration"]),
        )

