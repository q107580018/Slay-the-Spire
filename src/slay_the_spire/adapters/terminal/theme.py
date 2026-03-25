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
    }
)

PANEL_BOX = box.SQUARE
HP_BAR_WIDTH = 18
