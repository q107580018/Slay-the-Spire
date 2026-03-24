from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from slay_the_spire.adapters.terminal.prompts import prompt_for_room
from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.input_port import InputPort
from slay_the_spire.use_cases.enter_room import enter_room
from slay_the_spire.use_cases.start_run import start_new_run


def default_content_root() -> Path:
    return Path(__file__).resolve().parents[3] / "content"


@dataclass(slots=True)
class SessionState:
    run_state: RunState
    act_state: ActState
    room_state: RoomState


def start_session(*, seed: int, character_id: str = "ironclad", content_root: str | Path | None = None) -> SessionState:
    provider = StarterContentProvider(default_content_root() if content_root is None else content_root)
    run_state = start_new_run(character_id, seed=seed, registry=provider)
    act_state = generate_act_state(run_state.current_act_id or "act1", seed=seed, registry=provider)
    room_state = enter_room(run_state, act_state, node_id=act_state.current_node_id, registry=provider)
    return SessionState(run_state=run_state, act_state=act_state, room_state=room_state)


def render_session(session: SessionState) -> str:
    return render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
    )


def route_command(command: str, *, session: SessionState) -> tuple[bool, str]:
    normalized = command.strip().lower()
    if normalized in {"", "look"}:
        return True, render_session(session)
    if normalized in {"help", "?"}:
        return True, "Commands: look, help, quit"
    if normalized in {"quit", "exit"}:
        return False, "Goodbye."
    return True, f"Unknown command: {command.strip() or '<empty>'}"


def interactive_loop(*, session: SessionState, input_port: InputPort) -> list[str]:
    outputs = [render_session(session)]
    running = True
    while running:
        command = input_port.read(prompt_for_room(session.room_state))
        running, message = route_command(command, session=session)
        outputs.append(message)
    return outputs
