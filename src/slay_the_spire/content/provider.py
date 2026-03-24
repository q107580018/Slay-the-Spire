from __future__ import annotations

from pathlib import Path

from slay_the_spire.content.catalog import ContentCatalog
from slay_the_spire.content.registries import ActRegistry, CardRegistry, CharacterRegistry, EnemyRegistry, EventRegistry, RelicRegistry
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

    def relics(self) -> RelicRegistry:
        return self._catalog.relics

    def events(self) -> EventRegistry:
        return self._catalog.events

    def acts(self) -> ActRegistry:
        return self._catalog.acts
