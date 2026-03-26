from __future__ import annotations

from pathlib import Path

from slay_the_spire.content.catalog import ContentCatalog, WeightedPoolEntry
from slay_the_spire.content.registries import (
    ActRegistry,
    CardRegistry,
    CharacterRegistry,
    EncounterRegistry,
    EnemyRegistry,
    EventRegistry,
    PotionRegistry,
    RelicRegistry,
)
from slay_the_spire.ports.content_provider import ContentProviderPort


class StarterContentProvider(ContentProviderPort):
    def __init__(self, content_root: str | Path) -> None:
        self._catalog = ContentCatalog.from_content_root(content_root)

    def characters(self) -> CharacterRegistry:
        return self._catalog.characters

    def cards(self) -> CardRegistry:
        return self._catalog.cards

    def enemies(self) -> EnemyRegistry:
        return self._catalog.enemies

    def encounters(self) -> EncounterRegistry:
        return self._catalog.encounters

    def relics(self) -> RelicRegistry:
        return self._catalog.relics

    def potions(self) -> PotionRegistry:
        return self._catalog.potions

    def events(self) -> EventRegistry:
        return self._catalog.events

    def acts(self) -> ActRegistry:
        return self._catalog.acts

    def enemy_ids_for_pool(self, pool_id: str) -> tuple[str, ...]:
        return self._catalog.enemy_ids_for_pool(pool_id)

    def enemy_pool_entries(self, pool_id: str) -> tuple[WeightedPoolEntry, ...]:
        return self._catalog.enemy_pool_entries_for_pool(pool_id)

    def encounter_pool_entries(self, pool_id: str) -> tuple[WeightedPoolEntry, ...]:
        return self._catalog.encounter_pool_entries_for_pool(pool_id)

    def event_ids_for_pool(self, pool_id: str) -> tuple[str, ...]:
        return self._catalog.event_ids_for_pool(pool_id)

    def event_pool_entries(self, pool_id: str) -> tuple[WeightedPoolEntry, ...]:
        return self._catalog.event_pool_entries_for_pool(pool_id)

    def potion_ids_for_pool(self, pool_id: str) -> tuple[str, ...]:
        return self._catalog.potion_ids_for_pool(pool_id)
