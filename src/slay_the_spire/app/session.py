from __future__ import annotations

from dataclasses import dataclass, replace
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
    packaged_content_root = Path(__file__).resolve().parents[1] / "data" / "content"
    if _is_content_root(packaged_content_root):
        return packaged_content_root
    for candidate in _candidate_content_roots():
        if _is_content_root(candidate):
            return candidate
    raise FileNotFoundError("could not locate content root; pass --content-root explicitly")


def _candidate_content_roots() -> tuple[Path, ...]:
    module_path = Path(__file__).resolve()
    candidates = [module_path.parents[i] / "content" for i in range(1, min(5, len(module_path.parents)))]
    candidates.append(Path.cwd() / "content")
    return tuple(dict.fromkeys(candidates))


def _is_content_root(path: Path) -> bool:
    return path.is_dir() and (path / "characters" / "ironclad.json").exists()


@dataclass(slots=True)
class SessionState:
    run_state: RunState
    act_state: ActState
    room_state: RoomState
    content_root: Path
    command_history: list[str] | None = None


@dataclass(slots=True)
class SessionLoopResult:
    outputs: list[str]
    final_session: SessionState


def _with_command_history(session: SessionState, command: str) -> SessionState:
    history = list(session.command_history or [])
    history.append(command)
    return replace(session, command_history=history)


def _advance_to_next_room(session: SessionState) -> SessionState:
    next_node_ids = session.room_state.payload.get("next_node_ids", [])
    if not isinstance(next_node_ids, list) or not next_node_ids:
        return session
    next_node_id = next_node_ids[0]
    if not isinstance(next_node_id, str):
        return session
    provider = StarterContentProvider(session.content_root)
    room_state = enter_room(session.run_state, session.act_state, node_id=next_node_id, registry=provider)
    return replace(session, room_state=room_state)


def start_session(*, seed: int, character_id: str = "ironclad", content_root: str | Path | None = None) -> SessionState:
    resolved_content_root = default_content_root() if content_root is None else Path(content_root)
    provider = StarterContentProvider(resolved_content_root)
    run_state = start_new_run(character_id, seed=seed, registry=provider)
    act_state = generate_act_state(run_state.current_act_id or "act1", seed=seed, registry=provider)
    room_state = enter_room(run_state, act_state, node_id=act_state.current_node_id, registry=provider)
    return SessionState(
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        content_root=resolved_content_root,
    )


def render_session(session: SessionState) -> str:
    return render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
    )


def route_command(command: str, *, session: SessionState) -> tuple[bool, SessionState, str]:
    normalized = command.strip().lower()
    if normalized in {"", "look"}:
        return True, _with_command_history(session, normalized or "look"), render_session(session)
    if normalized in {"next", "advance"}:
        next_session = _advance_to_next_room(_with_command_history(session, normalized))
        return True, next_session, render_session(next_session)
    if normalized in {"help", "?"}:
        return True, _with_command_history(session, normalized), "Commands: look, next, help, quit"
    if normalized in {"quit", "exit"}:
        return False, _with_command_history(session, normalized), "Goodbye."
    return True, _with_command_history(session, normalized or command), f"Unknown command: {command.strip() or '<empty>'}"


def interactive_loop(*, session: SessionState, input_port: InputPort) -> SessionLoopResult:
    outputs = [render_session(session)]
    running = True
    while running:
        command = input_port.read(prompt_for_room(session.room_state))
        running, session, message = route_command(command, session=session)
        outputs.append(message)
    return SessionLoopResult(outputs=outputs, final_session=session)
