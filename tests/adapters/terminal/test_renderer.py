from dataclasses import replace

from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.room_state import RoomState


def _provider(session):
    return StarterContentProvider(session.content_root)


def test_combat_root_screen_keeps_full_context_and_hand_panel() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase=session.run_phase,
    )

    assert "当前能量" in output
    assert "手牌" in output
    assert "敌人意图" in output


def test_non_combat_renderer_shows_full_map_rows_and_current_position() -> None:
    session = start_session(seed=5)
    room_state = RoomState(
        room_id="act1:event",
        room_type="event",
        stage="waiting_input",
        payload={"node_id": "r1c0", "room_kind": "event", "event_id": "shining_light", "next_node_ids": ["r2c0"]},
        is_resolved=False,
        rewards=[],
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase="active",
    )

    assert "完整地图" in output
    assert "当前坐标" in output
    assert "第 0 层" in output
    assert "第 12 层" in output
    assert "当前金币" in output


def test_shop_renderer_shows_cards_relics_potions_and_remove_service() -> None:
    session = start_session(seed=5)
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "node_id": "r3c1",
            "cards": [
                {"offer_id": "card-1", "card_id": "strike", "price": 50},
                {"offer_id": "card-2", "card_id": "defend", "price": 50, "sold": True},
            ],
            "relics": [{"offer_id": "relic-1", "relic_id": "burning_blood", "price": 150}],
            "potions": [{"offer_id": "potion-1", "potion_id": "fire_potion", "price": 60}],
            "remove_price": 75,
            "remove_used": True,
            "next_node_ids": ["r4c0"],
        },
        is_resolved=False,
        rewards=[],
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="shop_root"),
        run_phase="active",
    )

    assert "商店" in output
    assert "卡牌商品" in output
    assert "遗物商品" in output
    assert "药水商品" in output
    assert "删牌服务" in output
    assert "当前金币" in output
    assert "打击" in output
    assert "防御" in output
    assert "火焰药水" in output
    assert "可购买" in output
    assert "金币不足" in output
    assert "已购买" in output
    assert "已使用" in output
    assert "strike" not in output
    assert "fire_potion" not in output
    assert "burning_blood" not in output


def test_rest_renderer_shows_root_and_upgrade_selection_states() -> None:
    session = start_session(seed=5)
    root_room = RoomState(
        room_id="act1:rest",
        room_type="rest",
        stage="waiting_input",
        payload={"node_id": "r5c0", "actions": ["rest", "smith"], "next_node_ids": ["r6c0"]},
        is_resolved=False,
        rewards=[],
    )
    root_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=root_room,
        registry=_provider(session),
        menu_state=MenuState(mode="rest_root"),
        run_phase="active",
    )
    upgrade_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=replace(root_room, stage="select_upgrade_card", payload={**root_room.payload, "upgrade_options": ["bash#9"]}),
        registry=_provider(session),
        menu_state=MenuState(mode="rest_upgrade_card"),
        run_phase="active",
    )

    assert "休息点" in root_output
    assert "休息" in root_output
    assert "锻造" in root_output
    assert "Rest" not in root_output
    assert "Smith" not in root_output
    assert "可升级卡牌" in upgrade_output
    assert "重击" in upgrade_output
    assert "bash#9" in upgrade_output


def test_reward_renderer_uses_concrete_gold_and_card_labels() -> None:
    session = start_session(seed=5)
    reward_room = RoomState(
        room_id="act1:hallway",
        room_type="combat",
        stage="completed",
        payload={"node_id": "r1c0", "next_node_ids": ["r2c0"]},
        is_resolved=True,
        rewards=["gold:11", "card:shrug_it_off"],
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=reward_room,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase="active",
    )

    assert "金币 +11" in output
    assert "卡牌 不屈意志" in output


def test_event_upgrade_menu_shows_card_name_with_instance_id() -> None:
    session = start_session(seed=5)
    room_state = RoomState(
        room_id="act1:event",
        room_type="event",
        stage="select_event_upgrade_card",
        payload={
            "node_id": "r1c1",
            "room_kind": "event",
            "event_id": "shining_light",
            "upgrade_options": ["bash#9"],
            "next_node_ids": ["r2c0"],
        },
        is_resolved=False,
        rewards=[],
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="event_upgrade_card"),
        run_phase="active",
    )

    assert "选择要升级的卡牌" in output
    assert "重击" in output
    assert "bash#9" in output


def test_victory_renderer_blocks_normal_room_menu() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=replace(session.room_state, stage="completed", is_resolved=True, rewards=[]),
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase="victory",
    )

    assert "胜利" in output
    assert "运行阶段" in output
    assert "Run Phase" not in output
    assert "Boss 已被击败" not in output
    assert "首领已被击败" in output
    assert "继续攀爬" not in output
    assert "出牌" not in output


def test_game_over_renderer_blocks_normal_room_menu() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=replace(session.run_state, current_hp=0),
        act_state=session.act_state,
        room_state=replace(session.room_state, stage="defeated"),
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase="game_over",
    )

    assert "游戏结束" in output
    assert "前往下一个房间" not in output
    assert "出牌" not in output
