from __future__ import annotations

from collections.abc import Mapping

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.rich_ui.theme import PANEL_BOX
from slay_the_spire.adapters.rich_ui.widgets import (
    card_rarity_label,
    card_label,
    format_card_cost,
    is_upgraded_card,
    render_statuses,
    render_card_name,
    special_card_rule_text,
    summarize_card_definition,
    summarize_card_effects,
    summarize_effect,
    summarize_active_powers,
    summarize_relic_effects,
    summarize_trigger_hooks,
)
from slay_the_spire.app.menu_definitions import (
    build_card_detail_menu,
    build_enemy_detail_menu,
    format_menu_lines,
)
from slay_the_spire.content.registries import CardDef, EnemyDef
from slay_the_spire.domain.combat.turn_flow import preview_enemy_move_for_display
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort


def _format_node_id(node_id: object) -> str:
    if str(node_id) == "start":
        return "起点"
    return str(node_id)


def _card_cost_label(card_def: CardDef) -> str:
    if not card_def.playable:
        return "无法打出"
    return format_card_cost(card_def.cost)


def _card_type_label(card_def: CardDef) -> str:
    effect_types = {str(effect.get("type")) for effect in card_def.effects}
    if effect_types & {"damage", "damage_all_enemies_x_times", "vulnerable", "weak"}:
        return "攻击"
    if effect_types:
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
    if effect.get("type") == "create_card_copy":
        card_id = effect.get("card_id")
        card_name = str(card_id)
        if isinstance(card_id, str):
            try:
                card_name = registry.cards().get(card_id).name
            except KeyError:
                card_name = card_id
        return f"复制一张 {card_name} 放入{_zone_label(effect.get('zone'))}"
    if effect.get("type") == "add_card_to_discard":
        card_id = effect.get("card_id")
        card_name = str(card_id)
        if isinstance(card_id, str):
            try:
                card_name = registry.cards().get(card_id).name
            except KeyError:
                card_name = card_label(card_id)
            rule_text = special_card_rule_text(card_id)
            if rule_text is not None:
                return f"向弃牌堆加入 {int(effect.get('count', 1))} 张 {card_name}（{rule_text}）"
        return f"向弃牌堆加入 {int(effect.get('count', 1))} 张 {card_name}"
    return summarize_effect(effect, detailed_status_cards=True)


def _full_effect_summary(card_def: CardDef, registry: ContentProviderPort) -> str:
    if not card_def.effects:
        return special_card_rule_text(card_def.id) or "无效果"
    return "；".join(_effect_description(effect, registry) for effect in card_def.effects)


def _upgrade_target_label(card_def: CardDef, registry: ContentProviderPort) -> str:
    if not card_def.upgrades_to:
        return "-"
    try:
        return registry.cards().get(card_def.upgrades_to).name
    except KeyError:
        return card_def.upgrades_to


def format_card_detail_lines(card_instance_id: str, registry: ContentProviderPort) -> list[Text]:
    card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
    cost_label = "无法打出" if not card_def.playable else format_card_cost(card_def.cost)
    lines = [
        Text.assemble(("名称 ", "summary.label"), render_card_name(card_def)),
        Text.assemble(("费用 ", "summary.label"), cost_label),
        Text.assemble(("效果 ", "summary.label"), summarize_card_definition(card_def)),
        Text.assemble(("稀有度 ", "summary.label"), card_rarity_label(card_def)),
        Text.assemble(("状态 ", "summary.label"), "已升级" if is_upgraded_card(card_def) else "未升级"),
        Text.assemble(("实例 ", "summary.label"), card_instance_id),
    ]
    if card_def.upgrades_to is not None:
        upgraded = registry.cards().get(card_def.upgrades_to)
        lines.append(Text.assemble(("升级为 ", "summary.label"), render_card_name(upgraded)))
    return lines


def _card_upgrade_preview_line(*, title: str, card_def: CardDef) -> Text:
    return Text.assemble(
        (f"{title} ", "summary.label"),
        ("名称 ", "summary.label"),
        render_card_name(card_def),
        (" | 费用 ", "summary.label"),
        _card_cost_label(card_def),
        (" | 效果 ", "summary.label"),
        summarize_card_definition(card_def),
        (" | 状态 ", "summary.label"),
        "已升级" if is_upgraded_card(card_def) else "未升级",
    )


def format_card_upgrade_preview_lines(card_instance_id: str, registry: ContentProviderPort) -> list[Text]:
    card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
    if card_def.upgrades_to is None:
        return format_card_detail_lines(card_instance_id, registry)
    upgraded_def = registry.cards().get(card_def.upgrades_to)
    return [
        _card_upgrade_preview_line(title="当前", card_def=card_def),
        _card_upgrade_preview_line(title="升级后", card_def=upgraded_def),
    ]


def format_relic_detail_lines(relic_id: str, registry: ContentProviderPort) -> list[Text]:
    relic_def = registry.relics().get(relic_id)
    lines = [
        Text.assemble(("名称 ", "summary.label"), relic_def.name),
        Text.assemble(("遗物 ", "summary.label"), relic_id),
        Text.assemble(("效果 ", "summary.label"), summarize_relic_effects(relic_def.passive_effects)),
    ]
    if relic_def.summary is not None:
        lines.append(Text.assemble(("摘要 ", "summary.label"), relic_def.summary))
    if relic_def.description is not None:
        lines.append(Text.assemble(("描述 ", "summary.label"), relic_def.description))
    if relic_def.replaces_relic_id is not None:
        replacement = relic_def.replaces_relic_id
        try:
            replacement = registry.relics().get(relic_def.replaces_relic_id).name
        except KeyError:
            pass
        lines.append(Text.assemble(("替换原遗物 ", "summary.label"), replacement))
    disabled_actions = {
        "gain_gold": "获得金币",
        "rest_heal": "休息回复",
        "smith": "锻造",
    }
    disabled_action_labels = [disabled_actions.get(action, action) for action in relic_def.disabled_actions]
    lines.append(
        Text.assemble(
            ("禁用操作 ", "summary.label"),
            " / ".join(disabled_action_labels) if disabled_action_labels else "无",
        )
    )
    lines.append(
        Text.assemble(
            ("金币规则 ", "summary.label"),
            "阻止获得金币" if relic_def.blocks_gold_gain else "可正常获得金币",
        )
    )
    if relic_def.trigger_hooks:
        lines.append(Text.assemble(("触发 ", "summary.label"), summarize_trigger_hooks(relic_def.trigger_hooks)))
    return lines


def format_potion_detail_lines(potion_id: str, registry: ContentProviderPort) -> list[Text]:
    potion_def = registry.potions().get(potion_id)
    return [
        Text.assemble(("名称 ", "summary.label"), potion_def.name),
        Text.assemble(("药水 ", "summary.label"), potion_id),
        Text.assemble(("效果 ", "summary.label"), summarize_effect(potion_def.effect)),
    ]


def _reward_card_id(reward_name: str) -> str:
    if reward_name == "reward_strike":
        return "strike_plus"
    if reward_name == "reward_defend":
        return "defend_plus"
    return reward_name


def _event_reward_label(result: str) -> str:
    if result == "gain_upgrade":
        return "事件结果 获得升级"
    if result == "nothing":
        return "事件结果 什么也没有发生"
    return f"事件结果 {result}"


def format_reward_detail_lines(reward_id: str, registry: ContentProviderPort) -> list[Text]:
    lines = [Text.assemble(("奖励 ID: ", "summary.label"), reward_id)]
    if reward_id.startswith("gold:"):
        amount = reward_id.split(":", 1)[1]
        lines.append(Text.assemble(("奖励类型: ", "summary.label"), f"金币 +{amount}"))
        return lines
    if reward_id.startswith("card_offer:") or reward_id.startswith("card:"):
        reward_name = reward_id.split(":", 1)[1]
        card_def = registry.cards().get(_reward_card_id(reward_name))
        lines.append(Text.assemble(("奖励类型: ", "summary.label"), "卡牌"))
        lines.append(Text.assemble(("名称: ", "summary.label"), render_card_name(card_def)))
        lines.append(Text.assemble(("效果: ", "summary.label"), summarize_card_definition(card_def)))
        return lines
    if reward_id.startswith("relic:"):
        relic_id = reward_id.split(":", 1)[1]
        relic_def = registry.relics().get(relic_id)
        lines.append(Text.assemble(("奖励类型: ", "summary.label"), "遗物"))
        lines.append(Text.assemble(("名称: ", "summary.label"), relic_def.name))
        lines.append(Text.assemble(("效果: ", "summary.label"), summarize_relic_effects(relic_def.passive_effects)))
        if relic_def.summary is not None:
            lines.append(Text.assemble(("摘要: ", "summary.label"), relic_def.summary))
        if relic_def.description is not None:
            lines.append(Text.assemble(("描述: ", "summary.label"), relic_def.description))
        if relic_def.replaces_relic_id is not None:
            replacement = relic_def.replaces_relic_id
            try:
                replacement = registry.relics().get(relic_def.replaces_relic_id).name
            except KeyError:
                pass
            lines.append(Text.assemble(("替换原遗物: ", "summary.label"), replacement))
        disabled_actions = {
            "gain_gold": "获得金币",
            "rest_heal": "休息回复",
            "smith": "锻造",
        }
        disabled_action_labels = [disabled_actions.get(action, action) for action in relic_def.disabled_actions]
        lines.append(
            Text.assemble(
                ("禁用操作: ", "summary.label"),
                " / ".join(disabled_action_labels) if disabled_action_labels else "无",
            )
        )
        lines.append(
            Text.assemble(
                ("金币规则: ", "summary.label"),
                "阻止获得金币" if relic_def.blocks_gold_gain else "可正常获得金币",
            )
        )
        if relic_def.trigger_hooks:
            lines.append(Text.assemble(("触发: ", "summary.label"), summarize_trigger_hooks(relic_def.trigger_hooks)))
        return lines
    if reward_id.startswith("event:"):
        result = reward_id.split(":", 1)[1]
        lines.append(Text.assemble(("奖励类型: ", "summary.label"), _event_reward_label(result)))
        return lines
    lines.append(Text.assemble(("说明: ", "summary.label"), reward_id))
    return lines


def render_reward_detail_panel(reward_id: str, registry: ContentProviderPort) -> Panel:
    return Panel(Group(*format_reward_detail_lines(reward_id, registry)), title="奖励详情", box=PANEL_BOX, expand=False)


def format_card_instance_menu(title: str, card_instance_ids: list[str], registry: ContentProviderPort) -> list[str | Text]:
    del title
    lines: list[str | Text] = []
    if not card_instance_ids:
        lines.append("-")
    else:
        for index, card_instance_id in enumerate(card_instance_ids, start=1):
            card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
            effect_summary = summarize_card_definition(card_def)
            lines.append(Text.assemble(f"{index}. ", render_card_name(card_def), f" | 费用 {_card_cost_label(card_def)} | 类型 {_card_type_label(card_def)} | {effect_summary}"))
    lines.append(f"{len(card_instance_ids) + 1}. 返回资料总览")
    return lines


def render_card_pile_panel(title: str, card_instance_ids: list[str], registry: ContentProviderPort) -> Panel:
    body = [line if isinstance(line, Text) else Text(line) for line in format_card_instance_menu(title, card_instance_ids, registry)]
    return Panel(Group(*body), title=title, box=PANEL_BOX, expand=False)


def format_card_list_footer(*, back_choice: int) -> list[str]:
    return [
        "输入上方编号查看卡牌详情",
        f"{back_choice}. 返回资料总览",
    ]


def _active_power_summary(active_powers: list[dict[str, object]]) -> str:
    return summarize_active_powers(active_powers)


def render_shared_stats_panel(
    *,
    title: str,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    combat_state: CombatState | None = None,
) -> Panel:
    lines = [
        f"当前生命: {run_state.current_hp}/{run_state.max_hp}",
        f"金币: {run_state.gold}",
        f"当前章节: {act_state.act_id}",
        f"当前房间: {_format_node_id(room_state.payload.get('node_id', act_state.current_node_id))}",
    ]
    if combat_state is not None:
        lines.extend(
            [
                f"格挡: {combat_state.player.block}",
                f"状态: {render_statuses(combat_state.player.statuses).plain}",
                f"持续效果: {_active_power_summary(combat_state.active_powers)}",
            ]
        )
    return Panel(Group(*[Text(line) for line in lines]), title=title, box=PANEL_BOX, expand=False)


def render_shared_relics_panel(*, title: str, run_state: RunState, registry: ContentProviderPort) -> Panel:
    lines = ["当前遗物:"]
    if not run_state.relics:
        lines.append("-")
    else:
        for relic_id in run_state.relics:
            lines.append(f"- {registry.relics().get(relic_id).name}")
    return Panel(Group(*[Text(line) for line in lines]), title=title, box=PANEL_BOX, expand=False)


def render_shared_potions_panel(*, title: str, run_state: RunState, registry: ContentProviderPort) -> Panel:
    lines = ["当前药水:"]
    if not run_state.potions:
        lines.append("-")
    else:
        for potion_id in run_state.potions:
            lines.append(f"- {registry.potions().get(potion_id).name}")
    return Panel(Group(*[Text(line) for line in lines]), title=title, box=PANEL_BOX, expand=False)


def format_card_detail_menu() -> list[str]:
    return format_menu_lines(build_card_detail_menu())


def render_card_detail_panel(card_instance_id: str, registry: ContentProviderPort) -> Panel:
    card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
    playable_label = "是" if card_def.playable else "否"
    lines = [
        Text.assemble(("名称: ", "summary.label"), render_card_name(card_def)),
        Text.assemble(("实例 ID: ", "summary.label"), card_instance_id),
        Text.assemble(("稀有度: ", "summary.label"), card_rarity_label(card_def)),
        Text.assemble(("状态: ", "summary.label"), "已升级" if is_upgraded_card(card_def) else "未升级"),
        Text.assemble(("费用: ", "summary.label"), _card_cost_label(card_def)),
        Text.assemble(("类型: ", "summary.label"), _card_type_label(card_def)),
        Text.assemble(("是否可打出: ", "summary.label"), playable_label),
        Text.assemble(("完整效果: ", "summary.label"), _full_effect_summary(card_def, registry)),
        Text.assemble(("升级目标: ", "summary.label"), _upgrade_target_label(card_def, registry)),
    ]
    return Panel(Group(*lines), title="卡牌详情", box=PANEL_BOX, expand=False)


def _move_summary(move: Mapping[str, object], registry: ContentProviderPort) -> str:
    if move.get("move") == "sleep":
        return f"睡眠中 ({move.get('sleep_turns', '?')} 回合)"
    effects = move.get("effects")
    if isinstance(effects, list) and effects:
        return " / ".join(_effect_description(effect, registry) for effect in effects if isinstance(effect, Mapping))
    return summarize_effect(move)


def _move_preview(enemy_def: EnemyDef, registry: ContentProviderPort) -> str:
    previews: list[str] = []
    for move in enemy_def.move_table:
        move_name = str(move.get("move", "-"))
        previews.append(f"{move_name}: {_move_summary(move, registry)}")
    return "；".join(previews) if previews else "-"


def _enemy_status_label(enemy: EnemyState) -> str:
    return "无" if not enemy.statuses else "".join(render_statuses(enemy.statuses).plain.splitlines())


def format_enemy_list_menu(enemies: list[EnemyState], registry: ContentProviderPort) -> list[str]:
    lines: list[str] = []
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
        line.append(f" | 当前意图: {_move_summary(preview_enemy_move_for_display(combat_state, enemy, enemy_def) or {}, registry)}")
        lines.append(line)
    return Panel(Group(*lines), title="敌人列表", box=PANEL_BOX, expand=False)


def format_enemy_detail_menu() -> list[str]:
    return format_menu_lines(build_enemy_detail_menu())


def format_enemy_list_footer(*, back_choice: int) -> list[str]:
    return [
        "输入上方编号查看敌人详情",
        f"{back_choice}. 返回资料总览",
    ]


def render_enemy_detail_panel(combat_state: CombatState, enemy: EnemyState, registry: ContentProviderPort) -> Panel:
    enemy_def = registry.enemies().get(enemy.enemy_id)
    current_move = preview_enemy_move_for_display(combat_state, enemy, enemy_def)
    lines = [
        Text.assemble("名称: ", (enemy_def.name, "enemy.name")),
        Text(f"当前生命: {enemy.hp}/{enemy.max_hp}"),
        Text(f"当前格挡: {enemy.block}"),
        Text(f"当前状态: {_enemy_status_label(enemy)}"),
        Text(f"当前意图摘要: {_move_summary(current_move or {}, registry)}"),
        Text(f"招式表预览: {_move_preview(enemy_def, registry)}"),
    ]
    return Panel(Group(*lines), title="敌人详情", box=PANEL_BOX, expand=False)
