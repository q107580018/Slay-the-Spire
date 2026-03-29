from __future__ import annotations

from dataclasses import replace
from random import Random

from slay_the_spire.app.opening_state import NeowOffer, OpeningState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.shared.rng import rng_for_room
from slay_the_spire.use_cases.apply_reward import apply_reward
from slay_the_spire.use_cases.start_run import start_new_run


def build_opening_state(*, seed: int, preferred_character_id: str | None, registry) -> OpeningState:
    character_ids = [character.id for character in registry.characters().all()]
    run_blueprint = None
    offers: list[NeowOffer] = []
    selected_character_id = preferred_character_id
    if selected_character_id is not None:
        run_blueprint = start_new_run(selected_character_id, seed=seed, registry=registry)
        offers = _generate_neow_offers(seed=seed, run_blueprint=run_blueprint, registry=registry)
    return OpeningState(
        seed=seed,
        available_character_ids=character_ids,
        selected_character_id=selected_character_id,
        run_blueprint=run_blueprint,
        neow_offers=offers,
    )


def apply_neow_offer(
    opening_state: OpeningState,
    offer_id: str,
    *,
    registry,
    target_card_instance_id: str | None = None,
) -> OpeningState:
    offer = next(item for item in opening_state.neow_offers if item.offer_id == offer_id)
    if offer.offer_id in opening_state.resolved_neow_offer_ids:
        raise ValueError("neow offer has already been resolved")
    if offer.requires_target is not None and target_card_instance_id is None:
        return replace(opening_state, pending_neow_offer_id=offer.offer_id)
    if opening_state.run_blueprint is None:
        return replace(opening_state, pending_neow_offer_id=offer.offer_id)
    _validate_target_for_offer(opening_state.run_blueprint, offer=offer, target_card_instance_id=target_card_instance_id, registry=registry)
    run_blueprint = _apply_cost(opening_state.run_blueprint, offer=offer)
    run_blueprint = _apply_reward(
        run_blueprint,
        offer=offer,
        registry=registry,
        target_card_instance_id=target_card_instance_id,
    )
    return replace(
        opening_state,
        run_blueprint=run_blueprint,
        pending_neow_offer_id=None,
        resolved_neow_offer_ids=[*opening_state.resolved_neow_offer_ids, offer.offer_id],
    )


def _generate_neow_offers(*, seed: int, run_blueprint: RunState, registry) -> list[NeowOffer]:
    character_id = run_blueprint.character_id
    rng = rng_for_room(seed=seed, room_id=f"opening:{character_id}", category="neow")
    free_offers = [
        _build_offer("free-1", "free", "gold", registry, rng),
        _build_offer("free-2", "free", _pick_free_reward_kind(rng), registry, rng),
    ]
    tradeoff_offers = [
        _build_offer("tradeoff-1", "tradeoff", _pick_tradeoff_reward_kind(rng), registry, rng),
        _build_offer("tradeoff-2", "tradeoff", _pick_tradeoff_reward_kind(rng), registry, rng),
    ]
    return [*free_offers, *tradeoff_offers]


def _pick_free_reward_kind(rng: Random) -> str:
    kinds = ["relic", "potion", "rare_card"]
    return rng.choice(kinds)


def _pick_tradeoff_reward_kind(rng: Random) -> str:
    kinds = ["upgrade_card", "remove_card", "curse_card"]
    return rng.choice(kinds)


def _build_offer(offer_id: str, category: str, reward_kind: str, registry, rng: Random) -> NeowOffer:
    reward_payload = _build_reward_payload(reward_kind=reward_kind, registry=registry, rng=rng)
    requires_target = reward_kind if reward_kind in {"upgrade_card", "remove_card"} else None
    cost_kind, cost_payload = _build_cost_payload(reward_kind=reward_kind, rng=rng)
    summary, detail_lines = _build_description(reward_kind=reward_kind, reward_payload=reward_payload, cost_kind=cost_kind, cost_payload=cost_payload)
    return NeowOffer(
        offer_id=offer_id,
        category=category,
        reward_kind=reward_kind,
        cost_kind=cost_kind,
        reward_payload=reward_payload,
        cost_payload=cost_payload,
        requires_target=requires_target,
        summary=summary,
        detail_lines=detail_lines,
    )


def _build_reward_payload(*, reward_kind: str, registry, rng: Random) -> dict[str, object]:
    if reward_kind == "gold":
        return {"reward_id": "gold:100", "amount": 100}
    if reward_kind == "relic":
        relic_id = _choose_relic_id(registry=registry, rng=rng)
        return {"reward_id": f"relic:{relic_id}", "relic_id": relic_id}
    if reward_kind == "potion":
        potion_id = _choose_potion_id(registry=registry, rng=rng)
        return {"potion_id": potion_id}
    if reward_kind == "rare_card":
        card_id = _choose_rare_card_id(registry=registry, rng=rng)
        return {"reward_id": f"card:{card_id}", "card_id": card_id}
    if reward_kind == "upgrade_card":
        return {"action": "upgrade_card"}
    if reward_kind == "remove_card":
        return {"action": "remove_card"}
    if reward_kind == "curse_card":
        card_id = _choose_curse_card_id(registry=registry, rng=rng)
        return {"reward_id": f"card:{card_id}", "card_id": card_id}
    raise ValueError(f"unsupported reward_kind: {reward_kind}")


def _build_cost_payload(*, reward_kind: str, rng: Random) -> tuple[str | None, dict[str, object]]:
    if reward_kind == "upgrade_card":
        return "hp_loss", {"amount": rng.choice([6, 8, 10])}
    if reward_kind == "remove_card":
        return "gold_loss", {"amount": 75}
    if reward_kind == "curse_card":
        return "curse", {"card_id": "doubt"}
    return None, {}


def _build_description(
    *,
    reward_kind: str,
    reward_payload: dict[str, object],
    cost_kind: str | None,
    cost_payload: dict[str, object],
) -> tuple[str, tuple[str, ...]]:
    summary_map = {
        "gold": "获得金币",
        "relic": "获得遗物",
        "potion": "获得药水",
        "rare_card": "获得稀有牌",
        "upgrade_card": "升级 1 张牌",
        "remove_card": "移除 1 张牌",
        "curse_card": "获得诅咒牌",
    }
    summary = summary_map[reward_kind]
    details = [summary]
    if reward_kind == "gold":
        details.append(f"获得 {reward_payload['amount']} 金币")
    elif reward_kind == "relic":
        details.append(f"获得遗物：{reward_payload['relic_id']}")
    elif reward_kind == "potion":
        details.append(f"获得药水：{reward_payload['potion_id']}")
    elif reward_kind == "rare_card":
        details.append(f"获得稀有牌：{reward_payload['card_id']}")
    elif reward_kind == "curse_card":
        details.append(f"获得诅咒牌：{reward_payload['card_id']}")
    if cost_kind is not None:
        details.append(_describe_cost(cost_kind, cost_payload))
    return summary, tuple(details)


def _describe_cost(cost_kind: str, cost_payload: dict[str, object]) -> str:
    if cost_kind == "hp_loss":
        return f"失去 {cost_payload['amount']} 点生命"
    if cost_kind == "gold_loss":
        return f"失去 {cost_payload['amount']} 金币"
    if cost_kind == "curse":
        return f"牌组中加入诅咒牌：{cost_payload['card_id']}"
    return cost_kind


def _choose_relic_id(*, registry, rng: Random) -> str:
    relic_ids = [
        relic.id
        for relic in registry.relics().all()
        if relic.can_appear_in_shop and relic.id not in {"burning_blood"}
    ]
    return rng.choice(relic_ids)


def _choose_potion_id(*, registry, rng: Random) -> str:
    potion_ids = [potion.id for potion in registry.potions().all()]
    return rng.choice(potion_ids)


def _choose_rare_card_id(*, registry, rng: Random) -> str:
    card_ids = [
        card.id
        for card in registry.cards().all()
        if card.rarity == "rare" and card.card_type not in {"curse", "status"}
    ]
    return rng.choice(card_ids)


def _choose_curse_card_id(*, registry, rng: Random) -> str:
    card_ids = [card.id for card in registry.cards().all() if card.card_type == "curse"]
    return rng.choice(card_ids)


def _apply_cost(run_blueprint: RunState, *, offer: NeowOffer) -> RunState:
    if offer.cost_kind == "hp_loss":
        amount = int(offer.cost_payload["amount"])
        return replace(run_blueprint, current_hp=max(1, run_blueprint.current_hp - amount))
    if offer.cost_kind == "gold_loss":
        amount = int(offer.cost_payload["amount"])
        return replace(run_blueprint, gold=max(0, run_blueprint.gold - amount))
    if offer.cost_kind == "curse":
        card_id = str(offer.cost_payload["card_id"])
        return replace(run_blueprint, deck=[*run_blueprint.deck, _next_instance_id(run_blueprint.deck, card_id)])
    return run_blueprint


def _apply_reward(
    run_blueprint: RunState,
    *,
    offer: NeowOffer,
    registry,
    target_card_instance_id: str | None,
) -> RunState:
    reward_kind = offer.reward_kind
    reward_payload = offer.reward_payload
    if reward_kind == "gold":
        return apply_reward(run_state=run_blueprint, reward_id=str(reward_payload["reward_id"]), registry=registry)
    if reward_kind == "relic":
        return apply_reward(run_state=run_blueprint, reward_id=str(reward_payload["reward_id"]), registry=registry)
    if reward_kind == "potion":
        potion_id = str(reward_payload["potion_id"])
        registry.potions().get(potion_id)
        return replace(run_blueprint, potions=[*run_blueprint.potions, potion_id])
    if reward_kind == "rare_card":
        return apply_reward(run_state=run_blueprint, reward_id=str(reward_payload["reward_id"]), registry=registry)
    if reward_kind == "curse_card":
        return apply_reward(run_state=run_blueprint, reward_id=str(reward_payload["reward_id"]), registry=registry)
    if reward_kind == "upgrade_card":
        return _apply_upgrade_card(run_blueprint, registry=registry, target_card_instance_id=target_card_instance_id)
    if reward_kind == "remove_card":
        return _apply_remove_card(run_blueprint, target_card_instance_id=target_card_instance_id)
    raise ValueError(f"unsupported reward_kind: {reward_kind}")


def _apply_upgrade_card(run_blueprint: RunState, *, registry, target_card_instance_id: str | None) -> RunState:
    if target_card_instance_id is None:
        return run_blueprint
    card_id = target_card_instance_id.split("#", 1)[0]
    upgraded_card_id = registry.cards().get(card_id).upgrades_to or card_id
    _old_card_id, suffix = target_card_instance_id.split("#", 1)
    upgraded_instance_id = f"{upgraded_card_id}#{suffix}"
    deck = [
        upgraded_instance_id if card_instance_id == target_card_instance_id else card_instance_id
        for card_instance_id in run_blueprint.deck
    ]
    return replace(run_blueprint, deck=deck)


def _apply_remove_card(run_blueprint: RunState, *, target_card_instance_id: str | None) -> RunState:
    if target_card_instance_id is None:
        return run_blueprint
    deck = [card_instance_id for card_instance_id in run_blueprint.deck if card_instance_id != target_card_instance_id]
    return replace(run_blueprint, deck=deck, card_removal_count=run_blueprint.card_removal_count + 1)


def _validate_target_for_offer(
    run_blueprint: RunState,
    *,
    offer: NeowOffer,
    target_card_instance_id: str | None,
    registry,
) -> None:
    if offer.requires_target is None:
        return
    if target_card_instance_id is None:
        return
    if target_card_instance_id not in run_blueprint.deck:
        raise ValueError("target card is not in deck")
    card_id = target_card_instance_id.split("#", 1)[0]
    card_def = registry.cards().get(card_id)
    if offer.requires_target == "upgrade_card" and card_def.upgrades_to is None:
        raise ValueError("target card cannot be upgraded")
    if offer.requires_target == "remove_card":
        return
    raise ValueError("unsupported target requirement")


def _next_instance_id(deck: list[str], card_id: str) -> str:
    highest_suffix = 0
    for card_instance_id in deck:
        _current_card_id, suffix = card_instance_id.split("#", 1)
        if suffix.isdigit():
            highest_suffix = max(highest_suffix, int(suffix))
    return f"{card_id}#{highest_suffix + 1}"
