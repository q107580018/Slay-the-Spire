from __future__ import annotations

from collections.abc import Mapping, Sequence

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.terminal.theme import HP_BAR_WIDTH, PANEL_BOX
from slay_the_spire.content.registries import EnemyDef
from slay_the_spire.domain.models.statuses import StatusState

_STATUS_LABELS: dict[str, tuple[str, str]] = {
    "vulnerable": ("易伤", "status.debuff"),
    "weak": ("虚弱", "status.debuff"),
    "strength": ("力量", "status.buff"),
    "dexterity": ("敏捷", "status.buff"),
    "artifact": ("人工制品", "status.buff"),
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


def summarize_effect(effect: Mapping[str, object]) -> str:
    effect_type = effect.get("type")
    if effect.get("move") == "divider":
        return "6 段攻击（每段伤害随生命变化）"
    if effect_type == "damage":
        return f"造成 {int(effect.get('amount', 0))} 伤害"
    if effect_type == "block":
        return f"获得 {int(effect.get('amount', 0))} 格挡"
    if effect_type == "heal":
        return f"回复 {int(effect.get('amount', 0))} 点生命"
    if effect_type == "draw":
        return f"抽 {int(effect.get('amount', 0))} 张牌"
    if effect_type == "vulnerable":
        return f"施加 {int(effect.get('stacks', 0))} 易伤"
    if effect_type == "weak":
        return f"施加 {int(effect.get('stacks', 0))} 虚弱"
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
        return f"向弃牌堆加入 {int(effect.get('count', 1))} 张牌"
    if isinstance(effect_type, str):
        return effect_type
    return "-"


def summarize_card_effects(effects: Sequence[Mapping[str, object]]) -> str:
    summaries = [summarize_effect(effect) for effect in effects]
    return " / ".join(summary for summary in summaries if summary) or "-"


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
    if cost < 0:
        return "无法打出"
    return str(cost)


def preview_enemy_intent(enemy_def: EnemyDef) -> str:
    for move in enemy_def.move_table:
        if not isinstance(move, Mapping):
            continue
        return summarize_enemy_move(move)
    return "-"
