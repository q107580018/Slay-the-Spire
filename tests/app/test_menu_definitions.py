from __future__ import annotations

from dataclasses import replace

from slay_the_spire.app.menu_definitions import (
    build_next_room_menu,
    build_inspect_root_menu,
    build_reward_menu,
    build_rest_upgrade_menu,
    build_root_menu,
    build_shop_root_menu,
    build_terminal_phase_menu,
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


def test_build_terminal_phase_menu_binds_result_and_system_actions() -> None:
    menu = build_terminal_phase_menu(run_phase="victory")

    assert format_menu_lines(menu) == [
        "终局:",
        "1. 查看胜利结果",
        "2. 保存游戏",
        "3. 读取存档",
        "4. 退出游戏",
    ]
    assert resolve_menu_action("1", menu) == "view_terminal"
    assert resolve_menu_action("4", menu) == "quit"


def test_build_next_room_menu_binds_node_actions_and_back() -> None:
    menu = build_next_room_menu(options=[("next_node:r2c0", "战 r2c0 (2,0)"), ("next_node:r2c1", "店 r2c1 (2,1)")])

    assert format_menu_lines(menu) == [
        "请选择下一个房间:",
        "1. 战 r2c0 (2,0)",
        "2. 店 r2c1 (2,1)",
        "3. 返回上一步",
    ]
    assert resolve_menu_action("2", menu) == "next_node:r2c1"
    assert resolve_menu_action("3", menu) == "back"


def test_build_shop_root_menu_binds_offer_and_system_actions() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            room_type="shop",
            payload={
                "cards": [{"offer_id": "card-1", "card_id": "strike", "price": 50}],
                "relics": [],
                "potions": [],
                "remove_price": 75,
            },
            is_resolved=False,
            rewards=[],
        ),
    )
    registry = StarterContentProvider(session.content_root)

    menu = build_shop_root_menu(run_state=session.run_state, room_state=session.room_state, registry=registry)

    assert format_menu_lines(menu) == [
        "商店操作:",
        f"当前金币: {session.run_state.gold}",
        "1. 购买卡牌 打击 - 50 金币 [可购买]",
        "2. 删牌服务 - 75 金币 [可购买]",
        "3. 离开商店",
        "4. 查看资料",
        "5. 保存游戏",
        "6. 读取存档",
        "7. 退出游戏",
    ]
    assert resolve_menu_action("1", menu) == "buy_card:card-1"
    assert resolve_menu_action("4", menu) == "inspect"


def test_build_rest_upgrade_menu_binds_cards_cancel_and_system_actions() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            room_type="rest",
            stage="select_upgrade_card",
            payload={"upgrade_options": ["bash#10"]},
            is_resolved=False,
            rewards=[],
        ),
    )
    registry = StarterContentProvider(session.content_root)

    menu = build_rest_upgrade_menu(room_state=session.room_state, registry=registry)

    assert format_menu_lines(menu) == [
        "可升级卡牌:",
        "1. 重击 (bash#10)",
        "2. 取消",
        "3. 保存游戏",
        "4. 读取存档",
        "5. 退出游戏",
    ]
    assert resolve_menu_action("1", menu) == "upgrade_card:bash#10"
    assert resolve_menu_action("2", menu) == "cancel"
