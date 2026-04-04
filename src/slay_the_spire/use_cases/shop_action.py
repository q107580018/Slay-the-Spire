from __future__ import annotations

from dataclasses import dataclass, replace

from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.use_cases.enter_room import (
    _scaled_shop_price,
    _shop_card_base_price,
    _shop_remove_price,
)
from slay_the_spire.use_cases.apply_reward import apply_reward


@dataclass(slots=True, frozen=True)
class ShopActionResult:
    run_state: RunState
    room_state: RoomState
    message: str | None = None


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


def _mark_offer_sold(items: object, offer_id: str) -> list[object]:
    if not isinstance(items, list):
        return []
    updated: list[object] = []
    for item in items:
        if isinstance(item, dict) and item.get("offer_id") == offer_id:
            sold_item = dict(item)
            sold_item["sold"] = True
            updated.append(sold_item)
            continue
        updated.append(item)
    return updated


def _refresh_unsold_offer(items: object, offer_id: str) -> list[object]:
    if not isinstance(items, list):
        return []
    updated: list[object] = []
    for item in items:
        if isinstance(item, dict) and item.get("offer_id") == offer_id:
            refreshed_item = dict(item)
            refreshed_item.pop("sold", None)
            updated.append(refreshed_item)
            continue
        updated.append(item)
    return updated


def _repriced_cards(
    items: object, *, run_state: RunState, preserve_offer_id: str | None = None
) -> list[object]:
    if not isinstance(items, list):
        return []
    updated: list[object] = []
    for item in items:
        if not isinstance(item, dict):
            updated.append(item)
            continue
        next_item = dict(item)
        if (
            next_item.get("sold") is not True
            or next_item.get("offer_id") == preserve_offer_id
        ):
            card_id = next_item.get("card_id")
            if isinstance(card_id, str):
                next_item["price"] = _scaled_shop_price(
                    _shop_card_base_price(card_id), run_state=run_state
                )
        updated.append(next_item)
    return updated


def _repriced_relics(
    items: object, *, run_state: RunState, preserve_offer_id: str | None = None
) -> list[object]:
    if not isinstance(items, list):
        return []
    updated: list[object] = []
    for item in items:
        if not isinstance(item, dict):
            updated.append(item)
            continue
        next_item = dict(item)
        if (
            next_item.get("sold") is not True
            or next_item.get("offer_id") == preserve_offer_id
        ):
            next_item["price"] = _scaled_shop_price(150, run_state=run_state)
        updated.append(next_item)
    return updated


def _repriced_potions(
    items: object, *, run_state: RunState, preserve_offer_id: str | None = None
) -> list[object]:
    if not isinstance(items, list):
        return []
    updated: list[object] = []
    for item in items:
        if not isinstance(item, dict):
            updated.append(item)
            continue
        next_item = dict(item)
        if (
            next_item.get("sold") is not True
            or next_item.get("offer_id") == preserve_offer_id
        ):
            next_item["price"] = _scaled_shop_price(60, run_state=run_state)
        updated.append(next_item)
    return updated


def _reprice_shop_payload(
    payload: dict[str, object],
    *,
    run_state: RunState,
    preserve_offer_id: str | None = None,
) -> dict[str, object]:
    payload["cards"] = _repriced_cards(
        payload.get("cards"), run_state=run_state, preserve_offer_id=preserve_offer_id
    )
    payload["relics"] = _repriced_relics(
        payload.get("relics"), run_state=run_state, preserve_offer_id=preserve_offer_id
    )
    payload["potions"] = _repriced_potions(
        payload.get("potions"), run_state=run_state, preserve_offer_id=preserve_offer_id
    )
    payload["remove_price"] = _shop_remove_price(run_state)
    return payload


def _replace_offer(
    items: object, offer_id: str, replacement: dict[str, object]
) -> list[object]:
    if not isinstance(items, list):
        return []
    updated: list[object] = []
    for item in items:
        if isinstance(item, dict) and item.get("offer_id") == offer_id:
            next_item = dict(replacement)
            next_item["offer_id"] = offer_id
            updated.append(next_item)
            continue
        updated.append(item)
    return updated


def _other_offer_values(items: object, *, offer_id: str, field_name: str) -> set[str]:
    if not isinstance(items, list):
        return set()
    values: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or item.get("offer_id") == offer_id:
            continue
        value = item.get(field_name)
        if isinstance(value, str) and value:
            values.add(value)
    return values


def _restock_card_offer(
    payload: dict[str, object], *, offer_id: str, registry
) -> dict[str, object] | None:
    excluded_ids = _other_offer_values(
        payload.get("cards"), offer_id=offer_id, field_name="card_id"
    )
    sold_offer = _offer_by_id(payload.get("cards"), offer_id)
    if sold_offer is not None and isinstance(sold_offer.get("card_id"), str):
        excluded_ids.add(sold_offer["card_id"])
    for card_def in registry.cards().all():
        if "shop" not in card_def.acquisition_tags or card_def.id in excluded_ids:
            continue
        return {
            "card_id": card_def.id,
            "price": sold_offer.get("price") if sold_offer else 60,
        }
    return None


def _next_relic_from_sequence(
    run_state: RunState, *, pool_id: str, excluded_ids: set[str]
) -> str | None:
    sequence = run_state.relic_sequences.get(pool_id, [])
    position = run_state.relic_sequence_positions.get(pool_id, 0)
    while position < len(sequence):
        relic_id = sequence[position]
        position += 1
        run_state.relic_sequence_positions[pool_id] = position
        if relic_id not in run_state.relics and relic_id not in excluded_ids:
            return relic_id
    run_state.relic_sequence_positions[pool_id] = position
    return None


def _restock_relic_offer(
    run_state: RunState, payload: dict[str, object], *, offer_id: str
) -> dict[str, object] | None:
    excluded_ids = set(run_state.relics)
    excluded_ids.update(
        _other_offer_values(
            payload.get("relics"), offer_id=offer_id, field_name="relic_id"
        )
    )
    sold_offer = _offer_by_id(payload.get("relics"), offer_id)
    if sold_offer is not None and isinstance(sold_offer.get("relic_id"), str):
        excluded_ids.add(sold_offer["relic_id"])
    relic_id = _next_relic_from_sequence(
        run_state, pool_id="shop", excluded_ids=excluded_ids
    )
    if relic_id is None:
        return None
    return {
        "relic_id": relic_id,
        "price": sold_offer.get("price") if sold_offer else 150,
    }


def _restock_potion_offer(
    payload: dict[str, object], *, offer_id: str, registry
) -> dict[str, object] | None:
    excluded_ids = _other_offer_values(
        payload.get("potions"), offer_id=offer_id, field_name="potion_id"
    )
    sold_offer = _offer_by_id(payload.get("potions"), offer_id)
    if sold_offer is not None and isinstance(sold_offer.get("potion_id"), str):
        excluded_ids.add(sold_offer["potion_id"])
    for potion_def in registry.potions().all():
        if potion_def.id in excluded_ids:
            continue
        return {
            "potion_id": potion_def.id,
            "price": sold_offer.get("price") if sold_offer else 60,
        }
    return None


def _result(
    run_state: RunState, room_state: RoomState, message: str | None = None
) -> ShopActionResult:
    return ShopActionResult(run_state=run_state, room_state=room_state, message=message)


def shop_action(
    *, run_state: RunState, room_state: RoomState, action_id: str, registry
) -> ShopActionResult:
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
            return _result(run_state, room_state, "本次商店的删牌服务已使用。")
        card_instance_id = action_id.removeprefix("remove_card:")
        candidates = payload.get("remove_candidates")
        if not isinstance(candidates, list) or card_instance_id not in candidates:
            return _result(run_state, room_state)
        remove_price = payload.get("remove_price", 75)
        if not isinstance(remove_price, int) or run_state.gold < remove_price:
            return _result(run_state, room_state, "金币不足，无法使用删牌服务。")
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
        remove_price = payload.get("remove_price", 75)
        if payload.get("remove_used") is True:
            return _result(run_state, room_state, "本次商店的删牌服务已使用。")
        if not isinstance(remove_price, int) or run_state.gold < remove_price:
            return _result(run_state, room_state, "金币不足，无法使用删牌服务。")
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
        if offer.get("sold") is True:
            return _result(run_state, room_state, "该商品已购买。")
        price = offer.get("price")
        card_id = offer.get("card_id")
        if (
            not isinstance(price, int)
            or not isinstance(card_id, str)
            or run_state.gold < price
        ):
            return _result(run_state, room_state, "金币不足，无法购买该商品。")
        payload["cards"] = _mark_offer_sold(payload.get("cards"), offer_id)
        if "the_courier" in run_state.relics:
            replacement = _restock_card_offer(
                payload, offer_id=offer_id, registry=registry
            )
            if replacement is not None:
                payload["cards"] = _replace_offer(
                    payload.get("cards"), offer_id, replacement
                )
        updated_run_state = replace(
            run_state,
            gold=run_state.gold - price,
            deck=[*run_state.deck, _next_instance_id(run_state.deck, card_id)],
        )
        payload = _reprice_shop_payload(payload, run_state=updated_run_state)
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
        if offer.get("sold") is True:
            return _result(run_state, room_state, "该商品已购买。")
        price = offer.get("price")
        relic_id = offer.get("relic_id")
        if (
            not isinstance(price, int)
            or not isinstance(relic_id, str)
            or run_state.gold < price
        ):
            return _result(run_state, room_state, "金币不足，无法购买该商品。")
        payload["relics"] = _mark_offer_sold(payload.get("relics"), offer_id)
        updated_run_state = apply_reward(
            run_state=replace(run_state, gold=run_state.gold - price),
            reward_id=f"relic:{relic_id}",
            registry=registry,
        )
        if "the_courier" in run_state.relics:
            replacement = _restock_relic_offer(
                updated_run_state, payload, offer_id=offer_id
            )
            if replacement is not None:
                payload["relics"] = _replace_offer(
                    payload.get("relics"), offer_id, replacement
                )
        payload = _reprice_shop_payload(
            payload, run_state=updated_run_state, preserve_offer_id=offer_id
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
        if offer.get("sold") is True:
            return _result(run_state, room_state, "该商品已购买。")
        if "sozu" in run_state.relics:
            return _result(run_state, room_state, "索祖禁止你获得药水。")
        price = offer.get("price")
        potion_id = offer.get("potion_id")
        if (
            not isinstance(price, int)
            or not isinstance(potion_id, str)
            or run_state.gold < price
        ):
            return _result(run_state, room_state, "金币不足，无法购买该商品。")
        payload["potions"] = _mark_offer_sold(payload.get("potions"), offer_id)
        if "the_courier" in run_state.relics:
            replacement = _restock_potion_offer(
                payload, offer_id=offer_id, registry=registry
            )
            if replacement is not None:
                payload["potions"] = _replace_offer(
                    payload.get("potions"), offer_id, replacement
                )
        updated_run_state = replace(
            run_state,
            gold=run_state.gold - price,
            potions=[*run_state.potions, potion_id],
        )
        payload = _reprice_shop_payload(payload, run_state=updated_run_state)
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
