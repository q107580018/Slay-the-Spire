from __future__ import annotations

from slay_the_spire.content.registries import CardRegistry, EnemyRegistry
from slay_the_spire.use_cases.combat_log import describe_enemy_turn, describe_player_action
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.use_cases.combat_events import (
    CombatEvent,
    build_enemy_turn_events,
    build_player_action_events,
    capture_entity_snapshots,
)


class _Provider:
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

    def potions(self):
        raise NotImplementedError

    def events(self):
        raise NotImplementedError

    def acts(self):
        raise NotImplementedError


def _combat_state() -> CombatState:
    return CombatState(
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


def _provider() -> _Provider:
    provider = _Provider()
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


def test_build_player_action_events_uses_structured_effect_results() -> None:
    state = _combat_state()
    snapshots = capture_entity_snapshots(state, _provider())
    resolved_effects = [
        {
            "type": "damage",
            "target_instance_id": "enemy-1",
            "result": {"applied_amount": 6, "blocked": 2, "actual_damage": 4, "target_defeated": False},
        },
        {
            "type": "vulnerable",
            "target_instance_id": "enemy-1",
            "result": {"applied_stacks": 2},
        },
    ]

    events = build_player_action_events(
        card_name="重击",
        resolved_effects=resolved_effects,
        entities=snapshots,
        registry=None,
    )

    assert events == [
        CombatEvent(event_type="card_played", actor_name="你", card_name="重击"),
        CombatEvent(event_type="damage", actor_name="你", target_name="Training Dummy", amount=6, blocked=2, actual_damage=4),
        CombatEvent(event_type="status_applied", actor_name="你", target_name="Training Dummy", status_id="vulnerable", stacks=2),
    ]


def test_build_enemy_turn_events_adds_sleep_event_without_damage_recomputation() -> None:
    state = _combat_state()
    snapshots = capture_entity_snapshots(state, _provider())

    events = build_enemy_turn_events(
        enemy_previews=[(state.enemies[0], {"move": "sleep", "sleep_turns": 2})],
        resolved_effects=[],
        entities=snapshots,
        registry=_provider(),
    )

    assert events == [
        CombatEvent(event_type="sleep", actor_name="Training Dummy", amount=2),
    ]


def test_build_player_action_events_include_created_card_copy_for_logs() -> None:
    state = _combat_state()
    snapshots = capture_entity_snapshots(state, _provider())
    resolved_effects = [
        {
            "type": "create_card_copy",
            "card_id": "anger",
            "zone": "discard_pile",
            "result": {"created_card_instance_id": "anger#2"},
        }
    ]

    events = build_player_action_events(
        card_name="愤怒",
        resolved_effects=resolved_effects,
        entities=snapshots,
        registry=None,
    )

    assert describe_player_action(events=events) == ["你打出 愤怒，向弃牌堆加入 1 张anger。"]


def test_build_enemy_turn_events_keeps_status_card_source_name() -> None:
    state = _combat_state()
    provider = _provider()
    provider.cards().register(
        {
            "id": "doubt",
            "name": "疑虑",
            "cost": -1,
            "playable": False,
            "can_appear_in_shop": False,
            "effects": [],
        }
    )
    snapshots = capture_entity_snapshots(state, provider)

    events = build_enemy_turn_events(
        enemy_previews=[],
        resolved_effects=[
            {
                "type": "weak",
                "source_instance_id": "doubt#1",
                "target_instance_id": "player-1",
                "result": {"applied_stacks": 1},
            }
        ],
        entities=snapshots,
        registry=provider,
    )

    assert events == [
        CombatEvent(event_type="status_applied", actor_name="疑虑", target_name="你", status_id="weak", stacks=1),
    ]


def test_build_enemy_turn_events_include_strength_gain_for_enemy_sources() -> None:
    state = _combat_state()
    snapshots = capture_entity_snapshots(state, _provider())

    events = build_enemy_turn_events(
        enemy_previews=[],
        resolved_effects=[
            {
                "type": "strength",
                "source_instance_id": "enemy-1",
                "result": {"applied_stacks": 3},
            }
        ],
        entities=snapshots,
        registry=_provider(),
    )

    assert events == [
        CombatEvent(event_type="gain_strength", actor_name="Training Dummy", amount=3),
    ]
    assert describe_enemy_turn(events=events) == ["Training Dummy获得 3 层力量。"]
