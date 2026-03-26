from __future__ import annotations

from collections import OrderedDict
from collections.abc import Sequence

from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.use_cases.combat_events import CombatEvent

MAX_COMBAT_LOG_ENTRIES = 20


def append_log_entries(combat_state: CombatState, entries: Sequence[str]) -> None:
    if not entries:
        return
    combat_state.log.extend(entry for entry in entries if entry)
    if len(combat_state.log) > MAX_COMBAT_LOG_ENTRIES:
        combat_state.log = combat_state.log[-MAX_COMBAT_LOG_ENTRIES:]


def describe_player_action(*, events: Sequence[CombatEvent]) -> list[str]:
    if not events:
        return []

    card_name = next((event.card_name for event in events if event.event_type == "card_played" and event.card_name), None)
    target_parts: OrderedDict[str, dict[str, int]] = OrderedDict()
    self_parts: list[str] = []

    for event in events:
        if event.event_type == "damage" and event.target_name is not None and event.actual_damage > 0:
            part = target_parts.setdefault(event.target_name, {"damage": 0, "vulnerable": 0})
            part["damage"] += event.actual_damage
            continue
        if event.event_type == "status_applied" and event.status_id == "vulnerable" and event.target_name is not None and event.stacks > 0:
            part = target_parts.setdefault(event.target_name, {"damage": 0, "vulnerable": 0})
            part["vulnerable"] += event.stacks
            continue
        if event.event_type == "block_gained" and event.amount > 0:
            self_parts.append(f"获得 {event.amount} 格挡")
            continue
        if event.event_type == "draw" and event.amount > 0:
            self_parts.append(f"抽 {event.amount} 张牌")

    parts: list[str] = []
    for target_name, values in target_parts.items():
        target_line = ""
        if values["damage"] > 0:
            target_line = f"对 {target_name} 造成 {values['damage']} 伤害"
        if values["vulnerable"] > 0:
            vulnerable_line = f"施加 {values['vulnerable']} 层易伤"
            target_line = f"{target_line}，并{vulnerable_line}" if target_line else f"对 {target_name}{vulnerable_line}"
        if target_line:
            parts.append(target_line)
    parts.extend(self_parts)

    if card_name is None:
        return []
    if not parts:
        return [f"你打出 {card_name}。"]
    return [f"你打出 {card_name}，{'，并'.join(parts)}。"]


def describe_enemy_turn(*, events: Sequence[CombatEvent]) -> list[str]:
    grouped: OrderedDict[str, list[CombatEvent]] = OrderedDict()
    for event in events:
        grouped.setdefault(event.actor_name, []).append(event)

    entries: list[str] = []
    for actor_name, actor_events in grouped.items():
        sleep_event = next((event for event in actor_events if event.event_type == "sleep"), None)
        if sleep_event is not None:
            entries.append(f"{actor_name}沉睡，暂不行动。")
            continue

        if all(event.event_type == "damage" and event.target_name == "你" for event in actor_events):
            if actor_name == "灼伤":
                total_amount = sum(event.amount for event in actor_events)
                total_blocked = sum(event.blocked for event in actor_events)
                total_actual = sum(event.actual_damage for event in actor_events)
                line = f"灼伤在回合结束时触发，对你造成 {total_amount}"
                if total_blocked > 0:
                    line += f"，格挡抵消 {total_blocked}"
                line += f"，实际受到 {total_actual}。"
                entries.append(line)
                continue

        parts: list[str] = []
        for event in actor_events:
            if event.event_type == "damage" and event.target_name == "你":
                damage_line = f"攻击你 {event.amount}"
                if event.blocked > 0:
                    damage_line += f"，格挡抵消 {event.blocked}"
                damage_line += f"，实际受到 {event.actual_damage}"
                parts.append(damage_line)
                continue
            if event.event_type == "add_card_to_discard" and event.card_name is not None and event.count > 0:
                parts.append(f"向你的弃牌堆加入 {event.count} 张{event.card_name}")
                continue
            if event.event_type == "status_applied" and event.status_id == "vulnerable" and event.stacks > 0:
                parts.append(f"施加 {event.stacks} 层易伤")
                continue
            if event.event_type == "block_gained" and event.amount > 0:
                parts.append(f"获得 {event.amount} 格挡")
        if parts:
            entries.append(f"{actor_name}{'，并'.join(parts)}。")
    return entries
