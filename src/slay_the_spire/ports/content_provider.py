from __future__ import annotations

from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from slay_the_spire.content.registries import ActRegistry, CardRegistry, CharacterRegistry, EnemyRegistry, EventRegistry, RelicRegistry


class ContentProviderPort(Protocol):
    def characters(self) -> "CharacterRegistry": ...

    def cards(self) -> "CardRegistry": ...

    def enemies(self) -> "EnemyRegistry": ...

    def relics(self) -> "RelicRegistry": ...

    def events(self) -> "EventRegistry": ...

    def acts(self) -> "ActRegistry": ...
