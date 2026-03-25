from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest

from slay_the_spire.app.session import MenuState, load_session, route_command, route_menu_choice, start_session
from slay_the_spire.adapters.persistence.save_files import JsonFileSaveRepository
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.rewards.reward_generator import generate_combat_rewards
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.use_cases.claim_reward import claim_reward
from slay_the_spire.use_cases.load_game import load_game
from slay_the_spire.use_cases.resolve_event_choice import resolve_event_choice
from slay_the_spire.use_cases.rest_action import rest_action
from slay_the_spire.use_cases.save_game import save_game
from slay_the_spire.use_cases.shop_action import shop_action
from slay_the_spire.use_cases.start_run import start_new_run
from slay_the_spire.domain.map.map_generator import generate_act_state


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def test_event_choice_is_not_reapplied_after_load(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=23, registry=provider)
    act_state = generate_act_state("act1", seed=23, registry=provider)
    room_state = RoomState(
        room_id="act1:event",
        room_type="event",
        stage="waiting_input",
        payload={"event_id": "shining_light"},
        is_resolved=False,
        rewards=[],
    )
    resolved_room = resolve_event_choice(room_state=room_state, choice_id="accept", registry=provider)
    repository = JsonFileSaveRepository(tmp_path / "event.json")
    save_game(repository=repository, run_state=run_state, act_state=act_state, room_state=resolved_room)

    restored_room = load_game(repository=repository)["room_state"]
    retried_room = resolve_event_choice(room_state=restored_room, choice_id="leave", registry=provider)

    assert retried_room.to_dict() == restored_room.to_dict()
    assert retried_room.payload["choice_id"] == "accept"
    assert retried_room.rewards == ["event:gain_upgrade"]


def test_shop_remove_subflow_survives_load_session(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=29, registry=provider)
    act_state = generate_act_state("act1", seed=29, registry=provider)
    entered_remove = shop_action(
        run_state=run_state,
        room_state=RoomState(
            room_id="act1:shop",
            room_type="shop",
            stage="waiting_input",
            payload={
                "cards": [{"offer_id": "card-1", "card_id": "strike", "price": 50}],
                "relics": [],
                "potions": [],
                "remove_price": 75,
            },
            is_resolved=False,
            rewards=[],
        ),
        action_id="remove",
    )
    repository = JsonFileSaveRepository(tmp_path / "shop.json")
    save_game(
        repository=repository,
        run_state=entered_remove.run_state,
        act_state=act_state,
        room_state=entered_remove.room_state,
    )

    restored_room = load_game(repository=repository)["room_state"]
    restored_session = load_session(save_path=tmp_path / "shop.json", content_root=Path(__file__).resolve().parents[2] / "content")

    assert restored_room.stage == "select_remove_card"
    assert restored_room.payload["remove_candidates"] == entered_remove.run_state.deck
    assert restored_session.menu_state.mode == "shop_remove_card"


def test_rest_upgrade_subflow_survives_load_session(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=31, registry=provider)
    act_state = generate_act_state("act1", seed=31, registry=provider)
    entered_smith = rest_action(
        run_state=run_state,
        room_state=RoomState(
            room_id="act1:rest",
            room_type="rest",
            stage="waiting_input",
            payload={"actions": ["rest", "smith"]},
            is_resolved=False,
            rewards=[],
        ),
        action_id="smith",
        registry=provider,
    )
    repository = JsonFileSaveRepository(tmp_path / "rest.json")
    save_game(
        repository=repository,
        run_state=entered_smith.run_state,
        act_state=act_state,
        room_state=entered_smith.room_state,
    )

    restored_room = load_game(repository=repository)["room_state"]
    restored_session = load_session(save_path=tmp_path / "rest.json", content_root=Path(__file__).resolve().parents[2] / "content")

    assert restored_room.stage == "select_upgrade_card"
    assert restored_room.payload["upgrade_options"] == ["bash#10"]
    assert restored_session.menu_state.mode == "rest_upgrade_card"


def test_reward_claim_is_not_reapplied_after_load(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=37, registry=provider)
    act_state = generate_act_state("act1", seed=37, registry=provider)
    generated_rewards = generate_combat_rewards(room_id="act1:reward", seed=37)
    room_state = RoomState(
        room_id="act1:reward",
        room_type="reward",
        stage="waiting_input",
        payload={"generated_by": "combat_reward_generator"},
        is_resolved=False,
        rewards=generated_rewards,
    )
    claimed_room = claim_reward(room_state=room_state, reward_id=generated_rewards[0])
    repository = JsonFileSaveRepository(tmp_path / "reward.json")
    save_game(repository=repository, run_state=run_state, act_state=act_state, room_state=claimed_room)

    restored_room = load_game(repository=repository)["room_state"]
    retried_room = claim_reward(room_state=restored_room, reward_id=generated_rewards[1])

    assert retried_room.to_dict() == restored_room.to_dict()
    assert retried_room.stage == "completed"
    assert retried_room.is_resolved is True
    assert retried_room.payload["claimed_reward_ids"] == [generated_rewards[0]]
    assert retried_room.payload["generated_by"] == "combat_reward_generator"
    assert retried_room.rewards == [generated_rewards[1]]


def test_claim_reward_marks_room_completed_immediately() -> None:
    generated_rewards = generate_combat_rewards(room_id="act1:reward", seed=43)
    room_state = RoomState(
        room_id="act1:reward",
        room_type="reward",
        stage="waiting_input",
        payload={"generated_by": "combat_reward_generator"},
        is_resolved=False,
        rewards=generated_rewards,
    )

    claimed_room = claim_reward(room_state=room_state, reward_id=generated_rewards[0])

    assert claimed_room.stage == "completed"
    assert claimed_room.is_resolved is True
    assert claimed_room.payload["claimed_reward_ids"] == [generated_rewards[0]]
    assert claimed_room.rewards == [generated_rewards[1]]


def test_generate_combat_rewards_feeds_reward_room_claim_flow() -> None:
    rewards = generate_combat_rewards(room_id="act1:hallway_reward", seed=41)

    assert rewards == ["gold:11", "card:reward_strike"]


def test_claiming_boss_reward_sets_session_victory_and_does_not_return_to_map() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={"node_id": "boss", "next_node_ids": []},
            is_resolved=True,
            rewards=["gold:99"],
        ),
        menu_state=MenuState(mode="select_reward"),
    )

    _running, next_session, _message = route_menu_choice("1", session=session)

    assert next_session.run_phase == "victory"
    assert next_session.room_state.rewards == []


def test_non_boss_reward_claim_returns_to_map_selection() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:hallway",
            room_type="combat",
            stage="completed",
            payload={"node_id": "r1c0", "next_node_ids": ["r2c0", "r2c1"]},
            is_resolved=True,
            rewards=["gold:11"],
        ),
        menu_state=MenuState(mode="select_reward"),
    )

    _running, next_session, _message = route_menu_choice("1", session=session)

    assert next_session.run_phase == "active"
    assert next_session.room_state.rewards == []
    assert next_session.menu_state.mode == "root"


def test_player_defeat_sets_session_game_over_and_blocks_further_actions(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=53, registry=provider)
    act_state = generate_act_state("act1", seed=53, registry=provider)
    defeated_combat = CombatState(
        round_number=2,
        energy=0,
        hand=[],
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id="player-ironclad",
            hp=0,
            max_hp=80,
            block=0,
            statuses=[],
        ),
        enemies=[
            EnemyState(
                instance_id="enemy-1",
                enemy_id="jaw_worm",
                hp=12,
                max_hp=40,
                block=0,
                statuses=[],
            )
        ],
        effect_queue=[],
        log=["player was defeated"],
    )
    repository = JsonFileSaveRepository(tmp_path / "defeat.json")
    save_game(
        repository=repository,
        run_state=replace(run_state, current_hp=0),
        act_state=act_state,
        room_state=RoomState(
            room_id="act1:elite",
            room_type="elite",
            stage="defeated",
            payload={"combat_state": defeated_combat.to_dict()},
            is_resolved=False,
            rewards=[],
        ),
    )

    restored = load_session(save_path=tmp_path / "defeat.json", content_root=Path(__file__).resolve().parents[2] / "content")
    _running, same_session, message = route_command("end", session=restored)

    assert restored.run_phase == "game_over"
    assert same_session.run_phase == "game_over"
    assert "已结束" in message


def test_burning_blood_heals_after_winning_combat() -> None:
    base_session = start_session(seed=7)
    combat_state = CombatState.from_dict(base_session.room_state.payload["combat_state"])
    combat_state.player.hp = 50
    combat_state.enemies[0].hp = 6
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, current_hp=50),
        room_state=RoomState(
            room_id=base_session.room_state.room_id,
            room_type=base_session.room_state.room_type,
            stage="waiting_input",
            payload={
                **base_session.room_state.payload,
                "combat_state": combat_state.to_dict(),
            },
            is_resolved=False,
            rewards=[],
        ),
    )

    _running, next_session, _message = route_command("play 1", session=session)

    assert next_session.room_state.is_resolved is True
    assert next_session.run_state.current_hp == 56


@pytest.mark.parametrize(
    ("factory", "kwargs", "match"),
    [
        (resolve_event_choice, {"room_state": RoomState(room_id="r1", room_type="shop", stage="waiting_input", payload={}, is_resolved=False, rewards=[]), "choice_id": "accept", "registry": _content_provider()}, "event"),
        (
            shop_action,
            {
                "run_state": start_new_run("ironclad", seed=7, registry=_content_provider()),
                "room_state": RoomState(room_id="r2", room_type="event", stage="waiting_input", payload={}, is_resolved=False, rewards=[]),
                "action_id": "buy",
            },
            "shop",
        ),
        (
            rest_action,
            {
                "run_state": start_new_run("ironclad", seed=8, registry=_content_provider()),
                "room_state": RoomState(room_id="r3", room_type="reward", stage="waiting_input", payload={}, is_resolved=False, rewards=[]),
                "action_id": "rest",
                "registry": _content_provider(),
            },
            "rest",
        ),
        (claim_reward, {"room_state": RoomState(room_id="r4", room_type="rest", stage="waiting_input", payload={}, is_resolved=False, rewards=[]), "reward_id": "gold"}, "reward"),
    ],
)
def test_room_actions_reject_wrong_room_type(factory, kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        factory(**kwargs)
