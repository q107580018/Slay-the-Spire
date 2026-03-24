from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from slay_the_spire.shared.types import JsonDict

T = TypeVar("T")


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


def _require_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list")
    return value


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _require_record_list(raw: object, field_name: str) -> list[Mapping[str, object]]:
    records = _require_list(raw, field_name)
    return [_require_mapping(item, f"{field_name} item") for item in records]


def _require_optional_str(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, field_name)


@dataclass(slots=True, frozen=True)
class CardDef:
    id: str
    name: str
    cost: int
    effects: list[JsonDict]
    upgrades_to: str | None = None


@dataclass(slots=True, frozen=True)
class EnemyDef:
    id: str
    name: str
    hp: int
    move_table: list[JsonDict]
    intent_policy: str


@dataclass(slots=True, frozen=True)
class RelicDef:
    id: str
    name: str
    trigger_hooks: list[str]
    passive_effects: list[JsonDict]


@dataclass(slots=True, frozen=True)
class EventDef:
    id: str
    text: str
    choices: list[JsonDict]
    outcomes: list[JsonDict]


@dataclass(slots=True, frozen=True)
class ActDef:
    id: str
    name: str
    enemy_pool_id: str
    elite_pool_id: str
    event_pool_id: str
    boss_pool_id: str
    nodes: list[JsonDict]


@dataclass(slots=True, frozen=True)
class CharacterDef:
    id: str
    name: str
    starter_deck: list[str]
    starter_relic_ids: list[str]
    starting_act_id: str
    starter_card_pool_id: str
    starter_relic_pool_id: str


@dataclass(slots=True)
class _BaseRegistry(Generic[T]):
    _items: dict[str, T] = field(default_factory=dict)

    def register_many(self, items: Iterable[Mapping[str, object]]) -> None:
        for item in items:
            self.register(item)

    def get(self, content_id: str) -> T:
        if content_id not in self._items:
            raise KeyError(content_id)
        return self._items[content_id]

    def all(self) -> tuple[T, ...]:
        return tuple(self._items.values())


class CardRegistry(_BaseRegistry[CardDef]):
    def register(self, payload: Mapping[str, object]) -> CardDef:
        record = self._build(payload)
        if record.id in self._items:
            raise ValueError(f"duplicate card id: {record.id}")
        self._items[record.id] = record
        return record

    def _build(self, payload: Mapping[str, object]) -> CardDef:
        data = _require_mapping(payload, "payload")
        effects = _require_record_list(data.get("effects"), "effects")
        return CardDef(
            id=_require_str(data.get("id"), "id"),
            name=_require_str(data.get("name"), "name"),
            cost=_require_int(data.get("cost"), "cost"),
            effects=[dict(item) for item in effects],
            upgrades_to=_require_optional_str(data.get("upgrades_to"), "upgrades_to"),
        )


class EnemyRegistry(_BaseRegistry[EnemyDef]):
    def register(self, payload: Mapping[str, object]) -> EnemyDef:
        record = self._build(payload)
        if record.id in self._items:
            raise ValueError(f"duplicate enemy id: {record.id}")
        self._items[record.id] = record
        return record

    def _build(self, payload: Mapping[str, object]) -> EnemyDef:
        data = _require_mapping(payload, "payload")
        if "move_table" not in data:
            raise ValueError("move_table is required")
        move_table = _require_record_list(data.get("move_table"), "move_table")
        return EnemyDef(
            id=_require_str(data.get("id"), "id"),
            name=_require_str(data.get("name"), "name"),
            hp=_require_int(data.get("hp"), "hp"),
            move_table=[dict(item) for item in move_table],
            intent_policy=_require_str(data.get("intent_policy"), "intent_policy"),
        )


class RelicRegistry(_BaseRegistry[RelicDef]):
    def register(self, payload: Mapping[str, object]) -> RelicDef:
        record = self._build(payload)
        if record.id in self._items:
            raise ValueError(f"duplicate relic id: {record.id}")
        self._items[record.id] = record
        return record

    def _build(self, payload: Mapping[str, object]) -> RelicDef:
        data = _require_mapping(payload, "payload")
        trigger_hooks = [_require_str(item, "trigger_hooks item") for item in _require_list(data.get("trigger_hooks"), "trigger_hooks")]
        passive_effects = _require_record_list(data.get("passive_effects"), "passive_effects")
        return RelicDef(
            id=_require_str(data.get("id"), "id"),
            name=_require_str(data.get("name"), "name"),
            trigger_hooks=trigger_hooks,
            passive_effects=[dict(item) for item in passive_effects],
        )


class EventRegistry(_BaseRegistry[EventDef]):
    def register(self, payload: Mapping[str, object]) -> EventDef:
        record = self._build(payload)
        if record.id in self._items:
            raise ValueError(f"duplicate event id: {record.id}")
        self._items[record.id] = record
        return record

    def _build(self, payload: Mapping[str, object]) -> EventDef:
        data = _require_mapping(payload, "payload")
        choices = _require_record_list(data.get("choices"), "choices")
        outcomes = _require_record_list(data.get("outcomes"), "outcomes")
        return EventDef(
            id=_require_str(data.get("id"), "id"),
            text=_require_str(data.get("text"), "text"),
            choices=[dict(item) for item in choices],
            outcomes=[dict(item) for item in outcomes],
        )


class ActRegistry(_BaseRegistry[ActDef]):
    def register(self, payload: Mapping[str, object]) -> ActDef:
        record = self._build(payload)
        if record.id in self._items:
            raise ValueError(f"duplicate act id: {record.id}")
        self._items[record.id] = record
        return record

    def _build(self, payload: Mapping[str, object]) -> ActDef:
        data = _require_mapping(payload, "payload")
        nodes = _require_record_list(data.get("nodes"), "nodes")
        return ActDef(
            id=_require_str(data.get("id"), "id"),
            name=_require_str(data.get("name"), "name"),
            enemy_pool_id=_require_str(data.get("enemy_pool_id"), "enemy_pool_id"),
            elite_pool_id=_require_str(data.get("elite_pool_id"), "elite_pool_id"),
            event_pool_id=_require_str(data.get("event_pool_id"), "event_pool_id"),
            boss_pool_id=_require_str(data.get("boss_pool_id"), "boss_pool_id"),
            nodes=[dict(item) for item in nodes],
        )


class CharacterRegistry(_BaseRegistry[CharacterDef]):
    def register(self, payload: Mapping[str, object]) -> CharacterDef:
        record = self._build(payload)
        if record.id in self._items:
            raise ValueError(f"duplicate character id: {record.id}")
        self._items[record.id] = record
        return record

    def _build(self, payload: Mapping[str, object]) -> CharacterDef:
        data = _require_mapping(payload, "payload")
        starter_deck = [_require_str(item, "starter_deck item") for item in _require_list(data.get("starter_deck"), "starter_deck")]
        starter_relic_ids = [_require_str(item, "starter_relic_ids item") for item in _require_list(data.get("starter_relic_ids"), "starter_relic_ids")]
        return CharacterDef(
            id=_require_str(data.get("id"), "id"),
            name=_require_str(data.get("name"), "name"),
            starter_deck=starter_deck,
            starter_relic_ids=starter_relic_ids,
            starting_act_id=_require_str(data.get("starting_act_id"), "starting_act_id"),
            starter_card_pool_id=_require_str(data.get("starter_card_pool_id"), "starter_card_pool_id"),
            starter_relic_pool_id=_require_str(data.get("starter_relic_pool_id"), "starter_relic_pool_id"),
        )


def validate_startup_integrity(
    *,
    characters: CharacterRegistry,
    cards: CardRegistry,
    enemies: EnemyRegistry,
    relics: RelicRegistry,
    events: EventRegistry,
    acts: ActRegistry,
    card_pool_ids: set[str],
    enemy_pool_ids: set[str],
    relic_pool_ids: set[str],
    event_pool_ids: set[str],
    character_id: str = "ironclad",
) -> None:
    try:
        character = characters.get(character_id)
    except KeyError as exc:
        raise ValueError(f"{character_id} character is required") from exc
    if character.starter_card_pool_id not in card_pool_ids:
        raise ValueError("starter_card_pool_id must reference a loaded card pool")
    if character.starter_relic_pool_id not in relic_pool_ids:
        raise ValueError("starter_relic_pool_id must reference a loaded relic pool")
    acts.get(character.starting_act_id)
    for card_id in character.starter_deck:
        cards.get(card_id)
    for relic_id in character.starter_relic_ids:
        relics.get(relic_id)
    act = acts.get(character.starting_act_id)
    if act.enemy_pool_id not in enemy_pool_ids:
        raise ValueError("enemy_pool_id must reference a loaded enemy pool")
    if act.elite_pool_id not in enemy_pool_ids:
        raise ValueError("elite_pool_id must reference a loaded enemy pool")
    if act.event_pool_id not in event_pool_ids:
        raise ValueError("event_pool_id must reference a loaded event pool")
    if act.boss_pool_id not in enemy_pool_ids:
        raise ValueError("boss_pool_id must reference a loaded enemy pool")
