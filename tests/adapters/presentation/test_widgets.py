from rich.console import Console

from slay_the_spire.adapters.presentation.theme import TERMINAL_THEME
from slay_the_spire.adapters.presentation.renderer import render_room
from slay_the_spire.adapters.presentation.widgets import (
    active_power_label,
    render_block,
    render_hp_bar,
    render_menu,
    render_statuses,
    preview_enemy_intent,
    summarize_card_effects,
    summarize_effect,
)
from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.content.registries import EnemyDef
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.statuses import StatusState


def _export(renderable) -> str:
    console = Console(
        width=80,
        record=True,
        force_terminal=False,
        color_system=None,
        theme=TERMINAL_THEME,
    )
    console.print(renderable)
    return console.export_text(clear=False)


def test_render_hp_bar_uses_full_and_empty_blocks() -> None:
    output = _export(render_hp_bar(current=18, maximum=30))
    assert "█" in output
    assert "░" in output
    assert "18/30" in output


def test_terminal_theme_uses_original_hp_bar_colors() -> None:
    assert str(TERMINAL_THEME.styles["hp.high"]) == "green"
    assert str(TERMINAL_THEME.styles["hp.medium"]) == "yellow"
    assert str(TERMINAL_THEME.styles["hp.low"]) == "bold red"


def test_render_statuses_returns_compact_chinese_labels() -> None:
    output = _export(render_statuses([StatusState(status_id="vulnerable", stacks=2)]))
    assert "易伤 2" in output


def test_render_statuses_renders_strength_labels() -> None:
    output = _export(render_statuses([StatusState(status_id="strength", stacks=3)]))
    assert "力量 3" in output


def test_render_statuses_uses_empty_label_for_no_statuses() -> None:
    output = _export(render_statuses([]))
    assert "无" in output


def test_render_block_uses_shield_icon() -> None:
    output = _export(render_block(5))
    assert "🛡 5" in output


def test_render_menu_preserves_numbered_choices() -> None:
    output = _export(render_menu(["1. 查看战场", "2. 出牌"]))
    assert "1. 查看战场" in output
    assert "2. 出牌" in output


def test_summarize_card_effects_compacts_damage_and_block() -> None:
    output = summarize_card_effects(
        [
            {"type": "damage", "amount": 6},
            {"type": "block", "amount": 5},
        ]
    )

    assert output == "造成 6 伤害 / 获得 5 格挡"


def test_summarize_card_effects_localizes_card_copy_effect() -> None:
    output = summarize_card_effects(
        [
            {"type": "damage", "amount": 6},
            {"type": "create_card_copy", "card_id": "anger", "zone": "discard_pile"},
        ]
    )

    assert output == "造成 6 伤害 / 复制一张卡牌放入弃牌堆"


def test_summarize_effect_localizes_strength_effect() -> None:
    output = summarize_effect({"type": "strength", "amount": 2})

    assert output == "获得 2 力量"


def test_summarize_effect_localizes_strength_loss_effect() -> None:
    output = summarize_effect({"type": "strength", "amount": -2})

    assert output == "失去 2 力量"


def test_summarize_effect_localizes_dexterity_loss_effect() -> None:
    output = summarize_effect({"type": "dexterity", "amount": -2})

    assert output == "失去 2 敏捷"


def test_active_power_label_localizes_battle_trance() -> None:
    assert active_power_label("battle_trance") == "战斗专注"


def test_active_power_label_localizes_berserk() -> None:
    assert active_power_label("berserk") == "狂暴"


def test_summarize_effect_localizes_battle_trance_power_effect() -> None:
    output = summarize_effect(
        {"type": "add_power", "power_id": "battle_trance", "amount": 1}
    )

    assert output == "本回合内不能再抽牌"


def test_summarize_effect_localizes_barricade_power_effect() -> None:
    output = summarize_effect(
        {"type": "add_power", "power_id": "barricade", "amount": 1}
    )

    assert output == "你的格挡不会在回合开始时失去"


def test_preview_enemy_intent_uses_move_table_without_state() -> None:
    enemy_def = EnemyDef(
        id="slime",
        name="绿史莱姆",
        hp=12,
        move_table=[
            {
                "move": "tackle",
                "weight": 1,
                "effects": [{"type": "damage", "amount": 3}],
            }
        ],
        intent_policy="weighted_random",
    )

    output = preview_enemy_intent(enemy_def)

    assert output == "造成 3 伤害"


def test_preview_enemy_intent_uses_first_move_for_multi_move_enemy() -> None:
    session = start_session(seed=5)
    enemy_def = StarterContentProvider(session.content_root).enemies().get("jaw_worm")

    output = preview_enemy_intent(enemy_def)

    assert output == "造成 7 伤害"


def test_summarize_effect_exhaust_all_in_hand_damage_mentions_per_card_damage() -> None:
    output = summarize_effect(
        {"type": "exhaust_all_in_hand_damage", "amount_per_card": 7}
    )

    assert output == "消耗手中所有牌。每张被消耗的牌造成 7 伤害"


def test_preview_enemy_intent_shows_readable_summary_for_divider() -> None:
    enemy_def = EnemyDef(
        id="hexaghost",
        name="六火幽魂",
        hp=250,
        move_table=[{"move": "divider", "effects": []}],
        intent_policy="scripted",
    )

    output = preview_enemy_intent(enemy_def)

    assert output == "6 段攻击（每段伤害随生命变化）"


def test_render_room_uses_shared_box_and_no_duplicate_hp_text() -> None:
    session = start_session(seed=1)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "╭" not in output
    assert "╮" not in output
    assert "┌" in output
    assert "┐" in output
    assert output.count("80/80") == 1
    for enemy in combat_state.enemies:
        assert output.count(f"{enemy.hp}/{enemy.max_hp}") == 1


def test_render_room_select_target_menu_uses_shared_hp_bar_contract() -> None:
    session = start_session(seed=1)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(mode="select_target"),
    )

    assert "选择敌人" in output
    assert "12/12 12/12" not in output


def test_summarize_effect_localizes_damage_equal_to_block() -> None:
    assert (
        summarize_effect({"type": "damage_equal_to_block"})
        == "造成等同于当前格挡的伤害"
    )


def test_summarize_effect_localizes_put_top_of_deck_from_discard() -> None:
    assert (
        summarize_effect({"type": "put_top_of_deck_from_discard"})
        == "将弃牌堆中的 1 张牌放到牌堆顶"
    )


def test_summarize_effect_localizes_double_tap_power() -> None:
    assert (
        summarize_effect({"type": "add_power", "power_id": "double_tap", "amount": 1})
        == "本回合下一张攻击牌额外触发一次"
    )


def test_summarize_effect_localizes_double_strength() -> None:
    assert summarize_effect({"type": "double_strength"}) == "使力量翻倍"


def test_summarize_effect_localizes_spot_weakness_strength() -> None:
    output = summarize_effect({"type": "spot_weakness_strength", "amount": 3})
    assert "力量" in output
    assert "3" in output


def test_summarize_effect_localizes_damage_on_kill_gain_max_hp() -> None:
    output = summarize_effect(
        {"type": "damage_on_kill_gain_max_hp", "amount": 10, "hp_gain": 3}
    )
    assert "伤害" in output
    assert "最大生命" in output


def test_summarize_effect_localizes_dark_embrace_power() -> None:
    assert (
        summarize_effect({"type": "add_power", "power_id": "dark_embrace", "amount": 1})
        == "每当有牌被消耗时，抽 1 张牌"
    )


def test_summarize_effect_localizes_rage_power() -> None:
    assert (
        summarize_effect({"type": "add_power", "power_id": "rage", "amount": 3})
        == "每次打出攻击牌时获得 3 格挡"
    )


def test_summarize_effect_localizes_rupture_power() -> None:
    assert (
        summarize_effect({"type": "add_power", "power_id": "rupture", "amount": 1})
        == "以牌的效果失去生命时，获得 1 层力量"
    )


def test_summarize_effect_localizes_feel_no_pain_power() -> None:
    assert (
        summarize_effect({"type": "add_power", "power_id": "feel_no_pain", "amount": 3})
        == "每当有牌被消耗时，获得 3 格挡"
    )


def test_summarize_effect_localizes_juggernaut_power() -> None:
    assert (
        summarize_effect({"type": "add_power", "power_id": "juggernaut", "amount": 5})
        == "获得格挡时对随机敌人造成 5 伤害"
    )


def test_summarize_effect_localizes_brutality_power() -> None:
    assert (
        summarize_effect({"type": "add_power", "power_id": "brutality", "amount": 1})
        == "每回合开始时失去 1 生命并抽 1 张牌"
    )


def test_summarize_effect_localizes_corruption_power() -> None:
    assert (
        summarize_effect({"type": "add_power", "power_id": "corruption", "amount": 1})
        == "所有技能牌耗能变为0。所有技能牌在被打出时被消耗。"
    )


def test_summarize_effect_localizes_berserk_power() -> None:
    assert (
        summarize_effect({"type": "add_power", "power_id": "berserk", "amount": 1})
        == "每回合开始时获得 1 点能量"
    )


def test_summarize_effect_localizes_flex_power() -> None:
    assert (
        summarize_effect({"type": "add_power", "power_id": "flex_power", "amount": 2})
        == "本回合结束时失去 2 层力量"
    )


def test_summarize_effect_uses_chinese_for_unknown_effect_type() -> None:
    assert summarize_effect({"type": "some_untranslated_effect"}) == "未知效果"


def test_render_room_inspect_enemy_detail_uses_shared_hp_bar_contract() -> None:
    session = start_session(seed=1)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    first_enemy = combat_state.enemies[0]
    first_enemy_name = (
        StarterContentProvider(session.content_root)
        .enemies()
        .get(first_enemy.enemy_id)
        .name
    )
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(
            mode="inspect_enemy_detail",
            inspect_parent_mode="inspect_enemy_list",
            inspect_item_id="enemy-1",
        ),
    )

    assert "敌人详情" in output
    assert first_enemy_name in output
    assert (
        f"{first_enemy.hp}/{first_enemy.max_hp} {first_enemy.hp}/{first_enemy.max_hp}"
        not in output
    )
