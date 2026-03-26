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
    PotionRegistry,
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


@dataclass(slots=True, frozen=True)
class WeightedPoolEntry:
    member_id: str
    weight: int
    once_per_run: bool = False


@dataclass(slots=True)
class ContentCatalog:
    characters: CharacterRegistry = field(default_factory=CharacterRegistry)
    cards: CardRegistry = field(default_factory=CardRegistry)
    enemies: EnemyRegistry = field(default_factory=EnemyRegistry)
    relics: RelicRegistry = field(default_factory=RelicRegistry)
    potions: PotionRegistry = field(default_factory=PotionRegistry)
    events: EventRegistry = field(default_factory=EventRegistry)
    acts: ActRegistry = field(default_factory=ActRegistry)
    card_pool_ids: set[str] = field(default_factory=set)
    enemy_pool_ids: set[str] = field(default_factory=set)
    relic_pool_ids: set[str] = field(default_factory=set)
    potion_pool_ids: set[str] = field(default_factory=set)
    event_pool_ids: set[str] = field(default_factory=set)
    enemy_pool_members: dict[str, tuple[str, ...]] = field(default_factory=dict)
    potion_pool_members: dict[str, tuple[str, ...]] = field(default_factory=dict)
    event_pool_members: dict[str, tuple[str, ...]] = field(default_factory=dict)
    enemy_pool_entries: dict[str, tuple[WeightedPoolEntry, ...]] = field(default_factory=dict)
    event_pool_entries: dict[str, tuple[WeightedPoolEntry, ...]] = field(default_factory=dict)

    @classmethod
    def from_content_root(cls, content_root: str | Path) -> ContentCatalog:
        root = Path(content_root)
        catalog = cls()
        catalog._load_characters(root / "characters")
        catalog._load_card_pools(root / "cards")
        catalog._load_enemy_pools(root / "enemies")
        catalog._load_event_pools(root / "events")
        catalog._load_relic_pools(root / "relics")
        catalog._load_potion_pools(root / "potions")
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
            entries = tuple(
                WeightedPoolEntry(
                    member_id=_require_str(_require_mapping(record, "enemy").get("id"), "enemy.id"),
                    weight=int(_require_mapping(record, "enemy").get("pool_weight", 1)),
                )
                for record in enemy_records
            )
            self.enemy_pool_entries[path.stem] = entries
            self.enemy_pool_members[path.stem] = tuple(entry.member_id for entry in entries)
            self.enemies.register_many(enemy_records)

    def _load_event_pools(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.event_pool_ids.add(path.stem)
            event_records = _require_list(_load_list_payload(path, "events"), "events")
            entries = tuple(
                WeightedPoolEntry(
                    member_id=_require_str(_require_mapping(record, "event").get("id"), "event.id"),
                    weight=int(_require_mapping(record, "event").get("pool_weight", 1)),
                    once_per_run=bool(_require_mapping(record, "event").get("once_per_run", False)),
                )
                for record in event_records
            )
            self.event_pool_entries[path.stem] = entries
            self.event_pool_members[path.stem] = tuple(entry.member_id for entry in entries)
            self.events.register_many(event_records)

    def _load_relic_pools(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.relic_pool_ids.add(path.stem)
            self.relics.register_many(_require_list(_load_list_payload(path, "relics"), "relics"))

    def _load_potion_pools(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.potion_pool_ids.add(path.stem)
            potion_records = _require_list(_load_list_payload(path, "potions"), "potions")
            self.potion_pool_members[path.stem] = tuple(
                _require_str(_require_mapping(record, "potion").get("id"), "potion.id")
                for record in potion_records
            )
            self.potions.register_many(potion_records)

    def _load_acts(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            self.acts.register_many(_require_list(_load_list_payload(path, "acts"), "acts"))

    def validate_startup_integrity(self) -> None:
        validate_startup_integrity(
            characters=self.characters,
            cards=self.cards,
            enemies=self.enemies,
            relics=self.relics,
            potions=self.potions,
            events=self.events,
            acts=self.acts,
            card_pool_ids=self.card_pool_ids,
            enemy_pool_ids=self.enemy_pool_ids,
            relic_pool_ids=self.relic_pool_ids,
            potion_pool_ids=self.potion_pool_ids,
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

    def enemy_pool_entries_for_pool(self, pool_id: str) -> tuple[WeightedPoolEntry, ...]:
        if pool_id not in self.enemy_pool_entries:
            raise KeyError(pool_id)
        return self.enemy_pool_entries[pool_id]

    def event_pool_entries_for_pool(self, pool_id: str) -> tuple[WeightedPoolEntry, ...]:
        if pool_id not in self.event_pool_entries:
            raise KeyError(pool_id)
        return self.event_pool_entries[pool_id]

    def potion_ids_for_pool(self, pool_id: str) -> tuple[str, ...]:
        if pool_id not in self.potion_pool_members:
            raise KeyError(pool_id)
        return self.potion_pool_members[pool_id]
