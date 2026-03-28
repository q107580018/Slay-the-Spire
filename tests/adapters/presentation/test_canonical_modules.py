from slay_the_spire.adapters.presentation.inspect import format_card_detail_lines
from slay_the_spire.adapters.presentation.inspect_registry import format_shared_inspect_menu
from slay_the_spire.adapters.presentation.renderer import render_room_renderable
from slay_the_spire.adapters.presentation.screens.combat import _format_card_menu, render_combat_screen
from slay_the_spire.adapters.presentation.screens.non_combat import render_full_map_panel
from slay_the_spire.adapters.presentation.widgets import render_card_name


def test_presentation_exports_are_canonical() -> None:
    assert render_room_renderable.__module__.startswith("slay_the_spire.adapters.presentation")
    assert render_card_name.__module__.startswith("slay_the_spire.adapters.presentation")
    assert format_card_detail_lines.__module__.startswith("slay_the_spire.adapters.presentation")
    assert format_shared_inspect_menu.__module__.startswith("slay_the_spire.adapters.presentation")
    assert render_combat_screen.__module__.startswith("slay_the_spire.adapters.presentation")
    assert _format_card_menu.__module__.startswith("slay_the_spire.adapters.presentation")
    assert render_full_map_panel.__module__.startswith("slay_the_spire.adapters.presentation")
