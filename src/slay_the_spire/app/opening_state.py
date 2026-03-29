from __future__ import annotations

from dataclasses import dataclass, field

from slay_the_spire.domain.models.run_state import RunState


@dataclass(frozen=True, slots=True)
class NeowOffer:
    offer_id: str
    category: str
    reward_kind: str
    cost_kind: str | None
    reward_payload: dict[str, object]
    cost_payload: dict[str, object]
    requires_target: str | None
    summary: str
    detail_lines: tuple[str, ...]


@dataclass(slots=True)
class OpeningState:
    seed: int
    available_character_ids: list[str]
    selected_character_id: str | None
    run_blueprint: RunState | None
    neow_offers: list[NeowOffer] = field(default_factory=list)
    pending_neow_offer_id: str | None = None
