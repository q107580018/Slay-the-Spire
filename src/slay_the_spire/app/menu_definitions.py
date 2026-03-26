from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from rich.text import Text

from slay_the_spire.adapters.terminal.widgets import summarize_card_definition
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort


@dataclass(frozen=True, slots=True)
class MenuOption:
    action_id: str
    label: str | Text


@dataclass(frozen=True, slots=True)
class MenuDefinition:
    title: str
    options: tuple[MenuOption, ...]
    header_lines: tuple[str | Text, ...] = ()


def _plain_text(line: str | Text) -> str:
    if isinstance(line, Text):
        return line.plain
    return str(line)


def _numbered_label(index: int, label: str | Text) -> str | Text:
    if isinstance(label, Text):
        numbered = Text(f"{index}. ")
        numbered.append_text(label)
        return numbered
    return f"{index}. {label}"


def build_menu(
    *,
    title: str,
    options: list[tuple[str, str | Text]] | tuple[tuple[str, str | Text], ...],
    header_lines: list[str | Text] | tuple[str | Text, ...] = (),
) -> MenuDefinition:
    return MenuDefinition(
        title=title,
        header_lines=tuple(header_lines),
        options=tuple(MenuOption(action_id=action_id, label=label) for action_id, label in options),
    )


def format_menu_entries(menu: MenuDefinition) -> list[str | Text]:
    entries: list[str | Text] = [f"{menu.title}:"]
    entries.extend(menu.header_lines)
    entries.extend(_numbered_label(index, option.label) for index, option in enumerate(menu.options, start=1))
    return entries


def format_menu_lines(menu: MenuDefinition) -> list[str]:
    return [_plain_text(line) for line in format_menu_entries(menu)]


def resolve_menu_action(choice: str, menu: MenuDefinition) -> str | None:
    try:
        index = int(choice)
    except ValueError:
        return None
    if index <= 0 or index > len(menu.options):
        return None
    return menu.options[index - 1].action_id


def _boss_rewards(room_state: RoomState) -> Mapping[str, object] | None:
    boss_rewards = room_state.payload.get("boss_rewards")
    if not isinstance(boss_rewards, Mapping):
        return None
    return boss_rewards


def _has_pending_boss_rewards(room_state: RoomState) -> bool:
    boss_rewards = _boss_rewards(room_state)
    if not room_state.is_resolved or room_state.room_type != "boss" or boss_rewards is None:
        return False
    claimed_relic_id = boss_rewards.get("claimed_relic_id")
    return not (boss_rewards.get("claimed_gold") is True and isinstance(claimed_relic_id, str) and bool(claimed_relic_id))


def build_root_menu(*, room_state: RoomState) -> MenuDefinition:
    if room_state.is_resolved:
        if _has_pending_boss_rewards(room_state):
            return build_menu(
                title="可选操作",
                options=[
                    ("view_rewards", "查看奖励"),
                    ("claim_rewards", "领取奖励"),
                    ("inspect", "查看资料"),
                    ("save", "保存游戏"),
                    ("load", "读取存档"),
                    ("quit", "退出游戏"),
                ],
            )
        if room_state.rewards:
            return build_menu(
                title="可选操作",
                options=[
                    ("view_rewards", "查看奖励"),
                    ("claim_rewards", "领取奖励"),
                    ("next_room", "前往下一个房间"),
                    ("inspect", "查看资料"),
                    ("save", "保存游戏"),
                    ("load", "读取存档"),
                    ("quit", "退出游戏"),
                ],
            )
        return build_menu(
            title="可选操作",
            options=[
                ("next_room", "前往下一个房间"),
                ("inspect", "查看资料"),
                ("save", "保存游戏"),
                ("load", "读取存档"),
                ("quit", "退出游戏"),
            ],
        )
    if room_state.room_type in {"combat", "elite", "boss"}:
        return build_menu(
            title="可选操作",
            options=[
                ("view_current", "查看战场"),
                ("play_card", "出牌"),
                ("end_turn", "结束回合"),
                ("inspect", "查看资料"),
                ("save", "保存游戏"),
                ("load", "读取存档"),
                ("quit", "退出游戏"),
            ],
        )
    if room_state.room_type == "event":
        return build_menu(
            title="可选操作",
            options=[
                ("view_current", "查看事件"),
                ("event_choice", "进行选择"),
                ("inspect", "查看资料"),
                ("save", "保存游戏"),
                ("load", "读取存档"),
                ("quit", "退出游戏"),
            ],
        )
    return build_menu(
        title="可选操作",
        options=[
            ("view_current", "查看当前状态"),
            ("next_room", "前往下一个房间"),
            ("inspect", "查看资料"),
            ("save", "保存游戏"),
            ("load", "读取存档"),
            ("quit", "退出游戏"),
        ],
    )


def build_inspect_root_menu(*, room_state: RoomState) -> MenuDefinition:
    reward_room_inspect = room_state.is_resolved and (bool(room_state.rewards) or _has_pending_boss_rewards(room_state))
    if room_state.room_type in {"combat", "elite", "boss"} and not reward_room_inspect:
        return build_menu(
            title="资料总览",
            options=[
                ("inspect_stats", "角色状态"),
                ("inspect_deck", "牌组列表"),
                ("inspect_relics", "遗物列表"),
                ("inspect_potions", "药水"),
                ("inspect_hand", "手牌"),
                ("inspect_draw_pile", "抽牌堆"),
                ("inspect_discard_pile", "弃牌堆"),
                ("inspect_exhaust_pile", "消耗堆"),
                ("inspect_enemies", "敌人详情"),
                ("back", "返回上一步"),
            ],
        )
    return build_menu(
        title="资料总览",
        options=[
            ("inspect_stats", "属性"),
            ("inspect_deck", "牌组"),
            ("inspect_relics", "遗物"),
            ("inspect_potions", "药水"),
            ("back", "返回上一步"),
        ],
    )


def build_leaf_menu(*, title: str) -> MenuDefinition:
    return build_menu(title=title, options=[("back", "返回上一步")])


def build_card_detail_menu() -> MenuDefinition:
    return build_menu(title="卡牌详情", options=[("back_to_list", "返回卡牌列表"), ("back_to_root", "返回资料总览")])


def build_enemy_detail_menu() -> MenuDefinition:
    return build_menu(title="敌人详情", options=[("back_to_list", "返回敌人列表"), ("back_to_root", "返回资料总览")])


def _reward_label(reward_id: str, registry: ContentProviderPort) -> str:
    if reward_id.startswith("gold:"):
        return f"金币 +{reward_id.split(':', 1)[1]}"
    if reward_id.startswith("card:"):
        reward_name = reward_id.split(":", 1)[1]
        card_id = "strike_plus" if reward_name == "reward_strike" else "defend_plus" if reward_name == "reward_defend" else reward_name
        return f"卡牌 {registry.cards().get(card_id).name}"
    if reward_id.startswith("event:"):
        result = reward_id.split(":", 1)[1]
        if result == "gain_upgrade":
            return "事件结果 获得升级"
        if result == "nothing":
            return "事件结果 什么也没有发生"
        return f"事件结果 {result}"
    return reward_id


def build_reward_menu(*, room_state: RoomState, registry: ContentProviderPort) -> MenuDefinition:
    return build_menu(
        title="奖励",
        options=[
            *[(f"claim_reward:{reward_id}", _reward_label(reward_id, registry)) for reward_id in room_state.rewards],
            ("claim_all", "全部领取"),
            ("back", "返回上一步"),
        ],
    )


def build_boss_reward_menu(boss_rewards: Mapping[str, object]) -> MenuDefinition:
    gold_reward = boss_rewards.get("gold_reward")
    claimed_gold = boss_rewards.get("claimed_gold") is True
    claimed_relic_id = boss_rewards.get("claimed_relic_id")
    gold_label = "已领取金币" if claimed_gold else f"领取金币 +{gold_reward}" if isinstance(gold_reward, int) and not isinstance(gold_reward, bool) else "领取金币"
    gold_action = "claimed_boss_gold" if claimed_gold else "claim_boss_gold"
    relic_label = "已选择遗物" if isinstance(claimed_relic_id, str) and claimed_relic_id else "选择遗物"
    relic_action = "claimed_boss_relic" if isinstance(claimed_relic_id, str) and claimed_relic_id else "choose_boss_relic"
    return build_menu(
        title="Boss奖励",
        options=[
            (gold_action, gold_label),
            (relic_action, relic_label),
            ("back", "返回上一步"),
        ],
    )


def build_boss_relic_menu(relic_ids: list[str], *, registry: ContentProviderPort) -> MenuDefinition:
    return build_menu(
        title="选择Boss遗物",
        options=[
            *[(f"claim_boss_relic:{relic_id}", registry.relics().get(relic_id).name) for relic_id in relic_ids],
            ("back", "返回上一步"),
        ],
    )


def build_terminal_phase_menu(*, run_phase: str) -> MenuDefinition:
    return build_menu(
        title="终局",
        options=[
            ("view_terminal", "查看胜利结果" if run_phase == "victory" else "查看失败结果"),
            ("save", "保存游戏"),
            ("load", "读取存档"),
            ("quit", "退出游戏"),
        ],
    )


def build_next_room_menu(*, options: list[tuple[str, str]]) -> MenuDefinition:
    return build_menu(
        title="请选择下一个房间",
        options=[*options, ("back", "返回上一步")],
    )


def build_event_choice_menu(*, options: list[tuple[str, str]]) -> MenuDefinition:
    return build_menu(title="事件选项", options=[*options, ("back", "返回上一步")])


def build_event_upgrade_menu(*, options: list[tuple[str, str]]) -> MenuDefinition:
    return build_menu(title="选择要升级的卡牌", options=[*options, ("cancel", "返回上一步")])


def build_event_remove_menu(*, options: list[tuple[str, str]]) -> MenuDefinition:
    return build_menu(title="选择要移除的卡牌", options=[*options, ("cancel", "返回上一步")])


def build_shop_root_menu(
    *,
    run_state: RunState,
    room_state: RoomState,
    registry: ContentProviderPort,
) -> MenuDefinition:
    options: list[tuple[str, str]] = []
    for offer in room_state.payload.get("cards", []):
        if not isinstance(offer, dict) or not isinstance(offer.get("offer_id"), str):
            continue
        card_id = offer.get("card_id")
        card_name = registry.cards().get(card_id).name if isinstance(card_id, str) else str(card_id)
        status = _shop_offer_status(price=offer.get("price"), sold=offer.get("sold") is True, current_gold=run_state.gold)
        options.append((f"buy_card:{offer['offer_id']}", f"购买卡牌 {card_name} - {offer.get('price')} 金币 [{status}]"))
    for offer in room_state.payload.get("relics", []):
        if not isinstance(offer, dict) or not isinstance(offer.get("offer_id"), str):
            continue
        relic_id = offer.get("relic_id")
        relic_name = registry.relics().get(relic_id).name if isinstance(relic_id, str) else str(relic_id)
        status = _shop_offer_status(price=offer.get("price"), sold=offer.get("sold") is True, current_gold=run_state.gold)
        options.append((f"buy_relic:{offer['offer_id']}", f"购买遗物 {relic_name} - {offer.get('price')} 金币 [{status}]"))
    for offer in room_state.payload.get("potions", []):
        if not isinstance(offer, dict) or not isinstance(offer.get("offer_id"), str):
            continue
        potion_id = offer.get("potion_id")
        potion_name = registry.potions().get(potion_id).name if isinstance(potion_id, str) else str(potion_id)
        status = _shop_offer_status(price=offer.get("price"), sold=offer.get("sold") is True, current_gold=run_state.gold)
        options.append((f"buy_potion:{offer['offer_id']}", f"购买药水 {potion_name} - {offer.get('price')} 金币 [{status}]"))
    remove_price = room_state.payload.get("remove_price", 75)
    remove_status = _remove_service_status(
        remove_used=room_state.payload.get("remove_used") is True,
        remove_price=remove_price,
        current_gold=run_state.gold,
    )
    options.extend(
        [
            ("remove", f"删牌服务 - {remove_price} 金币 [{remove_status}]"),
            ("leave", "离开商店"),
            ("inspect", "查看资料"),
            ("save", "保存游戏"),
            ("load", "读取存档"),
            ("quit", "退出游戏"),
        ]
    )
    return build_menu(title="商店操作", header_lines=[f"当前金币: {run_state.gold}"], options=options)


def build_shop_remove_menu(*, room_state: RoomState, registry: ContentProviderPort) -> MenuDefinition:
    options = []
    for card_instance_id in room_state.payload.get("remove_candidates", []):
        if not isinstance(card_instance_id, str):
            continue
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        options.append((f"remove_card:{card_instance_id}", f"{card_def.name} ({card_instance_id})"))
    options.extend(
        [
            ("cancel", "取消"),
            ("save", "保存游戏"),
            ("load", "读取存档"),
            ("quit", "退出游戏"),
        ]
    )
    return build_menu(title="选择要移除的卡牌", options=options)


def build_rest_root_menu(*, room_state: RoomState) -> MenuDefinition:
    options: list[tuple[str, str]] = []
    for action in room_state.payload.get("actions", []):
        if not isinstance(action, str):
            continue
        label = "休息" if action == "rest" else "锻造" if action == "smith" else action
        options.append((action, label))
    options.extend([("inspect", "查看资料"), ("save", "保存游戏"), ("load", "读取存档"), ("quit", "退出游戏")])
    return build_menu(title="休息点操作", options=options)


def build_rest_upgrade_menu(*, room_state: RoomState, registry: ContentProviderPort) -> MenuDefinition:
    options = []
    for card_instance_id in room_state.payload.get("upgrade_options", []):
        if not isinstance(card_instance_id, str):
            continue
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        options.append((f"upgrade_card:{card_instance_id}", f"{card_def.name} ({card_instance_id})"))
    options.extend([("cancel", "取消"), ("save", "保存游戏"), ("load", "读取存档"), ("quit", "退出游戏")])
    return build_menu(title="可升级卡牌", options=options)


def build_select_card_menu(*, combat_state: CombatState, registry: ContentProviderPort) -> MenuDefinition:
    options: list[tuple[str, str]] = []
    for index, card_instance_id in enumerate(combat_state.hand, start=1):
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        cost_label = "无法打出" if not getattr(card_def, "playable", True) or card_def.cost < 0 else f"费用{card_def.cost}"
        effect_summary = summarize_card_definition(card_def)
        options.append((f"play_card:{index}", f"{card_def.name} {cost_label} - {effect_summary}"))
    options.append(("back", "返回上一步"))
    return build_menu(title="手牌", options=options)


def build_target_menu(
    *,
    target_options: list[tuple[str, str | Text]],
    current_card_name: str | None,
    title: str = "选择目标",
    header_lines: list[str | Text] | tuple[str | Text, ...] = (),
) -> MenuDefinition:
    resolved_header_lines: list[str | Text] = list(header_lines)
    if current_card_name:
        resolved_header_lines.append(f"当前卡牌: {current_card_name}")
    return build_menu(title=title, header_lines=resolved_header_lines, options=[*target_options, ("back", "返回上一步")])


def _shop_offer_status(*, price: object, sold: bool, current_gold: int) -> str:
    if sold:
        return "已购买"
    if not isinstance(price, int) or current_gold < price:
        return "金币不足"
    return "可购买"


def _remove_service_status(*, remove_used: bool, remove_price: Any, current_gold: int) -> str:
    if remove_used:
        return "已使用"
    if not isinstance(remove_price, int) or current_gold < remove_price:
        return "金币不足"
    return "可购买"
