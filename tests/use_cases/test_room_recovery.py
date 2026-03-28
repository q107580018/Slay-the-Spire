from __future__ import annotations

from pathlib import Path
from dataclasses import replace

import pytest

from slay_the_spire.app.session import MenuState, _open_treasure, load_session, render_session, route_command, route_menu_choice, start_session
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


def _boss_reward_ready_session(*, act_id: str, next_act_id: str | None) -> SessionState:
    base_session = start_session(seed=7)
    return replace(
        base_session,
        run_state=replace(base_session.run_state, current_act_id=act_id),
        act_state=generate_act_state(act_id, seed=7, registry=_content_provider()),
        room_state=RoomState(
            room_id=f"{act_id}:boss",
            room_type="boss",
            stage="completed",
            payload={
                "act_id": act_id,
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
                **({"next_act_id": next_act_id} if next_act_id is not None else {}),
            },
            is_resolved=True,
            rewards=[],
        ),
        menu_state=MenuState(mode="select_boss_reward"),
    )


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


def test_open_treasure_via_menu_grants_relic_marks_room_resolved_and_is_not_reapplied_after_load(tmp_path: Path) -> None:
    session = replace(
        start_session(seed=41),
        room_state=RoomState(
            room_id="act1:treasure",
            room_type="treasure",
            stage="waiting_input",
            payload={
                "act_id": "act1",
                "node_id": "r9c0",
                "next_node_ids": [],
                "treasure_relic_id": "golden_idol",
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=MenuState(),
    )

    unopened_render = render_session(session)

    assert "宝箱" in unopened_render
    assert "未打开" in unopened_render
    assert "金神像" in unopened_render

    _running, opened_session, opened_message = route_menu_choice("1", session=session)

    assert opened_session.run_state.relics == ["burning_blood", "golden_idol"]
    assert opened_session.room_state.is_resolved is True
    assert opened_session.room_state.stage == "completed"
    assert opened_session.room_state.payload["claimed_treasure_relic_id"] == "golden_idol"
    assert "已获得" in opened_message
    assert "金神像" in opened_message

    repository = JsonFileSaveRepository(tmp_path / "treasure.json")
    save_game(
        repository=repository,
        run_state=opened_session.run_state,
        act_state=opened_session.act_state,
        room_state=opened_session.room_state,
    )

    restored_session = load_session(save_path=tmp_path / "treasure.json", content_root=Path(__file__).resolve().parents[2] / "content")
    before_relics = list(restored_session.run_state.relics)

    assert restored_session.room_state.is_resolved is True
    assert restored_session.room_state.payload["claimed_treasure_relic_id"] == "golden_idol"

    _running, final_session, _message = route_menu_choice("1", session=restored_session)

    assert final_session.run_state.relics == before_relics
    assert final_session.room_state.payload["claimed_treasure_relic_id"] == "golden_idol"


def test_open_treasure_without_relic_candidate_grants_circlet() -> None:
    session = replace(
        start_session(seed=41),
        room_state=RoomState(
            room_id="act2:treasure",
            room_type="treasure",
            stage="waiting_input",
            payload={
                "act_id": "act2",
                "node_id": "r8c1",
                "next_node_ids": [],
                "treasure_relic_id": "circlet",
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=MenuState(),
    )

    _running, opened_session, opened_message = route_menu_choice("1", session=session)

    assert opened_session.room_state.is_resolved is True
    assert opened_session.room_state.stage == "completed"
    assert opened_session.room_state.payload["claimed_treasure_relic_id"] == "circlet"
    assert opened_session.run_state.relics == ["burning_blood", "circlet"]
    assert "圆环" in opened_message


def test_open_treasure_is_idempotent_when_room_is_already_resolved() -> None:
    session = replace(
        start_session(seed=41),
        run_state=replace(start_session(seed=41).run_state, relics=["burning_blood", "golden_idol"]),
        room_state=RoomState(
            room_id="act1:treasure",
            room_type="treasure",
            stage="completed",
            payload={
                "act_id": "act1",
                "node_id": "r9c0",
                "next_node_ids": [],
                "treasure_relic_id": "golden_idol",
                "claimed_treasure_relic_id": "golden_idol",
            },
            is_resolved=True,
            rewards=[],
        ),
        menu_state=MenuState(),
    )

    reopened_session = _open_treasure(session)

    assert reopened_session.run_state.to_dict() == session.run_state.to_dict()
    assert reopened_session.room_state.to_dict() == session.room_state.to_dict()


def test_open_treasure_with_existing_claim_marker_converges_room_via_menu_choice() -> None:
    session = replace(
        start_session(seed=41),
        run_state=replace(start_session(seed=41).run_state, relics=["burning_blood", "golden_idol"]),
        room_state=RoomState(
            room_id="act1:treasure",
            room_type="treasure",
            stage="waiting_input",
            payload={
                "act_id": "act1",
                "node_id": "r9c0",
                "next_node_ids": [],
                "treasure_relic_id": "golden_idol",
                "claimed_treasure_relic_id": "golden_idol",
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=MenuState(),
    )

    _running, reopened_session, _message = route_menu_choice("1", session=session)

    assert reopened_session.run_state.to_dict() == session.run_state.to_dict()
    assert reopened_session.room_state.stage == "completed"
    assert reopened_session.room_state.is_resolved is True
    assert reopened_session.room_state.payload["claimed_treasure_relic_id"] == "golden_idol"


def test_reward_claim_is_not_reapplied_after_load(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=37, registry=provider)
    act_state = generate_act_state("act1", seed=37, registry=provider)
    generated_rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:reward",
        run_state=run_state,
        registry=provider,
    )
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
    assert retried_room.rewards == generated_rewards[1:]


def test_claim_reward_marks_room_completed_immediately() -> None:
    generated_rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:reward",
        run_state=start_new_run("ironclad", seed=43, registry=_content_provider()),
        registry=_content_provider(),
    )
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
    assert claimed_room.rewards == generated_rewards[1:]


def test_claiming_card_offer_removes_other_card_offers() -> None:
    generated_rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:reward",
        run_state=start_new_run("ironclad", seed=43, registry=_content_provider()),
        registry=_content_provider(),
    )
    room_state = RoomState(
        room_id="act1:reward",
        room_type="reward",
        stage="waiting_input",
        payload={"generated_by": "combat_reward_generator"},
        is_resolved=False,
        rewards=generated_rewards,
    )

    claimed_room = claim_reward(room_state=room_state, reward_id=generated_rewards[1])

    assert claimed_room.payload["claimed_reward_ids"] == [generated_rewards[1]]
    assert all(not reward.startswith("card_offer:") for reward in claimed_room.rewards)


def test_generate_combat_rewards_feeds_reward_room_claim_flow() -> None:
    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:hallway_reward",
        run_state=start_new_run("ironclad", seed=41, registry=_content_provider()),
        registry=_content_provider(),
    )

    assert rewards[0].startswith("gold:")
    gold_amount = int(rewards[0].split(":", 1)[1])
    assert 10 <= gold_amount <= 20
    assert len([reward for reward in rewards if reward.startswith("card_offer:")]) == 3


def test_boss_victory_generates_payload_boss_rewards_instead_of_room_rewards() -> None:
    base_session = start_session(seed=37)
    session = replace(
        base_session,
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="waiting_input",
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "combat_state": CombatState(
                    round_number=1,
                    energy=1,
                    hand=["strike#1"],
                    draw_pile=[],
                    discard_pile=[],
                    exhaust_pile=[],
                    player=PlayerCombatState(
                        instance_id="player-ironclad",
                        hp=80,
                        max_hp=80,
                        block=0,
                        statuses=[],
                    ),
                    enemies=[
                        EnemyState(
                            instance_id="enemy-1",
                            enemy_id="jaw_worm",
                            hp=6,
                            max_hp=6,
                            block=0,
                            statuses=[],
                        )
                    ],
                    effect_queue=[],
                    log=[],
                ).to_dict(),
            },
            is_resolved=False,
            rewards=[],
        ),
    )

    _running, next_session, _message = route_command("play 1", session=session)
    boss_rewards = next_session.room_state.payload["boss_rewards"]

    assert next_session.run_phase == "active"
    assert next_session.room_state.is_resolved is True
    assert next_session.room_state.rewards == []
    assert boss_rewards["generated_by"] == "boss_reward_generator"
    assert boss_rewards["gold_reward"] == 106


def test_claiming_boss_gold_only_does_not_enter_victory() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
        menu_state=MenuState(mode="select_boss_reward"),
    )

    _running, next_session, _message = route_menu_choice("1", session=session)

    assert next_session.run_phase == "active"
    assert next_session.room_state.payload["boss_rewards"]["claimed_gold"] is True
    assert next_session.run_state.gold == 198


def test_partial_boss_reward_progress_survives_load_session(tmp_path: Path) -> None:
    provider = _content_provider()
    initial_session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
        menu_state=MenuState(mode="select_boss_reward"),
    )

    _running, claimed_gold_session, _message = route_menu_choice("1", session=initial_session)
    repository = JsonFileSaveRepository(tmp_path / "boss_reward.json")
    save_game(
        repository=repository,
        run_state=claimed_gold_session.run_state,
        act_state=generate_act_state("act1", seed=7, registry=provider),
        room_state=claimed_gold_session.room_state,
    )

    restored_session = load_session(
        save_path=tmp_path / "boss_reward.json",
        content_root=Path(__file__).resolve().parents[2] / "content",
    )
    _running, reward_menu_session, _message = route_menu_choice("1", session=restored_session)
    _running, relic_menu_session, _message = route_menu_choice("2", session=reward_menu_session)
    _running, boss_chest_session, boss_chest_message = route_menu_choice("1", session=relic_menu_session)
    _running, transitioned_session, _message = route_menu_choice("1", session=boss_chest_session)

    assert claimed_gold_session.run_phase == "active"
    assert claimed_gold_session.room_state.payload["boss_rewards"]["claimed_gold"] is True
    assert restored_session.run_state.gold == claimed_gold_session.run_state.gold
    assert restored_session.run_phase == "active"
    assert restored_session.menu_state.mode == "root"
    assert restored_session.room_state.payload["boss_rewards"]["claimed_gold"] is True
    assert restored_session.room_state.payload["boss_rewards"]["claimed_relic_id"] is None
    assert set(restored_session.room_state.payload["boss_rewards"]["boss_relic_offers"]).isdisjoint(
        restored_session.run_state.relics
    )
    assert reward_menu_session.menu_state.mode == "select_boss_reward"
    assert relic_menu_session.menu_state.mode == "select_boss_relic"
    assert boss_chest_session.room_state.room_type == "boss_chest"
    assert boss_chest_session.room_state.payload["next_act_id"] == "act2"
    assert boss_chest_session.run_phase == "active"
    assert "Boss宝箱" in boss_chest_message
    assert "前往下一幕" in boss_chest_message
    assert transitioned_session.run_phase == "active"
    assert transitioned_session.run_state.current_act_id == "act2"
    assert transitioned_session.act_state.act_id == "act2"
    assert transitioned_session.room_state.payload["act_id"] == "act2"
    assert "black_blood" in transitioned_session.run_state.relics


def test_completed_boss_reward_state_enters_boss_chest_on_load(tmp_path: Path) -> None:
    provider = _content_provider()
    base_session = start_session(seed=11)
    initial_session = replace(
        base_session,
        run_state=replace(base_session.run_state, current_act_id="act1"),
        act_state=generate_act_state("act1", seed=11, registry=provider),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": True,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": "black_blood",
                },
            },
            is_resolved=True,
            rewards=[],
        ),
    )
    repository = JsonFileSaveRepository(tmp_path / "completed_boss_reward.json")
    save_game(
        repository=repository,
        run_state=initial_session.run_state,
        act_state=initial_session.act_state,
        room_state=initial_session.room_state,
    )

    restored_session = load_session(
        save_path=tmp_path / "completed_boss_reward.json",
        content_root=Path(__file__).resolve().parents[2] / "content",
    )

    assert restored_session.run_state.current_act_id == "act1"
    assert restored_session.act_state.act_id == "act1"
    assert restored_session.room_state.room_id == "act1:boss_chest"
    assert restored_session.room_state.room_type == "boss_chest"
    assert restored_session.room_state.payload["act_id"] == "act1"
    assert restored_session.room_state.payload["node_id"] == "boss_chest"
    assert restored_session.room_state.payload["next_act_id"] == "act2"
    assert restored_session.menu_state.mode == "root"
    assert restored_session.run_phase == "active"


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
    assert next_session.run_state.gold == 110


def test_reward_claim_flow_after_load_session_keeps_partial_rewards_open(tmp_path: Path) -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:hallway",
            room_type="combat",
            stage="completed",
            payload={"node_id": "r1c0", "next_node_ids": ["r2c0"]},
            is_resolved=True,
            rewards=["gold:11", "card_offer:anger"],
        ),
    )
    repository = JsonFileSaveRepository(tmp_path / "reward_detail.json")
    save_game(
        repository=repository,
        run_state=session.run_state,
        act_state=session.act_state,
        room_state=session.room_state,
    )

    restored_session = load_session(
        save_path=tmp_path / "reward_detail.json",
        content_root=Path(__file__).resolve().parents[2] / "content",
    )
    _running, claim_menu_session, claim_menu_message = route_menu_choice("1", session=restored_session)
    _running, claimed_gold_session, claimed_gold_message = route_menu_choice("1", session=claim_menu_session)
    _running, claimed_card_session, claimed_card_message = route_menu_choice("1", session=claimed_gold_session)

    assert restored_session.menu_state.mode == "root"
    assert restored_session.room_state.rewards == ["gold:11", "card_offer:anger"]
    assert claim_menu_session.menu_state.mode == "select_reward"
    assert claim_menu_session.room_state.rewards == ["gold:11", "card_offer:anger"]
    assert "奖励:" in claim_menu_message
    assert claimed_gold_session.menu_state.mode == "select_reward"
    assert claimed_gold_session.room_state.rewards == ["card_offer:anger"]
    assert claimed_gold_session.run_state.gold == 110
    assert "奖励:" in claimed_gold_message
    assert claimed_card_session.menu_state.mode == "root"
    assert claimed_card_session.room_state.rewards == []
    assert claimed_card_session.run_state.gold == 110
    assert "前往下一个房间" in claimed_card_message


def test_event_room_inspect_round_trip_keeps_choice_flow() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:event",
            room_type="event",
            stage="waiting_input",
            payload={
                "node_id": "r1c1",
                "room_kind": "event",
                "event_id": "golden_shrine",
                "next_node_ids": ["r2c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
    )

    _running, inspect_session, inspect_message = route_menu_choice("2", session=session)
    _running, stats_session, stats_message = route_menu_choice("1", session=inspect_session)
    _running, inspect_back_session, inspect_back_message = route_menu_choice("1", session=stats_session)
    _running, root_session, root_message = route_menu_choice("5", session=inspect_back_session)
    _running, choice_menu_session, _choice_menu_message = route_menu_choice("1", session=root_session)
    _running, next_session, _message = route_menu_choice("1", session=choice_menu_session)

    assert inspect_session.menu_state.mode == "inspect_root"
    assert "资料总览" in inspect_message
    assert stats_session.menu_state.mode == "inspect_stats"
    assert inspect_back_session.menu_state.mode == "inspect_root"
    assert root_session.menu_state.mode == "root"
    assert "事件操作" in root_message
    assert choice_menu_session.menu_state.mode == "select_event_choice"
    assert next_session.room_state.is_resolved is True


def test_boss_reward_root_inspect_round_trip_keeps_reward_menu_numbering() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
    )

    _running, inspect_session, inspect_message = route_menu_choice("2", session=session)
    _running, stats_session, stats_message = route_menu_choice("1", session=inspect_session)
    _running, inspect_back_session, inspect_back_message = route_menu_choice("1", session=stats_session)
    _running, reward_root_session, reward_root_message = route_menu_choice("5", session=inspect_back_session)
    _running, select_reward_session, select_reward_message = route_menu_choice("1", session=reward_root_session)
    _running, claimed_session, _claimed_message = route_menu_choice("1", session=select_reward_session)

    assert inspect_session.menu_state.mode == "inspect_root"
    assert "资料总览" in inspect_message
    assert stats_session.menu_state.mode == "inspect_stats"
    assert inspect_back_session.menu_state.mode == "inspect_root"
    assert reward_root_session.menu_state.mode == "root"
    assert "领取奖励" in reward_root_message
    assert select_reward_session.menu_state.mode == "select_boss_reward"
    assert "Boss奖励" in select_reward_message
    assert claimed_session.run_phase == "active"
    assert claimed_session.room_state.payload["boss_rewards"]["claimed_gold"] is True
    assert claimed_session.run_state.gold == 198


def test_claiming_already_claimed_boss_gold_stays_in_menu_with_message() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": True,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
        menu_state=MenuState(mode="select_boss_reward"),
    )

    _running, next_session, message = route_menu_choice("1", session=session)

    assert next_session.menu_state.mode == "select_boss_reward"
    assert next_session.run_state.gold == session.run_state.gold
    assert next_session.room_state.payload["boss_rewards"]["claimed_gold"] is True
    assert "金币已领取" in message


def test_combat_reward_root_inspect_uses_visible_back_choice_before_claim_flow() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:hallway",
            room_type="combat",
            stage="completed",
            payload={"node_id": "r1c0", "next_node_ids": ["r2c0"]},
            is_resolved=True,
            rewards=["gold:11"],
        ),
    )

    _running, inspect_session, inspect_message = route_menu_choice("3", session=session)
    _running, stats_session, stats_message = route_menu_choice("1", session=inspect_session)
    _running, inspect_back_session, inspect_back_message = route_menu_choice("1", session=stats_session)
    _running, reward_root_session, reward_root_message = route_menu_choice("5", session=inspect_back_session)
    _running, select_reward_session, select_reward_message = route_menu_choice("1", session=reward_root_session)
    _running, claimed_session, claimed_message = route_menu_choice("1", session=select_reward_session)

    assert inspect_session.menu_state.mode == "inspect_root"
    assert inspect_session.menu_state.inspect_parent_mode == "root"
    assert "资料总览" in inspect_message
    assert stats_session.menu_state.mode == "inspect_stats"
    assert "角色状态" in stats_message
    assert inspect_back_session.menu_state.mode == "inspect_root"
    assert inspect_back_session.menu_state.inspect_parent_mode == "root"
    assert "资料总览" in inspect_back_message
    assert reward_root_session.menu_state.mode == "root"
    assert reward_root_session.room_state.rewards == ["gold:11"]
    assert "领取奖励" in reward_root_message
    assert select_reward_session.menu_state.mode == "select_reward"
    assert "奖励" in select_reward_message
    assert claimed_session.menu_state.mode == "root"
    assert claimed_session.room_state.rewards == []
    assert claimed_session.run_state.gold == 110
    assert "前往下一个房间" in claimed_message


def test_reward_room_inspect_back_to_root_uses_current_claim_reward_title() -> None:
    combat_session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:hallway",
            room_type="combat",
            stage="completed",
            payload={"node_id": "r1c0", "next_node_ids": ["r2c0"]},
            is_resolved=True,
            rewards=["gold:11"],
        ),
    )
    boss_session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:boss",
            room_type="boss",
            stage="completed",
            payload={
                "node_id": "boss",
                "next_node_ids": [],
                "boss_rewards": {
                    "generated_by": "boss_reward_generator",
                    "gold_reward": 99,
                    "claimed_gold": False,
                    "boss_relic_offers": ["black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"],
                    "claimed_relic_id": None,
                },
            },
            is_resolved=True,
            rewards=[],
        ),
    )

    _running, combat_inspect_session, _combat_inspect_message = route_menu_choice("3", session=combat_session)
    _running, combat_root_session, combat_root_message = route_menu_choice("5", session=combat_inspect_session)
    _running, boss_inspect_session, _boss_inspect_message = route_menu_choice("2", session=boss_session)
    _running, boss_root_session, boss_root_message = route_menu_choice("5", session=boss_inspect_session)

    assert combat_inspect_session.menu_state.mode == "inspect_root"
    assert combat_root_session.menu_state.mode == "root"
    assert combat_root_message.splitlines()[0] == "领取奖励"
    assert boss_inspect_session.menu_state.mode == "inspect_root"
    assert boss_root_session.menu_state.mode == "root"
    assert boss_root_message.splitlines()[0] == "领取奖励"


def test_combat_reward_root_inspect_potions_follow_visible_menu_numbering() -> None:
    base_session = start_session(seed=7)
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, potions=["fire_potion"]),
        room_state=RoomState(
            room_id="act1:hallway",
            room_type="combat",
            stage="completed",
            payload={"node_id": "r1c0", "next_node_ids": ["r2c0"]},
            is_resolved=True,
            rewards=["gold:11"],
        ),
    )

    _running, inspect_session, inspect_message = route_menu_choice("3", session=session)
    _running, potions_session, potions_message = route_menu_choice("4", session=inspect_session)
    _running, inspect_back_session, inspect_back_message = route_menu_choice("1", session=potions_session)
    _running, reward_root_session, reward_root_message = route_menu_choice("5", session=inspect_back_session)
    _running, select_reward_session, select_reward_message = route_menu_choice("1", session=reward_root_session)
    _running, claimed_session, claimed_message = route_menu_choice("1", session=select_reward_session)

    assert inspect_session.menu_state.mode == "inspect_root"
    assert inspect_session.menu_state.inspect_parent_mode == "root"
    assert "资料总览" in inspect_message
    assert potions_session.menu_state.mode == "inspect_potions"
    assert potions_session.menu_state.inspect_parent_mode == "root"
    assert potions_session.menu_state.inspect_item_id == "potions"
    assert "药水列表" in potions_message
    assert inspect_back_session.menu_state.mode == "inspect_root"
    assert inspect_back_session.menu_state.inspect_parent_mode == "root"
    assert "资料总览" in inspect_back_message
    assert reward_root_session.menu_state.mode == "root"
    assert "领取奖励" in reward_root_message
    assert select_reward_session.menu_state.mode == "select_reward"
    assert "奖励" in select_reward_message
    assert claimed_session.room_state.rewards == []
    assert claimed_session.run_state.gold == 110
    assert "前往下一个房间" in claimed_message


def test_claim_all_rewards_clears_non_boss_room_rewards() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:hallway",
            room_type="combat",
            stage="completed",
            payload={"node_id": "r1c0", "next_node_ids": ["r2c0", "r2c1"]},
            is_resolved=True,
            rewards=["gold:11", "card:anger"],
        ),
        menu_state=MenuState(mode="select_reward"),
    )

    _running, next_session, _message = route_menu_choice("3", session=session)

    assert next_session.run_phase == "active"
    assert next_session.room_state.rewards == []
    assert next_session.menu_state.mode == "root"
    assert next_session.run_state.gold == 110
    assert next_session.run_state.deck[-1] == "anger#11"


def test_claiming_boss_relic_after_gold_enters_final_boss_chest_before_victory() -> None:
    session = _boss_reward_ready_session(act_id="act2", next_act_id=None)

    _running, session, _message = route_menu_choice("1", session=session)
    _running, session, _message = route_menu_choice("2", session=session)
    _running, next_session, render_message = route_menu_choice("1", session=session)

    assert next_session.run_phase == "active"
    assert next_session.run_state.current_act_id == "act2"
    assert next_session.room_state.room_type == "boss_chest"
    assert next_session.menu_state.mode == "root"
    assert next_session.room_state.payload["boss_rewards"]["claimed_relic_id"] == "black_blood"
    assert "Boss宝箱" in render_message
    assert "完成攀登" in render_message
    assert "black_blood" in next_session.run_state.relics

    _running, victory_session, _message = route_menu_choice("1", session=next_session)

    assert victory_session.run_phase == "victory"
    assert victory_session.run_state.current_act_id == "act2"


def test_claiming_final_boss_reward_in_act1_enters_boss_chest_before_act2() -> None:
    session = _boss_reward_ready_session(act_id="act1", next_act_id="act2")

    _running, gold_session, _message = route_menu_choice("1", session=session)
    _running, relic_menu_session, _message = route_menu_choice("2", session=gold_session)
    _running, boss_chest_session, render_message = route_menu_choice("1", session=relic_menu_session)

    assert boss_chest_session.run_phase == "active"
    assert boss_chest_session.run_state.current_act_id == "act1"
    assert boss_chest_session.act_state.act_id == "act1"
    assert boss_chest_session.room_state.room_type == "boss_chest"
    assert boss_chest_session.room_state.payload["act_id"] == "act1"
    assert boss_chest_session.room_state.payload["next_act_id"] == "act2"
    assert "Boss宝箱" in render_message
    assert "前往下一幕" in render_message

    _running, next_session, _message = route_menu_choice("1", session=boss_chest_session)

    assert next_session.run_phase == "active"
    assert next_session.run_state.current_act_id == "act2"
    assert next_session.act_state.act_id == "act2"
    assert next_session.room_state.payload["act_id"] == "act2"


def test_shop_menu_returns_prompt_when_gold_is_insufficient() -> None:
    session = replace(
        start_session(seed=7),
        run_state=replace(start_session(seed=7).run_state, gold=40),
        room_state=RoomState(
            room_id="act1:shop",
            room_type="shop",
            stage="waiting_input",
            payload={
                "node_id": "r3c1",
                "cards": [{"offer_id": "card-1", "card_id": "strike", "price": 50}],
                "relics": [],
                "potions": [],
                "remove_price": 75,
                "next_node_ids": ["r4c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=MenuState(mode="shop_root"),
    )

    _running, next_session, message = route_menu_choice("1", session=session)

    assert next_session.run_state.gold == 40
    assert "金币不足，无法购买该商品。" in message


def test_shop_menu_returns_prompt_when_item_is_already_purchased() -> None:
    base_session = start_session(seed=7)
    session = replace(
        base_session,
        room_state=RoomState(
            room_id="act1:shop",
            room_type="shop",
            stage="waiting_input",
            payload={
                "node_id": "r3c1",
                "cards": [{"offer_id": "card-1", "card_id": "strike", "price": 50, "sold": True}],
                "relics": [],
                "potions": [],
                "remove_price": 75,
                "next_node_ids": ["r4c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=MenuState(mode="shop_root"),
    )

    _running, _next_session, message = route_menu_choice("1", session=session)

    assert "该商品已购买。" in message


def test_shop_room_inspect_round_trip_keeps_shop_flow() -> None:
    session = replace(
        start_session(seed=7),
        room_state=RoomState(
            room_id="act1:shop",
            room_type="shop",
            stage="waiting_input",
            payload={
                "node_id": "r3c1",
                "cards": [{"offer_id": "card-1", "card_id": "strike", "price": 50}],
                "relics": [],
                "potions": [],
                "remove_price": 75,
                "next_node_ids": ["r4c0"],
            },
            is_resolved=False,
            rewards=[],
        ),
        menu_state=MenuState(mode="shop_root"),
    )

    _running, inspect_session, inspect_message = route_menu_choice("4", session=session)
    _running, stats_session, stats_message = route_menu_choice("1", session=inspect_session)
    _running, inspect_back_session, inspect_back_message = route_menu_choice("1", session=stats_session)
    _running, shop_session, shop_message = route_menu_choice("5", session=inspect_back_session)
    _running, leave_session, leave_message = route_menu_choice("3", session=shop_session)

    assert inspect_session.menu_state.mode == "inspect_root"
    assert "资料总览" in inspect_message
    assert stats_session.menu_state.mode == "inspect_stats"
    assert "角色状态" in stats_message
    assert inspect_back_session.menu_state.mode == "inspect_root"
    assert "资料总览" in inspect_back_message
    assert shop_session.menu_state.mode == "shop_root"
    assert "商店操作" in shop_message
    assert leave_session.room_state.is_resolved is True
    assert leave_session.menu_state.mode == "root"
    assert "前往下一个房间" in leave_message


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


def test_game_over_menu_uses_terminal_phase_choice_mapping(tmp_path: Path) -> None:
    base_session = start_session(seed=61, save_path=tmp_path / "game_over.json")
    session = replace(
        base_session,
        run_state=replace(base_session.run_state, current_hp=0),
        room_state=replace(base_session.room_state, stage="defeated", is_resolved=False),
        run_phase="game_over",
        menu_state=MenuState(),
    )

    running, viewed_session, viewed_message = route_menu_choice("1", session=session)

    assert running is True
    assert viewed_session.run_phase == "game_over"
    assert "游戏结束" in viewed_message

    running, saved_session, saved_message = route_menu_choice("2", session=session)

    assert running is True
    assert saved_session.save_path.exists()
    assert f"已保存到 {saved_session.save_path}" == saved_message

    altered_session = replace(session, run_state=replace(session.run_state, current_hp=7))

    running, loaded_session, loaded_message = route_menu_choice("3", session=altered_session)

    assert running is True
    assert loaded_session.run_state.current_hp == 0
    assert loaded_session.run_phase == "game_over"
    assert loaded_session.room_state.stage == "defeated"
    assert f"已从存档恢复。当前存档: {saved_session.save_path}" == loaded_message

    running, exited_session, exited_message = route_menu_choice("4", session=session)

    assert running is False
    assert exited_session.menu_state.mode == "root"
    assert exited_message == "已退出游戏。"


def test_burning_blood_heals_after_winning_combat() -> None:
    base_session = start_session(seed=7)
    combat_state = CombatState.from_dict(base_session.room_state.payload["combat_state"])
    combat_state.player.hp = 50
    combat_state.enemies = [replace(combat_state.enemies[0], hp=6, max_hp=6)]
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
