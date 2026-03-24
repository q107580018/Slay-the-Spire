from __future__ import annotations

from slay_the_spire.content.registries import CardRegistry, EnemyRegistry
from slay_the_spire.domain.combat.turn_flow import end_turn, resolve_player_actions
from slay_the_spire.domain.effects.effect_types import damage_effect
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
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
    state = _combat_state()

    resolved = end_turn(state, registry)

    assert state.player.hp == 25
    assert state.round_number == 2
    assert state.energy == 3
    assert state.hand == ["strike#2", "defend#2", "strike#3", "defend#3", "strike#4"]
    assert state.discard_pile == ["strike#1", "defend#1"]
    assert [effect["type"] for effect in resolved] == ["damage"]


def test_end_turn_use_case_returns_structured_result() -> None:
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
    state = _combat_state()

    result = run_end_turn(state, registry)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage"]
    assert state.round_number == 2
