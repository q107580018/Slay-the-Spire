from __future__ import annotations

from io import StringIO
from typing import Any

from rich.console import Console, RenderableType

from slay_the_spire.adapters.terminal.screens.combat import render_combat_screen
from slay_the_spire.adapters.terminal.screens.non_combat import render_non_combat_screen
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.adapters.terminal.theme import TERMINAL_THEME
from slay_the_spire.ports.content_provider import ContentProviderPort


def _render_to_text(renderable: RenderableType) -> str:
    buffer = StringIO()
    console = Console(
        file=buffer,
        width=100,
        record=True,
        force_terminal=False,
        color_system=None,
        theme=TERMINAL_THEME,
    )
    console.print(renderable)
    return console.export_text(clear=False).rstrip()


def _combat_state_from_room(room_state: RoomState) -> CombatState | None:
    combat_state = room_state.payload.get("combat_state")
    if not isinstance(combat_state, dict):
        return None
    return CombatState.from_dict(combat_state)


def _menu_mode(menu_state: Any) -> str:
    return str(getattr(menu_state, "mode", "root"))


def render_room_renderable(
    *,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    registry: ContentProviderPort,
    menu_state: Any,
    run_phase: str = "active",
) -> RenderableType:
    combat_state = _combat_state_from_room(room_state)
    if _menu_mode(menu_state) == "select_next_room":
        return render_non_combat_screen(
            run_state=run_state,
            act_state=act_state,
            room_state=room_state,
            registry=registry,
            menu_state=menu_state,
            run_phase=run_phase,
        )
    if room_state.is_resolved and room_state.rewards:
        return render_non_combat_screen(
            run_state=run_state,
            act_state=act_state,
            room_state=room_state,
            registry=registry,
            menu_state=menu_state,
            run_phase=run_phase,
        )
    if run_phase == "active" and combat_state is not None and room_state.room_type in {"combat", "elite", "boss"}:
        return render_combat_screen(
            run_state=run_state,
            act_state=act_state,
            room_state=room_state,
            combat_state=combat_state,
            registry=registry,
            menu_state=menu_state,
        )
    return render_non_combat_screen(
        run_state=run_state,
        act_state=act_state,
        room_state=room_state,
        registry=registry,
        menu_state=menu_state,
        run_phase=run_phase,
    )


def render_room(
    *,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    registry: ContentProviderPort,
    menu_state: Any,
    run_phase: str = "active",
) -> str:
    return _render_to_text(
        render_room_renderable(
            run_state=run_state,
            act_state=act_state,
            room_state=room_state,
            registry=registry,
            menu_state=menu_state,
            run_phase=run_phase,
        )
    )
