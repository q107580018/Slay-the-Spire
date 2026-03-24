from rich.console import Console

from slay_the_spire.adapters.terminal.theme import TERMINAL_THEME
from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.adapters.terminal.widgets import (
    render_block,
    render_hp_bar,
    render_menu,
    render_statuses,
    preview_enemy_intent,
    summarize_card_effects,
)
from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.content.registries import EnemyDef
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


def test_render_statuses_returns_compact_chinese_labels() -> None:
    output = _export(render_statuses([StatusState(status_id="vulnerable", stacks=2)]))
    assert "易伤 2" in output


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


def test_preview_enemy_intent_uses_move_table_without_state() -> None:
    enemy_def = EnemyDef(
        id="slime",
        name="绿史莱姆",
        hp=12,
        move_table=[{"move": "tackle", "weight": 1, "effects": [{"type": "damage", "amount": 3}]}],
        intent_policy="weighted_random",
    )

    output = preview_enemy_intent(enemy_def)

    assert output == "造成 3 伤害"


def test_preview_enemy_intent_uses_first_move_for_multi_move_enemy() -> None:
    session = start_session(seed=5)
    enemy_def = StarterContentProvider(session.content_root).enemies().get("jaw_worm")

    output = preview_enemy_intent(enemy_def)

    assert output == "造成 5 伤害"


def test_render_room_uses_shared_box_and_no_duplicate_hp_text() -> None:
    session = start_session(seed=5)
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
    assert output.count("12/12") == 1


def test_render_room_select_target_menu_uses_shared_hp_bar_contract() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(mode="select_target"),
    )

    assert "选择目标" in output
    assert "12/12 12/12" not in output
