from __future__ import annotations

from slay_the_spire.domain.combat.turn_flow import start_turn
from slay_the_spire.domain.effects.effect_resolver import resolve_effect_queue
from slay_the_spire.domain.hooks.hook_dispatcher import dispatch_hook
from slay_the_spire.domain.hooks.runtime import build_runtime_hook_registrations
from slay_the_spire.domain.models.act_state import ActState
from slay_the_spire.domain.models.combat_state import CombatState
from slay_the_spire.domain.models.entities import EnemyState, PlayerCombatState
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.models.statuses import StatusState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.rng import rng_for_room, weighted_choice

_SUPPORTED_ROOM_TYPES = {"combat", "elite", "event", "boss", "shop", "rest"}


def _room_type_for_node(act_state: ActState, node_id: str) -> str:
    room_type = act_state.get_node(node_id).room_type
    if room_type not in _SUPPORTED_ROOM_TYPES:
        raise ValueError(f"unsupported room_type: {room_type}")
    return room_type


def _build_card_instance_ids(card_ids: list[str]) -> list[str]:
    return [f"{card_id}#{index}" for index, card_id in enumerate(card_ids, start=1)]


def _build_enemy_state(enemy_id: str, registry: ContentProviderPort, *, instance_id: str) -> EnemyState:
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


def _select_combat_enemy_ids(
    run_state: RunState,
    *,
    room_id: str,
    enemy_pool_id: str,
    registry: ContentProviderPort,
) -> tuple[str | None, list[str]]:
    encounter_entries = list(registry.encounter_pool_entries(enemy_pool_id))
    if not encounter_entries:
        raise ValueError(f"encounter pool {enemy_pool_id} must contain at least one encounter")
    encounter_rng = _offer_rng(run_state, room_id, "enemy")
    encounter_id = weighted_choice(
        [(entry.member_id, entry.weight) for entry in encounter_entries],
        rng=encounter_rng,
    )
    encounter = registry.encounters().get(encounter_id)
    return encounter_id, list(encounter.enemy_ids)


def _build_combat_state(
    run_state: RunState,
    *,
    room_id: str,
    enemy_pool_id: str,
    registry: ContentProviderPort,
) -> tuple[CombatState, str | None]:
    character = registry.characters().get(run_state.character_id)
    deck_instance_ids = list(run_state.deck) or _build_card_instance_ids(list(character.starter_deck))
    encounter_id, enemy_ids = _select_combat_enemy_ids(
        run_state,
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
            statuses=[],
        ),
        enemies=[
            _build_enemy_state(enemy_id, registry, instance_id=f"enemy-{index}")
            for index, enemy_id in enumerate(enemy_ids, start=1)
        ],
        effect_queue=[],
        log=[],
    )
    state = start_turn(state)
    registrations = build_runtime_hook_registrations(run_state, registry)
    dispatch_hook(state, "on_combat_start", registrations)
    resolve_effect_queue(state, hook_registrations=registrations)
    return state, encounter_id


def _offer_rng(run_state: RunState, room_id: str, category: str):
    return rng_for_room(seed=run_state.seed, room_id=room_id, category=category)


def _sample_ids(ids: list[str], *, count: int, rng) -> list[str]:
    if not ids:
        return []
    if len(ids) <= count:
        return list(ids)
    working = list(ids)
    rng.shuffle(working)
    return working[:count]


def _build_shop_payload(run_state: RunState, *, room_id: str, registry: ContentProviderPort) -> dict[str, object]:
    card_ids = [card.id for card in registry.cards().all() if card.can_appear_in_shop]
    relic_ids = [relic.id for relic in registry.relics().all() if relic.can_appear_in_shop]
    potion_ids = [potion.id for potion in registry.potions().all()]
    card_rng = _offer_rng(run_state, room_id, "cards")
    relic_rng = _offer_rng(run_state, room_id, "relics")
    potion_rng = _offer_rng(run_state, room_id, "potions")

    card_prices = {"strike": 50, "defend": 50, "bash": 75}
    cards = [
        {"offer_id": f"card-{index}", "card_id": card_id, "price": card_prices.get(card_id, 60)}
        for index, card_id in enumerate(_sample_ids(card_ids, count=3, rng=card_rng), start=1)
    ]
    relics = [
        {"offer_id": f"relic-{index}", "relic_id": relic_id, "price": 150}
        for index, relic_id in enumerate(_sample_ids(relic_ids, count=1, rng=relic_rng), start=1)
    ]
    potions = [
        {"offer_id": f"potion-{index}", "potion_id": potion_id, "price": 60}
        for index, potion_id in enumerate(_sample_ids(potion_ids, count=2, rng=potion_rng), start=1)
    ]
    return {
        "cards": cards,
        "relics": relics,
        "potions": potions,
        "remove_price": 75 + (run_state.card_removal_count * 25),
    }


def _build_event_payload(run_state: RunState, *, room_id: str, event_pool_id: str, registry: ContentProviderPort) -> dict[str, object]:
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


def _mark_node_visited(act_state: ActState, node_id: str) -> None:
    act_state.current_node_id = node_id
    if node_id not in act_state.visited_node_ids:
        act_state.visited_node_ids.append(node_id)


def enter_room(run_state: RunState, act_state: ActState, node_id: str, registry: ContentProviderPort) -> RoomState:
    current_node = act_state.get_node(node_id)
    room_kind = _room_type_for_node(act_state, current_node.node_id)
    room_id = f"{act_state.act_id}:{current_node.node_id}"

    payload: dict[str, object] = {
        "act_id": act_state.act_id,
        "node_id": current_node.node_id,
        "room_kind": room_kind,
        "next_node_ids": list(current_node.next_node_ids),
    }
    if room_kind in {"combat", "elite", "boss"}:
        if room_kind == "combat":
            enemy_pool_id = act_state.enemy_pool_id
        elif room_kind == "elite":
            enemy_pool_id = act_state.elite_pool_id
        else:
            enemy_pool_id = act_state.boss_pool_id
        if enemy_pool_id is None:
            raise ValueError(f"{room_kind} rooms require an enemy pool id")
        payload["enemy_pool_id"] = enemy_pool_id
        combat_state, encounter_id = _build_combat_state(
            run_state,
            room_id=room_id,
            enemy_pool_id=enemy_pool_id,
            registry=registry,
        )
        if encounter_id is not None:
            payload["encounter_id"] = encounter_id
        payload["combat_state"] = combat_state.to_dict()
    elif room_kind == "event":
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
    elif room_kind == "shop":
        payload.update(_build_shop_payload(run_state, room_id=room_id, registry=registry))
    elif room_kind == "rest":
        payload["actions"] = ["rest", "smith"]
    room_state = RoomState(
        room_id=room_id,
        room_type=room_kind,
        stage="waiting_input",
        payload=payload,
        is_resolved=False,
        rewards=[],
    )
    _mark_node_visited(act_state, current_node.node_id)
    return room_state
