from __future__ import annotations

import shutil
from pathlib import Path

from slay_the_spire.app.cli import main
from slay_the_spire.app.session import interactive_loop, route_command, start_session
from slay_the_spire.adapters.terminal.prompts import prompt_for_room


class _InputPort:
    def __init__(self, commands: list[str]) -> None:
        self._commands = commands

    def read(self, prompt: str = "") -> str:
        del prompt
        return self._commands.pop(0)


def test_main_new_run_renders_first_room(capsys) -> None:
    exit_code = main(["new", "--seed", "5"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run seed: 5" in captured.out
    assert "Act: act1" in captured.out
    assert "Room: start" in captured.out


def test_main_new_run_accepts_explicit_content_root(tmp_path: Path, capsys) -> None:
    content_root = Path(__file__).resolve().parents[2] / "content"
    temp_content_root = tmp_path / "content"
    shutil.copytree(content_root, temp_content_root)

    exit_code = main(["new", "--seed", "5", "--content-root", str(temp_content_root)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Run seed: 5" in captured.out
    assert temp_content_root.exists()


def test_custom_content_root_is_preserved_across_next(tmp_path: Path) -> None:
    content_root = Path(__file__).resolve().parents[2] / "content"
    temp_content_root = tmp_path / "content"
    shutil.copytree(content_root, temp_content_root)

    session = start_session(seed=5, content_root=temp_content_root)
    _, next_session, _ = route_command("next", session=session)

    assert next_session.content_root == temp_content_root
    assert next_session.room_state.payload["node_id"] == "hallway"


def test_default_content_root_uses_packaged_data(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    from slay_the_spire.app.session import default_content_root

    content_root = default_content_root()

    assert content_root.name == "content"
    assert (content_root / "characters" / "ironclad.json").exists()


def test_session_loop_routes_basic_commands() -> None:
    session = start_session(seed=5)
    assert prompt_for_room(session.room_state) == "Command (look, next, help, quit): "

    running, next_session, message = route_command("look", session=session)
    assert running is True
    assert next_session is not session
    assert next_session.command_history == ["look"]
    assert "Run seed: 5" in message

    running, advanced_session, message = route_command("next", session=session)
    assert running is True
    assert advanced_session is not session
    assert advanced_session.room_state.payload["node_id"] == "hallway"
    assert "Room:" in message

    result = interactive_loop(session=session, input_port=_InputPort(["help", "quit"]))
    assert result.outputs[0].startswith("Run seed: 5")
    assert result.outputs[1] == "Commands: look, next, help, quit"
    assert result.outputs[2] == "Goodbye."
    assert result.final_session.command_history == ["help", "quit"]
