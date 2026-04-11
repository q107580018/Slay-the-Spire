from __future__ import annotations

import json
import shutil
from dataclasses import replace
from pathlib import Path

from slay_the_spire.app.session import MenuState, route_menu_choice, start_session
from slay_the_spire.domain.models.act_state import ActNodeState, ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.use_cases.enter_room import enter_room
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
            "relics": [
                {"offer_id": "relic-1", "relic_id": "burning_blood", "price": 150}
            ],
            "potions": [
                {"offer_id": "potion-1", "potion_id": "fire_potion", "price": 60}
            ],
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


def _single_room_act_state(*, node_id: str, room_type: str) -> ActState:
    return ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(
                node_id="start",
                row=0,
                col=0,
                room_type="combat",
                next_node_ids=[node_id],
            ),
            ActNodeState(
                node_id=node_id,
                row=1,
                col=0,
                room_type=room_type,
                next_node_ids=[],
            ),
        ],
        visited_node_ids=[],
        enemy_pool_id="act1_basic",
        elite_pool_id="act1_elites",
        boss_pool_id="act1_bosses",
        event_pool_id="act1_events",
    )


def test_shop_buy_card_spends_gold_and_adds_deck_instance() -> None:
    result = shop_action(
        run_state=_run_state(),
        room_state=_shop_room(),
        action_id="buy_card:card-1",
        registry=_content_provider(),
    )

    assert result.run_state.gold == 150
    assert result.run_state.deck[-1] == "strike#4"
    assert result.room_state.stage == "waiting_input"
    assert result.room_state.payload["cards"][0]["sold"] is True
    assert result.message is None


def test_shop_buy_potion_spends_gold_and_adds_potion() -> None:
    result = shop_action(
        run_state=_run_state(),
        room_state=_shop_room(),
        action_id="buy_potion:potion-1",
        registry=_content_provider(),
    )

    assert result.run_state.gold == 140
    assert result.run_state.potions == ["fire_potion"]
    assert result.room_state.payload["potions"][0]["sold"] is True
    assert result.message is None


def test_shop_buy_potion_is_blocked_by_sozu() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "sozu"])

    result = shop_action(
        run_state=run_state,
        room_state=_shop_room(),
        action_id="buy_potion:potion-1",
        registry=_content_provider(),
    )

    assert result.run_state.to_dict() == run_state.to_dict()
    assert result.room_state.to_dict() == _shop_room().to_dict()
    assert result.message == "索祖禁止你获得药水。"


def test_membership_card_halves_shop_prices() -> None:
    room_state = enter_room(
        replace(_run_state(), relics=["burning_blood", "membership_card"]),
        _single_room_act_state(node_id="shop-1", room_type="shop"),
        "shop-1",
        _content_provider(),
    )

    assert room_state.payload["cards"]
    assert room_state.payload["relics"]
    assert room_state.payload["potions"]
    assert all(offer["price"] % 5 == 0 for offer in room_state.payload["cards"])
    assert room_state.payload["relics"][0]["price"] == 75
    assert all(offer["price"] == 30 for offer in room_state.payload["potions"])
    assert room_state.payload["remove_price"] == 38


def test_smiling_mask_sets_card_remove_price_to_fifty() -> None:
    run_state = replace(_run_state(gold=200), relics=["burning_blood", "smiling_mask"])
    room_state = _shop_room(remove_price=50)

    entered_remove = shop_action(
        run_state=run_state,
        room_state=room_state,
        action_id="remove",
        registry=_content_provider(),
    )
    result = shop_action(
        run_state=entered_remove.run_state,
        room_state=entered_remove.room_state,
        action_id="remove_card:defend#2",
        registry=_content_provider(),
    )

    assert entered_remove.room_state.payload["remove_price"] == 50
    assert result.run_state.gold == 150


def test_meal_ticket_grants_five_healing_when_entering_shop() -> None:
    run_state = replace(
        _run_state(),
        current_hp=40,
        max_hp=80,
        relics=["burning_blood", "meal_ticket"],
    )

    enter_room(
        run_state,
        _single_room_act_state(node_id="shop-1", room_type="shop"),
        "shop-1",
        _content_provider(),
    )

    assert run_state.current_hp == 55


def test_the_courier_restocks_card_offer_with_different_card() -> None:
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "cards": [
                {"offer_id": "card-1", "card_id": "strike", "price": 40},
                {"offer_id": "card-2", "card_id": "defend", "price": 40},
            ],
            "relics": [],
            "potions": [],
            "remove_price": 60,
        },
        is_resolved=False,
        rewards=[],
    )

    result = shop_action(
        run_state=replace(_run_state(), relics=["burning_blood", "the_courier"]),
        room_state=room_state,
        action_id="buy_card:card-1",
        registry=_content_provider(),
    )

    restocked_offer = result.room_state.payload["cards"][0]

    assert restocked_offer.get("sold") is not True
    assert restocked_offer["card_id"] not in {"strike", "defend"}


def test_the_courier_restocks_relic_offer_with_different_relic() -> None:
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "cards": [],
            "relics": [
                {"offer_id": "relic-1", "relic_id": "anchor", "price": 120},
                {
                    "offer_id": "relic-2",
                    "relic_id": "bag_of_marbles",
                    "price": 120,
                },
            ],
            "potions": [],
            "remove_price": 60,
        },
        is_resolved=False,
        rewards=[],
    )

    result = shop_action(
        run_state=replace(
            _run_state(gold=400),
            relics=["burning_blood", "the_courier"],
            relic_sequences={"shop": ["anchor", "bag_of_marbles", "lantern"]},
            relic_sequence_positions={"shop": 2},
        ),
        room_state=room_state,
        action_id="buy_relic:relic-1",
        registry=_content_provider(),
    )

    restocked_offer = result.room_state.payload["relics"][0]

    assert result.run_state.relics == ["burning_blood", "the_courier", "anchor"]
    assert restocked_offer.get("sold") is not True
    assert restocked_offer["relic_id"] == "lantern"


def test_membership_card_purchase_reprices_current_shop_and_keeps_courier_restock() -> (
    None
):
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "cards": [
                {"offer_id": "card-1", "card_id": "strike", "price": 40},
                {"offer_id": "card-2", "card_id": "defend", "price": 40},
            ],
            "relics": [
                {
                    "offer_id": "relic-1",
                    "relic_id": "membership_card",
                    "price": 120,
                },
                {"offer_id": "relic-2", "relic_id": "anchor", "price": 120},
            ],
            "potions": [
                {"offer_id": "potion-1", "potion_id": "fire_potion", "price": 48},
                {"offer_id": "potion-2", "potion_id": "block_potion", "price": 48},
            ],
            "remove_price": 60,
        },
        is_resolved=False,
        rewards=[],
    )

    result = shop_action(
        run_state=replace(
            _run_state(gold=500),
            relics=["burning_blood", "the_courier"],
            relic_sequences={"shop": ["membership_card", "anchor", "bag_of_marbles"]},
            relic_sequence_positions={"shop": 2},
        ),
        room_state=room_state,
        action_id="buy_relic:relic-1",
        registry=_content_provider(),
    )

    assert result.run_state.gold == 380
    assert result.run_state.relics == [
        "burning_blood",
        "the_courier",
        "membership_card",
    ]
    assert [offer["price"] for offer in result.room_state.payload["cards"]] == [20, 20]
    assert result.room_state.payload["relics"][0]["relic_id"] == "bag_of_marbles"
    assert result.room_state.payload["relics"][0]["price"] == 60
    assert result.room_state.payload["relics"][1]["price"] == 60
    assert [offer["price"] for offer in result.room_state.payload["potions"]] == [
        24,
        24,
    ]
    assert result.room_state.payload["remove_price"] == 30


def test_the_courier_restocks_potion_offer_with_different_potion() -> None:
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "cards": [],
            "relics": [],
            "potions": [
                {"offer_id": "potion-1", "potion_id": "fire_potion", "price": 40},
                {"offer_id": "potion-2", "potion_id": "block_potion", "price": 40},
            ],
            "remove_price": 60,
        },
        is_resolved=False,
        rewards=[],
    )

    result = shop_action(
        run_state=replace(_run_state(), relics=["burning_blood", "the_courier"]),
        room_state=room_state,
        action_id="buy_potion:potion-1",
        registry=_content_provider(),
    )

    restocked_offer = result.room_state.payload["potions"][0]

    assert restocked_offer.get("sold") is not True
    assert restocked_offer["potion_id"] not in {"fire_potion", "block_potion"}


def test_maw_bank_adds_twelve_gold_when_entering_non_shop_room() -> None:
    run_state = replace(_run_state(gold=100), relics=["burning_blood", "maw_bank"])

    enter_room(
        run_state,
        _single_room_act_state(node_id="rest-1", room_type="rest"),
        "rest-1",
        _content_provider(),
    )

    assert run_state.gold == 112


def test_maw_bank_stops_adding_gold_after_entering_shop() -> None:
    run_state = replace(_run_state(gold=100), relics=["burning_blood", "maw_bank"])

    enter_room(
        run_state,
        _single_room_act_state(node_id="shop-1", room_type="shop"),
        "shop-1",
        _content_provider(),
    )
    enter_room(
        run_state,
        _single_room_act_state(node_id="rest-1", room_type="rest"),
        "rest-1",
        _content_provider(),
    )

    assert run_state.gold == 100


def test_dream_catcher_rest_adds_three_card_reward_choices() -> None:
    result = rest_action(
        run_state=replace(_run_state(), relics=["burning_blood", "dream_catcher"]),
        room_state=_rest_room(),
        action_id="rest",
        registry=_content_provider(),
    )

    card_rewards = [
        reward
        for reward in result.room_state.rewards
        if reward.startswith("card_offer:")
    ]

    assert len(card_rewards) == 3
    assert len(set(card_rewards)) == 3


def test_peace_pipe_enters_select_remove_card_stage() -> None:
    result = rest_action(
        run_state=replace(_run_state(), relics=["burning_blood", "peace_pipe"]),
        room_state=replace(
            _rest_room(), payload={"actions": ["rest", "smith", "digestion"]}
        ),
        action_id="digestion",
        registry=_content_provider(),
    )

    assert result.run_state.deck == ["strike#1", "defend#2", "bash#3"]
    assert result.room_state.stage == "select_remove_card"
    assert result.room_state.is_resolved is False
    assert result.room_state.payload["remove_candidates"] == [
        "strike#1",
        "defend#2",
        "bash#3",
    ]


def test_girya_lift_requires_girya_relic() -> None:
    run_state = _run_state()
    room_state = replace(_rest_room(), payload={"actions": ["rest", "smith", "lift"]})

    result = rest_action(
        run_state=run_state,
        room_state=room_state,
        action_id="lift",
        registry=_content_provider(),
    )

    assert result.run_state.to_dict() == run_state.to_dict()
    assert result.room_state.to_dict() == room_state.to_dict()
    assert result.message is None


def test_peace_pipe_digestion_requires_peace_pipe_relic() -> None:
    run_state = _run_state()
    room_state = replace(
        _rest_room(), payload={"actions": ["rest", "smith", "digestion"]}
    )

    result = rest_action(
        run_state=run_state,
        room_state=room_state,
        action_id="digestion",
        registry=_content_provider(),
    )

    assert result.run_state.to_dict() == run_state.to_dict()
    assert result.room_state.to_dict() == room_state.to_dict()
    assert result.message is None


def test_shovel_dig_requires_shovel_relic() -> None:
    run_state = _run_state()
    room_state = replace(_rest_room(), payload={"actions": ["rest", "smith", "dig"]})

    result = rest_action(
        run_state=run_state,
        room_state=room_state,
        action_id="dig",
        registry=_content_provider(),
    )

    assert result.run_state.to_dict() == run_state.to_dict()
    assert result.room_state.to_dict() == room_state.to_dict()
    assert result.message is None


def test_rest_action_rejects_relic_action_missing_from_room_whitelist() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "shovel"])
    room_state = _rest_room()

    result = rest_action(
        run_state=run_state,
        room_state=room_state,
        action_id="dig",
        registry=_content_provider(),
    )

    assert result.run_state.to_dict() == run_state.to_dict()
    assert result.room_state.to_dict() == room_state.to_dict()
    assert result.message is None


def test_peace_pipe_remove_card_removes_selected_card() -> None:
    entered_remove = rest_action(
        run_state=replace(_run_state(), relics=["burning_blood", "peace_pipe"]),
        room_state=replace(
            _rest_room(), payload={"actions": ["rest", "smith", "digestion"]}
        ),
        action_id="digestion",
        registry=_content_provider(),
    )

    result = rest_action(
        run_state=entered_remove.run_state,
        room_state=entered_remove.room_state,
        action_id="remove_card:defend#2",
        registry=_content_provider(),
    )

    assert result.run_state.deck == ["strike#1", "bash#3"]
    assert result.run_state.card_removal_count == 1
    assert result.room_state.stage == "completed"
    assert result.room_state.is_resolved is True


def test_shovel_dig_adds_generated_relic_reward() -> None:
    result = rest_action(
        run_state=replace(
            _run_state(),
            relics=["burning_blood", "shovel"],
            relic_sequences={
                "common": ["anchor"],
                "uncommon": ["oddly_smooth_stone"],
                "rare": ["bird_faced_urn"],
            },
            relic_sequence_positions={"common": 0, "uncommon": 0, "rare": 0},
        ),
        room_state=replace(_rest_room(), payload={"actions": ["rest", "smith", "dig"]}),
        action_id="dig",
        registry=_content_provider(),
    )

    assert result.room_state.rewards == ["relic:anchor"]


def test_girya_lift_persists_across_rest_sites_and_applies_strength_in_combat() -> None:
    lifted_run_state = replace(
        _run_state(),
        relics=["burning_blood", "girya"],
        relic_sequence_positions={"girya_lifts": 2},
    )

    lift_result = rest_action(
        run_state=lifted_run_state,
        room_state=replace(
            _rest_room(), payload={"actions": ["rest", "smith", "lift"]}
        ),
        action_id="lift",
        registry=_content_provider(),
    )

    assert lift_result.run_state.relic_sequence_positions["girya_lifts"] == 3

    combat_room = enter_room(
        lift_result.run_state,
        _single_room_act_state(node_id="combat-1", room_type="combat"),
        "combat-1",
        _content_provider(),
    )

    combat_state = CombatState.from_dict(combat_room.payload["combat_state"])

    assert StatusState(status_id="strength", stacks=3) in combat_state.player.statuses


def test_vajra_applies_strength_in_combat() -> None:
    combat_room = enter_room(
        replace(
            _run_state(),
            relics=["burning_blood", "vajra"],
            relic_sequence_positions={"relic:vajra:strength_bonus": 1},
        ),
        _single_room_act_state(node_id="combat-1", room_type="combat"),
        "combat-1",
        _content_provider(),
    )

    combat_state = CombatState.from_dict(combat_room.payload["combat_state"])

    assert StatusState(status_id="strength", stacks=1) in combat_state.player.statuses


def test_oddly_smooth_stone_applies_dexterity_in_combat() -> None:
    combat_room = enter_room(
        replace(
            _run_state(),
            relics=["burning_blood", "oddly_smooth_stone"],
            relic_sequence_positions={"relic:oddly_smooth_stone:dexterity_bonus": 1},
        ),
        _single_room_act_state(node_id="combat-1", room_type="combat"),
        "combat-1",
        _content_provider(),
    )

    combat_state = CombatState.from_dict(combat_room.payload["combat_state"])

    assert StatusState(status_id="dexterity", stacks=1) in combat_state.player.statuses


def test_eternal_feather_adds_three_healing_per_five_cards() -> None:
    run_state = replace(
        _run_state(),
        current_hp=30,
        max_hp=80,
        deck=[f"strike#{index}" for index in range(1, 11)],
        relics=["burning_blood", "eternal_feather"],
    )

    result = rest_action(
        run_state=run_state,
        room_state=_rest_room(),
        action_id="rest",
        registry=_content_provider(),
    )

    assert result.run_state.current_hp == 60


def test_girya_adds_lift_action_to_rest_site() -> None:
    room_state = enter_room(
        replace(_run_state(), relics=["burning_blood", "girya"]),
        _single_room_act_state(node_id="rest-1", room_type="rest"),
        "rest-1",
        _content_provider(),
    )

    assert "lift" in room_state.payload["actions"]


def test_dream_catcher_does_not_add_separate_rest_action() -> None:
    room_state = enter_room(
        replace(_run_state(), relics=["burning_blood", "dream_catcher"]),
        _single_room_act_state(node_id="rest-1", room_type="rest"),
        "rest-1",
        _content_provider(),
    )

    assert room_state.payload["actions"] == ["rest", "smith"]


def test_peace_pipe_adds_remove_action_to_rest_site() -> None:
    room_state = enter_room(
        replace(_run_state(), relics=["burning_blood", "peace_pipe"]),
        _single_room_act_state(node_id="rest-1", room_type="rest"),
        "rest-1",
        _content_provider(),
    )

    assert "digestion" in room_state.payload["actions"]


def test_shovel_adds_dig_action_to_rest_site() -> None:
    room_state = enter_room(
        replace(_run_state(), relics=["burning_blood", "shovel"]),
        _single_room_act_state(node_id="rest-1", room_type="rest"),
        "rest-1",
        _content_provider(),
    )

    assert "dig" in room_state.payload["actions"]


def test_shop_buy_relic_routes_through_apply_reward_replacement_rules() -> None:
    run_state = replace(_run_state(gold=300), relics=["burning_blood"])
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "cards": [],
            "relics": [
                {"offer_id": "relic-1", "relic_id": "black_blood", "price": 150}
            ],
            "potions": [],
            "remove_price": 75,
        },
        is_resolved=False,
        rewards=[],
    )

    result = shop_action(
        run_state=run_state,
        room_state=room_state,
        action_id="buy_relic:relic-1",
        registry=_content_provider(),
    )

    assert result.run_state.gold == 150
    assert result.run_state.relics == ["black_blood"]


def test_shop_buy_relic_uses_provided_registry_for_reward_application(
    tmp_path: Path,
) -> None:
    content_root = Path(__file__).resolve().parents[2] / "content"
    copied_root = tmp_path / "content"
    shutil.copytree(content_root, copied_root)

    boss_relics_path = copied_root / "relics" / "boss_relics.json"
    payload = json.loads(boss_relics_path.read_text(encoding="utf-8"))
    for relic in payload["relics"]:
        if relic["id"] == "black_blood":
            relic["replaces_relic_id"] = "golden_idol"
            break
    boss_relics_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    provider = StarterContentProvider(copied_root)
    run_state = replace(_run_state(gold=300), relics=["golden_idol"])
    room_state = RoomState(
        room_id="act1:shop",
        room_type="shop",
        stage="waiting_input",
        payload={
            "cards": [],
            "relics": [
                {"offer_id": "relic-1", "relic_id": "black_blood", "price": 150}
            ],
            "potions": [],
            "remove_price": 75,
        },
        is_resolved=False,
        rewards=[],
    )

    result = shop_action(
        run_state=run_state,
        room_state=room_state,
        action_id="buy_relic:relic-1",
        registry=provider,
    )

    assert result.run_state.gold == 150
    assert result.run_state.relics == ["black_blood"]


def test_shop_buy_card_with_insufficient_gold_returns_prompt() -> None:
    result = shop_action(
        run_state=_run_state(gold=40),
        room_state=_shop_room(),
        action_id="buy_card:card-1",
        registry=_content_provider(),
    )

    assert result.run_state.to_dict() == _run_state(gold=40).to_dict()
    assert result.room_state.to_dict() == _shop_room().to_dict()
    assert result.message == "金币不足，无法购买该商品。"


def test_shop_buying_sold_item_returns_prompt() -> None:
    first_result = shop_action(
        run_state=_run_state(),
        room_state=_shop_room(),
        action_id="buy_card:card-1",
        registry=_content_provider(),
    )

    result = shop_action(
        run_state=first_result.run_state,
        room_state=first_result.room_state,
        action_id="buy_card:card-1",
        registry=_content_provider(),
    )

    assert result.run_state.to_dict() == first_result.run_state.to_dict()
    assert result.room_state.to_dict() == first_result.room_state.to_dict()
    assert result.message == "该商品已购买。"


def test_shop_remove_card_uses_run_level_price_progression() -> None:
    entered_remove = shop_action(
        run_state=_run_state(gold=300, card_removal_count=2),
        room_state=_shop_room(remove_price=125),
        action_id="remove",
        registry=_content_provider(),
    )

    result = shop_action(
        run_state=entered_remove.run_state,
        room_state=entered_remove.room_state,
        action_id="remove_card:defend#2",
        registry=_content_provider(),
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
        registry=_content_provider(),
    )
    resolved_remove = shop_action(
        run_state=used_remove.run_state,
        room_state=used_remove.room_state,
        action_id="remove_card:defend#2",
        registry=_content_provider(),
    )

    result = shop_action(
        run_state=resolved_remove.run_state,
        room_state=resolved_remove.room_state,
        action_id="remove",
        registry=_content_provider(),
    )

    assert result.run_state.to_dict() == resolved_remove.run_state.to_dict()
    assert result.room_state.to_dict() == resolved_remove.room_state.to_dict()
    assert result.message == "本次商店的删牌服务已使用。"


def test_shop_cancel_remove_returns_to_root_without_spending_remove_use() -> None:
    entered_remove = shop_action(
        run_state=_run_state(),
        room_state=_shop_room(),
        action_id="remove",
        registry=_content_provider(),
    )

    result = shop_action(
        run_state=entered_remove.run_state,
        room_state=entered_remove.room_state,
        action_id="cancel",
        registry=_content_provider(),
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

    result = rest_action(
        run_state=run_state,
        room_state=_rest_room(),
        action_id="rest",
        registry=_content_provider(),
    )

    assert result.run_state.current_hp == 80
    assert result.room_state.stage == "completed"
    assert result.room_state.is_resolved is True


def test_rest_is_blocked_by_coffee_dripper() -> None:
    run_state = replace(
        _run_state(), current_hp=50, relics=["burning_blood", "coffee_dripper"]
    )

    result = rest_action(
        run_state=run_state,
        room_state=_rest_room(),
        action_id="rest",
        registry=_content_provider(),
    )

    assert result.run_state.current_hp == 50
    assert result.room_state.stage == "waiting_input"
    assert result.room_state.is_resolved is False
    assert result.message == "该动作被遗物效果禁用。"


def test_regal_pillow_adds_extra_rest_healing() -> None:
    run_state = replace(
        _run_state(),
        current_hp=30,
        max_hp=80,
        relics=["burning_blood", "regal_pillow"],
    )

    result = rest_action(
        run_state=run_state,
        room_state=_rest_room(),
        action_id="rest",
        registry=_content_provider(),
    )

    assert result.run_state.current_hp == 69


def test_rest_smith_transitions_to_select_upgrade_card() -> None:
    result = rest_action(
        run_state=_run_state(),
        room_state=_rest_room(),
        action_id="smith",
        registry=_content_provider(),
    )

    assert result.room_state.stage == "select_upgrade_card"
    assert result.room_state.payload["upgrade_options"] == [
        "strike#1",
        "defend#2",
        "bash#3",
    ]


def test_rest_is_blocked_by_fusion_hammer() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "fusion_hammer"])

    result = rest_action(
        run_state=run_state,
        room_state=_rest_room(),
        action_id="smith",
        registry=_content_provider(),
    )

    assert result.room_state.stage == "waiting_input"
    assert "upgrade_options" not in result.room_state.payload
    assert result.room_state.is_resolved is False
    assert result.message == "该动作被遗物效果禁用。"


def test_rest_leave_marks_room_completed() -> None:
    result = rest_action(
        run_state=_run_state(),
        room_state=_rest_room(),
        action_id="leave",
        registry=_content_provider(),
    )

    assert result.room_state.stage == "completed"
    assert result.room_state.is_resolved is True
    assert result.message is None


def test_rest_menu_route_surfaces_disabled_action_message() -> None:
    session = replace(
        start_session(seed=5),
        run_state=replace(
            start_session(seed=5).run_state, relics=["burning_blood", "coffee_dripper"]
        ),
        room_state=replace(
            _rest_room(), room_id="act1:rest", payload={"actions": ["rest", "smith"]}
        ),
        menu_state=MenuState(mode="rest_root"),
    )

    _running, next_session, message = route_menu_choice("1", session=session)

    assert message.startswith("该动作被遗物效果禁用。")
    assert next_session.room_state.stage == "waiting_input"


def test_rest_menu_route_can_leave_when_both_actions_disabled() -> None:
    session = replace(
        start_session(seed=5),
        run_state=replace(
            start_session(seed=5).run_state,
            relics=["burning_blood", "coffee_dripper", "fusion_hammer"],
        ),
        room_state=replace(
            _rest_room(),
            room_id="act1:rest",
            payload={
                "actions": ["rest", "smith"],
                "node_id": "r15c0",
                "next_node_ids": ["boss"],
            },
        ),
        menu_state=MenuState(mode="rest_root"),
    )

    _running, next_session, message = route_menu_choice("3", session=session)

    assert next_session.room_state.is_resolved is True
    assert next_session.menu_state.mode == "root"
    assert "前往下一个房间" in message


def test_rest_menu_route_enters_remove_card_subflow_for_peace_pipe() -> None:
    session = replace(
        start_session(seed=5),
        run_state=replace(
            start_session(seed=5).run_state, relics=["burning_blood", "peace_pipe"]
        ),
        room_state=replace(
            _rest_room(),
            room_id="act1:rest",
            payload={"actions": ["rest", "smith", "digestion"]},
        ),
        menu_state=MenuState(mode="rest_root"),
    )

    _running, next_session, message = route_menu_choice("3", session=session)

    assert next_session.room_state.stage == "select_remove_card"
    assert next_session.menu_state.mode == "rest_remove_card"
    assert "选择要移除的卡牌" in message


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


def test_rest_upgrade_selection_uses_apply_reward_path_for_non_upgradable_cards() -> (
    None
):
    entered_smith = rest_action(
        run_state=replace(_run_state(), deck=["doubt#1", "bash#3"]),
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

    assert result.run_state.deck == ["doubt#1", "bash_plus#3"]
