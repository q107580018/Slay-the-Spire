from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from slay_the_spire.app.session import MenuState, route_menu_choice, start_session
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.use_cases.use_potion import use_potion


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def _combat_state() -> CombatState:
    return CombatState(
        round_number=1,
        energy=3,
        hand=["strike#1"],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=40,
            max_hp=40,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="slime",
                hp=40,
                max_hp=40,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )


def _single_enemy_combat_state() -> CombatState:
    state = _combat_state()
    state.enemies = [
        EnemyState(
            instance_id="enemy-1",
            enemy_id="slime",
            hp=20,
            max_hp=20,
            block=0,
            statuses=[],
        )
    ]
    return state


def test_use_potion_damage_deals_damage_to_selected_enemy() -> None:
    state = _combat_state()
    provider = _content_provider()

    result = use_potion(state, potion_id="fire_potion", target_id="enemy-1", registry=provider)

    assert result.combat_state is state
    assert state.enemies[0].hp == 20
    assert state.log == ["你使用 火焰药水，对 绿史莱姆 造成 20 伤害。"]
    assert "火焰药水" in (result.message or "")
    assert "20 伤害" in (result.message or "")


def test_use_potion_block_grants_block_without_target() -> None:
    state = _combat_state()
    provider = _content_provider()

    result = use_potion(state, potion_id="block_potion", target_id=None, registry=provider)

    assert result.combat_state is state
    assert state.player.block == 12
    assert state.log == ["你使用 格挡药水，获得 12 格挡。"]


def test_use_potion_strength_grants_strength_status_without_target() -> None:
    state = _combat_state()
    provider = _content_provider()

    result = use_potion(state, potion_id="strength_potion", target_id=None, registry=provider)

    assert result.combat_state is state
    assert state.player.statuses == [StatusState(status_id="strength", stacks=2)]
    assert state.log == ["你使用 力量药水，获得 2 层力量。"]


def test_route_menu_choice_uses_selected_potion_and_consumes_it() -> None:
    session = replace(
        start_session(seed=5),
        run_state=replace(start_session(seed=5).run_state, potions=["fire_potion"]),
        menu_state=MenuState(mode="root"),
    )

    _running, potion_session, potion_message = route_menu_choice("2", session=session)
    _running, target_session, _target_message = route_menu_choice("1", session=potion_session)
    _running, final_session, final_message = route_menu_choice("1", session=target_session)

    assert potion_session.menu_state.mode == "select_potion"
    assert target_session.menu_state.mode == "select_target"
    assert final_session.run_state.potions == []
    assert final_session.room_state.payload["combat_state"]["enemies"][0]["hp"] == 0
    assert "火焰药水" in final_message
    assert "造成" in final_message


def test_route_menu_choice_uses_enemy_potion_without_target_selection_for_single_enemy() -> None:
    session = replace(
        start_session(seed=5),
        run_state=replace(start_session(seed=5).run_state, potions=["fire_potion"]),
        room_state=replace(
            start_session(seed=5).room_state,
            payload={
                **start_session(seed=5).room_state.payload,
                "combat_state": _single_enemy_combat_state().to_dict(),
            },
        ),
        menu_state=MenuState(mode="root"),
    )

    _running, potion_session, _message = route_menu_choice("2", session=session)
    _running, next_session, message = route_menu_choice("1", session=potion_session)

    assert potion_session.menu_state.mode == "select_potion"
    assert next_session.menu_state.mode == "root"
    assert next_session.run_state.potions == []
    assert next_session.room_state.payload["combat_state"]["enemies"][0]["hp"] == 0
    assert next_session.room_state.is_resolved is True
    assert "火焰药水" in message
