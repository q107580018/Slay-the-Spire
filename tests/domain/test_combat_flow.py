from __future__ import annotations

from pathlib import Path

import pytest

from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.content.registries import CardRegistry, EnemyRegistry
from slay_the_spire.domain.combat.turn_flow import end_turn, preview_enemy_move, resolve_player_actions
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


def _enemy_registry_without_attacks() -> _Registry:
    registry = _Registry()
    registry.enemies().register(
        {
            "id": "training_slime",
            "name": "Training Slime",
            "hp": 12,
            "move_table": [],
            "intent_policy": "scripted",
        }
    )
    return registry


def _hexaghost_registry() -> _Registry:
    registry = _Registry()
    registry.enemies().register(
        {
            "id": "hexaghost",
            "name": "Hexaghost",
            "hp": 250,
            "move_table": [
                {"move": "divider", "effects": []},
            ],
            "intent_policy": "scripted",
        }
    )
    return registry


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


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


def test_end_turn_applies_metallicize_power_before_enemy_attack() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.active_powers.append({"power_id": "metallicize", "amount": 3})

    resolved = end_turn(state, registry)

    assert [effect["type"] for effect in resolved] == ["block", "damage"]
    assert state.player.hp == 28


def test_end_turn_applies_combust_to_all_enemies_and_self() -> None:
    registry = _enemy_registry_without_attacks()
    state = _combat_state()
    state.enemies.append(
        EnemyState(
            instance_id="enemy-2",
            enemy_id="training_slime",
            hp=12,
            max_hp=12,
            block=0,
            statuses=[],
        )
    )
    state._refresh_entity_index()
    state.active_powers.append({"power_id": "combust", "amount": 5, "self_damage": 1})

    resolved = end_turn(state, registry)

    assert [effect["type"] for effect in resolved] == ["damage", "damage", "lose_hp"]
    assert [enemy.hp for enemy in state.enemies] == [7, 7]
    assert state.player.hp == 29


def test_end_turn_use_case_returns_structured_result() -> None:
    registry = _enemy_registry()
    state = _combat_state()

    result = run_end_turn(state, registry)

    assert result.combat_state is state
    assert [effect["type"] for effect in result.resolved_effects] == ["damage"]
    assert state.round_number == 2
    assert state.log == ["Training Slime攻击你 5，实际受到 5。"]


def test_gremlin_leader_cycles_from_weak_to_attacks() -> None:
    registry = _Registry()
    registry.enemies().register(
        {
            "id": "gremlin_leader",
            "name": "地精首领",
            "hp": 145,
            "move_table": [
                {"move": "rally", "effects": [{"type": "weak", "stacks": 1}]},
                {"move": "slash", "effects": [{"type": "damage", "amount": 10}]},
                {"move": "crush", "effects": [{"type": "damage", "amount": 16}]},
            ],
            "intent_policy": "cycle",
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
                enemy_id="gremlin_leader",
                hp=145,
                max_hp=145,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )

    run_end_turn(state, registry)
    assert state.log[-1] == "地精首领施加 1 层虚弱。"

    run_end_turn(state, registry)
    assert state.log[-1] == "地精首领攻击你 10，实际受到 10。"

    run_end_turn(state, registry)
    assert state.log[-1] == "地精首领攻击你 16，实际受到 16。"


def test_end_turn_use_case_logs_triggered_active_powers() -> None:
    registry = _enemy_registry_without_attacks()
    state = _combat_state()
    state.active_powers = [
        {"power_id": "metallicize", "amount": 3},
        {"power_id": "combust", "amount": 5, "self_damage": 1},
    ]
    state.enemies.append(
        EnemyState(
            instance_id="enemy-2",
            enemy_id="training_slime",
            hp=12,
            max_hp=12,
            block=0,
            statuses=[],
        )
    )
    state._refresh_entity_index()

    result = run_end_turn(state, registry)

    assert result.combat_state is state
    assert state.log == [
        "金属化触发，获得 3 格挡。",
        "燃烧躯体触发，对 Training Slime 造成 10 伤害，并失去 1 点生命。",
    ]


def test_end_turn_use_case_logs_triggered_active_powers_even_when_blocked() -> None:
    registry = _enemy_registry_without_attacks()
    state = _combat_state()
    state.active_powers = [{"power_id": "combust", "amount": 5, "self_damage": 1}]
    state.enemies[0].block = 5

    result = run_end_turn(state, registry)

    assert result.combat_state is state
    assert state.log == [
        "燃烧躯体触发，对 Training Slime 造成 5 伤害，格挡抵消 5，实际受到 0，并失去 1 点生命。",
    ]


def test_end_turn_use_case_logs_triggered_active_powers_with_lethal_overkill() -> None:
    registry = _enemy_registry_without_attacks()
    state = _combat_state()
    state.active_powers = [{"power_id": "combust", "amount": 5, "self_damage": 1}]
    state.enemies[0].hp = 3

    result = run_end_turn(state, registry)

    assert result.combat_state is state
    assert state.log == [
        "燃烧躯体触发，对 Training Slime 造成 3 伤害，并失去 1 点生命。",
    ]


def test_cultist_incantation_applies_strength_to_self() -> None:
    registry = _content_provider()
    state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
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
                enemy_id="cultist",
                hp=48,
                max_hp=48,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )

    resolved = end_turn(state, registry)

    assert any(effect["type"] == "strength" for effect in resolved)
    assert state.enemies[0].statuses == [StatusState(status_id="strength", stacks=3)]


def test_end_turn_clears_battle_trance_before_next_player_draw() -> None:
    registry = _enemy_registry_without_attacks()
    state = _combat_state()
    state.active_powers = [{"power_id": "battle_trance", "amount": 1}]
    state.hand = []
    state.draw_pile = ["strike#2", "defend#2", "strike#3", "defend#3", "strike#4"]

    end_turn(state, registry)

    assert state.active_powers == []
    assert state.hand == ["strike#2", "defend#2", "strike#3", "defend#3", "strike#4"]


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


def test_end_turn_log_reports_block_absorption_and_actual_damage() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.player.block = 2

    run_end_turn(state, registry)

    assert state.log == ["Training Slime攻击你 5，格挡抵消 2，实际受到 3。"]


def test_end_turn_clears_remaining_player_block_at_next_player_turn() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.player.block = 8

    end_turn(state, registry)

    assert state.player.block == 0


def test_end_turn_keeps_player_block_when_blur_status_is_active() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.player.block = 8
    state.player.statuses.append(StatusState(status_id="blur", stacks=1))

    end_turn(state, registry)

    assert state.player.block == 3
    assert state.player.statuses == []


def test_end_turn_clears_enemy_block_at_start_of_enemy_turn() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.enemies[0].block = 4

    end_turn(state, registry)

    assert state.enemies[0].block == 0


def test_end_turn_log_reports_sleeping_enemy() -> None:
    registry = _Registry()
    registry.enemies().register(
        {
            "id": "lagavulin",
            "name": "Lagavulin",
            "hp": 109,
            "move_table": [
                {"move": "sleep", "sleep_turns": 3},
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

    run_end_turn(state, registry)

    assert state.log == ["Lagavulin沉睡，暂不行动。"]


def test_enemy_weak_move_targets_player_by_default() -> None:
    registry = _Registry()
    registry.enemies().register(
        {
            "id": "acid_slime",
            "name": "Acid Slime",
            "hp": 15,
            "move_table": [
                {"move": "corrosive_lick", "effects": [{"type": "weak", "stacks": 1}]},
                {"move": "tackle", "effects": [{"type": "damage", "amount": 4}]},
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
            hp=30,
            max_hp=30,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="acid_slime",
                hp=15,
                max_hp=15,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )

    resolved = end_turn(state, registry)

    assert [effect["type"] for effect in resolved] == ["weak"]
    assert state.player.statuses == [StatusState(status_id="weak", stacks=1)]


def test_end_turn_consumes_existing_temporary_statuses_on_both_sides() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.player.statuses.append(StatusState(status_id="weak", stacks=1))
    state.enemies[0].statuses.append(StatusState(status_id="vulnerable", stacks=1))

    end_turn(state, registry)

    assert state.player.statuses == []
    assert state.enemies[0].statuses == []


def test_end_turn_log_reports_burn_trigger_and_enemy_adding_burn() -> None:
    registry = _Registry()
    registry.cards().register(
        {
            "id": "burn",
            "name": "灼伤",
            "cost": -1,
            "playable": False,
            "can_appear_in_shop": False,
            "effects": [],
        }
    )
    registry.enemies().register(
        {
            "id": "hexaghost",
            "name": "Hexaghost",
            "hp": 250,
            "move_table": [
                {"move": "divider", "effects": []},
                {
                    "move": "sear",
                    "effects": [
                        {"type": "damage", "amount": 6},
                        {"type": "add_card_to_discard", "card_id": "burn", "count": 1},
                    ],
                },
            ],
            "intent_policy": "scripted",
        }
    )
    state = CombatState(
        round_number=2,
        energy=3,
        hand=["burn#1", "strike#1"],
        draw_pile=["strike#2", "defend#2", "strike#3", "defend#3", "strike#4"],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=20,
            max_hp=20,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="hexaghost",
                hp=250,
                max_hp=250,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )

    run_end_turn(state, registry)

    assert state.log == [
        "灼伤在回合结束时触发，对你造成 2，实际受到 2。",
        "Hexaghost攻击你 6，实际受到 6，并向你的弃牌堆加入 1 张灼伤。",
    ]


def test_cultist_incantation_grants_strength_and_logs_it() -> None:
    registry = _Registry()
    registry.enemies().register(
        {
            "id": "cultist",
            "name": "邪教徒",
            "hp": 48,
            "move_table": [
                {
                    "move": "incantation",
                    "once": True,
                    "effects": [
                        {"type": "strength", "amount": 3},
                    ],
                },
                {
                    "move": "dark_strike",
                    "effects": [{"type": "damage", "amount": 6}],
                },
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
            hp=40,
            max_hp=40,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="cultist",
                hp=48,
                max_hp=48,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )

    result = run_end_turn(state, registry)

    assert [effect["type"] for effect in result.resolved_effects] == ["strength"]
    assert state.enemies[0].statuses == [StatusState(status_id="strength", stacks=3)]
    assert state.log == ["邪教徒获得 3 层力量。"]


def test_end_turn_doubt_applies_weak_after_existing_weak_expires() -> None:
    registry = _enemy_registry_without_attacks()
    state = _combat_state()
    state.hand = ["doubt#1"]
    state.player.statuses.append(StatusState(status_id="weak", stacks=1))

    resolved = end_turn(state, registry)

    assert [effect["type"] for effect in resolved] == ["weak"]
    assert state.player.statuses == [StatusState(status_id="weak", stacks=1)]


def test_run_end_turn_logs_doubt_triggered_weak() -> None:
    registry = _enemy_registry_without_attacks()
    registry.cards().register(
        {
            "id": "doubt",
            "name": "疑虑",
            "cost": -1,
            "playable": False,
            "can_appear_in_shop": False,
            "effects": [],
        }
    )
    state = _combat_state()
    state.hand = ["doubt#1"]

    run_end_turn(state, registry)

    assert state.log == ["疑虑施加 1 层虚弱。"]


def test_preview_enemy_move_reuses_combat_turn_logic_without_mutating_state() -> None:
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
        round_number=4,
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
                statuses=[StatusState(status_id="sleeping", stacks=2)],
            )
        ],
        effect_queue=[],
        log=[],
    )

    sleeping_preview = preview_enemy_move(state, state.enemies[0], registry.enemies().get("lagavulin"))
    assert sleeping_preview == {"move": "sleep", "sleep_turns": 2}
    assert [status.stacks for status in state.enemies[0].statuses if status.status_id == "sleeping"] == [2]

    state.enemies[0].statuses.clear()
    attack_preview = preview_enemy_move(state, state.enemies[0], registry.enemies().get("lagavulin"))
    assert attack_preview is not None
    assert attack_preview.get("move") == "heavy_slam"
    assert attack_preview.get("effects") == [{"type": "damage", "amount": 18}]


@pytest.mark.parametrize(
    ("starting_hp", "expected_total_damage"),
    [
        (24, 6),
        (25, 12),
        (49, 18),
        (73, 24),
    ],
)
def test_hexaghost_divider_scales_damage_by_player_hp(starting_hp: int, expected_total_damage: int) -> None:
    registry = _hexaghost_registry()
    state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-1",
            hp=starting_hp,
            max_hp=80,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="hexaghost",
                hp=250,
                max_hp=250,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )

    resolved = end_turn(state, registry)

    assert len(resolved) == 6
    assert [effect["type"] for effect in resolved] == ["damage"] * 6
    assert sum(int(effect["amount"]) for effect in resolved) == expected_total_damage
    assert state.player.hp == max(starting_hp - expected_total_damage, 0)


def test_hexaghost_divider_only_occurs_on_opening_turn_then_loops_without_it() -> None:
    registry = _Registry()
    registry.enemies().register(
        {
            "id": "hexaghost",
            "name": "Hexaghost",
            "hp": 250,
            "move_table": [
                {"move": "divider", "effects": [], "once": True},
                {"move": "sear", "effects": [{"type": "damage", "amount": 6}]},
                {"move": "tackle", "effects": [{"type": "damage", "amount": 14}]},
                {"move": "inferno", "effects": [{"type": "add_card_to_discard", "card_id": "burn", "count": 2}]},
                {"move": "tackle", "effects": [{"type": "damage", "amount": 14}]},
            ],
            "intent_policy": "scripted",
        }
    )
    state = CombatState(
        round_number=6,
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
                enemy_id="hexaghost",
                hp=250,
                max_hp=250,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=[],
    )

    preview = preview_enemy_move(state, state.enemies[0], registry.enemies().get("hexaghost"))

    assert preview is not None
    assert preview.get("move") == "sear"

    resolved = end_turn(state, registry)

    assert [effect["type"] for effect in resolved] == ["damage"]
    assert int(resolved[0]["amount"]) == 6
    assert state.player.hp == 74


def test_end_turn_resolves_burn_before_enemy_attack_and_discards_it() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.player.hp = 20
    state.hand = ["burn#1", "strike#1"]
    state.draw_pile = ["strike#2", "defend#2", "strike#3", "defend#3", "strike#4"]
    state.discard_pile = []

    resolved = end_turn(state, registry)

    assert [effect["type"] for effect in resolved] == ["damage", "damage"]
    assert [int(effect["amount"]) for effect in resolved] == [2, 5]
    assert state.player.hp == 13
    assert "burn#1" in state.discard_pile
    assert "burn#1" not in state.hand
    assert state.round_number == 2


def test_end_turn_stops_before_enemy_turn_when_burn_kills_player() -> None:
    registry = _enemy_registry()
    state = _combat_state()
    state.player.hp = 2
    state.hand = ["burn#1", "strike#1"]
    state.draw_pile = ["strike#2", "defend#2"]

    resolved = end_turn(state, registry)

    assert [effect["type"] for effect in resolved] == ["damage"]
    assert [int(effect["amount"]) for effect in resolved] == [2]
    assert state.player.hp == 0
    assert state.round_number == 1
