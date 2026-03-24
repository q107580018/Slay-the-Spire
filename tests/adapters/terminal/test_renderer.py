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
