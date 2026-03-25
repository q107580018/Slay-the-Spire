from dataclasses import replace

from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.room_state import RoomState


def _provider(session):
    return StarterContentProvider(session.content_root)


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


def test_render_non_combat_inspect_root_shows_shared_sections() -> None:
    session = replace(start_session(seed=5), room_state=_event_room(), menu_state=MenuState(mode="inspect_root"))

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=session.menu_state,
        run_phase=session.run_phase,
    )

    assert "资料总览" in output
    assert "1. 属性" in output
    assert "2. 牌组" in output
    assert "3. 遗物" in output
    assert "4. 药水" in output


def test_render_non_combat_inspect_pages_show_stats_deck_relics_and_potions() -> None:
    base_session = replace(start_session(seed=5), room_state=_event_room())
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, potions=["fire_potion"]),
    )

    stats_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_stats", inspect_parent_mode="root", inspect_item_id="stats"),
        run_phase=session.run_phase,
    )
    deck_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_deck", inspect_parent_mode="root", inspect_item_id="deck"),
        run_phase=session.run_phase,
    )
    relics_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_relics", inspect_parent_mode="root", inspect_item_id="relics"),
        run_phase=session.run_phase,
    )
    potions_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_potions", inspect_parent_mode="root", inspect_item_id="potions"),
        run_phase=session.run_phase,
    )

    assert "属性" in stats_output
    assert "当前生命" in stats_output
    assert "牌组" in deck_output
    assert "打击" in deck_output
    assert "遗物" in relics_output
    assert "燃烧之血" in relics_output
    assert "药水" in potions_output
    assert "火焰药水" in potions_output


def test_render_combat_inspect_root_includes_piles_and_enemy_details() -> None:
    session = replace(start_session(seed=5), menu_state=MenuState(mode="inspect_root"))

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=session.menu_state,
        run_phase=session.run_phase,
    )

    assert "1. 角色状态" in output
    assert "2. 牌组列表" in output
    assert "3. 遗物列表" in output
    assert "4. 药水" in output
    assert "5. 手牌" in output
    assert "6. 抽牌堆" in output
    assert "7. 弃牌堆" in output
    assert "8. 消耗堆" in output
    assert "9. 敌人详情" in output
    assert "10. 返回上一步" in output
    assert "返回战斗" not in output


def test_render_combat_inspect_pages_show_pile_summary_card_detail_and_enemy_detail() -> None:
    session = start_session(seed=5)

    hand_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_hand", inspect_parent_mode="root", inspect_item_id="hand"),
        run_phase=session.run_phase,
    )
    card_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(
            mode="inspect_card_detail",
            inspect_parent_mode="inspect_hand",
            inspect_item_id=session.room_state.payload["combat_state"]["hand"][0],
        ),
        run_phase=session.run_phase,
    )
    enemy_list_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_enemy_list", inspect_parent_mode="inspect_root", inspect_item_id="enemies"),
        run_phase=session.run_phase,
    )
    enemy_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_enemy_detail", inspect_parent_mode="inspect_enemy_list", inspect_item_id="enemy-1"),
        run_phase=session.run_phase,
    )

    assert "手牌列表" in hand_output
    assert "打击" in hand_output
    assert "费用 1" in hand_output
    assert "类型 攻击" in hand_output
    assert "造成 6 伤害" in hand_output
    assert "返回资料总览" in hand_output
    assert "卡牌详情" in card_output
    assert "名称: 打击" in card_output
    assert "实例 ID: strike#1" in card_output
    assert "费用: 1" in card_output
    assert "类型: 攻击" in card_output
    assert "是否可打出: 是" in card_output
    assert "完整效果: 造成 6 伤害" in card_output
    assert "升级目标: -" in card_output
    assert "返回卡牌列表" in card_output
    assert "敌人列表" in enemy_list_output
    assert "绿史莱姆" in enemy_list_output
    assert "生命:" in enemy_list_output
    assert "格挡:" in enemy_list_output
    assert "状态:" in enemy_list_output
    assert "当前意图:" in enemy_list_output
    assert "敌人详情" in enemy_output
    assert "绿史莱姆" in enemy_output
    assert "当前生命: 12/12" in enemy_output
    assert "当前格挡: 0" in enemy_output
    assert "当前状态: 无" in enemy_output
    assert "当前意图摘要:" in enemy_output
    assert "招式表预览:" in enemy_output
    assert "tackle" in enemy_output
    assert "返回敌人列表" in enemy_output


def test_render_combat_shared_inspect_pages_show_real_stats_and_relics() -> None:
    base_session = start_session(seed=5)
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, gold=123),
    )

    stats_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_stats", inspect_parent_mode="root", inspect_item_id="stats"),
        run_phase=session.run_phase,
    )
    relics_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_relics", inspect_parent_mode="root", inspect_item_id="relics"),
        run_phase=session.run_phase,
    )

    assert "角色状态" in stats_output
    assert "当前生命: 80/80" in stats_output
    assert "金币: 123" in stats_output
    assert "当前章节: act1" in stats_output
    assert "当前房间: 起点" in stats_output
    assert "当前处于角色状态查看。" not in stats_output
    assert "遗物列表" in relics_output
    assert "当前遗物:" in relics_output
    assert "燃烧之血" in relics_output
    assert "当前处于遗物列表查看。" not in relics_output
