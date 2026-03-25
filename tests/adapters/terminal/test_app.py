from __future__ import annotations

from io import StringIO

from rich.console import Console

from slay_the_spire.adapters.terminal.app import RichTerminal, run_terminal_session
from slay_the_spire.adapters.terminal.theme import TERMINAL_THEME
from slay_the_spire.app.session import start_session


class _FakeTerminal:
    def __init__(self, commands: list[str]) -> None:
        self._commands = commands
        self.calls: list[tuple[str, object | None]] = []

    def clear(self) -> None:
        self.calls.append(("clear", None))

    def print(self, text: object) -> None:
        self.calls.append(("print", text))

    def read(self, prompt: str = "") -> str:
        self.calls.append(("read", prompt))
        return self._commands.pop(0)


def _printed_text(rendered: object | None) -> str:
    if rendered is None:
        return ""
    if isinstance(rendered, str):
        return rendered
    buffer = StringIO()
    console = Console(
        file=buffer,
        width=100,
        record=True,
        force_terminal=False,
        color_system=None,
        theme=TERMINAL_THEME,
    )
    console.print(rendered)
    return console.export_text(clear=False)


def test_run_terminal_session_clears_before_first_frame_and_after_each_command() -> None:
    session = start_session(seed=5)
    terminal = _FakeTerminal(["6"])

    result = run_terminal_session(session=session, terminal=terminal)

    assert result.final_session.command_history == ["6"]
    assert terminal.calls[0] == ("clear", None)
    assert terminal.calls[1][0] == "print"
    assert "房间: 起点" in _printed_text(terminal.calls[1][1])
    assert terminal.calls[2] == ("read", "请输入编号: ")
    assert terminal.calls[3] == ("clear", None)
    assert terminal.calls[4][0] == "print"
    assert "房间: 起点" in _printed_text(terminal.calls[4][1])
    assert terminal.calls[5] == ("print", "已退出游戏。")


def test_run_terminal_session_redraws_current_frame_before_flash_message() -> None:
    session = start_session(seed=5)
    terminal = _FakeTerminal(["9", "6"])

    run_terminal_session(session=session, terminal=terminal)

    assert terminal.calls[3] == ("clear", None)
    assert terminal.calls[4][0] == "print"
    assert "房间: 起点" in _printed_text(terminal.calls[4][1])
    assert terminal.calls[5] == ("print", "无效选项，请输入菜单编号。")


def test_rich_terminal_uses_project_theme_by_default() -> None:
    terminal = RichTerminal()

    assert str(terminal._console.get_style("hp.high")) == "green"
    assert terminal._console.no_color is False
    assert terminal._console.color_system == "standard"


def test_run_terminal_session_prints_rich_frame_instead_of_plain_text() -> None:
    session = start_session(seed=5)
    terminal = _FakeTerminal(["6"])

    run_terminal_session(session=session, terminal=terminal)

    assert terminal.calls[1][0] == "print"
    assert not isinstance(terminal.calls[1][1], str)
