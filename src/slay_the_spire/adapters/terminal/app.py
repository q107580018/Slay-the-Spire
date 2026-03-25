from __future__ import annotations

from typing import Protocol

from rich.console import Console, RenderableType

from slay_the_spire.adapters.terminal.prompts import prompt_for_session
from slay_the_spire.adapters.terminal.theme import TERMINAL_THEME
from slay_the_spire.app.session import (
    SessionLoopResult,
    SessionState,
    render_session,
    render_session_renderable,
    route_menu_choice,
)


class TerminalPort(Protocol):
    def clear(self) -> None: ...

    def print(self, text: str | RenderableType) -> None: ...

    def read(self, prompt: str = "") -> str: ...


class RichTerminal:
    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console(
            theme=TERMINAL_THEME,
            force_terminal=True,
            color_system="standard",
            no_color=False,
        )

    def clear(self) -> None:
        self._console.clear()

    def print(self, text: str | RenderableType) -> None:
        self._console.print(text)

    def read(self, prompt: str = "") -> str:
        return self._console.input(prompt)


def _draw_frame(*, terminal: TerminalPort, session: SessionState, flash_message: str | None = None) -> str:
    frame = render_session(session)
    frame_renderable = render_session_renderable(session)
    terminal.clear()
    terminal.print(frame_renderable)
    if flash_message:
        terminal.print(flash_message)
    return frame


def run_terminal_session(
    *,
    session: SessionState,
    terminal: TerminalPort | None = None,
) -> SessionLoopResult:
    resolved_terminal = terminal or RichTerminal()
    outputs = [_draw_frame(terminal=resolved_terminal, session=session)]
    running = True

    while running:
        command = resolved_terminal.read(prompt_for_session(session))
        running, session, message = route_menu_choice(command, session=session)
        outputs.append(message)
        frame = render_session(session)
        frame_renderable = render_session_renderable(session)
        flash_message = None if message == frame else message
        resolved_terminal.clear()
        resolved_terminal.print(frame_renderable)
        if flash_message is not None:
            resolved_terminal.print(flash_message)

    return SessionLoopResult(outputs=outputs, final_session=session)
