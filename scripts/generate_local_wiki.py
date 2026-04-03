from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from slay_the_spire.adapters.presentation.widgets import (  # noqa: E402
    format_card_cost,
    special_card_rule_text,
    summarize_effect,
    summarize_enemy_move_preview,
    summarize_relic_effects,
)
from slay_the_spire.content.provider import StarterContentProvider  # noqa: E402
from slay_the_spire.content.registries import CardDef, EnemyDef, EventDef, RelicDef  # noqa: E402

RARITY_ORDER = {
    "basic": 0,
    "common": 1,
    "uncommon": 2,
    "rare": 3,
    "curse": 4,
    "special": 5,
}

CARD_TYPE_LABELS = {
    "attack": "攻击",
    "skill": "技能",
    "power": "能力",
    "status": "状态",
    "curse": "诅咒",
}

CARD_SECTION_TITLES = {
    "basic": "基础牌",
    "common": "普通牌",
    "uncommon": "罕见牌",
    "rare": "稀有牌",
    "curse": "诅咒牌",
    "special": "状态牌 / 特殊牌",
}

ACQUISITION_LABELS = {
    "starter": "开局自带",
    "combat_reward": "战斗奖励",
    "shop": "商店",
    "event": "事件",
    "generated": "生成物",
    "status": "状态牌",
    "curse": "诅咒来源",
}

PLAY_CONDITION_LABELS = {
    "all_attacks_in_hand": "只有当手牌中全部都是攻击牌时才能打出",
}

COST_REDUCER_LABELS = {
    "times_hit_this_combat": "本场战斗中每次受到攻击伤害后，费用减少 1",
}

HOOK_LABELS = {
    "on_combat_start": "战斗开始时",
    "on_combat_end": "战斗结束后",
}

DISABLED_ACTION_LABELS = {
    "gain_gold": "获得金币",
    "rest_heal": "休息回复",
    "smith": "锻造",
}

RELIC_RARITY_ORDER = {
    "starter": 0,
    "common": 1,
    "uncommon": 2,
    "rare": 3,
    "shop": 4,
    "boss": 5,
    "event": 6,
    "special": 7,
}

RELIC_SECTION_TITLES = {
    "starter": "起始遗物",
    "common": "普通遗物",
    "uncommon": "非普通遗物",
    "rare": "稀有遗物",
    "shop": "商店遗物",
    "boss": "Boss 遗物",
    "event": "事件遗物",
    "special": "特殊遗物",
}

RELIC_RARITY_LABELS = {
    "starter": "起始",
    "common": "普通",
    "uncommon": "非普通",
    "rare": "稀有",
    "shop": "商店",
    "boss": "Boss",
    "event": "事件",
    "special": "特殊",
}

RELIC_IMPLEMENTATION_STATUS_LABELS = {
    "implemented": "implemented",
    "placeholder": "placeholder",
}

ENEMY_POOL_SECTIONS = [
    ("act1_basic", "Act 1 小怪", "enemies-act1-basic"),
    ("act1_elites", "Act 1 精英", "enemies-act1-elites"),
    ("act1_bosses", "Act 1 Boss", "enemies-act1-bosses"),
    ("act2_basic", "Act 2 小怪", "enemies-act2-basic"),
    ("act2_elites", "Act 2 精英", "enemies-act2-elites"),
    ("act2_bosses", "Act 2 Boss", "enemies-act2-bosses"),
]

EVENT_POOL_SECTIONS = [
    ("act1_events", "Act 1 事件", "events-act1"),
    ("act2_events", "Act 2 事件", "events-act2"),
]

POWER_SUMMARY_OVERRIDES = {
    "flex_power": "本回合结束时失去等量力量",
    "berserk": "获得持续效果：狂暴",
    "corruption": "获得持续效果：腐化",
}

INTENT_POLICY_LABELS = {
    "weighted_random": "加权随机",
    "scripted": "脚本顺序",
    "cycle": "循环顺序",
}


def _base_card_sort_key(card: CardDef) -> tuple[str, int, str]:
    suffix = 1 if card.id.endswith("_plus") else 0
    normalized_id = card.id.removesuffix("_plus")
    return (normalized_id, suffix, card.id)


def _card_effect_summary(card: CardDef, provider: StarterContentProvider) -> str:
    if not card.effects:
        return special_card_rule_text(card.id) or "无效果"
    parts: list[str] = []
    for effect in card.effects:
        effect_type = effect.get("type")
        if effect_type == "create_card_copy":
            card_id = effect.get("card_id")
            card_name = str(card_id)
            if isinstance(card_id, str):
                try:
                    card_name = provider.cards().get(card_id).name
                except KeyError:
                    card_name = card_id
            zone = {
                "hand": "手牌",
                "draw_pile": "抽牌堆",
                "discard_pile": "弃牌堆",
                "exhaust_pile": "消耗堆",
            }.get(str(effect.get("zone")), str(effect.get("zone")))
            parts.append(f"复制一张 {card_name} 放入{zone}")
            continue
        if effect_type == "add_card_to_discard":
            count = int(effect.get("count", 1))
            card_id = effect.get("card_id")
            try:
                name = provider.cards().get(str(card_id)).name
            except KeyError:
                name = str(card_id)
            text = f"向弃牌堆加入 {count} 张 {name}"
            if isinstance(card_id, str):
                rule_text = special_card_rule_text(card_id)
                if rule_text is not None:
                    text += f"（{rule_text}）"
            parts.append(text)
            continue
        if effect_type == "add_card_to_draw_pile":
            count = int(effect.get("count", 1))
            card_id = effect.get("card_id")
            try:
                name = provider.cards().get(str(card_id)).name
            except KeyError:
                name = str(card_id)
            parts.append(f"向牌堆加入 {count} 张 {name}")
            continue
        if effect_type == "add_power":
            power_id = str(effect.get("power_id", ""))
            if power_id in POWER_SUMMARY_OVERRIDES:
                parts.append(POWER_SUMMARY_OVERRIDES[power_id])
                continue
        parts.append(summarize_effect(effect, detailed_status_cards=True))
    return "；".join(part for part in parts if part) or "无效果"


def _card_rules(card: CardDef) -> str:
    rules: list[str] = []
    if not card.playable:
        rules.append("无法打出")
    if card.ethereal:
        rules.append("Ethereal：回合结束时若仍在手牌中，则消耗")
    if card.innate:
        rules.append("Innate：起手必定在手牌中")
    if card.exhausts:
        rules.append("打出后消耗")
    if card.play_condition:
        rules.append(
            PLAY_CONDITION_LABELS.get(
                card.play_condition, f"出牌条件：{card.play_condition}"
            )
        )
    if card.cost_reducer:
        rules.append(
            COST_REDUCER_LABELS.get(card.cost_reducer, f"费用规则：{card.cost_reducer}")
        )
    for effect in card.on_exhaust_effects:
        rules.append(
            f"被消耗时：{summarize_effect(effect, detailed_status_cards=True)}"
        )
    return "；".join(rules) if rules else "-"


def _card_acquisition_labels(card: CardDef) -> str:
    if not card.acquisition_tags:
        return "-"
    labels = [ACQUISITION_LABELS.get(tag, tag) for tag in card.acquisition_tags]
    return " / ".join(labels)


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        f"| {' | '.join(headers)} |",
        f"| {' | '.join('---' for _ in headers)} |",
    ]
    for row in rows:
        escaped = [cell.replace("\n", "<br>").replace("|", "\\|") for cell in row]
        lines.append(f"| {' | '.join(escaped)} |")
    return "\n".join(lines)


def _render_card_section(
    rarity: str,
    cards: list[CardDef],
    provider: StarterContentProvider,
) -> str:
    section_cards = sorted(cards, key=_base_card_sort_key)
    rows = [
        [
            card.name,
            card.id,
            format_card_cost(card.cost),
            CARD_TYPE_LABELS.get(card.card_type, card.card_type),
            _card_effect_summary(card, provider),
            _card_rules(card),
            _card_acquisition_labels(card),
            provider.cards().get(card.upgrades_to).name if card.upgrades_to else "-",
        ]
        for card in section_cards
    ]
    table = _markdown_table(
        ["名称", "ID", "费用", "类型", "效果", "额外规则", "获得途径", "升级为"],
        rows,
    )
    return f"## {CARD_SECTION_TITLES.get(rarity, rarity)}\n\n{table}"


def _relic_rules(relic: RelicDef, provider: StarterContentProvider) -> str:
    rules: list[str] = []
    if relic.summary:
        rules.append(f"摘要：{relic.summary}")
    if relic.description:
        rules.append(f"描述：{relic.description}")
    if relic.replaces_relic_id:
        try:
            replaced = provider.relics().get(relic.replaces_relic_id).name
        except KeyError:
            replaced = relic.replaces_relic_id
        rules.append(f"替换：{replaced}")
    if relic.disabled_actions:
        actions = [
            DISABLED_ACTION_LABELS.get(action, action)
            for action in relic.disabled_actions
        ]
        rules.append(f"禁用操作：{' / '.join(actions)}")
    if relic.blocks_gold_gain:
        rules.append("金币规则：无法获得金币")
    if relic.trigger_hooks:
        hooks = [HOOK_LABELS.get(hook, hook) for hook in relic.trigger_hooks]
        rules.append(f"触发时机：{' / '.join(hooks)}")
    return "；".join(rules) if rules else "-"


def _relic_pool_labels(relic: RelicDef) -> str:
    return " / ".join(relic.pools) if relic.pools else "-"


def _relic_status_label(relic: RelicDef) -> str:
    return RELIC_IMPLEMENTATION_STATUS_LABELS.get(
        relic.implementation_status,
        relic.implementation_status or "-",
    )


def _relic_rarity_label(relic: RelicDef) -> str:
    return RELIC_RARITY_LABELS.get(relic.rarity, relic.rarity or "-")


def _render_relic_section(
    title: str,
    relics: list[RelicDef],
    provider: StarterContentProvider,
) -> str:
    rows = [
        [
            relic.name,
            relic.id,
            _relic_rarity_label(relic),
            _relic_pool_labels(relic),
            _relic_status_label(relic),
            summarize_relic_effects(relic.passive_effects),
            _relic_rules(relic, provider),
        ]
        for relic in sorted(relics, key=lambda item: item.name)
    ]
    table = _markdown_table(
        ["名称", "ID", "稀有度", "所属池", "实现状态", "效果", "补充说明"], rows
    )
    return f"## {title}\n\n{table}"


def _load_pool_ids(
    content_root: Path, category: str, pool_id: str, key: str
) -> list[str]:
    path = content_root / category / f"{pool_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get(key, [])
    result: list[str] = []
    for record in records:
        if isinstance(record, dict) and record.get("id") is not None:
            result.append(str(record.get("id")))
    return result


def _enemy_move_summary(enemy: EnemyDef) -> str:
    summaries: list[str] = []
    for move in enemy.move_table:
        move_id = str(move.get("move", "unknown"))
        summary = summarize_enemy_move_preview(move)
        suffix = "（仅一次）" if move.get("once") else ""
        summaries.append(f"{move_id}{suffix}：{summary}")
    return "<br>".join(summaries) if summaries else "-"


def _render_enemy_section(title: str, anchor: str, enemies: list[EnemyDef]) -> str:
    rows = [
        [
            enemy.name,
            enemy.id,
            str(enemy.hp),
            INTENT_POLICY_LABELS.get(enemy.intent_policy, enemy.intent_policy),
            _enemy_move_summary(enemy),
        ]
        for enemy in sorted(enemies, key=lambda item: item.name)
    ]
    table = _markdown_table(["名称", "ID", "生命", "意图规则", "招式与效果"], rows)
    return f'<a id="{anchor}"></a>\n## {title}\n\n{table}'


def _event_effect_summary(
    effect: dict[str, object], provider: StarterContentProvider
) -> str:
    effect_type = str(effect.get("type", ""))
    if effect_type == "nothing":
        return "无额外效果"
    if effect_type == "upgrade_card_selection":
        return "选择 1 张牌升级"
    if effect_type == "remove_card_selection":
        gold_cost = int(effect.get("gold_cost", 0))
        if gold_cost > 0:
            return f"支付 {gold_cost} 金币，移除 1 张牌"
        return "移除 1 张牌"
    if effect_type == "gain_gold_and_lose_hp":
        return f"获得 {int(effect.get('gain_gold', 0))} 金币，失去 {int(effect.get('lose_hp', 0))} 点生命"
    if effect_type == "lose_gold":
        return f"失去 {int(effect.get('lose_gold', 0))} 金币"
    if effect_type == "increase_max_hp":
        return f"最大生命 +{int(effect.get('amount', 0))}"
    if effect_type == "heal":
        return f"支付 {int(effect.get('gold_cost', 0))} 金币，恢复 {int(effect.get('heal_amount', 0))} 点生命"
    if effect_type == "heal_percent":
        return f"恢复最大生命的 {int(effect.get('heal_percent', 0))}%"
    if effect_type == "gain_gold":
        return f"获得 {int(effect.get('gain_gold', 0))} 金币"
    if effect_type == "gain_relic_and_lose_hp":
        relic_id = str(effect.get("relic_id", ""))
        relic_name = provider.relics().get(relic_id).name if relic_id else relic_id
        return f"获得遗物 {relic_name}，失去 {int(effect.get('lose_hp', 0))} 点生命"
    if effect_type == "gain_gold_and_add_curse":
        card_id = str(effect.get("curse_id") or effect.get("card_id") or "")
        card_name = provider.cards().get(card_id).name if card_id else card_id
        return f"获得 {int(effect.get('gain_gold', 0))} 金币，加入诅咒 {card_name}"
    if effect_type == "gain_relic_and_reduce_max_hp":
        relic_id = str(effect.get("relic_id", ""))
        relic_name = provider.relics().get(relic_id).name if relic_id else relic_id
        hp_loss = int(effect.get("lose_max_hp") or effect.get("max_hp_loss") or 0)
        return f"获得遗物 {relic_name}，最大生命减少 {hp_loss}"
    if effect_type == "gain_relic_and_add_curse":
        relic_id = str(effect.get("relic_id", ""))
        relic_name = provider.relics().get(relic_id).name if relic_id else relic_id
        card_id = str(effect.get("curse_id") or effect.get("card_id") or "")
        card_name = provider.cards().get(card_id).name if card_id else card_id
        return f"获得遗物 {relic_name}，加入诅咒 {card_name}"
    return effect_type or "-"


def _event_choice_summary(event: EventDef) -> str:
    return (
        "<br>".join(
            f"{choice.get('id', '-')}: {choice.get('label', '-')}"
            for choice in event.choices
        )
        or "-"
    )


def _event_outcome_summary(event: EventDef, provider: StarterContentProvider) -> str:
    choice_labels = {
        str(choice.get("id")): str(choice.get("label", "-")) for choice in event.choices
    }
    lines: list[str] = []
    for outcome in event.outcomes:
        choice_id = str(outcome.get("choice_id", "-"))
        label = choice_labels.get(choice_id, choice_id)
        result_text = str(outcome.get("result_text", "-"))
        effect = outcome.get("effect", {})
        effect_summary = "-"
        if isinstance(effect, dict):
            effect_summary = _event_effect_summary(effect, provider)
        lines.append(f"{label} -> {result_text}（{effect_summary}）")
    return "<br>".join(lines) if lines else "-"


def _render_event_section(
    title: str,
    anchor: str,
    events: list[EventDef],
    provider: StarterContentProvider,
) -> str:
    rows = [
        [
            event.id,
            event.text,
            _event_choice_summary(event),
            _event_outcome_summary(event, provider),
        ]
        for event in sorted(events, key=lambda item: item.id)
    ]
    table = _markdown_table(["ID", "事件文本", "可选项", "结果与效果"], rows)
    return f'<a id="{anchor}"></a>\n## {title}\n\n{table}'


def build_markdown(content_root: Path) -> str:
    provider = StarterContentProvider(content_root)
    all_cards = list(provider.cards().all())
    all_relics = list(provider.relics().all())
    all_enemies = list(provider.enemies().all())
    all_events = list(provider.events().all())

    cards_by_rarity: dict[str, list[CardDef]] = {key: [] for key in CARD_SECTION_TITLES}
    for card in sorted(
        all_cards,
        key=lambda item: (
            RARITY_ORDER.get(item.rarity or "", 99),
            _base_card_sort_key(item),
        ),
    ):
        cards_by_rarity.setdefault(card.rarity or "unknown", []).append(card)

    relics_by_rarity: dict[str, list[RelicDef]] = {}
    for relic in sorted(
        all_relics,
        key=lambda item: (
            RELIC_RARITY_ORDER.get(item.rarity or "", 99),
            item.name,
            item.id,
        ),
    ):
        relics_by_rarity.setdefault(relic.rarity or "unknown", []).append(relic)

    relic_sections = [
        _render_relic_section(title, relics_by_rarity.get(rarity, []), provider)
        for rarity, title in RELIC_SECTION_TITLES.items()
        if relics_by_rarity.get(rarity)
    ]

    card_sections = [
        _render_card_section(rarity, cards_by_rarity.get(rarity, []), provider)
        for rarity in CARD_SECTION_TITLES
        if cards_by_rarity.get(rarity)
    ]

    enemy_sections = []
    for pool_id, title, anchor in ENEMY_POOL_SECTIONS:
        pool_ids = _load_pool_ids(content_root, "enemies", pool_id, "enemies")
        enemies = [enemy for enemy in all_enemies if enemy.id in pool_ids]
        enemy_sections.append(_render_enemy_section(title, anchor, enemies))

    event_sections = []
    for pool_id, title, anchor in EVENT_POOL_SECTIONS:
        pool_ids = _load_pool_ids(content_root, "events", pool_id, "events")
        events = [event for event in all_events if event.id in pool_ids]
        event_sections.append(_render_event_section(title, anchor, events, provider))

    lines = [
        "# 已实现内容 Wiki",
        "",
        "这份文档基于仓库根目录 `content/` 当前内容生成，用来快速查阅项目里已经落地的卡牌、遗物、敌人和事件。",
        "",
        "## 概览",
        "",
        f"- 卡牌总数：{len(all_cards)}",
        f"- 遗物总数：{len(all_relics)}",
        f"- 敌人总数：{len(all_enemies)}",
        f"- 事件总数：{len(all_events)}",
        "- 卡牌覆盖：当前实现的 Ironclad 卡池、诅咒牌、状态牌",
        "- 内容真源：`content/cards/*.json`、`content/relics/*.json`、`content/enemies/*.json`、`content/events/*.json`",
        "- 刷新命令：`uv run python scripts/generate_local_wiki.py`",
        "",
        "## 目录",
        "",
        "- [遗物](#遗物)",
        "- [卡牌](#卡牌)",
        "- [敌人](#敌人)",
        "- [Act 1 小怪](#enemies-act1-basic)",
        "- [Act 1 精英](#enemies-act1-elites)",
        "- [Act 1 Boss](#enemies-act1-bosses)",
        "- [Act 2 小怪](#enemies-act2-basic)",
        "- [Act 2 精英](#enemies-act2-elites)",
        "- [Act 2 Boss](#enemies-act2-bosses)",
        "- [事件](#事件)",
        "- [Act 1 事件](#events-act1)",
        "- [Act 2 事件](#events-act2)",
        "",
        "# 遗物",
        "",
        *relic_sections,
        "",
        "# 卡牌",
        "",
        *card_sections,
        "",
        "# 敌人",
        "",
        *enemy_sections,
        "",
        "# 事件",
        "",
        *event_sections,
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成本地内容 wiki 文档。")
    parser.add_argument(
        "--content-root",
        type=Path,
        default=REPO_ROOT / "content",
        help="内容根目录，默认读取仓库根目录 content/。",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs" / "local_wiki" / "cards_and_relics.md",
        help="Markdown 输出路径。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    markdown = build_markdown(args.content_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")


if __name__ == "__main__":
    main()
