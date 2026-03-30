from __future__ import annotations

from rich.console import Group
from rich.columns import Columns


def build_standard_screen(*, summary, body, footer) -> Group:
    return Group(summary, body, footer)


def build_two_column_body(*, left, right) -> Columns:
    return Columns([left, right], equal=True, expand=True)
