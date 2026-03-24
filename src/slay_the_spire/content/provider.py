from __future__ import annotations

from pathlib import Path

from slay_the_spire.content.loaders import ContentRegistry
from slay_the_spire.content.registries import ActRegistry, CardRegistry, EnemyRegistry, EventRegistry, RelicRegistry
from slay_the_spire.ports.content_provider import ContentProviderPort


class StarterContentProvider(ContentProviderPort):
    def __init__(self, content_root: str | Path) -> None:
        self._registry = ContentRegistry.from_content_root(content_root)

    def cards(self) -> CardRegistry:
        return self._registry.cards

    def enemies(self) -> EnemyRegistry:
        return self._registry.enemies

    def relics(self) -> RelicRegistry:
        return self._registry.relics

    def events(self) -> EventRegistry:
        return self._registry.events

    def acts(self) -> ActRegistry:
        return self._registry.acts
