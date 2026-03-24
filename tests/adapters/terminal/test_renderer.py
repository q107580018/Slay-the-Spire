from dataclasses import replace

from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.content.provider import StarterContentProvider


def test_render_room_exports_rich_panelized_combat_screen() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "╭" in output or "┌" in output
    assert "当前能量" in output
    assert "抽牌堆" in output
    assert "可选操作" in output


def test_combat_root_screen_keeps_full_context_and_hand_panel() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "回合 1" in output
    assert "当前能量 3" in output
    assert "玩家状态" in output
    assert "敌人意图" in output
    assert "手牌" in output
    assert "1. 打击 (1)" in output


def test_select_card_only_replaces_bottom_menu_panel() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=replace(MenuState(), mode="select_card"),
    )

    assert "当前能量 3" in output
    assert "手牌" in output
    assert "返回上一步" in output


def test_select_reward_screen_shows_reward_list_after_victory() -> None:
    session = start_session(seed=5)
    room_state = replace(
        session.room_state,
        stage="completed",
        is_resolved=True,
        rewards=["gold:20", "card:reward_strike"],
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=replace(MenuState(), mode="select_reward"),
    )

    assert "奖励" in output
    assert "金币 20" in output
    assert "卡牌 打击+" in output
    assert "返回上一步" in output


def test_victory_root_screen_keeps_rewards_visible() -> None:
    session = start_session(seed=5)
    room_state = replace(
        session.room_state,
        stage="completed",
        is_resolved=True,
        rewards=["gold:20", "card:reward_strike"],
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "查看奖励" in output
    assert "金币 20" in output
    assert "卡牌 打击+" in output


def test_event_screen_shows_body_and_options_panel() -> None:
    session = start_session(seed=5)
    session = replace(
        session,
        room_state=replace(
            session.room_state,
            room_type="event",
            payload={
                "node_id": "event",
                "room_kind": "event",
                "event_id": "shining_light",
                "next_node_ids": ["boss"],
            },
        ),
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(mode="select_event_choice"),
    )

    assert "事件" in output
    assert "发光的牧师向你献上力量。" in output
    assert "1. 接受" in output
    assert "战斗摘要" not in output
    assert "敌人意图" not in output


def test_event_root_screen_uses_event_actions() -> None:
    session = start_session(seed=5)
    session = replace(
        session,
        room_state=replace(
            session.room_state,
            room_type="event",
            payload={
                "node_id": "event",
                "room_kind": "event",
                "event_id": "shining_light",
                "next_node_ids": ["boss"],
            },
        ),
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "查看事件" in output
    assert "进行选择" in output
    assert "查看当前状态" not in output
    assert "前往下一个房间" not in output


def test_resolved_room_with_rewards_uses_reward_screen() -> None:
    session = start_session(seed=5)
    resolved_room = replace(session.room_state, is_resolved=True, rewards=["gold:12", "card:reward_strike"])
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=resolved_room,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "奖励" in output
    assert "金币 12" in output
    assert "卡牌 打击+" in output
    assert "战斗摘要" not in output
    assert "当前能量" not in output
    assert "敌人意图" not in output


def test_resolved_event_screen_shows_result_panel_and_rewards() -> None:
    session = start_session(seed=5)
    room_state = replace(
        session.room_state,
        room_type="event",
        stage="completed",
        is_resolved=True,
        rewards=["gold:12", "card:reward_strike"],
        payload={
            **session.room_state.payload,
            "room_kind": "event",
            "event_id": "shining_light",
            "result": "gain_upgrade",
        },
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "结果" in output
    assert "获得升级" in output
    assert "奖励" in output
    assert "金币 12" in output
    assert "卡牌 打击+" in output
    assert "查看奖励" in output
    assert "前往下一个房间" in output
    assert "事件正文" not in output
    assert "查看事件" not in output
    assert "进行选择" not in output
    assert "战斗摘要" not in output
    assert "敌人意图" not in output


def test_select_next_room_uses_branch_selection_screen() -> None:
    session = start_session(seed=5)
    resolved_room = replace(
        session.room_state,
        is_resolved=True,
        rewards=["gold:12", "card:reward_strike"],
        payload={
            **session.room_state.payload,
            "next_node_ids": ["hallway", "event"],
        },
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=resolved_room,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(mode="select_next_room"),
    )

    assert "请选择下一个房间" in output
    assert "1. 走廊" in output
    assert "2. 事件" in output
    assert "奖励" not in output
    assert "金币 12" not in output
    assert "战斗摘要" not in output
