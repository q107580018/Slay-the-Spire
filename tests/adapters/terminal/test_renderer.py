from dataclasses import replace

from rich.console import Console

from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.adapters.terminal.theme import TERMINAL_THEME
from slay_the_spire.adapters.terminal.screens.non_combat import render_full_map_panel
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.act_state import ActNodeState, ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.statuses import StatusState


def _provider(session):
    return StarterContentProvider(session.content_root)


def _export(renderable) -> str:
    console = Console(
        width=100,
        record=True,
        force_terminal=False,
        color_system=None,
        theme=TERMINAL_THEME,
    )
    console.print(renderable)
    return console.export_text(clear=False)


def _hexaghost_combat_state(*, round_number: int) -> CombatState:
    return CombatState(
        round_number=round_number,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player",
            hp=80,
            max_hp=80,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="hexaghost",
                hp=250,
                max_hp=250,
                block=0,
                statuses=[],
            ),
        ],
        effect_queue=[],
        log=[],
    )


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
    assert "手牌（能量 3）" in output
    assert "敌人意图" in output
    assert "战斗记录" in output
    assert "4. 查看资料" in output
    assert "5. 保存游戏" in output
    assert "6. 读取存档" in output
    assert "7. 退出游戏" in output


def test_select_card_menu_shows_current_energy_in_menu_title() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="select_card"),
        run_phase=session.run_phase,
    )

    assert "手牌（当前能量 3）:" in output
    assert "1. 打击 费用1 - 造成 6 伤害" in output


def test_combat_root_screen_uses_current_round_enemy_intent() -> None:
    session = start_session(seed=5)
    combat_state = _hexaghost_combat_state(round_number=2)
    room_state = replace(
        session.room_state,
        room_type="boss",
        stage="waiting_input",
        payload={
            "node_id": "r12c0",
            "room_kind": "boss",
            "next_node_ids": [],
            "combat_state": combat_state.to_dict(),
        },
        is_resolved=False,
        rewards=[],
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase=session.run_phase,
    )

    assert "6 段攻击（每段伤害随生命变化）" not in output
    assert "造成 6 伤害" in output
    assert "向弃牌堆加" in output
    assert "1 张灼伤（回合结束时若仍在手中，失去 2 点生命）" in output


def test_combat_renderer_shows_recent_battle_log_entries() -> None:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state.log = [
        "你打出 打击，对 绿史莱姆 造成 6 伤害。",
        "绿史莱姆攻击你 3，实际受到 3。",
    ]
    room_state = replace(session.room_state, payload={**session.room_state.payload, "combat_state": combat_state.to_dict()})

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase=session.run_phase,
    )

    assert "战斗记录" in output
    assert "你打出 打击，对 绿史莱姆 造成 6 伤害。" in output
    assert "绿史莱姆攻击你 3，实际受到 3。" in output


def test_non_combat_renderer_shows_act2_masked_bandits_copy() -> None:
    session = start_session(seed=5)
    room_state = RoomState(
        room_id="act2:event",
        room_type="event",
        stage="waiting_input",
        payload={
            "act_id": "act2",
            "node_id": "r3c1",
            "room_kind": "event",
            "event_id": "masked_bandits",
            "next_node_ids": ["r4c0"],
        },
        is_resolved=False,
        rewards=[],
    )
    act_state = replace(session.act_state, act_id="act2")

    output = render_room(
        run_state=replace(session.run_state, current_act_id="act2"),
        act_state=act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="select_event_choice"),
        run_phase="active",
    )

    assert "蒙面强盗" in output
    assert "交出 75 金币" in output


def test_combat_renderer_uses_dynamic_enemy_intent_for_sleeping_enemy() -> None:
    session = start_session(seed=5)
    combat_state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
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
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="lagavulin",
                hp=109,
                max_hp=109,
                block=0,
                statuses=[StatusState(status_id="sleeping", stacks=2)],
            )
        ],
        effect_queue=[],
        log=[],
    )
    room_state = RoomState(
        room_id="act1:elite",
        room_type="elite",
        stage="waiting_input",
        payload={"node_id": "elite", "room_kind": "elite", "combat_state": combat_state.to_dict(), "next_node_ids": ["boss"]},
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

    assert "沉睡巨像" in output
    assert "意图: 沉睡 2 回合" in output


def test_combat_renderer_uses_dynamic_enemy_intent_for_awake_enemy() -> None:
    session = start_session(seed=5)
    combat_state = CombatState(
        round_number=4,
        energy=3,
        hand=[],
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
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="lagavulin",
                hp=109,
                max_hp=109,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )
    room_state = RoomState(
        room_id="act1:elite",
        room_type="elite",
        stage="waiting_input",
        payload={"node_id": "elite", "room_kind": "elite", "combat_state": combat_state.to_dict(), "next_node_ids": ["boss"]},
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

    assert "沉睡巨像" in output
    assert "意图: 造成 18 伤害" in output


def test_combat_renderer_shows_inspect_root_menu_when_in_inspect_mode() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_root", inspect_parent_mode="root"),
        run_phase=session.run_phase,
    )

    assert "资料总览" in output
    assert "查看战场" not in output
    assert "1. 角色状态" in output
    assert "4. 药水" in output
    assert "10. 返回上一步" in output


def test_combat_renderer_shows_deck_list_and_back_choice_in_inspect_mode() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_deck", inspect_parent_mode="root", inspect_item_id="deck"),
        run_phase=session.run_phase,
    )

    assert "牌组列表" in output
    assert "查看战场" not in output
    assert "打击" in output
    assert "返回上一步" in output


def test_combat_renderer_distinguishes_inspect_stats_and_relics_pages() -> None:
    base_session = start_session(seed=5)
    session = replace(base_session, run_state=replace(base_session.run_state, gold=123))
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
    assert "遗物列表" not in stats_output
    assert "遗物列表" in relics_output
    assert "当前遗物:" in relics_output
    assert "燃烧之血" in relics_output
    assert "角色状态" not in relics_output


def test_combat_renderer_shows_inspect_slot_after_resolved_combat_with_rewards() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, stage="completed", is_resolved=True, rewards=["gold:99"]),
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase=session.run_phase,
    )

    assert "1. 查看奖励" in output
    assert "2. 领取奖励" in output
    assert "3. 前往下一个房间" in output
    assert "4. 查看资料" in output
    assert "5. 保存游戏" in output
    assert "6. 读取存档" in output
    assert "7. 退出游戏" in output
    assert "4. 保存游戏" not in output


def test_non_combat_renderer_shows_reward_home_screen() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, stage="completed", is_resolved=True, rewards=["gold:11", "card_offer:anger"]),
        menu_state=MenuState(mode="inspect_reward_root", inspect_parent_mode="root"),
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=session.menu_state,
        run_phase=session.run_phase,
    )

    assert "奖励主页" in output
    assert "1. 领取奖励" in output
    assert "2. 查看奖励详情" in output
    assert "3. 返回" in output
    assert "查看资料" not in output


def test_non_combat_renderer_shows_reward_list_screen() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, stage="completed", is_resolved=True, rewards=["gold:11", "card_offer:anger"]),
        menu_state=MenuState(mode="inspect_reward_list", inspect_parent_mode="inspect_reward_root"),
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=session.menu_state,
        run_phase=session.run_phase,
    )

    assert "奖励详情列表" in output
    assert "1. gold:11" in output
    assert "2. card_offer:anger" in output
    assert "3. 返回奖励主页" in output


def test_non_combat_renderer_shows_reward_detail_screen() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, stage="completed", is_resolved=True, rewards=["gold:11", "card_offer:anger"]),
        menu_state=MenuState(mode="inspect_reward_detail", inspect_parent_mode="inspect_reward_list", inspect_item_id="gold:11"),
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=session.menu_state,
        run_phase=session.run_phase,
    )

    assert "奖励详情" in output
    assert "奖励 ID: gold:11" in output
    assert "金币 +11" in output
    assert "返回奖励列表" in output
    assert "返回奖励主页" in output


def test_boss_reward_renderer_shows_reward_actions_on_root_screen() -> None:
    session = replace(
        start_session(seed=5),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "room_kind": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase=session.run_phase,
    )

    assert "Boss奖励" in output
    assert "1. 查看奖励" in output
    assert "2. 领取奖励" in output
    assert "3. 查看资料" in output
    assert "4. 保存游戏" in output
    assert "前往下一个房间" not in output


def test_boss_reward_renderer_shows_boss_reward_menu() -> None:
    session = replace(
        start_session(seed=5),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "room_kind": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="select_boss_reward"),
        run_phase=session.run_phase,
    )

    assert "Boss奖励" in output
    assert "金币奖励：+99" in output
    assert "金币领取状态：未领取" in output
    assert "1. 领取金币 +99" in output
    assert "2. 选择遗物" in output
    assert "3. 返回上一步" in output


def test_boss_reward_renderer_shows_boss_relic_menu() -> None:
    session = replace(
        start_session(seed=5),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "room_kind": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": True,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="select_boss_relic"),
        run_phase=session.run_phase,
    )

    assert "Boss奖励" in output
    assert "1. 黑色之血" in output
    assert "2. 虚空质" in output
    assert "3. 咖啡滴滤器" in output
    assert "4. 融合之锤" in output
    assert "5. 返回上一步" in output


def test_boss_reward_renderer_shows_claimed_status_labels() -> None:
    session = replace(
        start_session(seed=5),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "room_kind": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": True,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": "black_blood",
                },
            },
            is_resolved=True,
            rewards=[],
        ),
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="select_boss_reward"),
        run_phase=session.run_phase,
    )

    assert "金币领取状态：已领取" in output
    assert "已选遗物：黑色之血" in output
    assert "1. 已领取金币" in output
    assert "2. 已选择遗物" in output


def test_combat_renderer_shows_inspect_slot_after_resolved_combat_without_rewards() -> None:
    session = replace(
        start_session(seed=5),
        room_state=replace(start_session(seed=5).room_state, stage="completed", is_resolved=True, rewards=[]),
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase=session.run_phase,
    )

    assert "1. 前往下一个房间" in output
    assert "2. 查看资料" in output
    assert "3. 保存游戏" in output
    assert "4. 读取存档" in output
    assert "5. 退出游戏" in output
    assert "2. 保存游戏" not in output


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
    assert "POS" in output
    assert "ROW" in output
    assert "NEXT" in output
    assert "L00 |" in output
    assert "L12 |" in output
    assert "当前金币" in output


def test_full_map_panel_lists_reachable_nodes_and_topology_hint() -> None:
    act_state = ActState(
        act_id="act1",
        current_node_id="r2c0",
        nodes=[
            ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=["r1c0"]),
            ActNodeState(node_id="r1c0", row=1, col=0, room_type="event", next_node_ids=["r2c0", "r2c1"]),
            ActNodeState(node_id="r2c0", row=2, col=0, room_type="event", next_node_ids=["r3c1", "r3c2"]),
            ActNodeState(node_id="r2c1", row=2, col=1, room_type="combat", next_node_ids=["r3c0", "r3c1"]),
            ActNodeState(node_id="r3c0", row=3, col=0, room_type="shop", next_node_ids=[]),
            ActNodeState(node_id="r3c1", row=3, col=1, room_type="combat", next_node_ids=[]),
            ActNodeState(node_id="r3c2", row=3, col=2, room_type="combat", next_node_ids=[]),
        ],
        visited_node_ids=["start", "r1c0", "r2c0"],
        enemy_pool_id="act1_basic",
        elite_pool_id="act1_elites",
        boss_pool_id="act1_bosses",
        event_pool_id="act1_events",
    )

    output = _export(render_full_map_panel(act_state))

    assert "NEXT  [战斗] r3c1 (3,1), [战斗] r3c2 (3,2)" in output
    assert "TIP | 只有 [可达] 节点可以作为下一步" in output
    assert "线条只表示整张地图的连接关系" in output


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
    assert "7. 查看资料" in output
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


def test_shop_renderer_shows_current_gold_and_affordance_statuses() -> None:
    session = replace(start_session(seed=5), run_state=replace(start_session(seed=5).run_state, gold=60))
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "node_id": "r3c1",
            "cards": [
                {"offer_id": "card-1", "card_id": "strike", "price": 50},
                {"offer_id": "card-2", "card_id": "defend", "price": 75},
            ],
            "relics": [{"offer_id": "relic-1", "relic_id": "burning_blood", "price": 150, "sold": True}],
            "potions": [],
            "remove_price": 75,
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

    assert "当前金币" in output
    assert "60" in output
    assert "[可购买]" in output
    assert "[金币不足]" in output
    assert "[已购买]" in output
    assert "6. 查看资料" in output


def test_shop_remove_renderer_uses_localized_card_labels() -> None:
    session = start_session(seed=5)
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="select_remove_card",
        payload={
            "node_id": "r3c1",
            "remove_candidates": ["strike#1", "defend#2"],
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
        menu_state=MenuState(mode="shop_remove_card"),
        run_phase="active",
    )

    assert "选择要移除的卡牌" in output
    assert "打击 (strike#1)" in output
    assert "防御 (defend#2)" in output
    assert "1. strike#1" not in output
    assert "2. defend#2" not in output


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
    assert "3. 查看资料" in root_output
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
    assert "卡牌 耸肩无视" in output


def test_reward_renderer_uses_concrete_card_offer_labels() -> None:
    session = start_session(seed=5)
    reward_room = RoomState(
        room_id="act1:hallway",
        room_type="combat",
        stage="completed",
        payload={"node_id": "r1c0", "next_node_ids": ["r2c0"]},
        is_resolved=True,
        rewards=["card_offer:pommel_strike", "card_offer:bash", "card_offer:anger"],
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=reward_room,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase="active",
    )

    assert "卡牌 柄击" in output
    assert "卡牌 重击" in output
    assert "卡牌 愤怒" in output
    assert "card_offer:" not in output


def test_map_renderer_marks_current_and_reachable_nodes_inline() -> None:
    session = start_session(seed=5)
    act_state = ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=["r1c0", "r1c1"]),
            ActNodeState(node_id="r1c0", row=1, col=0, room_type="event", next_node_ids=["r2c0"]),
            ActNodeState(node_id="r1c1", row=1, col=1, room_type="shop", next_node_ids=["r2c0"]),
            ActNodeState(node_id="r2c0", row=2, col=0, room_type="boss", next_node_ids=[]),
        ],
        visited_node_ids=["start"],
        enemy_pool_id="act1_basic",
        elite_pool_id="act1_elites",
        boss_pool_id="act1_bosses",
        event_pool_id="act1_events",
    )
    room_state = RoomState(
        room_id="act1:event",
        room_type="event",
        stage="waiting_input",
        payload={"node_id": "start", "room_kind": "event", "event_id": "shining_light", "next_node_ids": ["r1c0", "r1c1"]},
        is_resolved=False,
        rewards=[],
    )

    output = render_room(
        run_state=session.run_state,
        act_state=act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase="active",
    )

    assert ">战斗<" in output
    assert "[事件]" in output
    assert "[商店]" in output
    assert "[1]" not in output


def test_map_renderer_draws_continuous_connectors_for_branch_and_merge() -> None:
    session = start_session(seed=5)
    act_state = ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(node_id="start", row=0, col=1, room_type="combat", next_node_ids=["r1c0", "r1c2"]),
            ActNodeState(node_id="r1c0", row=1, col=0, room_type="event", next_node_ids=["r2c1"]),
            ActNodeState(node_id="r1c2", row=1, col=2, room_type="shop", next_node_ids=["r2c1"]),
            ActNodeState(node_id="r2c1", row=2, col=1, room_type="boss", next_node_ids=[]),
        ],
        visited_node_ids=["start"],
        enemy_pool_id="act1_basic",
        elite_pool_id="act1_elites",
        boss_pool_id="act1_bosses",
        event_pool_id="act1_events",
    )
    room_state = RoomState(
        room_id="act1:event",
        room_type="event",
        stage="waiting_input",
        payload={"node_id": "start", "room_kind": "event", "event_id": "shining_light", "next_node_ids": ["r1c0", "r1c2"]},
        is_resolved=False,
        rewards=[],
    )

    output = render_room(
        run_state=session.run_state,
        act_state=act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase="active",
    )

    assert "─" in output or "|" in output
    assert any(char in output for char in ("┌", "┐", "└", "┘", "┼", "├", "┤"))


def test_map_renderer_uses_terminal_ruler_and_legend_layout() -> None:
    session = start_session(seed=5)
    act_state = ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=["r1c0", "r1c1"]),
            ActNodeState(node_id="r1c0", row=1, col=0, room_type="event", next_node_ids=["r2c0"]),
            ActNodeState(node_id="r1c1", row=1, col=1, room_type="elite", next_node_ids=["r2c0"]),
            ActNodeState(node_id="r2c0", row=2, col=0, room_type="boss", next_node_ids=[]),
        ],
        visited_node_ids=["start"],
        enemy_pool_id="act1_basic",
        elite_pool_id="act1_elites",
        boss_pool_id="act1_bosses",
        event_pool_id="act1_events",
    )
    room_state = RoomState(
        room_id="act1:event",
        room_type="event",
        stage="waiting_input",
        payload={"node_id": "start", "room_kind": "event", "event_id": "shining_light", "next_node_ids": ["r1c0", "r1c1"]},
        is_resolved=False,
        rewards=[],
    )

    output = render_room(
        run_state=session.run_state,
        act_state=act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(),
        run_phase="active",
    )

    assert "POS  (0, 0)" in output
    assert "ROW  L00..L02" in output
    assert "L02 |" in output
    assert "L00 |" in output
    assert "TYPE | 战斗 精英 Boss 事件 商店 休息" in output
    assert "STAT | >当前< 所在 [可达] 下一步 节点 其他" in output
    assert "[精英]" in output
    assert "Boss" in output


def test_map_renderer_applies_light_rich_styles_to_priority_tokens() -> None:
    act_state = ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=["r1c0", "r1c1"]),
            ActNodeState(node_id="r1c0", row=1, col=0, room_type="event", next_node_ids=["r2c0"]),
            ActNodeState(node_id="r1c1", row=1, col=1, room_type="elite", next_node_ids=["r2c0"]),
            ActNodeState(node_id="r2c0", row=2, col=0, room_type="boss", next_node_ids=[]),
        ],
        visited_node_ids=["start"],
        enemy_pool_id="act1_basic",
        elite_pool_id="act1_elites",
        boss_pool_id="act1_bosses",
        event_pool_id="act1_events",
    )

    panel = render_full_map_panel(act_state)
    text_lines = [renderable for renderable in panel.renderable.renderables if hasattr(renderable, "plain")]
    styled_lines = {line.plain: {span.style for span in line.spans} for line in text_lines}

    assert "POS  (0, 0)" in styled_lines
    assert "TYPE | 战斗 精英 Boss 事件 商店 休息" in styled_lines
    assert "map.metric.label" in styled_lines["POS  (0, 0)"]
    assert "map.legend.label" in styled_lines["TYPE | 战斗 精英 Boss 事件 商店 休息"]

    current_line_styles = next(styles for line, styles in styled_lines.items() if ">战斗<" in line)
    assert "map.node.current" in current_line_styles
    assert "map.room.combat" in current_line_styles

    reachable_line_styles = next(
        styles
        for line, styles in styled_lines.items()
        if line.startswith("L01 |") and "[事件]" in line and "[精英]" in line
    )
    assert "map.node.reachable" in reachable_line_styles
    assert "map.room.event" in reachable_line_styles
    assert "map.room.elite" in reachable_line_styles

    boss_line_styles = next(styles for line, styles in styled_lines.items() if line.startswith("L02 |") and "Boss" in line)
    assert "map.room.boss" in boss_line_styles


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
