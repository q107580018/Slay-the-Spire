from __future__ import annotations

from dataclasses import replace

from slay_the_spire.app.session import MenuState, route_menu_choice, start_session
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.room_state import RoomState


def _event_room() -> RoomState:
    return RoomState(
        room_id="act1:event",
        room_type="event",
        stage="waiting_input",
        payload={
            "node_id": "r1c0",
            "room_kind": "event",
            "event_id": "shining_light",
            "next_node_ids": ["r2c0"],
        },
        is_resolved=False,
        rewards=[],
    )


def _shop_room() -> RoomState:
    return RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "node_id": "r3c1",
            "cards": [{"offer_id": "card-1", "card_id": "strike", "price": 50}],
            "relics": [],
            "potions": [],
            "remove_price": 75,
            "next_node_ids": ["r4c0"],
        },
        is_resolved=False,
        rewards=[],
    )


def _rest_room() -> RoomState:
    return RoomState(
        room_id="act1:rest",
        room_type="rest",
        stage="waiting_input",
        payload={
            "node_id": "r5c0",
            "actions": ["rest", "smith"],
            "next_node_ids": ["r6c0"],
        },
        is_resolved=False,
        rewards=[],
    )


def _combat_room(*, hand: list[str], enemy_count: int = 1, enemy_hp: int = 12) -> RoomState:
    enemies = [
        EnemyState(
            instance_id=f"enemy-{index}",
            enemy_id="slime",
            hp=enemy_hp,
            max_hp=enemy_hp,
            block=0,
            statuses=[],
        )
        for index in range(1, enemy_count + 1)
    ]
    combat_state = CombatState(
        round_number=1,
        energy=3,
        hand=hand,
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=80,
            max_hp=80,
            block=0,
            statuses=[],
        ),
        enemies=enemies,
        effect_queue=[],
        log=[],
    )
    return RoomState(
        room_id="act1:hallway",
        room_type="combat",
        stage="waiting_input",
        payload={
            "node_id": "r1c0",
            "room_kind": "hallway",
            "enemy_pool_id": "act1_basic",
            "next_node_ids": ["r2c0"],
            "combat_state": combat_state.to_dict(),
        },
        is_resolved=False,
        rewards=[],
    )


def test_combat_root_menu_can_enter_inspect_root() -> None:
    session = start_session(seed=5)

    running, next_session, message = route_menu_choice("3", session=session)

    assert running is True
    assert next_session.menu_state.mode == "inspect_root"
    assert next_session.menu_state.inspect_parent_mode == "root"
    assert next_session.menu_state.inspect_item_id is None
    assert "资料总览" in message


def test_route_menu_choice_separates_status_and_render_messages_for_inspect_transition() -> None:
    result = route_menu_choice("3", session=start_session(seed=5))

    assert result.running is True
    assert result.status_message == "资料总览"
    assert result.render_message is not None
    assert "战斗摘要" in result.render_message


def test_route_menu_choice_leaves_status_empty_for_render_only_menu_transition() -> None:
    result = route_menu_choice("1", session=replace(start_session(seed=5), room_state=_combat_room(hand=["strike#1"])))

    assert result.running is True
    assert result.status_message is None
    assert result.render_message is not None
    assert "手牌" in result.render_message


def test_route_menu_choice_keeps_status_empty_after_nested_play_command() -> None:
    session = replace(
        start_session(seed=5),
        room_state=_combat_room(hand=["strike#1"]),
        menu_state=MenuState(mode="select_card"),
    )

    result = route_menu_choice("1", session=session)

    assert result.running is True
    assert result.status_message is None
    assert result.render_message is not None
    assert "战斗记录" in result.render_message


def test_single_enemy_attack_card_plays_without_entering_target_menu() -> None:
    session = replace(start_session(seed=5), room_state=_combat_room(hand=["strike#1"], enemy_count=1))

    _running, select_card_session, _message = route_menu_choice("1", session=session)
    _running, played_session, message = route_menu_choice("1", session=select_card_session)

    assert select_card_session.menu_state.mode == "select_card"
    assert played_session.menu_state.mode == "root"
    assert "选择敌人" not in message
    assert "造成 6 伤害" in message


def test_nonlethal_card_play_keeps_select_card_menu_open_when_hand_remains() -> None:
    session = replace(start_session(seed=5), room_state=_combat_room(hand=["anger#1", "strike#2"], enemy_count=1))

    _running, select_card_session, _message = route_menu_choice("1", session=session)
    _running, played_session, message = route_menu_choice("1", session=select_card_session)

    assert select_card_session.menu_state.mode == "select_card"
    assert played_session.menu_state.mode == "select_card"
    assert played_session.room_state.payload["combat_state"]["hand"] == ["strike#2"]
    assert "造成 6 伤害" in message


def test_lethal_card_play_exits_select_card_even_when_other_hand_cards_remain() -> None:
    session = replace(
        start_session(seed=5),
        room_state=_combat_room(hand=["strike#1", "defend#2"], enemy_count=1, enemy_hp=6),
    )

    _running, select_card_session, _message = route_menu_choice("1", session=session)
    _running, played_session, message = route_menu_choice("1", session=select_card_session)

    assert select_card_session.menu_state.mode == "select_card"
    assert played_session.menu_state.mode == "root"
    assert played_session.room_state.is_resolved is True
    assert played_session.room_state.stage == "completed"
    assert played_session.room_state.payload["combat_state"]["hand"] == ["defend#2"]
    assert played_session.room_state.rewards
    assert "领取奖励" in message


def test_hand_target_card_still_enters_hand_target_menu() -> None:
    session = replace(
        start_session(seed=5),
        room_state=_combat_room(hand=["armaments#1", "strike#2"], enemy_count=1),
    )

    _running, select_card_session, _message = route_menu_choice("1", session=session)
    _running, target_session, message = route_menu_choice("1", session=select_card_session)

    assert select_card_session.menu_state.mode == "select_card"
    assert target_session.menu_state.mode == "select_target"
    assert target_session.menu_state.selected_card_instance_id == "armaments#1"
    assert "选择手牌" in message


def test_targeted_card_play_keeps_select_card_menu_open_after_target_choice() -> None:
    session = replace(
        start_session(seed=5),
        room_state=_combat_room(hand=["anger#1", "strike#2"], enemy_count=2),
    )

    _running, select_card_session, _message = route_menu_choice("1", session=session)
    _running, target_session, _message = route_menu_choice("1", session=select_card_session)
    _running, played_session, message = route_menu_choice("1", session=target_session)

    assert target_session.menu_state.mode == "select_target"
    assert played_session.menu_state.mode == "select_card"
    assert played_session.room_state.payload["combat_state"]["hand"] == ["strike#2"]
    assert "造成 6 伤害" in message


def test_end_turn_can_be_triggered_inside_select_card_menu() -> None:
    session = replace(
        start_session(seed=5),
        room_state=_combat_room(hand=["defend#1"], enemy_count=1),
        menu_state=MenuState(mode="select_card"),
    )

    _running, next_session, _message = route_menu_choice("2", session=session)
    combat_state = CombatState.from_dict(next_session.room_state.payload["combat_state"])

    assert combat_state.round_number == 2
    assert next_session.menu_state.mode == "select_card"


def test_resolved_combat_without_rewards_can_enter_inspect_root_from_choice_two() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, stage="completed", is_resolved=True, rewards=[]),
    )

    running, next_session, message = route_menu_choice("2", session=session)

    assert running is True
    assert next_session.menu_state.mode == "inspect_root"
    assert next_session.menu_state.inspect_parent_mode == "root"
    assert next_session.menu_state.inspect_item_id is None
    assert "资料总览" in message


def test_boss_chest_root_menu_can_enter_inspect_root_from_choice_two() -> None:
    session = replace(
        start_session(seed=5),
        room_state=RoomState(
            room_id="act1:boss_chest",
            room_type="boss_chest",
            stage="completed",
            payload={
                "act_id": "act1",
                "node_id": "boss_chest",
                "next_node_ids": [],
                "next_act_id": "act2",
            },
            is_resolved=True,
            rewards=[],
        ),
    )

    running, next_session, message = route_menu_choice("2", session=session)

    assert running is True
    assert next_session.menu_state.mode == "inspect_root"
    assert next_session.menu_state.inspect_parent_mode == "root"
    assert next_session.menu_state.inspect_item_id is None
    assert "资料总览" in message


def test_inspect_root_can_open_deck_and_return() -> None:
    session = replace(start_session(seed=5), menu_state=MenuState(mode="inspect_root"))

    _running, deck_session, deck_message = route_menu_choice("2", session=session)
    _running, back_session, back_message = route_menu_choice(str(len(deck_session.run_state.deck) + 1), session=deck_session)

    assert deck_session.menu_state.mode == "inspect_deck"
    assert deck_session.menu_state.inspect_parent_mode == "root"
    assert deck_session.menu_state.inspect_item_id == "deck"
    assert "牌组列表" in deck_message
    assert back_session.menu_state.mode == "inspect_root"
    assert back_session.menu_state.inspect_parent_mode == "root"
    assert back_session.menu_state.inspect_item_id is None
    assert "资料总览" in back_message


def test_inspect_deck_can_return_to_parent_root_menu() -> None:
    session = start_session(seed=5)

    _running, inspect_session, _message = route_menu_choice("3", session=session)
    _running, deck_session, _message = route_menu_choice("2", session=inspect_session)
    _running, back_session, _message = route_menu_choice(str(len(deck_session.run_state.deck) + 1), session=deck_session)
    _running, root_session, root_message = route_menu_choice("10", session=back_session)

    assert inspect_session.menu_state.mode == "inspect_root"
    assert deck_session.menu_state.mode == "inspect_deck"
    assert deck_session.menu_state.inspect_parent_mode == "root"
    assert deck_session.menu_state.inspect_item_id == "deck"
    assert back_session.menu_state.mode == "inspect_root"
    assert back_session.menu_state.inspect_parent_mode == "root"
    assert root_session.menu_state.mode == "root"
    assert "出牌" in root_message
    assert "查看战场" not in root_message


def test_non_combat_inspect_deck_can_open_card_detail_and_return() -> None:
    session = replace(start_session(seed=5), room_state=_event_room(), menu_state=MenuState(mode="inspect_root", inspect_parent_mode="root"))

    _running, deck_session, deck_message = route_menu_choice("2", session=session)
    _running, detail_session, detail_message = route_menu_choice("1", session=deck_session)
    _running, back_to_list_session, back_to_list_message = route_menu_choice("1", session=detail_session)
    _running, back_to_root_session, back_to_root_message = route_menu_choice("2", session=detail_session)

    assert deck_session.menu_state.mode == "inspect_deck"
    assert deck_session.menu_state.inspect_parent_mode == "root"
    assert deck_session.menu_state.inspect_item_id == "deck"
    assert deck_message.splitlines()[0] == "牌组列表"
    assert detail_session.menu_state.mode == "inspect_card_detail"
    assert detail_session.menu_state.inspect_parent_mode == "inspect_deck"
    assert detail_session.menu_state.inspect_item_id == "strike#1"
    assert detail_message.splitlines()[0] == "卡牌详情"
    assert back_to_list_session.menu_state.mode == "inspect_deck"
    assert back_to_list_session.menu_state.inspect_parent_mode == "root"
    assert back_to_list_session.menu_state.inspect_item_id == "deck"
    assert back_to_list_message.splitlines()[0] == "牌组列表"
    assert back_to_root_session.menu_state.mode == "inspect_root"
    assert back_to_root_session.menu_state.inspect_parent_mode == "root"
    assert back_to_root_session.menu_state.inspect_item_id is None
    assert back_to_root_message.splitlines()[0] == "资料总览"


def test_resolved_reward_root_enters_select_reward_directly() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            stage="completed",
            is_resolved=True,
            rewards=["gold:11", "card_offer:anger"],
        ),
    )

    _running, claim_menu_session, claim_menu_message = route_menu_choice("1", session=session)

    assert claim_menu_session.menu_state.mode == "select_reward"
    assert claim_menu_session.room_state.rewards == ["gold:11", "card_offer:anger"]
    assert "奖励:" in claim_menu_message
    assert "奖励主页" not in claim_menu_message


def test_legacy_reward_inspect_mode_redirects_to_current_claim_flow() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            stage="completed",
            is_resolved=True,
            rewards=["gold:11", "card_offer:anger"],
        ),
        menu_state=MenuState(mode="inspect_reward_detail", inspect_parent_mode="inspect_reward_list", inspect_item_id="gold:11"),
    )

    _running, next_session, message = route_menu_choice("1", session=session)

    assert next_session.menu_state.mode == "select_reward"
    assert "奖励:" in message
    assert "奖励主页" not in message


def test_claiming_partial_rewards_keeps_reward_menu_open_until_empty() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(
            start_session(seed=5).room_state,
            stage="completed",
            is_resolved=True,
            rewards=["gold:11", "card_offer:anger"],
        ),
        menu_state=MenuState(mode="select_reward"),
    )

    _running, after_gold_session, after_gold_message = route_menu_choice("1", session=session)
    _running, after_card_session, after_card_message = route_menu_choice("1", session=after_gold_session)

    assert after_gold_session.menu_state.mode == "select_reward"
    assert after_gold_session.room_state.rewards == ["card_offer:anger"]
    assert "奖励:" in after_gold_message
    assert after_card_session.menu_state.mode == "root"
    assert after_card_session.room_state.rewards == []
    assert "奖励:" not in after_card_message


def test_claiming_boss_gold_keeps_boss_reward_menu_open_until_relic_is_picked() -> None:
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
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper"],
                    "claimed_relic_id": None,
                },
            },
        ),
        menu_state=MenuState(mode="select_boss_reward"),
    )

    _running, next_session, message = route_menu_choice("1", session=session)

    assert next_session.menu_state.mode == "select_boss_reward"
    assert next_session.room_state.payload["boss_rewards"]["claimed_gold"] is True
    assert next_session.room_state.payload["boss_rewards"]["claimed_relic_id"] is None
    assert "Boss奖励:" in message


def test_claiming_boss_relic_returns_to_boss_reward_menu_when_gold_is_unclaimed() -> None:
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
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper"],
                    "claimed_relic_id": None,
                },
            },
        ),
        menu_state=MenuState(mode="select_boss_relic"),
    )

    _running, next_session, message = route_menu_choice("1", session=session)

    assert next_session.menu_state.mode == "select_boss_reward"
    assert next_session.room_state.payload["boss_rewards"]["claimed_gold"] is False
    assert next_session.room_state.payload["boss_rewards"]["claimed_relic_id"] == "black_blood"
    assert "Boss奖励:" in message


def test_inspect_leaf_pages_keep_transition_messages_consistent() -> None:
    session = start_session(seed=5)

    _running, inspect_session, _message = route_menu_choice("3", session=session)
    _running, stats_session, stats_message = route_menu_choice("1", session=inspect_session)
    _running, stats_back_session, stats_back_message = route_menu_choice("1", session=stats_session)
    _running, relic_session, relic_message = route_menu_choice("3", session=stats_back_session)
    _running, relic_back_session, relic_back_message = route_menu_choice(
        str(len(relic_session.run_state.relics) + 1),
        session=relic_session,
    )

    assert stats_session.menu_state.mode == "inspect_stats"
    assert stats_session.menu_state.inspect_item_id == "stats"
    assert stats_message.splitlines()[0] == "角色状态"
    assert stats_back_session.menu_state.mode == "inspect_root"
    assert stats_back_message.splitlines()[0] == "资料总览"
    assert relic_session.menu_state.mode == "inspect_relics"
    assert relic_session.menu_state.inspect_item_id == "relics"
    assert relic_message.splitlines()[0] == "遗物列表"
    assert relic_back_session.menu_state.mode == "inspect_root"
    assert relic_back_message.splitlines()[0] == "资料总览"


def test_inspect_relic_branch_round_trip_keeps_mode_and_parent_state() -> None:
    session = start_session(seed=5)

    _running, inspect_session, _inspect_message = route_menu_choice("3", session=session)
    _running, relic_list_session, relic_list_message = route_menu_choice("3", session=inspect_session)
    _running, detail_session, detail_message = route_menu_choice("1", session=relic_list_session)
    _running, back_to_list_session, back_to_list_message = route_menu_choice("1", session=detail_session)
    _running, back_to_root_session, back_to_root_message = route_menu_choice("2", session=detail_session)

    assert relic_list_session.menu_state.mode == "inspect_relics"
    assert relic_list_session.menu_state.inspect_parent_mode == "root"
    assert relic_list_session.menu_state.inspect_item_id == "relics"
    assert relic_list_message.splitlines()[0] == "遗物列表"
    assert detail_session.menu_state.mode == "inspect_relic_detail"
    assert detail_session.menu_state.inspect_parent_mode == "inspect_relics"
    assert detail_session.menu_state.inspect_item_id == "burning_blood"
    assert detail_message.splitlines()[0] == "遗物详情"
    assert back_to_list_session.menu_state.mode == "inspect_relics"
    assert back_to_list_session.menu_state.inspect_parent_mode == "root"
    assert back_to_list_session.menu_state.inspect_item_id == "relics"
    assert back_to_list_message.splitlines()[0] == "遗物列表"
    assert back_to_root_session.menu_state.mode == "inspect_root"
    assert back_to_root_session.menu_state.inspect_parent_mode == "root"
    assert back_to_root_session.menu_state.inspect_item_id is None
    assert back_to_root_message.splitlines()[0] == "资料总览"


def test_combat_inspect_root_includes_potions_hand_enemy_pages_and_back() -> None:
    base_session = start_session(seed=5)
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, potions=["fire_potion"]),
        menu_state=MenuState(mode="inspect_root", inspect_parent_mode="root"),
    )

    _running, potion_session, potion_message = route_menu_choice("4", session=session)
    _running, hand_session, hand_message = route_menu_choice("5", session=session)
    _running, enemy_session, enemy_message = route_menu_choice("9", session=session)
    _running, root_session, root_message = route_menu_choice("10", session=session)

    assert potion_session.menu_state.mode == "inspect_potions"
    assert potion_message.splitlines()[0] == "药水列表"
    assert hand_session.menu_state.mode == "inspect_hand"
    assert hand_message.splitlines()[0] == "手牌列表"
    assert enemy_session.menu_state.mode == "inspect_enemy_list"
    assert enemy_message.splitlines()[0] == "敌人列表"
    assert root_session.menu_state.mode == "root"
    assert "出牌" in root_message
    assert "查看战场" not in root_message


def test_combat_inspect_card_branch_round_trip_keeps_mode_and_parent_state() -> None:
    session = start_session(seed=5)
    expected_first_hand_card = session.room_state.payload["combat_state"]["hand"][0]

    _running, inspect_session, inspect_message = route_menu_choice("3", session=session)
    _running, hand_session, hand_message = route_menu_choice("5", session=inspect_session)
    _running, detail_session, detail_message = route_menu_choice("1", session=hand_session)
    _running, back_to_list_session, back_to_list_message = route_menu_choice("1", session=detail_session)
    _running, back_to_root_session, back_to_root_message = route_menu_choice("2", session=detail_session)

    assert inspect_session.menu_state.mode == "inspect_root"
    assert inspect_message.splitlines()[0] == "资料总览"
    assert hand_session.menu_state.mode == "inspect_hand"
    assert hand_session.menu_state.inspect_parent_mode == "inspect_root"
    assert hand_session.menu_state.inspect_item_id == "hand"
    assert hand_message.splitlines()[0] == "手牌列表"
    assert detail_session.menu_state.mode == "inspect_card_detail"
    assert detail_session.menu_state.inspect_parent_mode == "inspect_hand"
    assert detail_session.menu_state.inspect_item_id == expected_first_hand_card
    assert detail_message.splitlines()[0] == "卡牌详情"
    assert back_to_list_session.menu_state.mode == "inspect_hand"
    assert back_to_list_session.menu_state.inspect_parent_mode == "inspect_root"
    assert back_to_list_session.menu_state.inspect_item_id is None
    assert back_to_list_message.splitlines()[0] == "卡牌列表"
    assert back_to_root_session.menu_state.mode == "inspect_root"
    assert back_to_root_session.menu_state.inspect_parent_mode == "root"
    assert back_to_root_session.menu_state.inspect_item_id is None
    assert back_to_root_message.splitlines()[0] == "资料总览"


def test_combat_inspect_enemy_branch_round_trip_keeps_mode_and_parent_state() -> None:
    session = start_session(seed=5)

    _running, inspect_session, _inspect_message = route_menu_choice("3", session=session)
    _running, enemy_list_session, enemy_list_message = route_menu_choice("9", session=inspect_session)
    _running, detail_session, detail_message = route_menu_choice("1", session=enemy_list_session)
    _running, back_to_list_session, back_to_list_message = route_menu_choice("1", session=detail_session)
    _running, back_to_root_session, back_to_root_message = route_menu_choice("2", session=detail_session)

    assert enemy_list_session.menu_state.mode == "inspect_enemy_list"
    assert enemy_list_session.menu_state.inspect_parent_mode == "inspect_root"
    assert enemy_list_session.menu_state.inspect_item_id == "enemies"
    assert enemy_list_message.splitlines()[0] == "敌人列表"
    assert detail_session.menu_state.mode == "inspect_enemy_detail"
    assert detail_session.menu_state.inspect_parent_mode == "inspect_enemy_list"
    assert detail_session.menu_state.inspect_item_id == "enemy-1"
    assert detail_message.splitlines()[0] == "敌人详情"
    assert back_to_list_session.menu_state.mode == "inspect_enemy_list"
    assert back_to_list_session.menu_state.inspect_parent_mode == "inspect_root"
    assert back_to_list_session.menu_state.inspect_item_id == "enemies"
    assert back_to_list_message.splitlines()[0] == "敌人列表"
    assert back_to_root_session.menu_state.mode == "inspect_root"
    assert back_to_root_session.menu_state.inspect_parent_mode == "root"
    assert back_to_root_session.menu_state.inspect_item_id is None
    assert back_to_root_message.splitlines()[0] == "资料总览"


def test_non_combat_root_menu_can_enter_inspect_root() -> None:
    session = replace(start_session(seed=5), room_state=_event_room())

    running, next_session, message = route_menu_choice("2", session=session)

    assert running is True
    assert next_session.menu_state.mode == "inspect_root"
    assert next_session.menu_state.inspect_parent_mode == "root"
    assert next_session.menu_state.inspect_item_id is None
    assert "资料总览" in message


def test_non_combat_inspect_root_can_open_potions_and_return() -> None:
    base_session = replace(start_session(seed=5), room_state=_event_room())
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, potions=["fire_potion"]),
        menu_state=MenuState(mode="inspect_root", inspect_parent_mode="root"),
    )

    _running, potion_session, potion_message = route_menu_choice("4", session=session)
    _running, back_session, back_message = route_menu_choice("1", session=potion_session)
    _running, root_session, root_message = route_menu_choice("5", session=back_session)

    assert potion_session.menu_state.mode == "inspect_potions"
    assert potion_session.menu_state.inspect_parent_mode == "root"
    assert potion_session.menu_state.inspect_item_id == "potions"
    assert potion_message.splitlines()[0] == "药水列表"
    assert back_session.menu_state.mode == "inspect_root"
    assert back_message.splitlines()[0] == "资料总览"
    assert root_session.menu_state.mode == "root"
    assert "事件操作" in root_message


def test_shop_root_menu_can_enter_inspect_and_return_to_shop() -> None:
    session = replace(start_session(seed=5), room_state=_shop_room(), menu_state=MenuState(mode="shop_root"))

    _running, inspect_session, inspect_message = route_menu_choice("4", session=session)
    _running, stats_session, stats_message = route_menu_choice("1", session=inspect_session)
    _running, inspect_back_session, inspect_back_message = route_menu_choice("1", session=stats_session)
    _running, shop_session, shop_message = route_menu_choice("5", session=inspect_back_session)

    assert inspect_session.menu_state.mode == "inspect_root"
    assert inspect_session.menu_state.inspect_parent_mode == "shop_root"
    assert inspect_message.splitlines()[0] == "资料总览"
    assert stats_session.menu_state.mode == "inspect_stats"
    assert stats_session.menu_state.inspect_parent_mode == "shop_root"
    assert stats_message.splitlines()[0] == "角色状态"
    assert inspect_back_session.menu_state.mode == "inspect_root"
    assert inspect_back_message.splitlines()[0] == "资料总览"
    assert shop_session.menu_state.mode == "shop_root"
    assert "商店操作" in shop_message


def test_rest_root_menu_can_enter_inspect_and_return_to_rest() -> None:
    session = replace(start_session(seed=5), room_state=_rest_room(), menu_state=MenuState(mode="rest_root"))

    _running, inspect_session, inspect_message = route_menu_choice("3", session=session)
    _running, relics_session, relics_message = route_menu_choice("3", session=inspect_session)
    _running, inspect_back_session, inspect_back_message = route_menu_choice(
        str(len(relics_session.run_state.relics) + 1),
        session=relics_session,
    )
    _running, rest_session, rest_message = route_menu_choice("5", session=inspect_back_session)

    assert inspect_session.menu_state.mode == "inspect_root"
    assert inspect_session.menu_state.inspect_parent_mode == "rest_root"
    assert inspect_message.splitlines()[0] == "资料总览"
    assert relics_session.menu_state.mode == "inspect_relics"
    assert relics_session.menu_state.inspect_parent_mode == "rest_root"
    assert relics_message.splitlines()[0] == "遗物列表"
    assert inspect_back_session.menu_state.mode == "inspect_root"
    assert inspect_back_message.splitlines()[0] == "资料总览"
    assert rest_session.menu_state.mode == "rest_root"
    assert "休息点操作" in rest_message
