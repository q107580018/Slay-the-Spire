from __future__ import annotations

from pathlib import Path

from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.use_cases.rest_action import rest_action
from slay_the_spire.use_cases.shop_action import shop_action


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def _run_state(*, gold: int = 200, card_removal_count: int = 0) -> RunState:
    return RunState(
        seed=7,
        character_id="ironclad",
        current_act_id="act1",
        current_hp=80,
        max_hp=80,
        gold=gold,
        deck=["strike#1", "defend#2", "bash#3"],
        relics=["burning_blood"],
        potions=[],
        card_removal_count=card_removal_count,
    )


def _shop_room(*, remove_price: int = 75) -> RoomState:
    return RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "cards": [{"offer_id": "card-1", "card_id": "strike", "price": 50}],
            "relics": [{"offer_id": "relic-1", "relic_id": "burning_blood", "price": 150}],
            "potions": [{"offer_id": "potion-1", "potion_id": "fire_potion", "price": 60}],
            "remove_price": remove_price,
        },
        is_resolved=False,
        rewards=[],
    )


def _rest_room() -> RoomState:
    return RoomState(
        room_id="act1:rest",
        room_type="rest",
        stage="waiting_input",
        payload={"actions": ["rest", "smith"]},
        is_resolved=False,
        rewards=[],
    )


def test_shop_buy_card_spends_gold_and_adds_deck_instance() -> None:
    result = shop_action(run_state=_run_state(), room_state=_shop_room(), action_id="buy_card:card-1")

    assert result.run_state.gold == 150
    assert result.run_state.deck[-1] == "strike#4"
    assert result.room_state.stage == "waiting_input"
    assert result.room_state.payload["cards"][0]["sold"] is True
    assert result.message is None


def test_shop_buy_potion_spends_gold_and_adds_potion() -> None:
    result = shop_action(run_state=_run_state(), room_state=_shop_room(), action_id="buy_potion:potion-1")

    assert result.run_state.gold == 140
    assert result.run_state.potions == ["fire_potion"]
    assert result.room_state.payload["potions"][0]["sold"] is True
    assert result.message is None


def test_shop_buy_card_with_insufficient_gold_returns_prompt() -> None:
    result = shop_action(run_state=_run_state(gold=40), room_state=_shop_room(), action_id="buy_card:card-1")

    assert result.run_state.to_dict() == _run_state(gold=40).to_dict()
    assert result.room_state.to_dict() == _shop_room().to_dict()
    assert result.message == "金币不足，无法购买该商品。"


def test_shop_buying_sold_item_returns_prompt() -> None:
    first_result = shop_action(run_state=_run_state(), room_state=_shop_room(), action_id="buy_card:card-1")

    result = shop_action(
        run_state=first_result.run_state,
        room_state=first_result.room_state,
        action_id="buy_card:card-1",
    )

    assert result.run_state.to_dict() == first_result.run_state.to_dict()
    assert result.room_state.to_dict() == first_result.room_state.to_dict()
    assert result.message == "该商品已购买。"


def test_shop_remove_card_uses_run_level_price_progression() -> None:
    entered_remove = shop_action(
        run_state=_run_state(gold=300, card_removal_count=2),
        room_state=_shop_room(remove_price=125),
        action_id="remove",
    )

    result = shop_action(
        run_state=entered_remove.run_state,
        room_state=entered_remove.room_state,
        action_id="remove_card:defend#2",
    )

    assert result.run_state.gold == 175
    assert result.run_state.deck == ["strike#1", "bash#3"]
    assert result.run_state.card_removal_count == 3
    assert result.room_state.stage == "waiting_input"
    assert result.room_state.payload["remove_used"] is True
    assert result.message is None


def test_shop_remove_service_after_use_returns_prompt() -> None:
    used_remove = shop_action(
        run_state=_run_state(gold=300, card_removal_count=2),
        room_state=_shop_room(remove_price=125),
        action_id="remove",
    )
    resolved_remove = shop_action(
        run_state=used_remove.run_state,
        room_state=used_remove.room_state,
        action_id="remove_card:defend#2",
    )

    result = shop_action(
        run_state=resolved_remove.run_state,
        room_state=resolved_remove.room_state,
        action_id="remove",
    )

    assert result.run_state.to_dict() == resolved_remove.run_state.to_dict()
    assert result.room_state.to_dict() == resolved_remove.room_state.to_dict()
    assert result.message == "本次商店的删牌服务已使用。"


def test_shop_cancel_remove_returns_to_root_without_spending_remove_use() -> None:
    entered_remove = shop_action(
        run_state=_run_state(),
        room_state=_shop_room(),
        action_id="remove",
    )

    result = shop_action(
        run_state=entered_remove.run_state,
        room_state=entered_remove.room_state,
        action_id="cancel",
    )

    assert result.run_state.to_dict() == _run_state().to_dict()
    assert result.room_state.stage == "waiting_input"
    assert "remove_candidates" not in result.room_state.payload
    assert result.room_state.payload.get("remove_used") is not True


def test_rest_heal_restores_thirty_percent_of_max_hp_and_caps() -> None:
    run_state = RunState(
        seed=7,
        character_id="ironclad",
        current_act_id="act1",
        current_hp=70,
        max_hp=80,
        gold=99,
        deck=["strike#1", "defend#2", "bash#3"],
        relics=["burning_blood"],
        potions=[],
        card_removal_count=0,
    )

    result = rest_action(run_state=run_state, room_state=_rest_room(), action_id="rest", registry=_content_provider())

    assert result.run_state.current_hp == 80
    assert result.room_state.stage == "completed"
    assert result.room_state.is_resolved is True


def test_rest_smith_transitions_to_select_upgrade_card() -> None:
    result = rest_action(
        run_state=_run_state(),
        room_state=_rest_room(),
        action_id="smith",
        registry=_content_provider(),
    )

    assert result.room_state.stage == "select_upgrade_card"
    assert result.room_state.payload["upgrade_options"] == ["bash#3"]


def test_rest_select_upgrade_card_rewrites_card_instance_to_upgraded_card() -> None:
    entered_smith = rest_action(
        run_state=_run_state(),
        room_state=_rest_room(),
        action_id="smith",
        registry=_content_provider(),
    )

    result = rest_action(
        run_state=entered_smith.run_state,
        room_state=entered_smith.room_state,
        action_id="upgrade_card:bash#3",
        registry=_content_provider(),
    )

    assert result.run_state.deck == ["strike#1", "defend#2", "bash_plus#3"]
    assert result.room_state.stage == "completed"
    assert result.room_state.is_resolved is True
