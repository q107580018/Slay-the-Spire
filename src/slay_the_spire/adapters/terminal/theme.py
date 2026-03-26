from __future__ import annotations

from rich import box
from rich.theme import Theme

TERMINAL_THEME = Theme(
    {
        "summary.label": "bold cyan",
        "player.name": "bold green",
        "enemy.name": "bold red",
        "menu.number": "bold yellow",
        "menu.border": "yellow",
        "hp.high": "green",
        "hp.medium": "yellow",
        "hp.low": "bold red",
        "status.buff": "black on bright_cyan",
        "status.debuff": "black on bright_magenta",
        "map.metric.label": "bold cyan",
        "map.metric.sep": "dim cyan",
        "map.metric.value": "cyan",
        "map.ruler": "dim cyan",
        "map.connector": "dim white",
        "map.legend.label": "bold cyan",
        "map.legend.sep": "dim cyan",
        "map.legend.value": "white",
        "map.node.default": "dim white",
        "map.node.reachable": "bold cyan",
        "map.node.current": "bold bright_cyan",
        "map.room.combat": "white",
        "map.room.event": "cyan",
        "map.room.shop": "magenta",
        "map.room.rest": "green",
        "map.room.elite": "bold yellow",
        "map.room.boss": "bold red",
    }
)

PANEL_BOX = box.SQUARE
HP_BAR_WIDTH = 18
