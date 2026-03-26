from __future__ import annotations

from dataclasses import dataclass

from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.ports.content_provider import ContentProviderPort


@dataclass(frozen=True, slots=True)
class MenuOption:
    action_id: str
    label: str


@dataclass(frozen=True, slots=True)
class MenuDefinition:
    title: str
    options: tuple[MenuOption, ...]


def format_menu_lines(menu: MenuDefinition) -> list[str]:
    return [f"{menu.title}:"] + [f"{index}. {option.label}" for index, option in enumerate(menu.options, start=1)]


def resolve_menu_action(choice: str, menu: MenuDefinition) -> str | None:
    try:
        index = int(choice)
    except ValueError:
        return None
    if index <= 0 or index > len(menu.options):
        return None
    return menu.options[index - 1].action_id


def build_root_menu(*, room_state: RoomState) -> MenuDefinition:
    if room_state.is_resolved:
        if room_state.rewards:
            return MenuDefinition(
                title="可选操作",
                options=(
                    MenuOption("view_rewards", "查看奖励"),
                    MenuOption("claim_rewards", "领取奖励"),
                    MenuOption("next_room", "前往下一个房间"),
                    MenuOption("inspect", "查看资料"),
                    MenuOption("save", "保存游戏"),
                    MenuOption("load", "读取存档"),
                    MenuOption("quit", "退出游戏"),
                ),
            )
        return MenuDefinition(
            title="可选操作",
            options=(
                MenuOption("next_room", "前往下一个房间"),
                MenuOption("inspect", "查看资料"),
                MenuOption("save", "保存游戏"),
                MenuOption("load", "读取存档"),
                MenuOption("quit", "退出游戏"),
            ),
        )
    if room_state.room_type in {"combat", "elite", "boss"}:
        return MenuDefinition(
            title="可选操作",
            options=(
                MenuOption("view_current", "查看战场"),
                MenuOption("play_card", "出牌"),
                MenuOption("end_turn", "结束回合"),
                MenuOption("inspect", "查看资料"),
                MenuOption("save", "保存游戏"),
                MenuOption("load", "读取存档"),
                MenuOption("quit", "退出游戏"),
            ),
        )
    if room_state.room_type == "event":
        return MenuDefinition(
            title="可选操作",
            options=(
                MenuOption("view_current", "查看事件"),
                MenuOption("event_choice", "进行选择"),
                MenuOption("inspect", "查看资料"),
                MenuOption("save", "保存游戏"),
                MenuOption("load", "读取存档"),
                MenuOption("quit", "退出游戏"),
            ),
        )
    return MenuDefinition(
        title="可选操作",
        options=(
            MenuOption("view_current", "查看当前状态"),
            MenuOption("next_room", "前往下一个房间"),
            MenuOption("inspect", "查看资料"),
            MenuOption("save", "保存游戏"),
            MenuOption("load", "读取存档"),
            MenuOption("quit", "退出游戏"),
        ),
    )


def build_inspect_root_menu(*, room_state: RoomState) -> MenuDefinition:
    reward_room_inspect = room_state.is_resolved and bool(room_state.rewards)
    if room_state.room_type in {"combat", "elite", "boss"} and not reward_room_inspect:
        return MenuDefinition(
            title="资料总览",
            options=(
                MenuOption("inspect_stats", "角色状态"),
                MenuOption("inspect_deck", "牌组列表"),
                MenuOption("inspect_relics", "遗物列表"),
                MenuOption("inspect_potions", "药水"),
                MenuOption("inspect_hand", "手牌"),
                MenuOption("inspect_draw_pile", "抽牌堆"),
                MenuOption("inspect_discard_pile", "弃牌堆"),
                MenuOption("inspect_exhaust_pile", "消耗堆"),
                MenuOption("inspect_enemies", "敌人详情"),
                MenuOption("back", "返回上一步"),
            ),
        )
    return MenuDefinition(
        title="资料总览",
        options=(
            MenuOption("inspect_stats", "属性"),
            MenuOption("inspect_deck", "牌组"),
            MenuOption("inspect_relics", "遗物"),
            MenuOption("inspect_potions", "药水"),
            MenuOption("back", "返回上一步"),
        ),
    )


def build_leaf_menu(*, title: str) -> MenuDefinition:
    return MenuDefinition(title=title, options=(MenuOption("back", "返回上一步"),))


def build_card_detail_menu() -> MenuDefinition:
    return MenuDefinition(
        title="卡牌详情",
        options=(
            MenuOption("back_to_list", "返回卡牌列表"),
            MenuOption("back_to_root", "返回资料总览"),
        ),
    )


def build_enemy_detail_menu() -> MenuDefinition:
    return MenuDefinition(
        title="敌人详情",
        options=(
            MenuOption("back_to_list", "返回敌人列表"),
            MenuOption("back_to_root", "返回资料总览"),
        ),
    )


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
    reward_options = tuple(
        MenuOption(f"claim_reward:{reward_id}", _reward_label(reward_id, registry)) for reward_id in room_state.rewards
    )
    return MenuDefinition(
        title="奖励",
        options=reward_options
        + (
            MenuOption("claim_all", "全部领取"),
            MenuOption("back", "返回上一步"),
        ),
    )
