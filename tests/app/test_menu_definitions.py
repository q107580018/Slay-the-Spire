from __future__ import annotations

from dataclasses import replace

from slay_the_spire.app.menu_definitions import (
    build_inspect_root_menu,
    build_reward_menu,
    build_root_menu,
    format_menu_lines,
    resolve_menu_action,
)
from slay_the_spire.app.session import start_session
from slay_the_spire.content.provider import StarterContentProvider


def test_build_root_menu_binds_resolved_combat_without_rewards_to_inspect_action() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, stage="completed", is_resolved=True, rewards=[]),
    )

    menu = build_root_menu(room_state=session.room_state)

    assert format_menu_lines(menu) == [
        "可选操作:",
        "1. 前往下一个房间",
        "2. 查看资料",
        "3. 保存游戏",
        "4. 读取存档",
        "5. 退出游戏",
    ]
    assert resolve_menu_action("2", menu) == "inspect"
    assert resolve_menu_action("3", menu) == "save"


def test_build_inspect_root_menu_binds_combat_choices_to_actions() -> None:
    session = start_session(seed=5)

    menu = build_inspect_root_menu(room_state=session.room_state)

    assert format_menu_lines(menu) == [
        "资料总览:",
        "1. 角色状态",
        "2. 牌组列表",
        "3. 遗物列表",
        "4. 药水",
        "5. 手牌",
        "6. 抽牌堆",
        "7. 弃牌堆",
        "8. 消耗堆",
        "9. 敌人详情",
        "10. 返回上一步",
    ]
    assert resolve_menu_action("5", menu) == "inspect_hand"
    assert resolve_menu_action("9", menu) == "inspect_enemies"
    assert resolve_menu_action("10", menu) == "back"


def test_build_inspect_root_menu_binds_non_combat_choices_to_actions() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, room_type="event"),
    )

    menu = build_inspect_root_menu(room_state=session.room_state)

    assert format_menu_lines(menu) == [
        "资料总览:",
        "1. 属性",
        "2. 牌组",
        "3. 遗物",
        "4. 药水",
        "5. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "inspect_stats"
    assert resolve_menu_action("4", menu) == "inspect_potions"
    assert resolve_menu_action("5", menu) == "back"


def test_build_reward_menu_binds_labels_and_claim_actions() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, is_resolved=True, rewards=["gold:99"]),
    )
    registry = StarterContentProvider(session.content_root)

    menu = build_reward_menu(room_state=session.room_state, registry=registry)

    assert format_menu_lines(menu) == [
        "奖励:",
        "1. 金币 +99",
        "2. 全部领取",
        "3. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "claim_reward:gold:99"
    assert resolve_menu_action("2", menu) == "claim_all"
    assert resolve_menu_action("3", menu) == "back"
