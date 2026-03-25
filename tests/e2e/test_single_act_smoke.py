from __future__ import annotations

import re
import shutil
from pathlib import Path
from dataclasses import replace

from slay_the_spire.app.cli import main
from slay_the_spire.app.session import SessionState, interactive_loop, route_command, route_menu_choice, start_session
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState


class _InputPort:
    def __init__(self, commands: list[str]) -> None:
        self._commands = commands
        self.prompts: list[str] = []

    def read(self, prompt: str = "") -> str:
        assert isinstance(prompt, str)
        self.prompts.append(prompt)
        return self._commands.pop(0)


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_main_new_run_renders_first_room(capsys, monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt="": "6")

    exit_code = main(["new", "--seed", "5"])

    captured = capsys.readouterr()
    output = _strip_ansi(captured.out)

    assert exit_code == 0
    assert "种子: 5" in output
    assert "章节: 第一幕" in output
    assert "房间: 起点" in output
    assert "6. 退出游戏" in output
    assert "已退出游戏。" in output


def test_main_new_run_accepts_explicit_content_root(tmp_path: Path, capsys, monkeypatch) -> None:
    content_root = Path(__file__).resolve().parents[2] / "content"
    temp_content_root = tmp_path / "content"
    shutil.copytree(content_root, temp_content_root)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "6")

    exit_code = main(["new", "--seed", "5", "--content-root", str(temp_content_root)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "种子: 5" in captured.out
    assert temp_content_root.exists()


def test_custom_content_root_is_preserved_across_next(tmp_path: Path) -> None:
    content_root = Path(__file__).resolve().parents[2] / "content"
    temp_content_root = tmp_path / "content"
    shutil.copytree(content_root, temp_content_root)

    session = start_session(seed=5, content_root=temp_content_root)
    _, session, _ = route_command("play 1", session=session)
    _, session, _ = route_command("play 2", session=session)
    _, next_session, _ = route_command("next", session=session)

    assert next_session.content_root == temp_content_root
    assert next_session.room_state.payload["node_id"] == "hallway"


def test_default_content_root_uses_packaged_data(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    from slay_the_spire.app.session import default_content_root

    content_root = default_content_root()

    assert content_root.name == "content"
    assert (content_root / "characters" / "ironclad.json").exists()


def test_player_hp_persists_across_combat_rooms() -> None:
    session = start_session(seed=5)
    _, session, _ = route_command("end", session=session)
    _, session, _ = route_command("play 4", session=session)
    _, session, _ = route_command("play 4", session=session)
    _, session, message = route_command("next", session=session)

    assert session.room_state.payload["node_id"] == "hallway"
    assert session.run_state.current_hp == 77
    assert "玩家生命: 77/80" in message


def _session_with_two_enemies_for_target_selection() -> tuple[SessionState, _InputPort]:
    session = start_session(seed=5)
    combat_state = CombatState.from_dict(session.room_state.payload["combat_state"])
    combat_state = CombatState(
        round_number=combat_state.round_number,
        energy=combat_state.energy,
        hand=list(combat_state.hand),
        draw_pile=list(combat_state.draw_pile),
        discard_pile=list(combat_state.discard_pile),
        exhaust_pile=list(combat_state.exhaust_pile),
        player=combat_state.player,
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="slime",
                hp=12,
                max_hp=12,
                block=0,
                statuses=[],
            ),
            EnemyState(
                instance_id="enemy-2",
                enemy_id="jaw_worm",
                hp=16,
                max_hp=16,
                block=0,
                statuses=[],
            ),
        ],
        effect_queue=list(combat_state.effect_queue),
        log=list(combat_state.log),
    )
    session = replace(
        session,
        room_state=replace(
            session.room_state,
            payload={**session.room_state.payload, "combat_state": combat_state.to_dict()},
        ),
    )
    return session, _InputPort(["2", "1", "2", "6"])


def test_session_loop_uses_chinese_numbered_menus() -> None:
    session = start_session(seed=5)
    result = interactive_loop(session=session, input_port=_InputPort(["2", "1", "2", "1", "3", "6"]))

    assert "╭" in result.outputs[0] or "┌" in result.outputs[0]
    assert "当前能量: 3" in result.outputs[0]
    assert "抽牌堆: 4" in result.outputs[0]
    assert "1. 查看战场" in result.outputs[0]
    assert "2. 出牌" in result.outputs[0]
    assert "1. 打击 费用1" in result.outputs[1]
    assert "6. 返回上一步" in result.outputs[1]
    assert "绿史莱姆 生命: 6/12" in result.outputs[2]
    assert "1. 打击 费用1" in result.outputs[3]
    assert "房间已完成: 是" in result.outputs[4]
    assert "1. 查看奖励" in result.outputs[4]
    assert "房间: 走廊" in result.outputs[5]
    assert result.outputs[6] == "已退出游戏。"
    assert result.final_session.command_history == ["2", "1", "2", "1", "3", "6"]


def test_session_loop_routes_through_target_selection_menu() -> None:
    session, input_port = _session_with_two_enemies_for_target_selection()

    result = interactive_loop(session=session, input_port=input_port)
    final_combat_state = CombatState.from_dict(result.final_session.room_state.payload["combat_state"])

    assert any("选择目标:" in output and "当前卡牌: 打击" in output and "2. 颚虫" in output for output in result.outputs)
    assert any("绿史莱姆 生命: 12/12" in output and "颚虫 生命: 10/16" in output for output in result.outputs)
    assert final_combat_state.enemies[0].hp == 12
    assert final_combat_state.enemies[1].hp == 10
    assert result.outputs[-1] == "已退出游戏。"
    assert all(isinstance(prompt, str) for prompt in input_port.prompts)
    assert result.final_session.command_history == ["2", "1", "2", "6"]


def test_session_loop_routes_through_reward_selection_menu() -> None:
    session = start_session(seed=5)
    input_port = _InputPort(["2", "1", "2", "1", "2", "1", "6"])

    result = interactive_loop(session=session, input_port=input_port)

    assert any("房间已完成: 是" in output for output in result.outputs)
    assert any("1. 查看奖励" in output for output in result.outputs)
    assert any("1. 金币 15" in output for output in result.outputs)
    assert any("2. 卡牌 打击+" in output for output in result.outputs)
    assert any("奖励" in output and "3. 返回上一步" in output and "1. 金币 15" in output for output in result.outputs)
    assert result.final_session.room_state.rewards == ["card:reward_strike"]
    assert result.final_session.room_state.payload["claimed_reward_ids"] == ["gold:15"]
    assert result.outputs[-1] == "已退出游戏。"
    assert all(isinstance(prompt, str) for prompt in input_port.prompts)
    assert result.final_session.command_history == ["2", "1", "2", "1", "2", "1", "6"]


def test_branch_event_save_and_load_use_chinese_numbered_menus(tmp_path: Path) -> None:
    save_path = tmp_path / "save.json"
    session = start_session(seed=5, save_path=save_path)
    input_port = _InputPort(
        [
            "2",  # 出牌
            "1",  # 打击
            "2",  # 出牌
            "1",  # 打击
            "3",  # 前往走廊
            "2",  # 出牌
            "1",  # 打击
            "2",  # 出牌
            "1",  # 打击
            "3",  # 选择下一个房间
            "2",  # 事件
            "2",  # 进行选择
            "1",  # 接受
            "4",  # 保存游戏
            "5",  # 读取存档
            "6",  # 退出
        ]
    )

    result = interactive_loop(
        session=session,
        input_port=input_port,
    )

    assert any("请选择下一个房间:" in output for output in result.outputs)
    assert any("2. 事件" in output for output in result.outputs)
    assert any("房间: 事件" in output for output in result.outputs)
    assert any("事件正文" in output for output in result.outputs)
    assert any("发光的牧师向你献上力量。" in output for output in result.outputs)
    assert any("事件选项:" in output for output in result.outputs)
    assert any("1. 接受" in output for output in result.outputs)
    assert any("奖励" in output and "结果: 获得升级" in output for output in result.outputs)
    assert any("1. 事件结果 获得升级" in output for output in result.outputs)
    assert any("房间已完成: 是" in output for output in result.outputs)
    assert any("已保存到" in output for output in result.outputs)
    assert any("已从存档恢复。" in output for output in result.outputs)
    assert result.outputs[-1] == "已退出游戏。"
    assert all(isinstance(prompt, str) for prompt in input_port.prompts)
    assert result.final_session.command_history == ["2", "1", "2", "1", "3", "2", "1", "2", "1", "3", "2", "2", "1", "4", "5", "6"]


def test_cli_load_command_restores_saved_session(tmp_path: Path, capsys, monkeypatch) -> None:
    save_path = tmp_path / "save.json"
    session = start_session(seed=5, save_path=save_path)
    _, session, _ = route_menu_choice("2", session=session)
    _, session, _ = route_menu_choice("1", session=session)
    _, session, _ = route_menu_choice("2", session=session)
    _, session, _ = route_menu_choice("1", session=session)
    _, session, _ = route_menu_choice("4", session=session)

    monkeypatch.setattr("builtins.input", lambda _prompt="": "6")

    exit_code = main(["load", "--save-path", str(save_path)])

    captured = capsys.readouterr()
    output = _strip_ansi(captured.out)

    assert exit_code == 0
    assert "房间已完成: 是" in output
    assert "1. 查看奖励" in output
