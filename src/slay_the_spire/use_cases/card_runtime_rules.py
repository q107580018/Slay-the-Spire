from __future__ import annotations

from typing import Literal

from slay_the_spire.content.registries import CardDef
from slay_the_spire.domain.models.combat_state import CombatState

# 用于承载会覆写卡牌运行时费用、出牌后去向等战斗内规则。
# 以后遇到类似 Corruption 的特殊卡牌/能力，优先复用这里，而不是把特判散落回 play_card 主流程。
PostPlayDestination = Literal["discard", "exhaust", "void"]


def _has_player_power(state: CombatState, power_id: str) -> bool:
    return any(power.get("power_id") == power_id for power in state.active_powers)


def _resolve_base_card_cost(
    card_def: CardDef, combat_state: CombatState, card_instance_id: str
) -> int:
    if card_instance_id in combat_state.temporary_costs:
        return max(0, combat_state.temporary_costs[card_instance_id])
    if card_def.cost_reducer == "times_hit_this_combat":
        return max(0, card_def.cost - combat_state.times_hit_this_combat)
    return card_def.cost


def resolve_runtime_card_cost(
    card_def: CardDef, combat_state: CombatState, card_instance_id: str
) -> int:
    if card_def.card_type == "skill" and _has_player_power(combat_state, "corruption"):
        return 0
    return _resolve_base_card_cost(card_def, combat_state, card_instance_id)


def resolve_post_play_destination(
    card_def: CardDef, combat_state: CombatState, card_instance_id: str
) -> PostPlayDestination:
    del card_instance_id
    if card_def.card_type == "power":
        return "void"
    if card_def.card_type == "skill" and _has_player_power(combat_state, "corruption"):
        return "exhaust"
    if getattr(card_def, "exhausts", False):
        return "exhaust"
    return "discard"
