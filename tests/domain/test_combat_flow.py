from __future__ import annotations

from slay_the_spire.content.registries import CardRegistry, EnemyRegistry
from slay_the_spire.domain.combat.turn_flow import end_turn, resolve_player_actions
from slay_the_spire.domain.effects.effect_types import damage_effect
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.use_cases.end_turn import end_turn as run_end_turn


class _Registry:
    def __init__(self) -> None:
        self._cards = CardRegistry()
        self._enemies = EnemyRegistry()

    def characters(self):
        raise NotImplementedError

    def cards(self) -> CardRegistry:
        return self._cards

    def enemies(self) -> EnemyRegistry:
        return self._enemies

    def relics(self):
        raise NotImplementedError

    def events(self):
        raise NotImplementedError

    def acts(self):
        raise NotImplementedError


def _combat_state() -> CombatState:
    return CombatState(
        round_number=1,
        energy=3,
        hand=["strike#1", "defend#1"],
        draw_pile=["strike#2", "defend#2", "strike#3", "defend#3", "strike#4"],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=30,
            max_hp=30,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="training_slime",
                hp=12,
                max_hp=12,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )


def _enemy_registry() -> _Registry:
    registry = _Registry()
    registry.enemies().register(
        {
            "id": "training_slime",
            "name": "Training Slime",
            "hp": 12,
            "move_table": [
                {
                    "move": "tackle",
                    "effects": [{"type": "damage", "amount": 5}],
                }
            ],
            "intent_policy": "scripted",
        }
    )
    return registry


def test_playing_strike_spends_energy_and_deals_damage() -> None:
    state = _combat_state()
    state.energy -= 1
    state.effect_queue.append(
        damage_effect(
            source_instance_id="player-1",
            target_instance_id="enemy-1",
            amount=6,
        )
    )

    resolved = resolve_player_actions(state)

    assert state.energy == 2
    assert state.enemies[0].hp == 6
    assert [effect["type"] for effect in resolved] == ["damage"]


def test_end_turn_runs_enemy_intents_and_draws_new_hand() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.draw_pile = ["strike#2"]
    state.discard_pile = ["defend#2", "strike#3", "defend#3", "strike#4"]

    resolved = end_turn(state, registry)

    assert state.player.hp == 25
    assert state.round_number == 2
    assert state.energy == 3
    assert state.hand == ["strike#2", "defend#2", "strike#3", "defend#3", "strike#4"]
    assert state.draw_pile == ["strike#1", "defend#1"]
    assert state.discard_pile == []
    assert [effect["type"] for effect in resolved] == ["damage"]


def test_end_turn_use_case_returns_structured_result() -> None:
    registry = _enemy_registry()
    state = _combat_state()

    result = run_end_turn(state, registry)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage"]
    assert state.round_number == 2


def test_end_turn_stops_before_next_turn_when_player_dies() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.player.hp = 4
    state.energy = 1
    state.draw_pile = ["strike#2", "defend#2", "strike#3", "defend#3", "strike#4"]

    result = run_end_turn(state, registry)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage"]
    assert state.player.hp == 0
    assert state.round_number == 1
    assert state.energy == 1
    assert state.hand == []


def test_lagavulin_sleeps_for_first_three_enemy_turns_then_attacks() -> None:
    registry = _Registry()
    registry.enemies().register(
        {
            "id": "lagavulin",
            "name": "Lagavulin",
            "hp": 109,
            "move_table": [
                {"move": "sleep", "sleep_turns": 3},
                {"move": "heavy_slam", "effects": [{"type": "damage", "amount": 18}]},
                {"move": "heavy_slam", "effects": [{"type": "damage", "amount": 18}]},
            ],
            "intent_policy": "scripted",
        }
    )
    state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=80,
            max_hp=80,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="lagavulin",
                hp=109,
                max_hp=109,
                block=0,
                statuses=[StatusState(status_id="sleeping", stacks=3)],
            )
        ],
        effect_queue=[],
        log=[],
    )

    for expected_sleep_stacks in (2, 1, 0):
        resolved = end_turn(state, registry)
        assert resolved == []
        assert state.player.hp == 80
        sleeping_statuses = [status for status in state.enemies[0].statuses if status.status_id == "sleeping"]
        if expected_sleep_stacks == 0:
            assert sleeping_statuses == []
        else:
            assert [status.stacks for status in sleeping_statuses] == [expected_sleep_stacks]

    resolved = end_turn(state, registry)

    assert [effect["type"] for effect in resolved] == ["damage"]
    assert state.player.hp == 62
