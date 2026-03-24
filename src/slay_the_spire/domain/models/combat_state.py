from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.shared.types import JsonDict, JsonValue

SCHEMA_VERSION = 1


def _require_json_key(key: object) -> str:
    if not isinstance(key, str):
        raise TypeError("effect_queue keys must be strings")
    return key


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


def _require_schema_version(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("schema_version must be an int")
    return value


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


def _require_mapping_data(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("data must be a mapping")
    return value


def _normalize_json_dict(effect: Mapping[str, object]) -> JsonDict:
    result: JsonDict = {}
    for key, value in effect.items():
        normalized_key = _require_json_key(key)
        if value is None or isinstance(value, (str, int, float, bool)):
            result[normalized_key] = value
        elif isinstance(value, list):
            normalized_list: list[JsonValue] = []
            for item in value:
                if item is None or isinstance(item, (str, int, float, bool)):
                    normalized_list.append(item)
                elif isinstance(item, Mapping):
                    normalized_list.append(_normalize_json_dict(item))
                else:
                    raise TypeError("effect_queue must contain JSON-compatible values")
            result[normalized_key] = normalized_list
        elif isinstance(value, Mapping):
            result[normalized_key] = _normalize_json_dict(value)
        else:
            raise TypeError("effect_queue must contain JSON-compatible values")
    return result


@dataclass(slots=True, kw_only=True)
class CombatState:
    schema_version: int = SCHEMA_VERSION
    round_number: int
    energy: int
    hand: list[str] = field(default_factory=list)
    draw_pile: list[str] = field(default_factory=list)
    discard_pile: list[str] = field(default_factory=list)
    exhaust_pile: list[str] = field(default_factory=list)
    player: PlayerCombatState
    enemies: list[EnemyState] = field(default_factory=list)
    effect_queue: list[JsonDict] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    _entity_by_id: dict[str, PlayerCombatState | EnemyState] = field(
        init=False,
        repr=False,
        compare=False,
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        self.schema_version = _require_schema_version(self.schema_version)
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for CombatState")
        self.round_number = _require_int(self.round_number, "round_number")
        self.energy = _require_int(self.energy, "energy")
        if not isinstance(self.player, PlayerCombatState):
            raise TypeError("player must be a PlayerCombatState")
        if self.round_number <= 0:
            raise ValueError("round_number must be positive")
        if self.energy < 0:
            raise ValueError("energy must be non-negative")
        if not isinstance(self.hand, list):
            raise TypeError("hand must be a list")
        if not isinstance(self.draw_pile, list):
            raise TypeError("draw_pile must be a list")
        if not isinstance(self.discard_pile, list):
            raise TypeError("discard_pile must be a list")
        if not isinstance(self.exhaust_pile, list):
            raise TypeError("exhaust_pile must be a list")
        if not isinstance(self.enemies, list):
            raise TypeError("enemies must be a list")
        if not isinstance(self.effect_queue, list):
            raise TypeError("effect_queue must be a list")
        if not isinstance(self.log, list):
            raise TypeError("log must be a list")
        self.hand = [_require_str(item, "hand item") for item in self.hand]
        self.draw_pile = [_require_str(item, "draw_pile item") for item in self.draw_pile]
        self.discard_pile = [_require_str(item, "discard_pile item") for item in self.discard_pile]
        self.exhaust_pile = [_require_str(item, "exhaust_pile item") for item in self.exhaust_pile]
        self.enemies = list(self.enemies)
        self.effect_queue = [_normalize_json_dict(effect) for effect in self.effect_queue]
        self.log = [_require_str(item, "log item") for item in self.log]
        self._refresh_entity_index()

    def _refresh_entity_index(self) -> None:
        self._entity_by_id.clear()
        if self.player.instance_id in self._entity_by_id:
            raise ValueError("duplicate instance_id found in CombatState")
        self._entity_by_id[self.player.instance_id] = self.player
        for enemy in self.enemies:
            if not isinstance(enemy, EnemyState):
                raise TypeError("enemies must contain EnemyState instances")
            if enemy.instance_id in self._entity_by_id:
                raise ValueError("duplicate instance_id found in CombatState")
            self._entity_by_id[enemy.instance_id] = enemy

    def get_entity(self, instance_id: str) -> PlayerCombatState | EnemyState:
        return self._entity_by_id[instance_id]

    def to_dict(self) -> JsonDict:
        return {
            "schema_version": self.schema_version,
            "round_number": self.round_number,
            "energy": self.energy,
            "hand": list(self.hand),
            "draw_pile": list(self.draw_pile),
            "discard_pile": list(self.discard_pile),
            "exhaust_pile": list(self.exhaust_pile),
            "player": self.player.to_dict(),
            "enemies": [enemy.to_dict() for enemy in self.enemies],
            "effect_queue": [_normalize_json_dict(effect) for effect in self.effect_queue],
            "log": list(self.log),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> CombatState:
        data = _require_mapping_data(data)
        schema_version = _require_schema_version(data.get("schema_version"))
        if schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported schema_version for CombatState")
        hand = _require_list(data.get("hand", []), "hand")
        draw_pile = _require_list(data.get("draw_pile", []), "draw_pile")
        discard_pile = _require_list(data.get("discard_pile", []), "discard_pile")
        exhaust_pile = _require_list(data.get("exhaust_pile", []), "exhaust_pile")
        enemies_raw = _require_list(data.get("enemies", []), "enemies")
        effect_queue_raw = _require_list(data.get("effect_queue", []), "effect_queue")
        log = _require_list(data.get("log", []), "log")
        return cls(
            schema_version=SCHEMA_VERSION,
            round_number=_require_int(data["round_number"], "round_number"),
            energy=_require_int(data["energy"], "energy"),
            hand=[_require_str(item, "hand item") for item in hand],
            draw_pile=[_require_str(item, "draw_pile item") for item in draw_pile],
            discard_pile=[_require_str(item, "discard_pile item") for item in discard_pile],
            exhaust_pile=[_require_str(item, "exhaust_pile item") for item in exhaust_pile],
            player=PlayerCombatState.from_dict(_require_mapping(data["player"], "player")),
            enemies=[EnemyState.from_dict(_require_mapping(item, "enemies item")) for item in enemies_raw],
            effect_queue=[_normalize_json_dict(_require_mapping(effect, "effect_queue item")) for effect in effect_queue_raw],
            log=[_require_str(item, "log item") for item in log],
        )
