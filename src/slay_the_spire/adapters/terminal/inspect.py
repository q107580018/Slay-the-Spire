from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.terminal.theme import PANEL_BOX
from slay_the_spire.adapters.terminal.widgets import (
    preview_enemy_intent,
    render_block,
    render_hp_bar,
    render_statuses,
    summarize_card_effects,
)
from slay_the_spire.content.registries import CardDef
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.entities import EnemyState
from slay_the_spire.ports.content_provider import ContentProviderPort


def format_card_instance_menu(title: str, card_instance_ids: list[str], registry: ContentProviderPort) -> list[str]:
    lines = [f"{title}:"]
    if not card_instance_ids:
        lines.append("-")
    else:
        for index, card_instance_id in enumerate(card_instance_ids, start=1):
            card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
            lines.append(f"{index}. {card_def.name}")
    lines.append(f"{len(card_instance_ids) + 1}. 返回资料总览")
    return lines


def render_card_pile_panel(title: str, card_instance_ids: list[str], registry: ContentProviderPort) -> Panel:
    return Panel(Group(*[Text(line) for line in format_card_instance_menu(title, card_instance_ids, registry)]), title=title, box=PANEL_BOX, expand=False)


def format_card_detail_menu() -> list[str]:
    return ["卡牌详情:", "1. 返回卡牌列表", "2. 返回资料总览"]


def render_card_detail_panel(card_instance_id: str, registry: ContentProviderPort) -> Panel:
    card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
    lines = _card_detail_lines(card_def)
    return Panel(Group(*[Text(line) for line in lines]), title="卡牌详情", box=PANEL_BOX, expand=False)


def _card_detail_lines(card_def: CardDef) -> list[str]:
    cost_label = "无法打出" if not getattr(card_def, "playable", True) or card_def.cost < 0 else str(card_def.cost)
    effect_summary = summarize_card_effects(card_def.effects) if card_def.effects else "无效果"
    lines = [
        f"名称: {card_def.name}",
        f"费用: {cost_label}",
        f"效果: {effect_summary}",
    ]
    return lines


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


def render_enemy_list_panel(enemies: list[EnemyState], registry: ContentProviderPort) -> Panel:
    if not enemies:
        return Panel(Group(Text("-")), title="敌人列表", box=PANEL_BOX, expand=False)
    lines = []
    for index, enemy in enumerate(enemies, start=1):
        enemy_def = registry.enemies().get(enemy.enemy_id)
        line = Text(f"{index}. ")
        line.append(enemy_def.name, style="enemy.name")
        line.append(" 生命: ")
        line.append_text(render_hp_bar(enemy.hp, enemy.max_hp))
        line.append(" 格挡: ")
        line.append_text(render_block(enemy.block))
        lines.append(line)
    return Panel(Group(*lines), title="敌人列表", box=PANEL_BOX, expand=False)


def format_enemy_detail_menu() -> list[str]:
    return ["敌人详情:", "1. 返回敌人列表", "2. 返回资料总览"]


def render_enemy_detail_panel(enemy: EnemyState, registry: ContentProviderPort) -> Panel:
    enemy_def = registry.enemies().get(enemy.enemy_id)
    lines = [
        Text.assemble("名称: ", (enemy_def.name, "enemy.name")),
        Text.assemble("生命: ", render_hp_bar(enemy.hp, enemy.max_hp)),
        Text.assemble("格挡: ", render_block(enemy.block)),
        Text.assemble("状态: ", render_statuses(enemy.statuses)),
        Text(f"意图: {preview_enemy_intent(enemy_def)}"),
    ]
    return Panel(Group(*lines), title="敌人详情", box=PANEL_BOX, expand=False)
