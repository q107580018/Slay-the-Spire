from __future__ import annotations

from typing import Literal

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from slay_the_spire.adapters.rich_ui.inspect import (
    format_card_detail_menu,
    render_card_detail_panel,
    render_shared_potions_panel,
    render_shared_relics_panel,
    render_shared_stats_panel,
)
from slay_the_spire.adapters.rich_ui.theme import PANEL_BOX
from slay_the_spire.adapters.rich_ui.widgets import render_card_name
from slay_the_spire.app.menu_definitions import build_inspect_root_menu, build_leaf_menu, format_menu_lines
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort

InspectContext = Literal["combat", "non_combat"]

SHARED_INSPECT_MODES = frozenset(
    {
        "inspect_root",
        "inspect_deck",
        "inspect_stats",
        "inspect_relics",
        "inspect_potions",
        "inspect_card_detail",
    }
)

_LEAF_TITLES: dict[str, dict[InspectContext, str]] = {
    "inspect_stats": {
        "combat": "角色状态",
        "non_combat": "属性",
    },
    "inspect_relics": {
        "combat": "遗物列表",
        "non_combat": "遗物",
    },
    "inspect_potions": {
        "combat": "药水",
        "non_combat": "药水",
    },
}

_DECK_PANEL_TITLES: dict[InspectContext, str] = {
    "combat": "牌组列表",
    "non_combat": "牌组",
}


def format_shared_inspect_menu(
    *,
    mode: str,
    context: InspectContext,
    run_state: RunState,
    room_state: RoomState,
    registry: ContentProviderPort,
) -> list[str] | None:
    del registry
    if mode == "inspect_root":
        return format_menu_lines(build_inspect_root_menu(room_state=room_state))
    if mode == "inspect_deck":
        return _format_inspect_deck_footer(run_state)
    if mode in _LEAF_TITLES:
        return format_menu_lines(build_leaf_menu(title=_LEAF_TITLES[mode][context]))
    if mode == "inspect_card_detail":
        return format_card_detail_menu()
    return None


def render_shared_inspect_panel(
    *,
    mode: str,
    context: InspectContext,
    run_state: RunState,
    act_state: ActState,
    room_state: RoomState,
    registry: ContentProviderPort,
    card_instance_id: str | None = None,
    combat_state: CombatState | None = None,
) -> Panel | None:
    if mode == "inspect_deck":
        lines = [line if isinstance(line, Text) else Text(line) for line in _format_inspect_deck_lines(run_state, registry)]
        return Panel(Group(*lines), title=_DECK_PANEL_TITLES[context], box=PANEL_BOX, expand=False)
    if mode == "inspect_stats":
        return render_shared_stats_panel(
            title=_LEAF_TITLES[mode][context],
            run_state=run_state,
            act_state=act_state,
            room_state=room_state,
            combat_state=combat_state if context == "combat" else None,
        )
    if mode == "inspect_relics":
        return render_shared_relics_panel(title=_LEAF_TITLES[mode][context], run_state=run_state, registry=registry)
    if mode == "inspect_potions":
        return render_shared_potions_panel(title=_LEAF_TITLES[mode][context], run_state=run_state, registry=registry)
    if mode == "inspect_card_detail" and isinstance(card_instance_id, str):
        return render_card_detail_panel(card_instance_id, registry)
    return None


def _format_inspect_deck_lines(run_state: RunState, registry: ContentProviderPort) -> list[str | Text]:
    lines: list[str | Text] = []
    if not run_state.deck:
        lines.append("-")
    else:
        for index, card_instance_id in enumerate(run_state.deck, start=1):
            card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
            lines.append(Text.assemble(f"{index}. ", render_card_name(card_def)))
    lines.append(f"{len(run_state.deck) + 1}. 返回上一步")
    return lines


def _format_inspect_deck_footer(run_state: RunState) -> list[str]:
    return [
        "输入上方编号查看卡牌详情",
        f"{len(run_state.deck) + 1}. 返回上一步",
    ]
