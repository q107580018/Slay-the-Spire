from __future__ import annotations

from collections.abc import Mapping, Sequence

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.presentation.theme import HP_BAR_WIDTH, PANEL_BOX
from slay_the_spire.content.registries import CardDef, EnemyDef
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
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
    "wound": "伤口",
    "dazed": "迷糊",
    "injury": "伤口",
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
    "combust": "自燃",
    "flame_barrier": "火焰屏障",
    "battle_trance": "战斗专注",
    "demon_form": "恶魔形态",
    "barricade": "壁垒",
    "brutality": "残暴",
    "evolve": "进化",
    "fire_breathing": "火焰吐息",
    "dark_embrace": "黑暗之拥",
    "rage": "狂怒",
    "rupture": "撕裂",
    "feel_no_pain": "无惧疼痛",
    "juggernaut": "势不可当",
    "double_tap": "双发",
    "spot_weakness": "观察弱点",
    "berserk": "狂暴",
    "flex_power": "活动肌肉",
    "corruption": "腐化",
}

_POTION_TARGET_LABELS: dict[str, str] = {
    "self": "自己",
    "enemy": "敌人",
    "any": "任意目标",
}

_POTION_TARGET_SHORT_LABELS: dict[str, str] = {
    "self": "对己",
    "enemy": "对敌",
    "any": "任意",
}

_POTION_TIMING_LABELS: dict[str, str] = {
    "in_combat": "战斗中",
    "out_of_combat": "战斗外",
    "any": "任意时机",
}


def _is_strike_like_card(card_instance_id: str) -> bool:
    try:
        card_id = card_id_from_instance_id(card_instance_id)
    except (TypeError, ValueError):
        return False
    return "strike" in card_id


def _count_strike_cards(combat_state: CombatState) -> int:
    return sum(
        1
        for other_card_instance_id in [
            *combat_state.hand,
            *combat_state.draw_pile,
            *combat_state.discard_pile,
            *combat_state.exhaust_pile,
        ]
        if _is_strike_like_card(other_card_instance_id)
    )


def hp_style_for_ratio(ratio: float) -> str:
    if ratio <= 0.25:
        return "hp.low"
    if ratio <= 0.6:
        return "hp.medium"
    return "hp.high"


def render_hp_bar(
    current: int, maximum: int, *, width: int = HP_BAR_WIDTH, show_values: bool = True
) -> Text:
    ratio = 0 if maximum <= 0 else max(0, min(current / maximum, 1))
    filled = round(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    if show_values:
        return Text.assemble(f"{current}/{maximum} ", (bar, hp_style_for_ratio(ratio)))
    return Text(bar, style=hp_style_for_ratio(ratio))


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
    return Panel(
        body,
        title=title or None,
        box=PANEL_BOX,
        border_style="menu.border",
        expand=False,
    )


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


def potion_target_label(target: str) -> str:
    return _POTION_TARGET_LABELS.get(target, target)


def potion_target_short_label(target: str) -> str:
    return _POTION_TARGET_SHORT_LABELS.get(target, target)


def potion_timing_label(timing: str) -> str:
    return _POTION_TIMING_LABELS.get(timing, timing)


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
    rendered.append(
        card_def.name, style=_CARD_RARITY_STYLES.get(card_def.rarity or "", "card.name")
    )
    if is_upgraded_card(card_def):
        rendered.stylize("card.upgraded")
    return rendered


def _signed_status_change(amount: int, label: str) -> str:
    if amount < 0:
        return f"失去 {abs(amount)} {label}"
    return f"获得 {amount} {label}"


def summarize_effect(
    effect: Mapping[str, object], *, detailed_status_cards: bool = False
) -> str:
    effect_type = effect.get("type")
    if effect.get("move") == "divider":
        return "6 段攻击（每段伤害随生命变化）"
    if effect_type == "damage_all_enemies":
        return f"对所有敌人造成 {int(effect.get('amount', 0))} 伤害"
    if effect_type == "damage_all_enemies_x_times":
        return f"按本次消耗的能量值，对所有敌人各造成 {int(effect.get('amount', 0))} 伤害"
    if effect_type == "damage_equal_to_block":
        return "造成等同于当前格挡的伤害"
    if effect_type == "double_strength":
        return "使力量翻倍"
    if effect_type == "put_top_of_deck_from_discard":
        return "将弃牌堆中的 1 张牌放到牌堆顶"
    if effect_type == "put_top_of_deck_from_hand":
        return "将 1 张手牌放到牌堆顶"
    if effect_type == "copy_card_to_hand":
        return "复制 1 张手中的攻击牌或能力牌"
    if effect_type == "select_from_exhaust_to_hand":
        return "从消耗堆中取回 1 张牌"
    if effect_type == "add_random_attack_zero_cost_to_hand":
        return "获得 1 张费用为 0 的随机攻击牌"
    if effect_type == "damage_lifesteal_all_enemies":
        amount = int(effect.get("amount", 0))
        return f"对所有敌人造成 {amount} 伤害，回复等量生命"
    if effect_type == "spot_weakness_strength":
        amount = int(effect.get("amount", 0))
        return f"若敌人意图进行攻击，获得 {amount} 层力量"
    if effect_type == "damage_on_kill_gain_max_hp":
        amount = int(effect.get("amount", 0))
        hp_gain = int(effect.get("hp_gain", 0))
        return f"造成 {amount} 伤害，击杀则永久增加 {hp_gain} 最大生命"
    if effect_type == "rampage_damage":
        amount = int(effect.get("amount", 0))
        increment = int(effect.get("increment", 5))
        return f"造成 {amount} 伤害（每次使用后永久增加 {increment} 伤害）"
    if effect_type == "damage_with_strength_multiplier":
        base = int(effect.get("base", 0))
        multiplier = int(effect.get("multiplier", 1))
        return f"造成 {base} + 力量 × {multiplier} 伤害"
    if effect_type == "damage_per_strike_in_deck":
        base = int(effect.get("base", 0))
        bonus_per_strike = int(
            effect.get("bonus_per_strike", effect.get("amount_per_strike", 0))
        )
        resolved_amount = effect.get("resolved_amount")
        strike_count = effect.get("strike_count")
        if isinstance(resolved_amount, int) and isinstance(strike_count, int):
            return (
                f"造成 {resolved_amount} 伤害"
                f"（你每有一张名字中有“打击”的牌，伤害+{bonus_per_strike}；"
                f"当前共 {strike_count} 张）"
            )
        return f"造成 {base} 伤害。你每有一张名字中有“打击”的牌，伤害+{bonus_per_strike}"
    if effect_type == "dropkick_effect":
        amount = int(effect.get("amount", 0))
        return f"造成 {amount} 伤害；若敌人处于易伤状态，获得 1 点能量并抽 1 张牌"
    if effect_type == "exhaust_all_non_attacks_gain_block":
        amount_per = int(effect.get("amount_per_card", 0))
        return f"消耗手中所有非攻击牌，每张获得 {amount_per} 格挡"
    if effect_type == "exhaust_all_non_attacks_in_hand":
        return "消耗手中所有非攻击牌"
    if effect_type == "exhaust_all_in_hand":
        return "消耗手中所有牌"
    if effect_type == "exhaust_all_in_hand_damage":
        amount_per = int(effect.get("amount_per_card", 0))
        return f"消耗手中所有牌。每张被消耗的牌造成 {amount_per} 伤害"
    if effect_type == "play_top_of_deck":
        return "打出牌堆顶的牌"
    if effect_type == "add_card_to_draw_pile":
        count = int(effect.get("count", 1))
        card_id = effect.get("card_id", "")
        name = card_label(card_id) if isinstance(card_id, str) else "牌"
        return f"向牌堆加入 {count} 张{name}"
    if effect_type == "weak_all_enemies":
        stacks = int(effect.get("stacks", 0))
        return f"对所有敌人施加 {stacks} 虚弱"
    if effect_type == "add_cards_to_hand":
        count = int(effect.get("count", 1))
        return f"获得 {count} 张牌到手牌"
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
    if effect_type == "double_block":
        return "格挡翻倍"
    if effect_type == "add_power":
        power_id = effect.get("power_id")
        amount = int(effect.get("amount", 0))
        if power_id == "inflame":
            return f"获得 {amount} 层力量"
        if power_id == "metallicize":
            return f"回合结束时获得 {amount} 格挡"
        if power_id == "combust":
            self_damage = int(effect.get("self_damage", 1))
            return (
                f"回合结束时对所有敌人造成 {amount} 伤害，自己失去 {self_damage} 点生命"
            )
        if power_id == "flame_barrier":
            return f"本回合内每次被敌人攻击时反弹 {amount} 伤害"
        if power_id == "battle_trance":
            return "本回合内不能再抽牌"
        if power_id == "demon_form":
            return f"每回合开始时获得 {amount} 层力量"
        if power_id == "barricade":
            return "你的格挡不会在回合开始时失去"
        if power_id == "double_tap":
            return "本回合下一张攻击牌额外触发一次"
        if power_id == "dark_embrace":
            return f"每当有牌被消耗时，抽 {amount} 张牌"
        if power_id == "rage":
            return f"每次打出攻击牌时获得 {amount} 格挡"
        if power_id == "rupture":
            return f"以牌的效果失去生命时，获得 {amount} 层力量"
        if power_id == "feel_no_pain":
            return f"每当有牌被消耗时，获得 {amount} 格挡"
        if power_id == "juggernaut":
            return f"获得格挡时对随机敌人造成 {amount} 伤害"
        if power_id == "brutality":
            return f"每回合开始时失去 {amount} 生命并抽 {amount} 张牌"
        if power_id == "spot_weakness":
            return f"若敌人意图进行攻击，获得 {amount} 层力量"
        if power_id == "evolve":
            return f"每次抽到状态牌时，抽 {amount} 张牌"
        if power_id == "fire_breathing":
            return f"每次抽到状态牌或诅咒牌时，对所有敌人造成 {amount} 伤害"
        if power_id == "corruption":
            return "所有技能牌耗能变为0。所有技能牌在被打出时被消耗。"
        if power_id == "berserk":
            return f"每回合开始时获得 {amount} 点能量"
        if power_id == "flex_power":
            return f"本回合结束时失去 {amount} 层力量"
        if isinstance(power_id, str):
            power_name = active_power_label(power_id)
            if power_name != power_id:
                return f"获得持续效果：{power_name} {amount}"
        return f"获得持续效果 {amount}"
    if effect_type == "strength":
        return _signed_status_change(int(effect.get("amount", 0)), "力量")
    if effect_type == "dexterity":
        return _signed_status_change(int(effect.get("amount", 0)), "敏捷")
    if effect_type == "vulnerable":
        stacks = int(effect.get("stacks", 0))
        if effect.get("target_instance_id") == "self":
            return f"获得 {stacks} 层易伤"
        return f"施加 {stacks} 易伤"
    if effect_type == "vulnerable_all_enemies":
        return f"对所有敌人施加 {int(effect.get('stacks', 0))} 易伤"
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
        return "未知效果"
    return "-"


def summarize_card_effects(
    effects: Sequence[Mapping[str, object]],
    *,
    detailed_status_cards: bool = False,
) -> str:
    summaries = [
        summarize_effect(effect, detailed_status_cards=detailed_status_cards)
        for effect in effects
    ]
    return " / ".join(summary for summary in summaries if summary) or "-"


def _resolve_effect_for_card_instance(
    effect: Mapping[str, object],
    *,
    card_instance_id: str,
    combat_state: CombatState | None,
) -> Mapping[str, object]:
    if effect.get("type") == "rampage_damage":
        play_count = 0
        if combat_state is not None:
            play_count = int(combat_state.card_play_data.get(card_instance_id, 0))
        base_amount = int(effect.get("amount", 0))
        increment = int(effect.get("increment", 5))
        resolved = dict(effect)
        resolved["amount"] = base_amount + increment * play_count
        return resolved
    if effect.get("type") == "damage_per_strike_in_deck" and combat_state is not None:
        base_amount = int(effect.get("base", 0))
        bonus_per_strike = int(
            effect.get("bonus_per_strike", effect.get("amount_per_strike", 0))
        )
        strike_count = _count_strike_cards(combat_state)
        resolved = dict(effect)
        resolved["resolved_amount"] = base_amount + bonus_per_strike * strike_count
        resolved["strike_count"] = strike_count
        return resolved
    return effect


def summarize_card_effects_for_instance(
    effects: Sequence[Mapping[str, object]],
    *,
    card_instance_id: str,
    combat_state: CombatState | None = None,
    detailed_status_cards: bool = False,
) -> str:
    summaries = [
        summarize_effect(
            _resolve_effect_for_card_instance(
                effect,
                card_instance_id=card_instance_id,
                combat_state=combat_state,
            ),
            detailed_status_cards=detailed_status_cards,
        )
        for effect in effects
    ]
    return " / ".join(summary for summary in summaries if summary) or "-"


def summarize_card_definition(card_def: CardDef) -> str:
    if card_def.id == "disarm":
        return "使敌人失去2点力量。"
    if card_def.id == "disarm_plus":
        return "使敌人失去3点力量。"
    summary = summarize_card_effects(card_def.effects)
    if summary != "-":
        return summary
    special_rule = special_card_rule_text(card_def.id)
    if special_rule is not None:
        return special_rule
    return "无效果"


def summarize_card_definition_for_instance(
    card_def: CardDef,
    *,
    card_instance_id: str,
    combat_state: CombatState | None = None,
) -> str:
    if card_def.id == "disarm":
        return "使敌人失去2点力量。"
    if card_def.id == "disarm_plus":
        return "使敌人失去3点力量。"
    summary = summarize_card_effects_for_instance(
        card_def.effects,
        card_instance_id=card_instance_id,
        combat_state=combat_state,
    )
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
