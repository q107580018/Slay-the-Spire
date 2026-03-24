from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from slay_the_spire.content.loaders import load_json_file
from slay_the_spire.content.registries import (
    ActRegistry,
    CardRegistry,
    CharacterRegistry,
    EnemyRegistry,
    EventRegistry,
    RelicRegistry,
    validate_startup_integrity,
)


def _require_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list")
    return value


def _require_str(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


def _require_mapping(value: object, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return value


def _load_list_payload(path: Path, key: str) -> object:
    payload = load_json_file(path)
    if not isinstance(payload, Mapping):
        raise TypeError(f"{path.name} must contain a JSON object")
    if key not in payload:
        raise ValueError(f"{key} is required in {path.name}")
    return payload[key]


@dataclass(slots=True)
class ContentCatalog:
    characters: CharacterRegistry = field(default_factory=CharacterRegistry)
    cards: CardRegistry = field(default_factory=CardRegistry)
    enemies: EnemyRegistry = field(default_factory=EnemyRegistry)
    relics: RelicRegistry = field(default_factory=RelicRegistry)
    events: EventRegistry = field(default_factory=EventRegistry)
    acts: ActRegistry = field(default_factory=ActRegistry)
    card_pool_ids: set[str] = field(default_factory=set)
    enemy_pool_ids: set[str] = field(default_factory=set)
    relic_pool_ids: set[str] = field(default_factory=set)
    event_pool_ids: set[str] = field(default_factory=set)
    enemy_pool_members: dict[str, tuple[str, ...]] = field(default_factory=dict)
    event_pool_members: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def from_content_root(cls, content_root: str | Path) -> ContentCatalog:
        root = Path(content_root)
        catalog = cls()
        catalog._load_characters(root / "characters")
        catalog._load_card_pools(root / "cards")
        catalog._load_enemy_pools(root / "enemies")
        catalog._load_event_pools(root / "events")
        catalog._load_relic_pools(root / "relics")
        catalog._load_acts(root / "acts")
        catalog.validate_startup_integrity()
        return catalog

    def _load_characters(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.characters.register(load_json_file(path))

    def _load_card_pools(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.card_pool_ids.add(path.stem)
            self.cards.register_many(_require_list(_load_list_payload(path, "cards"), "cards"))

    def _load_enemy_pools(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.enemy_pool_ids.add(path.stem)
            enemy_records = _require_list(_load_list_payload(path, "enemies"), "enemies")
            self.enemy_pool_members[path.stem] = tuple(
                _require_str(_require_mapping(record, "enemy").get("id"), "enemy.id")
                for record in enemy_records
            )
            self.enemies.register_many(enemy_records)

    def _load_event_pools(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.event_pool_ids.add(path.stem)
            event_records = _require_list(_load_list_payload(path, "events"), "events")
            self.event_pool_members[path.stem] = tuple(
                _require_str(_require_mapping(record, "event").get("id"), "event.id")
                for record in event_records
            )
            self.events.register_many(event_records)

    def _load_relic_pools(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.relic_pool_ids.add(path.stem)
            self.relics.register_many(_require_list(_load_list_payload(path, "relics"), "relics"))

    def _load_acts(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.acts.register_many(_require_list(_load_list_payload(path, "acts"), "acts"))

    def validate_startup_integrity(self) -> None:
        validate_startup_integrity(
            characters=self.characters,
            cards=self.cards,
            enemies=self.enemies,
            relics=self.relics,
            events=self.events,
            acts=self.acts,
            card_pool_ids=self.card_pool_ids,
            enemy_pool_ids=self.enemy_pool_ids,
            relic_pool_ids=self.relic_pool_ids,
            event_pool_ids=self.event_pool_ids,
        )

    def enemy_ids_for_pool(self, pool_id: str) -> tuple[str, ...]:
        if pool_id not in self.enemy_pool_members:
            raise KeyError(pool_id)
        return self.enemy_pool_members[pool_id]

    def event_ids_for_pool(self, pool_id: str) -> tuple[str, ...]:
        if pool_id not in self.event_pool_members:
            raise KeyError(pool_id)
        return self.event_pool_members[pool_id]
