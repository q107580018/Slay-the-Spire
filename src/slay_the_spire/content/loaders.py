from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from slay_the_spire.content.registries import (
    ActRegistry,
    CardRegistry,
    CharacterRegistry,
    EnemyRegistry,
    EventRegistry,
    RelicRegistry,
    validate_startup_integrity,
)
from slay_the_spire.shared.types import JsonValue


def load_json_file(path: str | Path) -> JsonValue:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _require_list(value: object, field_name: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{field_name} must be a list")
    return value


def _load_list_payload(path: Path, key: str) -> object:
    payload = load_json_file(path)
    if not isinstance(payload, Mapping):
        raise TypeError(f"{path.name} must contain a JSON object")
    if key not in payload:
        raise ValueError(f"{key} is required in {path.name}")
    return payload[key]


@dataclass(slots=True)
class ContentRegistry:
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

    @classmethod
    def from_content_root(cls, content_root: str | Path) -> ContentRegistry:
        root = Path(content_root)
        registry = cls()
        registry._load_characters(root / "characters")
        registry._load_card_pools(root / "cards")
        registry._load_enemy_pools(root / "enemies")
        registry._load_event_pools(root / "events")
        registry._load_relic_pools(root / "relics")
        registry._load_acts(root / "acts")
        registry.validate_startup_integrity()
        return registry

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
            self.enemies.register_many(_require_list(_load_list_payload(path, "enemies"), "enemies"))

    def _load_event_pools(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.event_pool_ids.add(path.stem)
            self.events.register_many(_require_list(_load_list_payload(path, "events"), "events"))

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
