from __future__ import annotations

from dataclasses import dataclass, replace

from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState


@dataclass(slots=True, frozen=True)
class ShopActionResult:
    run_state: RunState
    room_state: RoomState


def _next_instance_id(deck: list[str], card_id: str) -> str:
    highest_suffix = 0
    for card_instance_id in deck:
        current_card_id = card_id_from_instance_id(card_instance_id)
        _card_id, suffix = card_instance_id.split("#", 1)
        if current_card_id == card_id or suffix.isdigit():
            highest_suffix = max(highest_suffix, int(suffix))
    return f"{card_id}#{highest_suffix + 1}"


def _offer_by_id(items: object, offer_id: str) -> dict[str, object] | None:
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and item.get("offer_id") == offer_id:
            return item
    return None


def _remove_offer(items: object, offer_id: str) -> list[object]:
    if not isinstance(items, list):
        return []
    return [item for item in items if not (isinstance(item, dict) and item.get("offer_id") == offer_id)]


def _result(run_state: RunState, room_state: RoomState) -> ShopActionResult:
    return ShopActionResult(run_state=run_state, room_state=room_state)


def shop_action(*, run_state: RunState, room_state: RoomState, action_id: str) -> ShopActionResult:
    if room_state.room_type != "shop":
        raise ValueError("shop_action requires a shop room")

    payload = dict(room_state.payload)
    if room_state.stage == "select_remove_card":
        if action_id == "cancel":
            payload.pop("remove_candidates", None)
            return _result(
                run_state,
                RoomState(
                    schema_version=room_state.schema_version,
                    room_id=room_state.room_id,
                    room_type=room_state.room_type,
                    stage="waiting_input",
                    payload=payload,
                    is_resolved=False,
                    rewards=list(room_state.rewards),
                ),
            )
        if not action_id.startswith("remove_card:"):
            return _result(run_state, room_state)
        if payload.get("remove_used") is True:
            return _result(run_state, room_state)
        card_instance_id = action_id.removeprefix("remove_card:")
        candidates = payload.get("remove_candidates")
        if not isinstance(candidates, list) or card_instance_id not in candidates:
            return _result(run_state, room_state)
        remove_price = payload.get("remove_price", 75)
        if not isinstance(remove_price, int) or run_state.gold < remove_price:
            return _result(run_state, room_state)
        payload.pop("remove_candidates", None)
        payload["remove_used"] = True
        updated_run_state = replace(
            run_state,
            gold=run_state.gold - remove_price,
            deck=[card for card in run_state.deck if card != card_instance_id],
            card_removal_count=run_state.card_removal_count + 1,
        )
        return _result(
            updated_run_state,
            RoomState(
                schema_version=room_state.schema_version,
                room_id=room_state.room_id,
                room_type=room_state.room_type,
                stage="waiting_input",
                payload=payload,
                is_resolved=False,
                rewards=list(room_state.rewards),
            ),
        )

    if action_id == "remove":
        payload["remove_candidates"] = list(run_state.deck)
        return _result(
            run_state,
            RoomState(
                schema_version=room_state.schema_version,
                room_id=room_state.room_id,
                room_type=room_state.room_type,
                stage="select_remove_card",
                payload=payload,
                is_resolved=False,
                rewards=list(room_state.rewards),
            ),
        )
    if action_id == "leave":
        return _result(
            run_state,
            RoomState(
                schema_version=room_state.schema_version,
                room_id=room_state.room_id,
                room_type=room_state.room_type,
                stage="completed",
                payload=payload,
                is_resolved=True,
                rewards=list(room_state.rewards),
            ),
        )
    if action_id.startswith("buy_card:"):
        offer_id = action_id.removeprefix("buy_card:")
        offer = _offer_by_id(payload.get("cards"), offer_id)
        if offer is None:
            return _result(run_state, room_state)
        price = offer.get("price")
        card_id = offer.get("card_id")
        if not isinstance(price, int) or not isinstance(card_id, str) or run_state.gold < price:
            return _result(run_state, room_state)
        payload["cards"] = _remove_offer(payload.get("cards"), offer_id)
        updated_run_state = replace(
            run_state,
            gold=run_state.gold - price,
            deck=[*run_state.deck, _next_instance_id(run_state.deck, card_id)],
        )
        return _result(
            updated_run_state,
            RoomState(
                schema_version=room_state.schema_version,
                room_id=room_state.room_id,
                room_type=room_state.room_type,
                stage="waiting_input",
                payload=payload,
                is_resolved=False,
                rewards=list(room_state.rewards),
            ),
        )
    if action_id.startswith("buy_relic:"):
        offer_id = action_id.removeprefix("buy_relic:")
        offer = _offer_by_id(payload.get("relics"), offer_id)
        if offer is None:
            return _result(run_state, room_state)
        price = offer.get("price")
        relic_id = offer.get("relic_id")
        if not isinstance(price, int) or not isinstance(relic_id, str) or run_state.gold < price:
            return _result(run_state, room_state)
        payload["relics"] = _remove_offer(payload.get("relics"), offer_id)
        updated_run_state = replace(
            run_state,
            gold=run_state.gold - price,
            relics=[*run_state.relics, relic_id],
        )
        return _result(
            updated_run_state,
            RoomState(
                schema_version=room_state.schema_version,
                room_id=room_state.room_id,
                room_type=room_state.room_type,
                stage="waiting_input",
                payload=payload,
                is_resolved=False,
                rewards=list(room_state.rewards),
            ),
        )
    if action_id.startswith("buy_potion:"):
        offer_id = action_id.removeprefix("buy_potion:")
        offer = _offer_by_id(payload.get("potions"), offer_id)
        if offer is None:
            return _result(run_state, room_state)
        price = offer.get("price")
        potion_id = offer.get("potion_id")
        if not isinstance(price, int) or not isinstance(potion_id, str) or run_state.gold < price:
            return _result(run_state, room_state)
        payload["potions"] = _remove_offer(payload.get("potions"), offer_id)
        updated_run_state = replace(
            run_state,
            gold=run_state.gold - price,
            potions=[*run_state.potions, potion_id],
        )
        return _result(
            updated_run_state,
            RoomState(
                schema_version=room_state.schema_version,
                room_id=room_state.room_id,
                room_type=room_state.room_type,
                stage="waiting_input",
                payload=payload,
                is_resolved=False,
                rewards=list(room_state.rewards),
            ),
        )
    return _result(run_state, room_state)
