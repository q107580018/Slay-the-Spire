from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from slay_the_spire.shared.types import JsonDict, JsonValue

SCHEMA_VERSION = 1


def _ensure_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_ensure_json_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _ensure_json_value(item) for key, item in value.items()}
    raise TypeError("payload must contain only JSON-compatible values")


def _copy_payload(payload: Mapping[str, JsonValue]) -> JsonDict:
    return {str(key): _ensure_json_value(value) for key, value in payload.items()}


@dataclass(slots=True, kw_only=True)
class RoomState:
    schema_version: int = SCHEMA_VERSION
    room_id: str
    room_type: str
    stage: str
    payload: JsonDict = field(default_factory=dict)
    is_resolved: bool
    rewards: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for RoomState")
        if not self.room_id:
            raise ValueError("room_id must not be empty")
        if not self.room_type:
            raise ValueError("room_type must not be empty")
        if not self.stage:
            raise ValueError("stage must not be empty")
        self.payload = _copy_payload(self.payload)
        self.rewards = list(self.rewards)

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "room_id": self.room_id,
            "room_type": self.room_type,
            "stage": self.stage,
            "payload": dict(self.payload),
            "is_resolved": self.is_resolved,
            "rewards": list(self.rewards),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> RoomState:
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for RoomState")
        payload = data.get("payload", {})
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            schema_version=SCHEMA_VERSION,
            room_id=str(data["room_id"]),
            room_type=str(data["room_type"]),
            stage=str(data["stage"]),
            payload={str(key): value for key, value in payload.items()},
            is_resolved=bool(data["is_resolved"]),
            rewards=[str(item) for item in data.get("rewards", [])],
        )
