from __future__ import annotations

from dataclasses import dataclass

from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.shared.types import JsonDict


@dataclass(slots=True, frozen=True)
class CombatActionResult:
    combat_state: CombatState
    resolved_effects: list[JsonDict]


def card_id_from_instance_id(card_instance_id: str) -> str:
    if not isinstance(card_instance_id, str):
        raise TypeError("card_instance_id must be a string")
    if not card_instance_id:
        raise ValueError("card_instance_id must not be empty")
    if card_instance_id.count("#") != 1:
        raise ValueError("card_instance_id must use card_id#instance_suffix format")
    card_id, instance_suffix = card_instance_id.split("#", 1)
    if not card_id or not instance_suffix:
        raise ValueError("card_instance_id must use card_id#instance_suffix format")
    return card_id
