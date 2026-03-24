from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from slay_the_spire.domain.effects.effect_types import copy_effect
from slay_the_spire.shared.types import JsonDict, JsonValue

CATEGORY_PRIORITY: dict[str, int] = {
    "system": 0,
    "status": 1,
    "relic": 2,
    "card": 3,
}

SOURCE_TYPE_PRIORITY: dict[str, int] = {
    "player": 0,
    "enemy": 1,
    "status": 2,
    "relic": 3,
    "card": 4,
}


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _require_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be an int")
    return value


def _require_mapping(value: object, field_name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    for key in value:
        if not isinstance(key, str):
            raise TypeError(f"{field_name} keys must be strings")
    return value


@dataclass(slots=True, kw_only=True)
class HookRegistration:
    hook_name: str
    category: str
    priority: int
    source_type: str
    source_instance_id: str
    registration_index: int
    effects: list[JsonDict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.hook_name = _require_str(self.hook_name, "hook_name")
        self.category = _require_str(self.category, "category")
        self.priority = _require_int(self.priority, "priority")
        self.source_type = _require_str(self.source_type, "source_type")
        self.source_instance_id = _require_str(self.source_instance_id, "source_instance_id")
        self.registration_index = _require_int(self.registration_index, "registration_index")
        if self.registration_index < 0:
            raise ValueError("registration_index must be non-negative")
        if not isinstance(self.effects, list):
            raise TypeError("effects must be a list")
        self.effects = [copy_effect(_require_mapping(effect, "effects item")) for effect in self.effects]

    def sort_key(self) -> tuple[int, str, int, int, str, str, int]:
        return (
            CATEGORY_PRIORITY.get(self.category, len(CATEGORY_PRIORITY)),
            self.category,
            self.priority,
            SOURCE_TYPE_PRIORITY.get(self.source_type, len(SOURCE_TYPE_PRIORITY)),
            self.source_type,
            self.source_instance_id,
            self.registration_index,
        )

    def to_dict(self) -> JsonDict:
        return {
            "hook_name": self.hook_name,
            "category": self.category,
            "priority": self.priority,
            "source_type": self.source_type,
            "source_instance_id": self.source_instance_id,
            "registration_index": self.registration_index,
            "effects": [copy_effect(effect) for effect in self.effects],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> HookRegistration:
        data = _require_mapping(data, "data")
        effects = data.get("effects")
        if not isinstance(effects, list):
            raise TypeError("effects must be a list")
        return cls(
            hook_name=_require_str(data.get("hook_name"), "hook_name"),
            category=_require_str(data.get("category"), "category"),
            priority=_require_int(data.get("priority"), "priority"),
            source_type=_require_str(data.get("source_type"), "source_type"),
            source_instance_id=_require_str(data.get("source_instance_id"), "source_instance_id"),
            registration_index=_require_int(data.get("registration_index"), "registration_index"),
            effects=[copy_effect(_require_mapping(effect, "effects item")) for effect in effects],
        )


def hook_sort_key(registration: HookRegistration) -> tuple[int, str, int, int, str, str, int]:
    return registration.sort_key()
