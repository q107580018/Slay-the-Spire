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


def _snapshot_json_value(value: JsonValue) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_snapshot_json_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _snapshot_json_value(item) for key, item in value.items()}
    raise TypeError("payload must contain only JSON-compatible values")


def _copy_payload(payload: Mapping[str, JsonValue]) -> JsonDict:
    return {str(key): _ensure_json_value(value) for key, value in payload.items()}


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _require_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list")
    return value


def _require_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be a bool")
    return value


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


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
            "payload": {str(key): _snapshot_json_value(value) for key, value in self.payload.items()},
            "is_resolved": self.is_resolved,
            "rewards": list(self.rewards),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> RoomState:
        if not isinstance(data, Mapping):
            raise TypeError("data must be a mapping")
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for RoomState")
        payload = _require_mapping(data.get("payload", {}), "payload")
        rewards = _require_list(data.get("rewards", []), "rewards")
        return cls(
            schema_version=SCHEMA_VERSION,
            room_id=_require_str(data["room_id"], "room_id"),
            room_type=_require_str(data["room_type"], "room_type"),
            stage=_require_str(data["stage"], "stage"),
            payload={str(key): value for key, value in payload.items()},
            is_resolved=_require_bool(data["is_resolved"], "is_resolved"),
            rewards=[_require_str(item, "rewards item") for item in rewards],
        )
