from dataclasses import replace

from slay_the_spire.adapters.terminal.renderer import render_room
from slay_the_spire.app.session import MenuState, start_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.room_state import RoomState


def _provider(session):
    return StarterContentProvider(session.content_root)


def _event_room() -> RoomState:
    return RoomState(
        room_id="act1:event",
        room_type="event",
        stage="waiting_input",
        payload={
            "node_id": "r1c0",
            "room_kind": "event",
            "event_id": "shining_light",
            "next_node_ids": ["r2c0"],
        },
        is_resolved=False,
        rewards=[],
    )


def test_render_non_combat_inspect_root_shows_shared_sections() -> None:
    session = replace(start_session(seed=5), room_state=_event_room(), menu_state=MenuState(mode="inspect_root"))

    output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=session.menu_state,
        run_phase=session.run_phase,
    )

    assert "资料总览" in output
    assert "1. 属性" in output
    assert "2. 牌组" in output
    assert "3. 遗物" in output
    assert "4. 药水" in output


def test_render_non_combat_inspect_pages_show_stats_deck_relics_and_potions() -> None:
    base_session = replace(start_session(seed=5), room_state=_event_room())
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, potions=["fire_potion"]),
    )

    stats_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_stats", inspect_parent_mode="root", inspect_item_id="stats"),
        run_phase=session.run_phase,
    )
    deck_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_deck", inspect_parent_mode="root", inspect_item_id="deck"),
        run_phase=session.run_phase,
    )
    relics_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_relics", inspect_parent_mode="root", inspect_item_id="relics"),
        run_phase=session.run_phase,
    )
    potions_output = render_room(
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
        registry=_provider(session),
        menu_state=MenuState(mode="inspect_potions", inspect_parent_mode="root", inspect_item_id="potions"),
        run_phase=session.run_phase,
    )

    assert "属性" in stats_output
    assert "当前生命" in stats_output
    assert "牌组" in deck_output
    assert "打击" in deck_output
    assert "遗物" in relics_output
    assert "燃烧之血" in relics_output
    assert "药水" in potions_output
    assert "火焰药水" in potions_output
