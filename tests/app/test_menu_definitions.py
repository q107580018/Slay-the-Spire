from __future__ import annotations

from dataclasses import replace

from rich.text import Text

from slay_the_spire.app.menu_definitions import (
    build_boss_relic_menu,
    build_boss_reward_menu,
    build_potion_target_menu,
    build_select_potion_menu,
    build_next_room_menu,
    build_inspect_root_menu,
    build_reward_menu,
    build_rest_upgrade_menu,
    build_root_menu,
    build_select_card_menu,
    build_shop_root_menu,
    build_target_menu,
    build_terminal_phase_menu,
    format_menu_lines,
    resolve_menu_action,
)
from slay_the_spire.app.session import start_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.content.registries import EnemyDef, PotionDef
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState


def _span_styles(text: Text) -> set[str]:
    return {str(span.style) for span in text.spans}


class _RegistryMap:
    def __init__(self, items: dict[str, object]) -> None:
        self._items = items

    def get(self, content_id: str) -> object:
        return self._items[content_id]


class _PotionTestProvider:
    def __init__(self, *, potions: dict[str, PotionDef], enemies: dict[str, EnemyDef] | None = None) -> None:
        self._potions = _RegistryMap(potions)
        self._enemies = _RegistryMap(enemies or {})

    def potions(self) -> _RegistryMap:
        return self._potions

    def enemies(self) -> _RegistryMap:
        return self._enemies


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


def test_build_root_menu_binds_combat_use_potion_action() -> None:
    session = start_session(seed=5)

    menu = build_root_menu(room_state=session.room_state, run_state=replace(session.run_state, potions=["fire_potion"]))

    assert format_menu_lines(menu) == [
        "可选操作:",
        "1. 出牌",
        "2. 使用药水",
        "3. 结束回合",
        "4. 查看资料",
        "5. 保存游戏",
        "6. 读取存档",
        "7. 退出游戏",
    ]
    assert resolve_menu_action("2", menu) == "use_potion"


def test_build_root_menu_hides_out_of_combat_potions_when_registry_is_provided() -> None:
    session = start_session(seed=5)
    registry = _PotionTestProvider(
        potions={
            "rest_potion": PotionDef(
                id="rest_potion",
                name="休息药水",
                effect={"type": "heal", "amount": 5},
                timing="out_of_combat",
                target="self",
            )
        }
    )

    menu = build_root_menu(room_state=session.room_state, run_state=replace(session.run_state, potions=["rest_potion"]), registry=registry)

    assert "使用药水" not in format_menu_lines(menu)


def test_build_select_potion_menu_hides_out_of_combat_potions() -> None:
    session = start_session(seed=5)
    registry = _PotionTestProvider(
        potions={
            "rest_potion": PotionDef(
                id="rest_potion",
                name="休息药水",
                effect={"type": "heal", "amount": 5},
                timing="out_of_combat",
                target="self",
            )
        }
    )

    menu = build_select_potion_menu(run_state=replace(session.run_state, potions=["rest_potion"]), registry=registry)

    assert format_menu_lines(menu) == [
        "药水:",
        "1. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "back"


def test_build_potion_target_menu_for_any_target_includes_self_and_enemies() -> None:
    combat_state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=40,
            max_hp=40,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="slime",
                hp=20,
                max_hp=20,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )
    registry = _PotionTestProvider(
        potions={
            "flex_potion": PotionDef(
                id="flex_potion",
                name="灵活药水",
                effect={"type": "damage", "amount": 7},
                timing="in_combat",
                target="any",
            )
        },
        enemies={
            "slime": EnemyDef(
                id="slime",
                name="绿史莱姆",
                hp=20,
                move_table=[],
                intent_policy="random",
            )
        },
    )

    menu = build_potion_target_menu(combat_state=combat_state, potion_id="flex_potion", registry=registry)

    assert format_menu_lines(menu) == [
        "选择目标:",
        "当前药水: 灵活药水",
        "效果: 造成 7 伤害（目标：任意目标 / 时机：战斗中）",
        "1. 自己",
        "2. 绿史莱姆",
        "3. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "target_self"
    assert resolve_menu_action("2", menu) == "target_enemy:1"


def test_build_root_menu_binds_pending_boss_rewards_to_reward_actions() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            room_type="boss",
            stage="completed",
            is_resolved=True,
            rewards=[],
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 95,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
        ),
    )

    menu = build_root_menu(room_state=session.room_state)

    assert format_menu_lines(menu) == [
        "可选操作:",
        "1. 领取奖励",
        "2. 查看资料",
        "3. 保存游戏",
        "4. 读取存档",
        "5. 退出游戏",
    ]
    assert resolve_menu_action("1", menu) == "claim_rewards"
    assert resolve_menu_action("2", menu) == "inspect"
    assert "前往下一个房间" not in format_menu_lines(menu)


def test_build_root_menu_binds_boss_chest_transition_into_next_act() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            room_id="act1:boss_chest",
            room_type="boss_chest",
            stage="completed",
            is_resolved=True,
            rewards=[],
            payload={
                "act_id": "act1",
                "node_id": "boss_chest",
                "next_node_ids": [],
                "next_act_id": "act2",
            },
        ),
    )

    menu = build_root_menu(room_state=session.room_state)

    assert format_menu_lines(menu) == [
        "可选操作:",
        "1. 前往下一幕",
        "2. 查看资料",
        "3. 保存游戏",
        "4. 读取存档",
        "5. 退出游戏",
    ]
    assert resolve_menu_action("1", menu) == "advance_boss_chest"
    assert resolve_menu_action("2", menu) == "inspect"


def test_build_root_menu_binds_final_boss_chest_to_climb_completion() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            room_id="act2:boss_chest",
            room_type="boss_chest",
            stage="completed",
            is_resolved=True,
            rewards=[],
            payload={
                "act_id": "act2",
                "node_id": "boss_chest",
                "next_node_ids": [],
            },
        ),
    )

    menu = build_root_menu(room_state=session.room_state)

    assert format_menu_lines(menu) == [
        "可选操作:",
        "1. 完成攀登",
        "2. 查看资料",
        "3. 保存游戏",
        "4. 读取存档",
        "5. 退出游戏",
    ]
    assert resolve_menu_action("1", menu) == "advance_boss_chest"
    assert resolve_menu_action("2", menu) == "inspect"


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


def test_build_inspect_root_menu_binds_pending_boss_rewards_to_non_combat_choices() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            room_type="boss",
            stage="completed",
            is_resolved=True,
            rewards=[],
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 95,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
        ),
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
    assert resolve_menu_action("5", menu) == "back"


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


def test_build_select_potion_menu_lists_potions_with_effects_and_back() -> None:
    session = start_session(seed=5)
    session.run_state.potions = ["fire_potion", "strength_potion"]
    registry = StarterContentProvider(session.content_root)

    menu = build_select_potion_menu(run_state=session.run_state, registry=registry)

    assert format_menu_lines(menu) == [
        "药水:",
        "1. 对敌 火焰药水 - 造成 20 伤害（目标：敌人 / 时机：战斗中）",
        "2. 对己 力量药水 - 获得 2 力量（目标：自己 / 时机：战斗中）",
        "3. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "use_potion:1"
    assert resolve_menu_action("3", menu) == "back"


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


def test_build_reward_menu_lists_skip_card_rewards_when_card_offers_exist() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            is_resolved=True,
            rewards=["gold:11", "card_offer:anger", "card_offer:pommel_strike", "card_offer:shrug_it_off"],
        ),
    )
    registry = StarterContentProvider(session.content_root)

    menu = build_reward_menu(room_state=session.room_state, registry=registry)

    assert format_menu_lines(menu) == [
        "奖励:",
        "1. 金币 +11",
        "2. 卡牌 愤怒",
        "3. 卡牌 柄击",
        "4. 卡牌 耸肩无视",
        "5. 跳过卡牌奖励",
        "6. 全部领取",
        "7. 返回上一步",
    ]
    assert resolve_menu_action("2", menu) == "claim_reward:card_offer:anger"
    assert resolve_menu_action("5", menu) == "skip_card_rewards"


def test_build_root_menu_binds_combat_choices_without_view_current() -> None:
    session = start_session(seed=5)
    menu = build_root_menu(room_state=session.room_state, run_state=session.run_state)

    assert format_menu_lines(menu) == [
        "可选操作:",
        "1. 出牌",
        "2. 结束回合",
        "3. 查看资料",
        "4. 保存游戏",
        "5. 读取存档",
        "6. 退出游戏",
    ]
    assert resolve_menu_action("1", menu) == "play_card"
    assert resolve_menu_action("3", menu) == "inspect"


def test_build_select_card_menu_includes_round_end_turn_and_back() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])

    menu = build_select_card_menu(combat_state=combat_state, registry=registry)
    lines = format_menu_lines(menu)

    assert menu.title == "手牌（第1回合，当前能量 3）"
    assert lines[-2] == f"{len(combat_state.hand) + 1}. 结束回合"
    assert lines[-1] == f"{len(combat_state.hand) + 2}. 返回上一步"
    assert resolve_menu_action(str(len(combat_state.hand) + 1), menu) == "end_turn"


def test_build_root_menu_binds_event_choices_without_view_current() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, room_type="event"),
    )

    menu = build_root_menu(room_state=session.room_state)

    assert format_menu_lines(menu) == [
        "可选操作:",
        "1. 进行选择",
        "2. 查看资料",
        "3. 保存游戏",
        "4. 读取存档",
        "5. 退出游戏",
    ]
    assert resolve_menu_action("1", menu) == "event_choice"
    assert resolve_menu_action("2", menu) == "inspect"


def test_build_root_menu_binds_unresolved_treasure_to_open_chest_action() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            room_type="treasure",
            stage="waiting_input",
            is_resolved=False,
            payload={
                "node_id": "r9c0",
                "next_node_ids": ["boss"],
                "treasure_relic_id": "golden_idol",
            },
        ),
    )

    menu = build_root_menu(room_state=session.room_state)

    assert format_menu_lines(menu) == [
        "可选操作:",
        "1. 打开宝箱",
        "2. 查看资料",
        "3. 保存游戏",
        "4. 读取存档",
        "5. 退出游戏",
    ]
    assert resolve_menu_action("1", menu) == "open_treasure"
    assert "查看当前状态" not in format_menu_lines(menu)
    assert "前往下一个房间" not in format_menu_lines(menu)


def test_build_root_menu_returns_resolved_treasure_to_next_room_flow() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            room_type="treasure",
            stage="completed",
            is_resolved=True,
            rewards=[],
            payload={
                "node_id": "r9c0",
                "next_node_ids": ["boss"],
                "treasure_relic_id": "golden_idol",
                "claimed_treasure_relic_id": "golden_idol",
            },
        ),
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
    assert resolve_menu_action("1", menu) == "next_room"


def test_build_boss_reward_menu_binds_gold_relic_and_back_actions() -> None:
    menu = build_boss_reward_menu(
        {
            "generated_by": "boss_reward_generator",
            "gold_reward": 99,
            "claimed_gold": False,
            "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
            "claimed_relic_id": None,
        }
    )

    assert format_menu_lines(menu) == [
        "Boss奖励:",
        "1. 领取金币 +99",
        "2. 选择遗物",
        "3. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "claim_boss_gold"
    assert resolve_menu_action("2", menu) == "choose_boss_relic"
    assert resolve_menu_action("3", menu) == "back"


def test_build_boss_reward_menu_marks_claimed_gold_as_completed() -> None:
    menu = build_boss_reward_menu(
        {
            "generated_by": "boss_reward_generator",
            "gold_reward": 99,
            "claimed_gold": True,
            "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
            "claimed_relic_id": None,
        }
    )

    assert format_menu_lines(menu) == [
        "Boss奖励:",
        "1. 已领取金币",
        "2. 选择遗物",
        "3. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "claimed_boss_gold"
    assert resolve_menu_action("2", menu) == "choose_boss_relic"
    assert resolve_menu_action("3", menu) == "back"


def test_build_target_menu_supports_explicit_enemy_title() -> None:
    menu = build_target_menu(
        target_options=[("target_enemy:1", "绿史莱姆")],
        current_card_name="打击",
        title="选择敌人",
    )

    assert format_menu_lines(menu) == [
        "选择敌人:",
        "当前卡牌: 打击",
        "1. 绿史莱姆",
        "2. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "target_enemy:1"
    assert resolve_menu_action("2", menu) == "back"


def test_build_target_menu_supports_hand_target_headers() -> None:
    menu = build_target_menu(
        target_options=[("target_hand:1", "打击 (strike#2)")],
        current_card_name="武装",
        title="选择手牌",
        header_lines=["手牌目标:"],
    )

    assert format_menu_lines(menu) == [
        "选择手牌:",
        "手牌目标:",
        "当前卡牌: 武装",
        "1. 打击 (strike#2)",
        "2. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "target_hand:1"
    assert resolve_menu_action("2", menu) == "back"


def test_build_target_menu_keeps_current_card_text_style() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)
    from slay_the_spire.adapters.presentation.widgets import render_card_name

    current_card_name = render_card_name(registry.cards().get("anger_plus"))

    menu = build_target_menu(
        target_options=[("target_enemy:1", "绿史莱姆")],
        current_card_name=current_card_name,
    )

    assert isinstance(menu.header_lines[0], Text)
    assert menu.header_lines[0].plain == "当前卡牌: 愤怒+"
    assert "card.rarity.common" in _span_styles(menu.header_lines[0])
    assert "card.upgraded" in _span_styles(menu.header_lines[0])


def test_build_boss_reward_menu_marks_claimed_relic_as_completed() -> None:
    menu = build_boss_reward_menu(
        {
            "generated_by": "boss_reward_generator",
            "gold_reward": 99,
            "claimed_gold": True,
            "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
            "claimed_relic_id": "black_blood",
        }
    )

    assert format_menu_lines(menu) == [
        "Boss奖励:",
        "1. 已领取金币",
        "2. 已选择遗物",
        "3. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "claimed_boss_gold"
    assert resolve_menu_action("2", menu) == "claimed_boss_relic"


def test_build_boss_relic_menu_binds_three_relic_choices_and_back() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    menu = build_boss_relic_menu(
        ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
        registry=registry,
    )

    assert format_menu_lines(menu) == [
        "选择Boss遗物:",
        "1. 黑色之血",
        "2. 虚空质",
        "3. 咖啡滴滤器",
        "4. 融合之锤",
        "5. 返回上一步",
    ]
    assert resolve_menu_action("1", menu) == "claim_boss_relic:black_blood"
    assert resolve_menu_action("4", menu) == "claim_boss_relic:fusion_hammer"
    assert resolve_menu_action("5", menu) == "back"


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
