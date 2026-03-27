from dataclasses import replace
from pathlib import Path

from slay_the_spire.adapters.terminal.inspect import (
    format_card_detail_lines,
    format_card_detail_menu,
    format_reward_detail_lines,
    format_relic_detail_lines,
    render_reward_detail_panel,
)
from slay_the_spire.adapters.terminal.inspect_registry import format_shared_inspect_menu
from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
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


def test_format_card_detail_lines_include_cost_effects_and_upgrade() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    lines = format_card_detail_lines("bash#1", registry)

    assert any("费用" in line.plain for line in lines)
    assert any("造成 8 伤害" in line.plain for line in lines)
    assert any("施加 2 易伤" in line.plain for line in lines)
    assert any("升级为" in line.plain for line in lines)
    assert any("重击+" in line.plain for line in lines)


def test_format_relic_detail_lines_include_passive_effect_description() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    lines = format_relic_detail_lines("burning_blood", registry)

    assert any("燃烧之血" in line.plain for line in lines)
    assert any("回复 6 点生命" in line.plain for line in lines)
    assert any("战斗结束后" in line.plain for line in lines)
    assert all("on_combat_end" not in line.plain for line in lines)


def test_format_relic_detail_lines_translate_gold_bonus_effect() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    lines = format_relic_detail_lines("golden_idol", registry)

    assert any("金神像" in line.plain for line in lines)
    assert any("金币" in line.plain for line in lines)
    assert all("event_gold_bonus" not in line.plain for line in lines)


def test_format_card_detail_lines_explain_burn_end_turn_penalty() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    lines = format_card_detail_lines("burn#1", registry)

    assert any("灼伤" in line.plain for line in lines)
    assert any("回合结束时若仍在手中，失去 2 点生命" in line.plain for line in lines)


def test_inspect_module_does_not_define_heal_specific_localization() -> None:
    inspect_source = Path(__file__).resolve().parents[3] / "src" / "slay_the_spire" / "adapters" / "terminal" / "inspect.py"

    assert "heal" not in inspect_source.read_text(encoding="utf-8")


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


def test_shared_inspect_menu_registry_formats_shared_modes_for_both_contexts() -> None:
    session = replace(start_session(seed=5), room_state=_event_room())
    registry = _provider(session)

    combat_card_detail_menu = format_shared_inspect_menu(
        mode="inspect_card_detail",
        context="combat",
        run_state=session.run_state,
        room_state=session.room_state,
        registry=registry,
    )
    non_combat_card_detail_menu = format_shared_inspect_menu(
        mode="inspect_card_detail",
        context="non_combat",
        run_state=session.run_state,
        room_state=session.room_state,
        registry=registry,
    )
    deck_menu = format_shared_inspect_menu(
        mode="inspect_deck",
        context="combat",
        run_state=session.run_state,
        room_state=session.room_state,
        registry=registry,
    )

    assert combat_card_detail_menu == format_card_detail_menu()
    assert non_combat_card_detail_menu == format_card_detail_menu()
    assert deck_menu == ["输入上方编号查看卡牌详情", f"{len(session.run_state.deck) + 1}. 返回上一步"]


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
    assert "牌组:" not in deck_output
    assert "遗物" in relics_output
    assert "燃烧之血" in relics_output
    assert "药水" in potions_output
    assert "火焰药水" in potions_output


def test_render_non_combat_card_detail_does_not_fall_back_to_root_menu() -> None:
    session = replace(start_session(seed=5), room_state=_event_room())

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_card_detail", inspect_parent_mode="inspect_deck", inspect_item_id="strike#1"),
        run_phase=session.run_phase,
    )

    assert "卡牌详情" in output
    assert "名称: 打击" in output
    assert "返回卡牌列表" in output
    assert "前往下一个房间" not in output


def test_format_reward_detail_lines_include_reward_id_and_human_readable_labels() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    gold_lines = format_reward_detail_lines("gold:11", registry)
    card_offer_lines = format_reward_detail_lines("card_offer:anger", registry)
    card_lines = format_reward_detail_lines("card:anger", registry)
    relic_lines = format_reward_detail_lines("relic:burning_blood", registry)

    assert any("奖励 ID: gold:11" in line.plain for line in gold_lines)
    assert any("金币 +11" in line.plain for line in gold_lines)
    assert any("奖励 ID: card_offer:anger" in line.plain for line in card_offer_lines)
    assert any("愤怒" in line.plain for line in card_offer_lines)
    assert any("奖励 ID: card:anger" in line.plain for line in card_lines)
    assert any("愤怒" in line.plain for line in card_lines)
    assert any("奖励 ID: relic:burning_blood" in line.plain for line in relic_lines)
    assert any("燃烧之血" in line.plain for line in relic_lines)


def test_format_reward_detail_lines_localize_event_rewards() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    gain_upgrade_lines = format_reward_detail_lines("event:gain_upgrade", registry)
    nothing_lines = format_reward_detail_lines("event:nothing", registry)
    other_lines = format_reward_detail_lines("event:unknown_outcome", registry)

    assert any("奖励 ID: event:gain_upgrade" in line.plain for line in gain_upgrade_lines)
    assert any("事件结果" in line.plain for line in gain_upgrade_lines)
    assert any("获得升级" in line.plain for line in gain_upgrade_lines)
    assert any("奖励 ID: event:nothing" in line.plain for line in nothing_lines)
    assert any("什么也没有发生" in line.plain for line in nothing_lines)
    assert any("奖励 ID: event:unknown_outcome" in line.plain for line in other_lines)
    assert any("事件结果 unknown_outcome" in line.plain for line in other_lines)


def test_render_reward_detail_panel_shows_reward_detail_and_return_choices() -> None:
    session = start_session(seed=5)
    registry = StarterContentProvider(session.content_root)

    panel = render_reward_detail_panel("gold:11", registry)
    panel_text = "\n".join(item.plain for item in panel.renderable.renderables)

    assert "奖励详情" in panel.title
    assert "奖励 ID" in panel_text
    assert "gold:11" in panel_text
    assert "金币 +11" in panel_text


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
    session = start_session(seed=1)

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


def test_render_combat_inspect_list_pages_do_not_repeat_full_list_in_footer() -> None:
    session = start_session(seed=1)

    draw_pile_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_draw_pile", inspect_parent_mode="root", inspect_item_id="draw_pile"),
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

    assert draw_pile_output.count("抽牌堆列表") == 1
    assert draw_pile_output.count("5. 重击 | 费用 2 | 类型 攻击 | 造成 8 伤害 / 施加 2 易伤") == 1
    assert enemy_list_output.count("敌人列表") == 1
    assert enemy_list_output.count("1. 绿史莱姆 | 生命: 12/12 | 格挡: 0 | 状态: 无 | 当前意图: 造成 3 伤害") == 1


def test_render_hexaghost_enemy_detail_localizes_divider_summary() -> None:
    session = start_session(seed=1)
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
                enemy_id="hexaghost",
                hp=250,
                max_hp=250,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )
    room_state = replace(
        session.room_state,
        payload={**session.room_state.payload, "combat_state": combat_state.to_dict()},
    )

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_enemy_detail", inspect_parent_mode="inspect_enemy_list", inspect_item_id="enemy-1"),
        run_phase=session.run_phase,
    )

    assert "当前意图摘要: 6 段攻击（每段伤害随生命变化）" in output
    assert "招式表预览: divider: 6 段攻击（每段伤害随生命变化）" in output
