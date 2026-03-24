from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.content.provider import StarterContentProvider


def test_render_room_exports_rich_panelized_combat_screen() -> None:
    session = start_session(seed=5)
    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=StarterContentProvider(session.content_root),
        menu_state=MenuState(),
    )

    assert "╭" in output or "┌" in output
    assert "当前能量" in output
    assert "抽牌堆" in output
    assert "可选操作" in output
