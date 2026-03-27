from __future__ import annotations

import pytest

from slay_the_spire.content.registries import CardRegistry, EnemyRegistry
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.statuses import StatusState
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
    provider.enemies().register(
        {
            "id": "training_dummy",
            "name": "Training Dummy",
            "hp": 10,
            "move_table": [],
            "intent_policy": "scripted",
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


def test_play_card_creates_a_new_anger_copy_in_discard_pile() -> None:
    state = _combat_state(hand=["anger#1"], energy=3)
    provider = _provider_with_card(
        card_id="anger",
        cost=0,
        effects=[
            {"type": "damage", "amount": 6},
            {"type": "create_card_copy", "card_id": "anger", "zone": "discard_pile"},
        ],
    )

    result = play_card(state, "anger#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage", "create_card_copy"]
    assert state.energy == 3
    assert state.hand == []
    assert state.discard_pile == ["anger#1", "anger#2"]
    assert state.enemies[0].hp == 4
    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 6 伤害，并向弃牌堆加入 1 张Custom Strike。"]


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


def test_play_card_applies_player_strength_to_damage_effects() -> None:
    state = _combat_state(hand=["custom_strike#1"])
    state.player.statuses.append(StatusState(status_id="strength", stacks=2))
    provider = _provider_with_card(effects=[{"type": "damage", "amount": 4}])

    result = play_card(state, "custom_strike#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage"]
    assert result.resolved_effects[0]["result"] == {
        "applied_amount": 6,
        "blocked": 0,
        "actual_damage": 6,
        "target_defeated": False,
    }
    assert state.enemies[0].hp == 4


def test_play_card_applies_vulnerable_status_effects() -> None:
    state = _combat_state(hand=["bash#1"], energy=2)
    provider = _provider_with_card(
        card_id="bash",
        cost=2,
        effects=[
            {"type": "damage", "amount": 8},
            {"type": "vulnerable", "stacks": 2},
        ],
    )

    result = play_card(state, "bash#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage", "vulnerable"]
    assert state.enemies[0].hp == 2
    assert len(state.enemies[0].statuses) == 1
    assert state.enemies[0].statuses[0].status_id == "vulnerable"
    assert state.enemies[0].statuses[0].stacks == 2
    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 8 伤害，并施加 2 层易伤。"]


def test_play_card_damage_is_reduced_while_player_is_weak() -> None:
    state = _combat_state(hand=["custom_strike#1"])
    state.player.statuses.append(StatusState(status_id="weak", stacks=1))
    provider = _provider_with_card(effects=[{"type": "damage", "amount": 6}])

    result = play_card(state, "custom_strike#1", "enemy-1", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage"]
    assert state.enemies[0].hp == 6
    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 4 伤害。"]


def test_play_card_rejects_unplayable_cards() -> None:
    state = _combat_state(hand=["doubt#1"])
    provider = _Provider()
    provider.cards().register(
        {
            "id": "doubt",
            "name": "疑虑",
            "cost": -1,
            "playable": False,
            "effects": [],
        }
    )

    with pytest.raises(ValueError, match="无法打出"):
        play_card(state, "doubt#1", None, provider)


def test_play_card_appends_damage_log_entry() -> None:
    state = _combat_state(hand=["custom_strike#1"])
    provider = _provider_with_card(effects=[{"type": "damage", "amount": 4}])

    play_card(state, "custom_strike#1", "enemy-1", provider)

    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 4 伤害。"]


def test_play_card_appends_block_log_entry() -> None:
    state = _combat_state(hand=["guard#1"])
    provider = _provider_with_card(card_id="guard", effects=[{"type": "block", "amount": 5}])

    play_card(state, "guard#1", None, provider)

    assert state.log == ["你打出 Custom Strike，获得 5 格挡。"]


def test_play_card_draw_log_uses_refilled_discard_cards() -> None:
    state = _combat_state(hand=["pommel_strike_plus#1"])
    state.draw_pile = ["bonus_a#1"]
    state.discard_pile = ["bonus_b#1"]
    provider = _provider_with_card(
        card_id="pommel_strike_plus",
        effects=[
            {"type": "damage", "amount": 10},
            {"type": "draw", "amount": 2},
        ],
    )

    play_card(state, "pommel_strike_plus#1", "enemy-1", provider)

    assert state.hand == ["bonus_a#1", "bonus_b#1"]
    assert state.log == ["你打出 Custom Strike，对 Training Dummy 造成 10 伤害，并抽 2 张牌。"]


def test_play_card_bloodletting_gains_energy_and_loses_hp() -> None:
    state = _combat_state(hand=["bloodletting#1"], energy=1)
    provider = _provider_with_card(
        card_id="bloodletting",
        cost=0,
        effects=[
            {"type": "gain_energy", "amount": 2},
            {"type": "lose_hp", "amount": 3},
        ],
    )

    result = play_card(state, "bloodletting#1", None, provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["gain_energy", "lose_hp"]
    assert state.energy == 3
    assert state.player.hp == 37
    assert state.log == ["你打出 Custom Strike，获得 2 点能量，并失去 3 点生命。"]


def test_play_card_true_grit_plus_can_target_a_hand_card_to_exhaust() -> None:
    state = _combat_state(hand=["true_grit_plus#1", "strike#2"])
    provider = _provider_with_card(
        card_id="true_grit_plus",
        cost=1,
        effects=[
            {"type": "block", "amount": 9},
            {"type": "exhaust_target_card"},
        ],
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "Strike",
            "cost": 1,
            "effects": [{"type": "damage", "amount": 6}],
        }
    )

    result = play_card(state, "true_grit_plus#1", "strike#2", provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["block", "exhaust_target_card"]
    assert state.hand == []
    assert state.discard_pile == ["true_grit_plus#1"]
    assert state.exhaust_pile == ["strike#2"]
    assert state.player.block == 9
    assert state.log == ["你打出 Custom Strike，获得 9 格挡，并消耗 1 张手牌。"]


def test_play_card_armaments_plus_upgrades_all_remaining_hand_cards() -> None:
    state = _combat_state(hand=["armaments_plus#1", "strike#2", "defend#3"])
    provider = _provider_with_card(
        card_id="armaments_plus",
        cost=1,
        effects=[
            {"type": "block", "amount": 5},
            {"type": "upgrade_all_hand"},
        ],
    )
    provider.cards().register(
        {
            "id": "strike",
            "name": "Strike",
            "cost": 1,
            "upgrades_to": "strike_plus",
            "effects": [{"type": "damage", "amount": 6}],
        }
    )
    provider.cards().register(
        {
            "id": "strike_plus",
            "name": "Strike+",
            "cost": 1,
            "effects": [{"type": "damage", "amount": 9}],
        }
    )
    provider.cards().register(
        {
            "id": "defend",
            "name": "Defend",
            "cost": 1,
            "upgrades_to": "defend_plus",
            "effects": [{"type": "block", "amount": 5}],
        }
    )
    provider.cards().register(
        {
            "id": "defend_plus",
            "name": "Defend+",
            "cost": 1,
            "effects": [{"type": "block", "amount": 8}],
        }
    )

    result = play_card(state, "armaments_plus#1", None, provider)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["block", "upgrade_all_hand"]
    assert state.hand == ["strike_plus#2", "defend_plus#3"]
    assert state.discard_pile == ["armaments_plus#1"]
    assert state.player.block == 5
