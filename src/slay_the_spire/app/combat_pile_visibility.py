from __future__ import annotations

from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.run_state import RunState


def can_view_draw_pile_order(run_state: RunState | None) -> bool:
    if run_state is None:
        return False
    return "frozen_eye" in run_state.relics


def visible_combat_pile_cards(
    *,
    run_state: RunState | None,
    combat_state: CombatState,
    pile_key: str,
) -> list[str]:
    pile_cards = list(getattr(combat_state, pile_key))
    if pile_key != "draw_pile" or can_view_draw_pile_order(run_state):
        return pile_cards
    return sorted(pile_cards)
