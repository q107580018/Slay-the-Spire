from __future__ import annotations

from math import ceil

from slay_the_spire.domain.combat.turn_flow import start_turn
from slay_the_spire.domain.effects.effect_resolver import resolve_effect_queue
from slay_the_spire.domain.hooks.hook_dispatcher import dispatch_hook
from slay_the_spire.domain.hooks.runtime import build_runtime_hook_registrations
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.rng import rng_for_room, weighted_choice

_SUPPORTED_ROOM_TYPES = {"combat", "elite", "event", "boss", "shop", "rest", "treasure"}
_TREASURE_FALLBACK_RELIC_ID = "circlet"
_COMMON_RELIC_RARITY = "common"
_UNCOMMON_RELIC_RARITY = "uncommon"
_RARE_RELIC_RARITY = "rare"
_UNKNOWN_EVENT_ROOM_TYPES = ("event", "combat", "treasure")


def _scaled_shop_price(price: int, *, run_state: RunState) -> int:
    scaled_price = price
    if "membership_card" in run_state.relics:
        scaled_price = ceil(scaled_price / 2)
    if "the_courier" in run_state.relics:
        scaled_price = (scaled_price * 80) // 100
    return max(0, scaled_price)


def _heal_on_shop_entry(run_state: RunState) -> None:
    if "meal_ticket" not in run_state.relics:
        return
    run_state.current_hp = min(run_state.max_hp, run_state.current_hp + 15)


def _room_type_for_node(act_state: ActState, node_id: str) -> str:
    room_type = act_state.get_node(node_id).room_type
    if room_type not in _SUPPORTED_ROOM_TYPES:
        raise ValueError(f"unsupported room_type: {room_type}")
    return room_type


def _build_card_instance_ids(card_ids: list[str]) -> list[str]:
    return [f"{card_id}#{index}" for index, card_id in enumerate(card_ids, start=1)]


def _combat_encounter_count(act_state: ActState) -> int:
    return sum(
        1
        for node_id in act_state.visited_node_ids
        if act_state.get_node(node_id).room_type == "combat"
    )


def _build_enemy_state(
    enemy_id: str, registry: ContentProviderPort, *, instance_id: str
) -> EnemyState:
    enemy_def = registry.enemies().get(enemy_id)
    statuses: list[StatusState] = []
    if enemy_def.move_table:
        first_move = enemy_def.move_table[0]
        if first_move.get("move") == "sleep":
            sleep_turns = first_move.get("sleep_turns", 0)
            if not isinstance(sleep_turns, int):
                raise TypeError("sleep_turns must be an int")
            if sleep_turns > 0:
                statuses.append(StatusState(status_id="sleeping", stacks=sleep_turns))
    return EnemyState(
        instance_id=instance_id,
        enemy_id=enemy_def.id,
        hp=enemy_def.hp,
        max_hp=enemy_def.hp,
        block=0,
        statuses=statuses,
    )


def _player_start_statuses(run_state: RunState) -> list[StatusState]:
    statuses: list[StatusState] = []
    girya_lifts = run_state.relic_sequence_positions.get("girya_lifts", 0)
    if girya_lifts > 0:
        statuses.append(StatusState(status_id="strength", stacks=girya_lifts))
    return statuses


def _apply_preserved_insect(enemy: EnemyState) -> EnemyState:
    reduced_max_hp = max((enemy.max_hp * 3) // 4, 1)
    return EnemyState(
        instance_id=enemy.instance_id,
        enemy_id=enemy.enemy_id,
        hp=min(enemy.hp, reduced_max_hp),
        max_hp=reduced_max_hp,
        block=enemy.block,
        statuses=list(enemy.statuses),
    )


def _select_combat_enemy_ids(
    run_state: RunState,
    act_state: ActState,
    *,
    room_id: str,
    enemy_pool_id: str,
    registry: ContentProviderPort,
) -> tuple[str | None, list[str]]:
    encounter_entries = list(registry.encounter_pool_entries(enemy_pool_id))
    if not encounter_entries:
        raise ValueError(
            f"encounter pool {enemy_pool_id} must contain at least one encounter"
        )
    combat_count = _combat_encounter_count(act_state)
    eligible_entries = [
        entry
        for entry in encounter_entries
        if (entry.min_combat_count is None or combat_count >= entry.min_combat_count)
        and (entry.max_combat_count is None or combat_count <= entry.max_combat_count)
    ]
    if not eligible_entries:
        raise ValueError(
            f"no encounter entries match combat count {combat_count} for pool {enemy_pool_id}"
        )
    encounter_rng = _offer_rng(run_state, room_id, "enemy")
    encounter_id = weighted_choice(
        [(entry.member_id, entry.weight) for entry in eligible_entries],
        rng=encounter_rng,
    )
    encounter = registry.encounters().get(encounter_id)
    return encounter_id, list(encounter.enemy_ids)


def _split_innate_cards(
    deck_instance_ids: list[str], registry: ContentProviderPort
) -> tuple[list[str], list[str]]:
    innate_cards: list[str] = []
    normal_cards: list[str] = []
    for card_instance_id in deck_instance_ids:
        try:
            card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
            if getattr(card_def, "innate", False):
                innate_cards.append(card_instance_id)
            else:
                normal_cards.append(card_instance_id)
        except (KeyError, ValueError):
            normal_cards.append(card_instance_id)
    return innate_cards, normal_cards


def _build_combat_state(
    run_state: RunState,
    act_state: ActState,
    *,
    room_id: str,
    enemy_pool_id: str,
    registry: ContentProviderPort,
) -> tuple[CombatState, str | None]:
    character = registry.characters().get(run_state.character_id)
    deck_instance_ids = list(run_state.deck) or _build_card_instance_ids(
        list(character.starter_deck)
    )
    _offer_rng(run_state, room_id, "combat:draw_order").shuffle(deck_instance_ids)
    innate_cards, normal_cards = _split_innate_cards(deck_instance_ids, registry)
    deck_instance_ids = innate_cards + normal_cards
    encounter_id, enemy_ids = _select_combat_enemy_ids(
        run_state,
        act_state,
        room_id=room_id,
        enemy_pool_id=enemy_pool_id,
        registry=registry,
    )

    state = CombatState(
        round_number=1,
        energy=3,
        hand=[],
        draw_pile=deck_instance_ids,
        discard_pile=[],
        exhaust_pile=[],
        player=PlayerCombatState(
            instance_id=f"player-{run_state.character_id}",
            hp=run_state.current_hp,
            max_hp=run_state.max_hp,
            block=0,
            statuses=_player_start_statuses(run_state),
        ),
        enemies=[
            _build_enemy_state(enemy_id, registry, instance_id=f"enemy-{index}")
            for index, enemy_id in enumerate(enemy_ids, start=1)
        ],
        effect_queue=[],
        log=[],
    )
    if (
        enemy_pool_id == act_state.elite_pool_id
        and "preserved_insect" in run_state.relics
    ):
        state.enemies = [_apply_preserved_insect(enemy) for enemy in state.enemies]
        state._refresh_entity_index()
    registrations = build_runtime_hook_registrations(run_state, registry)
    state = start_turn(
        state,
        hook_registrations=registrations,
        registry=registry,
    )
    dispatch_hook(state, "on_combat_start", registrations)
    resolve_effect_queue(state, hook_registrations=registrations)
    return state, encounter_id


def _offer_rng(run_state: RunState, room_id: str, category: str):
    return rng_for_room(seed=run_state.seed, room_id=room_id, category=category)


def _resolved_unknown_room_kind(run_state: RunState, *, room_id: str) -> str:
    tiny_chest_counter = run_state.relic_sequence_positions.get("tiny_chest_counter", 0)
    if "tiny_chest" in run_state.relics and tiny_chest_counter + 1 >= 4:
        run_state.relic_sequence_positions["tiny_chest_counter"] = 0
        return "treasure"

    rng = _offer_rng(run_state, room_id, "unknown_room")
    choices = [("event", 55), ("combat", 30), ("treasure", 15)]
    if "juzu_bracelet" in run_state.relics:
        choices = [("event", 79), ("treasure", 21)]
    resolved_kind = weighted_choice(choices, rng=rng)
    if "tiny_chest" in run_state.relics:
        run_state.relic_sequence_positions["tiny_chest_counter"] = (
            tiny_chest_counter + 1
        )
    return resolved_kind


def _sample_ids(ids: list[str], *, count: int, rng) -> list[str]:
    if not ids:
        return []
    if len(ids) <= count:
        return list(ids)
    working = list(ids)
    rng.shuffle(working)
    return working[:count]


def _next_relic_from_sequence(*, run_state: RunState, pool_id: str) -> str | None:
    sequence = run_state.relic_sequences.get(pool_id, [])
    position = run_state.relic_sequence_positions.get(pool_id, 0)
    while position < len(sequence):
        relic_id = sequence[position]
        position += 1
        run_state.relic_sequence_positions[pool_id] = position
        if relic_id not in run_state.relics:
            return relic_id
    run_state.relic_sequence_positions[pool_id] = position
    return None


def _peek_relic_from_sequence(*, run_state: RunState, pool_id: str) -> str | None:
    sequence = run_state.relic_sequences.get(pool_id, [])
    position = run_state.relic_sequence_positions.get(pool_id, 0)
    while position < len(sequence):
        relic_id = sequence[position]
        if relic_id not in run_state.relics:
            return relic_id
        position += 1
    return None


def _roll_treasure_relic_rarity(*, room_id: str, seed: int) -> str:
    rng = rng_for_room(seed=seed, room_id=room_id, category="treasure_relic_rarity")
    roll = rng.randint(1, 100)
    if roll <= 3:
        return _RARE_RELIC_RARITY
    if roll <= 40:
        return _UNCOMMON_RELIC_RARITY
    return _COMMON_RELIC_RARITY


def _build_shop_payload(
    run_state: RunState, *, room_id: str, registry: ContentProviderPort
) -> dict[str, object]:
    _heal_on_shop_entry(run_state)
    card_ids = [
        card.id for card in registry.cards().all() if "shop" in card.acquisition_tags
    ]
    potion_ids = [potion.id for potion in registry.potions().all()]
    card_rng = _offer_rng(run_state, room_id, "cards")
    potion_rng = _offer_rng(run_state, room_id, "potions")
    shop_relic_id = (
        _next_relic_from_sequence(run_state=run_state, pool_id="shop")
        or _TREASURE_FALLBACK_RELIC_ID
    )

    card_prices = {"strike": 50, "defend": 50, "bash": 75}
    cards = [
        {
            "offer_id": f"card-{index}",
            "card_id": card_id,
            "price": _scaled_shop_price(
                card_prices.get(card_id, 60), run_state=run_state
            ),
        }
        for index, card_id in enumerate(
            _sample_ids(card_ids, count=3, rng=card_rng), start=1
        )
    ]
    relics = [
        {
            "offer_id": "relic-1",
            "relic_id": shop_relic_id,
            "price": _scaled_shop_price(150, run_state=run_state),
        }
    ]
    potions = [
        {
            "offer_id": f"potion-{index}",
            "potion_id": potion_id,
            "price": _scaled_shop_price(60, run_state=run_state),
        }
        for index, potion_id in enumerate(
            _sample_ids(potion_ids, count=2, rng=potion_rng), start=1
        )
    ]
    return {
        "cards": cards,
        "relics": relics,
        "potions": potions,
        "remove_price": 50
        if "smiling_mask" in run_state.relics
        else _scaled_shop_price(
            75 + (run_state.card_removal_count * 25), run_state=run_state
        ),
    }


def _room_payload_for_entry(
    act_state: ActState,
    *,
    current_node: ActNodeState,
    room_id: str,
    room_kind: str,
    run_state: RunState,
    registry: ContentProviderPort,
) -> dict[str, object]:
    cached_payload = act_state.room_payloads.get(room_id)
    if cached_payload is not None:
        return dict(cached_payload)

    payload: dict[str, object] = {
        "act_id": act_state.act_id,
        "node_id": current_node.node_id,
        "room_kind": room_kind,
        "next_node_ids": list(current_node.next_node_ids),
    }
    resolved_room_kind = room_kind
    if room_kind == "event":
        resolved_room_kind = _resolved_unknown_room_kind(run_state, room_id=room_id)
        payload["resolved_room_kind"] = resolved_room_kind
    if resolved_room_kind in {"combat", "elite", "boss"}:
        if room_kind == "combat":
            enemy_pool_id = act_state.enemy_pool_id
        elif room_kind == "elite":
            enemy_pool_id = act_state.elite_pool_id
        else:
            enemy_pool_id = act_state.boss_pool_id
        if resolved_room_kind == "combat":
            enemy_pool_id = act_state.enemy_pool_id
        elif resolved_room_kind == "elite":
            enemy_pool_id = act_state.elite_pool_id
        elif resolved_room_kind == "boss":
            enemy_pool_id = act_state.boss_pool_id
        if enemy_pool_id is None:
            raise ValueError(f"{resolved_room_kind} rooms require an enemy pool id")
        payload["enemy_pool_id"] = enemy_pool_id
        combat_state, encounter_id = _build_combat_state(
            run_state,
            act_state,
            room_id=room_id,
            enemy_pool_id=enemy_pool_id,
            registry=registry,
        )
        if encounter_id is not None:
            payload["encounter_id"] = encounter_id
        payload["combat_state"] = combat_state.to_dict()
    elif resolved_room_kind == "event":
        if act_state.event_pool_id is None:
            raise ValueError("event rooms require an event pool id")
        payload.update(
            _build_event_payload(
                run_state,
                room_id=room_id,
                event_pool_id=act_state.event_pool_id,
                registry=registry,
            )
        )
    elif resolved_room_kind == "shop":
        payload.update(
            _build_shop_payload(run_state, room_id=room_id, registry=registry)
        )
    elif resolved_room_kind == "rest":
        payload["actions"] = ["rest", "smith"]
        if "girya" in run_state.relics:
            payload["actions"].append("lift")
        if "peace_pipe" in run_state.relics:
            payload["actions"].append("digestion")
        if "shovel" in run_state.relics:
            payload["actions"].append("dig")
    elif resolved_room_kind == "treasure":
        payload.update(
            _build_treasure_payload(run_state, room_id=room_id, registry=registry)
        )

    if resolved_room_kind in {"shop", "treasure"}:
        act_state.room_payloads[room_id] = dict(payload)
    return payload


def _build_event_payload(
    run_state: RunState,
    *,
    room_id: str,
    event_pool_id: str,
    registry: ContentProviderPort,
) -> dict[str, object]:
    event_entries = [
        entry
        for entry in registry.event_pool_entries(event_pool_id)
        if not (entry.once_per_run and entry.member_id in run_state.seen_event_ids)
    ]
    if not event_entries:
        raise ValueError(f"event pool {event_pool_id} must contain at least one event")
    rng = _offer_rng(run_state, room_id, "event")
    event_id = weighted_choice(
        [(entry.member_id, entry.weight) for entry in event_entries],
        rng=rng,
    )
    if event_id not in run_state.seen_event_ids:
        run_state.seen_event_ids.append(event_id)
    return {"event_pool_id": event_pool_id, "event_id": event_id}


def _build_treasure_payload(
    run_state: RunState, *, room_id: str, registry: ContentProviderPort
) -> dict[str, object]:
    matryoshka_chests_opened = run_state.relic_sequence_positions.get(
        "matryoshka_chests_opened", 0
    )
    if "matryoshka" in run_state.relics and matryoshka_chests_opened < 2:
        rarity_pool_order = ["common", "uncommon", "rare"]
        first_relic = None
        second_relic = None
        for pool_id in rarity_pool_order:
            first_relic = _next_relic_from_sequence(
                run_state=run_state, pool_id=pool_id
            )
            if first_relic is not None:
                break
        for pool_id in rarity_pool_order:
            second_relic = _next_relic_from_sequence(
                run_state=run_state, pool_id=pool_id
            )
            if second_relic is not None:
                break
        relic_ids = [relic_id for relic_id in [first_relic, second_relic] if relic_id]
        if relic_ids:
            run_state.relic_sequence_positions["matryoshka_chests_opened"] = (
                matryoshka_chests_opened + 1
            )
            return {"treasure_relic_id": relic_ids[0], "treasure_relic_ids": relic_ids}
    treasure_relic_id = _next_relic_from_sequence(
        run_state=run_state,
        pool_id=_roll_treasure_relic_rarity(room_id=room_id, seed=run_state.seed),
    )
    if treasure_relic_id is None:
        registry.relics().get(_TREASURE_FALLBACK_RELIC_ID)
        return {"treasure_relic_id": _TREASURE_FALLBACK_RELIC_ID}
    return {"treasure_relic_id": treasure_relic_id}


def _grant_room_entry_gold(run_state: RunState, room_kind: str) -> None:
    if "maw_bank" in run_state.relics and room_kind == "shop":
        run_state.relic_sequence_positions["maw_bank_disabled"] = 1
    if (
        "maw_bank" in run_state.relics
        and room_kind != "shop"
        and run_state.relic_sequence_positions.get("maw_bank_disabled", 0) == 0
    ):
        run_state.gold += 12
    if "ssserpent_head" in run_state.relics and room_kind == "event":
        run_state.gold += 50


def _record_event_room_progress(
    act_state: ActState, room_id: str, run_state: RunState, room_kind: str
) -> None:
    if room_kind != "event" or "tiny_chest" not in run_state.relics:
        return
    counter = run_state.relic_sequence_positions.get("tiny_chest_counter", 0)
    act_state.room_payloads[room_id] = {"tiny_chest_counter": counter}


def _mark_node_visited(act_state: ActState, node_id: str) -> None:
    act_state.current_node_id = node_id
    if node_id not in act_state.visited_node_ids:
        act_state.visited_node_ids.append(node_id)


def enter_room(
    run_state: RunState,
    act_state: ActState,
    node_id: str,
    registry: ContentProviderPort,
) -> RoomState:
    current_node = act_state.get_node(node_id)
    room_kind = _room_type_for_node(act_state, current_node.node_id)
    room_id = f"{act_state.act_id}:{current_node.node_id}"
    _grant_room_entry_gold(run_state, room_kind)
    payload = _room_payload_for_entry(
        act_state,
        current_node=current_node,
        room_id=room_id,
        room_kind=room_kind,
        run_state=run_state,
        registry=registry,
    )
    resolved_room_kind = payload.get("resolved_room_kind", room_kind)
    if not isinstance(resolved_room_kind, str):
        resolved_room_kind = room_kind
    room_state = RoomState(
        room_id=room_id,
        room_type=resolved_room_kind,
        stage="waiting_input",
        payload=payload,
        is_resolved=False,
        rewards=[],
    )
    _record_event_room_progress(act_state, room_id, run_state, room_kind)
    _mark_node_visited(act_state, current_node.node_id)
    return room_state
