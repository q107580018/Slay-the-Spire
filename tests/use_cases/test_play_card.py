from __future__ import annotations

import pytest

from slay_the_spire.content.registries import CardRegistry, EnemyRegistry
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.use_cases.play_card import play_card


class _Provider:
    def __init__(self) -> None:
        self._cards = CardRegistry()
        self._enemies = EnemyRegistry()
        self.cards_calls = 0

    def characters(self):
        raise NotImplementedError

    def cards(self) -> CardRegistry:
        self.cards_calls += 1
        return self._cards

    def enemies(self) -> EnemyRegistry:
        return self._enemies

    def relics(self):
        raise NotImplementedError

    def events(self):
        raise NotImplementedError

    def acts(self):
        raise NotImplementedError


def _combat_state(*, hand: list[str] | None = None, energy: int = 3) -> CombatState:
    return CombatState(
        round_number=1,
        energy=energy,
        hand=list(hand or ["custom_strike#1"]),
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
                enemy_id="training_dummy",
                hp=10,
                max_hp=10,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )


def _provider_with_card(*, card_id: str = "custom_strike", cost: int = 1, effects: list[dict[str, object]] | None = None) -> _Provider:
    provider = _Provider()
    provider.cards().register(
        {
            "id": card_id,
            "name": "Custom Strike",
            "cost": cost,
            "effects": effects or [{"type": "damage", "amount": 4}],
        }
    )
    return provider


def test_play_card_rejects_card_not_in_hand() -> None:
    state = _combat_state(hand=["custom_strike#1"])
    provider = _provider_with_card()

    with pytest.raises(ValueError, match="not in hand"):
        play_card(state, "custom_strike#2", "enemy-1", provider)


def test_play_card_rejects_insufficient_energy() -> None:
    state = _combat_state(energy=0)
    provider = _provider_with_card(cost=1)

    with pytest.raises(ValueError, match="energy"):
        play_card(state, "custom_strike#1", "enemy-1", provider)


def test_play_card_rejects_missing_target_for_targeted_effect() -> None:
    state = _combat_state()
    provider = _provider_with_card(effects=[{"type": "damage", "amount": 4}])
    before = state.to_dict()

    with pytest.raises(ValueError, match="target"):
        play_card(state, "custom_strike#1", None, provider)

    assert state.to_dict() == before


def test_play_card_rejects_unknown_card() -> None:
    state = _combat_state(hand=["unknown_card#1"])
    provider = _Provider()

    with pytest.raises(KeyError):
        play_card(state, "unknown_card#1", "enemy-1", provider)


def test_play_card_rejects_invalid_card_instance_id_format() -> None:
    state = _combat_state(hand=["registry_card"])
    provider = _provider_with_card(card_id="registry_card")
    before = state.to_dict()

    with pytest.raises(ValueError, match="card_instance_id"):
        play_card(state, "registry_card", "enemy-1", provider)

    assert state.to_dict() == before


def test_play_card_defaults_draw_target_to_player() -> None:
    state = _combat_state(hand=["draw_card#1"])
    state.draw_pile = ["bonus_card#1"]
    provider = _provider_with_card(card_id="draw_card", effects=[{"type": "draw", "amount": 1}])

    result = play_card(state, "draw_card#1", None, provider)

    assert [effect["type"] for effect in result.resolved_effects] == ["draw"]
    assert state.hand == ["bonus_card#1"]
    assert state.discard_pile == ["draw_card#1"]


def test_play_card_uses_registry_to_resolve_card_definition() -> None:
    state = _combat_state(hand=["registry_card#9"])
    provider = _provider_with_card(card_id="registry_card", effects=[{"type": "damage", "amount": 7}])

    result = play_card(state, "registry_card#9", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage"]
    assert state.energy == 2
    assert state.hand == []
    assert state.discard_pile == ["registry_card#9"]
    assert state.enemies[0].hp == 3
    assert provider.cards_calls >= 2
