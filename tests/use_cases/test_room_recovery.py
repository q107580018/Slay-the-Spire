from __future__ import annotations

from pathlib import Path

import pytest

from slay_the_spire.adapters.persistence.save_files import JsonFileSaveRepository
from slay_the_spire.content.provider import StarterContentProvider
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


def test_shop_action_is_not_reapplied_after_load(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=29, registry=provider)
    act_state = generate_act_state("act1", seed=29, registry=provider)
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={"inventory": ["card:strike_plus", "relic:burning_blood"]},
        is_resolved=False,
        rewards=[],
    )
    shopped_room = shop_action(room_state=room_state, action_id="buy:card:strike_plus")
    repository = JsonFileSaveRepository(tmp_path / "shop.json")
    save_game(repository=repository, run_state=run_state, act_state=act_state, room_state=shopped_room)

    restored_room = load_game(repository=repository)["room_state"]
    retried_room = shop_action(room_state=restored_room, action_id="leave")

    assert retried_room.to_dict() == restored_room.to_dict()
    assert retried_room.payload["action_id"] == "buy:card:strike_plus"
    assert retried_room.rewards == ["shop:card:strike_plus"]


def test_rest_action_is_not_reapplied_after_load(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=31, registry=provider)
    act_state = generate_act_state("act1", seed=31, registry=provider)
    room_state = RoomState(
        room_id="act1:rest",
        room_type="rest",
        stage="waiting_input",
        payload={"options": ["rest", "smith"]},
        is_resolved=False,
        rewards=[],
    )
    rested_room = rest_action(room_state=room_state, action_id="rest")
    repository = JsonFileSaveRepository(tmp_path / "rest.json")
    save_game(repository=repository, run_state=run_state, act_state=act_state, room_state=rested_room)

    restored_room = load_game(repository=repository)["room_state"]
    retried_room = rest_action(room_state=restored_room, action_id="smith")

    assert retried_room.to_dict() == restored_room.to_dict()
    assert retried_room.payload["action_id"] == "rest"
    assert retried_room.rewards == ["rest:heal"]


def test_reward_claim_is_not_reapplied_after_load(tmp_path: Path) -> None:
    provider = _content_provider()
    run_state = start_new_run("ironclad", seed=37, registry=provider)
    act_state = generate_act_state("act1", seed=37, registry=provider)
    room_state = RoomState(
        room_id="act1:reward",
        room_type="reward",
        stage="waiting_input",
        payload={},
        is_resolved=False,
        rewards=["gold:12", "card:strike_plus"],
    )
    claimed_room = claim_reward(room_state=room_state, reward_id="gold:12")
    repository = JsonFileSaveRepository(tmp_path / "reward.json")
    save_game(repository=repository, run_state=run_state, act_state=act_state, room_state=claimed_room)

    restored_room = load_game(repository=repository)["room_state"]
    retried_room = claim_reward(room_state=restored_room, reward_id="card:strike_plus")

    assert retried_room.to_dict() == restored_room.to_dict()
    assert retried_room.payload["claimed_reward_ids"] == ["gold:12"]
    assert retried_room.rewards == ["card:strike_plus"]


@pytest.mark.parametrize(
    ("factory", "kwargs", "match"),
    [
        (resolve_event_choice, {"room_state": RoomState(room_id="r1", room_type="shop", stage="waiting_input", payload={}, is_resolved=False, rewards=[]), "choice_id": "accept", "registry": _content_provider()}, "event"),
        (shop_action, {"room_state": RoomState(room_id="r2", room_type="event", stage="waiting_input", payload={}, is_resolved=False, rewards=[]), "action_id": "buy"}, "shop"),
        (rest_action, {"room_state": RoomState(room_id="r3", room_type="reward", stage="waiting_input", payload={}, is_resolved=False, rewards=[]), "action_id": "rest"}, "rest"),
        (claim_reward, {"room_state": RoomState(room_id="r4", room_type="rest", stage="waiting_input", payload={}, is_resolved=False, rewards=[]), "reward_id": "gold"}, "reward"),
    ],
)
def test_room_actions_reject_wrong_room_type(factory, kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        factory(**kwargs)
