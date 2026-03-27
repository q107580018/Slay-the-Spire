from __future__ import annotations

from collections.abc import Mapping, Sequence

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.rich_ui.theme import HP_BAR_WIDTH, PANEL_BOX
from slay_the_spire.content.registries import CardDef, EnemyDef
from slay_the_spire.domain.models.statuses import StatusState

_STATUS_LABELS: dict[str, tuple[str, str]] = {
    "vulnerable": ("易伤", "status.debuff"),
    "weak": ("虚弱", "status.debuff"),
    "strength": ("力量", "status.buff"),
    "dexterity": ("敏捷", "status.buff"),
    "artifact": ("人工制品", "status.buff"),
}

_SPECIAL_CARD_RULE_TEXT: dict[str, str] = {
    "burn": "回合结束时若仍在手中，失去 2 点生命",
    "doubt": "回合结束时若仍在手中，获得 1 层虚弱",
}

_SPECIAL_CARD_LABELS: dict[str, str] = {
    "burn": "灼伤",
    "doubt": "疑虑",
}

_CARD_RARITY_LABELS: dict[str, str] = {
    "basic": "基础",
    "common": "普通",
    "uncommon": "罕见",
    "rare": "稀有",
    "curse": "诅咒",
    "special": "特殊",
}

_CARD_RARITY_STYLES: dict[str, str] = {
    "basic": "card.rarity.basic",
    "common": "card.rarity.common",
    "uncommon": "card.rarity.uncommon",
    "rare": "card.rarity.rare",
    "curse": "card.rarity.curse",
    "special": "card.rarity.special",
}

_POWER_LABELS: dict[str, str] = {
    "inflame": "燃烧",
    "metallicize": "金属化",
    "combust": "燃烧躯体",
}


def hp_style_for_ratio(ratio: float) -> str:
    if ratio <= 0.25:
        return "hp.low"
    if ratio <= 0.6:
        return "hp.medium"
    return "hp.high"


def render_hp_bar(current: int, maximum: int, *, width: int = HP_BAR_WIDTH) -> Text:
    ratio = 0 if maximum <= 0 else max(0, min(current / maximum, 1))
    filled = round(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    return Text.assemble(f"{current}/{maximum} ", (bar, hp_style_for_ratio(ratio)))


def _status_label(status_id: str) -> tuple[str, str]:
    return _STATUS_LABELS.get(status_id, (status_id, "status.debuff"))


def render_statuses(statuses: Sequence[StatusState]) -> Text:
    if not statuses:
        return Text("无")

    rendered = Text()
    for index, status in enumerate(statuses):
        if index > 0:
            rendered.append(" / ")
        label, style = _status_label(status.status_id)
        rendered.append(label, style=style)
        rendered.append(f" {status.stacks}")
    return rendered


def render_block(block: int) -> Text:
    return Text(f"🛡 {block}")


def _styled_choice(option: str | Text) -> Text:
    if isinstance(option, Text):
        prefix, separator, _ = option.plain.partition(" ")
        if separator and prefix.endswith(".") and prefix[:-1].isdigit():
            rendered = option.copy()
            rendered.stylize("menu.number", 0, len(prefix))
            return rendered
        return option
    prefix, separator, remainder = option.partition(" ")
    if separator and prefix.endswith(".") and prefix[:-1].isdigit():
        return Text.assemble((prefix, "menu.number"), f"{separator}{remainder}")
    return Text(option)


def render_menu(options: list[str | Text], *, title: str | None = None) -> Panel:
    body = Group(*(_styled_choice(option) for option in options))
    return Panel(body, title=title or None, box=PANEL_BOX, border_style="menu.border", expand=False)


def special_card_rule_text(card_id: str) -> str | None:
    return _SPECIAL_CARD_RULE_TEXT.get(card_id)


def card_label(card_id: str) -> str:
    return _SPECIAL_CARD_LABELS.get(card_id, card_id)


def is_upgraded_card(card_def: CardDef) -> bool:
    return card_def.id.endswith("_plus") or card_def.name.endswith("+")


def card_rarity_label(card_def: CardDef) -> str:
    if card_def.rarity is None:
        return "未知"
    return _CARD_RARITY_LABELS.get(card_def.rarity, card_def.rarity)


def active_power_label(power_id: str) -> str:
    return _POWER_LABELS.get(power_id, power_id)


def summarize_active_powers(active_powers: Sequence[Mapping[str, object]]) -> str:
    labels: list[str] = []
    for power in active_powers:
        power_id = power.get("power_id")
        if not isinstance(power_id, str):
            continue
        amount = power.get("amount")
        power_name = active_power_label(power_id)
        if isinstance(amount, int):
            labels.append(f"{power_name} {amount}")
        else:
            labels.append(power_name)
    return " / ".join(labels) if labels else "无"


def render_card_name(card_def: CardDef) -> Text:
    rendered = Text()
    rendered.append(card_def.name, style=_CARD_RARITY_STYLES.get(card_def.rarity or "", "card.name"))
    if is_upgraded_card(card_def):
        rendered.stylize("card.upgraded")
    return rendered


def summarize_effect(effect: Mapping[str, object], *, detailed_status_cards: bool = False) -> str:
    effect_type = effect.get("type")
    if effect.get("move") == "divider":
        return "6 段攻击（每段伤害随生命变化）"
    if effect_type == "damage_all_enemies_x_times":
        return f"X 次对所有敌人各造成 {int(effect.get('amount', 0))} 伤害"
    if effect_type == "damage":
        return f"造成 {int(effect.get('amount', 0))} 伤害"
    if effect_type == "block":
        return f"获得 {int(effect.get('amount', 0))} 格挡"
    if effect_type == "heal":
        return f"回复 {int(effect.get('amount', 0))} 点生命"
    if effect_type == "lose_hp":
        return f"失去 {int(effect.get('amount', 0))} 点生命"
    if effect_type == "draw":
        return f"抽 {int(effect.get('amount', 0))} 张牌"
    if effect_type == "gain_energy":
        return f"获得 {int(effect.get('amount', 0))} 点能量"
    if effect_type == "add_power":
        power_id = effect.get("power_id")
        amount = int(effect.get("amount", 0))
        if power_id == "inflame":
            return f"获得 {amount} 层力量"
        if power_id == "metallicize":
            return f"回合结束时获得 {amount} 格挡"
        if power_id == "combust":
            self_damage = int(effect.get("self_damage", 1))
            return f"回合结束时对所有敌人造成 {amount} 伤害，自己失去 {self_damage} 点生命"
        return f"获得持续效果 {power_id} {amount}"
    if effect_type == "strength":
        return f"获得 {int(effect.get('amount', 0))} 力量"
    if effect_type == "vulnerable":
        return f"施加 {int(effect.get('stacks', 0))} 易伤"
    if effect_type == "weak":
        return f"施加 {int(effect.get('stacks', 0))} 虚弱"
    if effect_type == "exhaust_random_hand":
        return f"随机消耗 {int(effect.get('count', 1))} 张手牌"
    if effect_type == "exhaust_target_card":
        return "消耗 1 张手牌"
    if effect_type == "upgrade_target_card":
        return "升级 1 张手牌"
    if effect_type == "upgrade_all_hand":
        return "升级所有手牌"
    if effect_type == "create_card_copy":
        zone_labels = {
            "hand": "手牌",
            "draw_pile": "抽牌堆",
            "discard_pile": "弃牌堆",
            "exhaust_pile": "消耗堆",
        }
        zone = zone_labels.get(str(effect.get("zone")), str(effect.get("zone")))
        return f"复制一张卡牌放入{zone}"
    if effect_type == "add_card_to_discard":
        count = int(effect.get("count", 1))
        raw_card_id = effect.get("card_id")
        card_name = card_label(raw_card_id) if isinstance(raw_card_id, str) else "牌"
        summary = f"向弃牌堆加入 {count} 张{card_name}"
        if detailed_status_cards and isinstance(raw_card_id, str):
            rule_text = special_card_rule_text(raw_card_id)
            if rule_text is not None:
                summary += f"（{rule_text}）"
        return summary
    if isinstance(effect_type, str):
        return effect_type
    return "-"


def summarize_card_effects(
    effects: Sequence[Mapping[str, object]],
    *,
    detailed_status_cards: bool = False,
) -> str:
    summaries = [summarize_effect(effect, detailed_status_cards=detailed_status_cards) for effect in effects]
    return " / ".join(summary for summary in summaries if summary) or "-"


def summarize_card_definition(card_def: CardDef) -> str:
    summary = summarize_card_effects(card_def.effects)
    if summary != "-":
        return summary
    special_rule = special_card_rule_text(card_def.id)
    if special_rule is not None:
        return special_rule
    return "无效果"


def summarize_relic_effect(effect: Mapping[str, object]) -> str:
    effect_type = effect.get("type")
    if effect_type == "event_gold_bonus":
        return f"事件金币奖励 +{int(effect.get('percent', 0))}%"
    return summarize_effect(effect)


def summarize_relic_effects(effects: Sequence[Mapping[str, object]]) -> str:
    summaries = [summarize_relic_effect(effect) for effect in effects]
    return " / ".join(summary for summary in summaries if summary) or "-"


def summarize_enemy_move(move: Mapping[str, object]) -> str:
    effects = move.get("effects")
    if isinstance(effects, Sequence) and not isinstance(effects, (str, bytes)):
        filtered_effects = [effect for effect in effects if isinstance(effect, Mapping)]
        if filtered_effects:
            return summarize_card_effects(filtered_effects)
    return summarize_effect(move)


def summarize_trigger_hooks(trigger_hooks: Sequence[str]) -> str:
    hook_labels = {
        "on_combat_end": "战斗结束后",
    }
    labels = [hook_labels.get(hook, hook) for hook in trigger_hooks]
    return " / ".join(labels) if labels else "-"


def format_card_cost(cost: int) -> str:
    if cost == -1:
        return "X"
    if cost < 0:
        return "无法打出"
    return str(cost)


def preview_enemy_intent(enemy_def: EnemyDef) -> str:
    for move in enemy_def.move_table:
        if not isinstance(move, Mapping):
            continue
        return summarize_enemy_move(move)
    return "-"


def summarize_enemy_move_preview(move: Mapping[str, object] | None) -> str:
    if move is None:
        return "-"
    if move.get("move") == "sleep":
        sleep_turns = int(move.get("sleep_turns", 0))
        return f"沉睡 {sleep_turns} 回合"
    effects = move.get("effects")
    if isinstance(effects, Sequence) and not isinstance(effects, (str, bytes)):
        return summarize_card_effects(
            [effect for effect in effects if isinstance(effect, Mapping)],
            detailed_status_cards=True,
        )
    return summarize_effect(move, detailed_status_cards=True)
