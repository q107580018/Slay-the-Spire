from __future__ import annotations

from collections.abc import Mapping

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.terminal.theme import PANEL_BOX
from slay_the_spire.adapters.terminal.widgets import render_block, render_hp_bar, render_statuses, summarize_card_effects
from slay_the_spire.content.registries import CardDef, EnemyDef
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState
from slay_the_spire.ports.content_provider import ContentProviderPort


def _card_cost_label(card_def: CardDef) -> str:
    if not card_def.playable or card_def.cost < 0:
        return "无法打出"
    return str(card_def.cost)


def _card_type_label(card_def: CardDef) -> str:
    effect_types = {str(effect.get("type")) for effect in card_def.effects}
    if effect_types & {"damage", "vulnerable"}:
        return "攻击"
    if effect_types & {"block", "draw", "heal", "strength", "create_card_copy"}:
        return "技能"
    return "未知"


def _zone_label(zone: object) -> str:
    zone_labels = {
        "hand": "手牌",
        "draw_pile": "抽牌堆",
        "discard_pile": "弃牌堆",
        "exhaust_pile": "消耗堆",
    }
    return zone_labels.get(str(zone), str(zone))


def _effect_description(effect: Mapping[str, object], registry: ContentProviderPort) -> str:
    effect_type = effect.get("type")
    if effect_type == "damage":
        return f"造成 {effect.get('amount', '?')} 伤害"
    if effect_type == "block":
        return f"获得 {effect.get('amount', '?')} 格挡"
    if effect_type == "draw":
        return f"抽 {effect.get('amount', '?')} 张牌"
    if effect_type == "vulnerable":
        return f"施加 {effect.get('stacks', '?')} 层易伤"
    if effect_type == "create_card_copy":
        card_id = effect.get("card_id")
        card_name = str(card_id)
        if isinstance(card_id, str):
            try:
                card_name = registry.cards().get(card_id).name
            except KeyError:
                card_name = card_id
        return f"复制一张 {card_name} 放入{_zone_label(effect.get('zone'))}"
    return str(dict(effect))


def _full_effect_summary(card_def: CardDef, registry: ContentProviderPort) -> str:
    if not card_def.effects:
        return "无效果"
    return "；".join(_effect_description(effect, registry) for effect in card_def.effects)


def _upgrade_target_label(card_def: CardDef, registry: ContentProviderPort) -> str:
    if not card_def.upgrades_to:
        return "-"
    try:
        return registry.cards().get(card_def.upgrades_to).name
    except KeyError:
        return card_def.upgrades_to


def format_card_instance_menu(title: str, card_instance_ids: list[str], registry: ContentProviderPort) -> list[str]:
    lines = [f"{title}:"]
    if not card_instance_ids:
        lines.append("-")
    else:
        for index, card_instance_id in enumerate(card_instance_ids, start=1):
            card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
            effect_summary = summarize_card_effects(card_def.effects) if card_def.effects else "无效果"
            lines.append(
                f"{index}. {card_def.name} | 费用 {_card_cost_label(card_def)} | 类型 {_card_type_label(card_def)} | {effect_summary}"
            )
    lines.append(f"{len(card_instance_ids) + 1}. 返回资料总览")
    return lines


def render_card_pile_panel(title: str, card_instance_ids: list[str], registry: ContentProviderPort) -> Panel:
    return Panel(Group(*[Text(line) for line in format_card_instance_menu(title, card_instance_ids, registry)]), title=title, box=PANEL_BOX, expand=False)


def format_card_detail_menu() -> list[str]:
    return ["卡牌详情:", "1. 返回卡牌列表", "2. 返回资料总览"]


def render_card_detail_panel(card_instance_id: str, registry: ContentProviderPort) -> Panel:
    card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
    lines = [
        f"名称: {card_def.name}",
        f"实例 ID: {card_instance_id}",
        f"费用: {_card_cost_label(card_def)}",
        f"类型: {_card_type_label(card_def)}",
        f"是否可打出: {'是' if card_def.playable and card_def.cost >= 0 else '否'}",
        f"完整效果: {_full_effect_summary(card_def, registry)}",
        f"升级目标: {_upgrade_target_label(card_def, registry)}",
    ]
    return Panel(Group(*[Text(line) for line in lines]), title="卡牌详情", box=PANEL_BOX, expand=False)


def _sleeping_stacks(enemy: EnemyState) -> int:
    for status in enemy.statuses:
        if status.status_id == "sleeping":
            return status.stacks
    return 0


def _sleep_turns(enemy_def: EnemyDef) -> int:
    if not enemy_def.move_table:
        return 0
    first_move = enemy_def.move_table[0]
    if first_move.get("move") != "sleep":
        return 0
    sleep_turns = first_move.get("sleep_turns", 0)
    return sleep_turns if isinstance(sleep_turns, int) and sleep_turns > 0 else 0


def _current_enemy_move(combat_state: CombatState, enemy: EnemyState, enemy_def: EnemyDef) -> Mapping[str, object] | None:
    if enemy.hp <= 0 or not enemy_def.move_table:
        return None
    sleeping_stacks = _sleeping_stacks(enemy)
    if sleeping_stacks > 0:
        return {"move": "sleep", "sleep_turns": sleeping_stacks}
    sleep_turns = _sleep_turns(enemy_def)
    active_moves = enemy_def.move_table[1:] if sleep_turns > 0 else enemy_def.move_table
    if not active_moves:
        return None
    if enemy_def.intent_policy != "scripted":
        return active_moves[0]
    move_index = max(combat_state.round_number - sleep_turns - 1, 0) % len(active_moves)
    return active_moves[move_index]


def _move_summary(move: Mapping[str, object], registry: ContentProviderPort) -> str:
    if move.get("move") == "sleep":
        return f"睡眠中 ({move.get('sleep_turns', '?')} 回合)"
    effects = move.get("effects")
    if isinstance(effects, list) and effects:
        return " / ".join(_effect_description(effect, registry) for effect in effects if isinstance(effect, Mapping))
    return "-"


def _move_preview(enemy_def: EnemyDef, registry: ContentProviderPort) -> str:
    previews: list[str] = []
    for move in enemy_def.move_table:
        move_name = str(move.get("move", "-"))
        previews.append(f"{move_name}: {_move_summary(move, registry)}")
    return "；".join(previews) if previews else "-"


def _enemy_status_label(enemy: EnemyState) -> str:
    return "无" if not enemy.statuses else "".join(render_statuses(enemy.statuses).plain.splitlines())


def format_enemy_list_menu(enemies: list[EnemyState], registry: ContentProviderPort) -> list[str]:
    lines = ["敌人列表:"]
    if not enemies:
        lines.append("-")
    else:
        for index, enemy in enumerate(enemies, start=1):
            enemy_def = registry.enemies().get(enemy.enemy_id)
            lines.append(f"{index}. {enemy_def.name}")
    lines.append(f"{len(enemies) + 1}. 返回资料总览")
    return lines


def render_enemy_list_panel(combat_state: CombatState, registry: ContentProviderPort) -> Panel:
    if not combat_state.enemies:
        return Panel(Group(Text("-")), title="敌人列表", box=PANEL_BOX, expand=False)
    lines = []
    for index, enemy in enumerate(combat_state.enemies, start=1):
        enemy_def = registry.enemies().get(enemy.enemy_id)
        line = Text(f"{index}. ")
        line.append(enemy_def.name, style="enemy.name")
        line.append(f" | 生命: {enemy.hp}/{enemy.max_hp}")
        line.append(f" | 格挡: {enemy.block}")
        line.append(f" | 状态: {_enemy_status_label(enemy)}")
        line.append(f" | 当前意图: {_move_summary(_current_enemy_move(combat_state, enemy, enemy_def) or {}, registry)}")
        lines.append(line)
    return Panel(Group(*lines), title="敌人列表", box=PANEL_BOX, expand=False)


def format_enemy_detail_menu() -> list[str]:
    return ["敌人详情:", "1. 返回敌人列表", "2. 返回资料总览"]


def render_enemy_detail_panel(combat_state: CombatState, enemy: EnemyState, registry: ContentProviderPort) -> Panel:
    enemy_def = registry.enemies().get(enemy.enemy_id)
    current_move = _current_enemy_move(combat_state, enemy, enemy_def)
    lines = [
        Text.assemble("名称: ", (enemy_def.name, "enemy.name")),
        Text(f"当前生命: {enemy.hp}/{enemy.max_hp}"),
        Text(f"当前格挡: {enemy.block}"),
        Text(f"当前状态: {_enemy_status_label(enemy)}"),
        Text(f"当前意图摘要: {_move_summary(current_move or {}, registry)}"),
        Text(f"招式表预览: {_move_preview(enemy_def, registry)}"),
    ]
    return Panel(Group(*lines), title="敌人详情", box=PANEL_BOX, expand=False)
