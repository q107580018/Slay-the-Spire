from __future__ import annotations

from dataclasses import dataclass, replace

from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort


@dataclass(slots=True, frozen=True)
class EventActionResult:
    run_state: RunState
    room_state: RoomState
    message: str | None = None


def _result(run_state: RunState, room_state: RoomState, message: str | None = None) -> EventActionResult:
    return EventActionResult(run_state=run_state, room_state=room_state, message=message)


def _upgrade_options(run_state: RunState, registry: ContentProviderPort) -> list[str]:
    options: list[str] = []
    for card_instance_id in run_state.deck:
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        if card_def.upgrades_to is not None:
            options.append(card_instance_id)
    return options


def _next_instance_id(deck: list[str], card_id: str) -> str:
    highest_suffix = 0
    for card_instance_id in deck:
        _current_card_id, suffix = card_instance_id.split("#", 1)
        if suffix.isdigit():
            highest_suffix = max(highest_suffix, int(suffix))
    return f"{card_id}#{highest_suffix + 1}"


def _with_added_card(run_state: RunState, card_id: str) -> RunState:
    return replace(run_state, deck=[*run_state.deck, _next_instance_id(run_state.deck, card_id)])


def _with_added_relic(run_state: RunState, relic_id: str) -> RunState:
    if relic_id in run_state.relics:
        return run_state
    return replace(run_state, relics=[*run_state.relics, relic_id])


def _event_gold_bonus(run_state: RunState, amount: int) -> int:
    if "ectoplasm" in run_state.relics:
        return 0
    if "golden_idol" not in run_state.relics:
        return amount
    return amount + (amount // 4)


def _pending_effect(payload: dict[str, object]) -> dict[str, object]:
    pending = payload.get("pending_effect")
    return dict(pending) if isinstance(pending, dict) else {}


def _complete_event_room(
    room_state: RoomState,
    payload: dict[str, object],
    *,
    result: str,
    result_text: str,
) -> RoomState:
    payload.pop("pending_effect", None)
    payload.pop("pending_result", None)
    payload.pop("pending_result_text", None)
    payload.pop("upgrade_options", None)
    payload.pop("remove_candidates", None)
    payload["result"] = result
    payload["result_text"] = result_text
    payload["action_committed"] = True
    return RoomState(
        schema_version=room_state.schema_version,
        room_id=room_state.room_id,
        room_type=room_state.room_type,
        stage="completed",
        payload=payload,
        is_resolved=True,
        rewards=[],
    )


def _waiting_event_room(room_state: RoomState, payload: dict[str, object]) -> RoomState:
    payload.pop("pending_effect", None)
    payload.pop("pending_result", None)
    payload.pop("pending_result_text", None)
    payload.pop("upgrade_options", None)
    payload.pop("remove_candidates", None)
    payload.pop("choice_id", None)
    payload.pop("result", None)
    payload.pop("result_text", None)
    payload.pop("action_committed", None)
    return RoomState(
        schema_version=room_state.schema_version,
        room_id=room_state.room_id,
        room_type=room_state.room_type,
        stage="waiting_input",
        payload=payload,
        is_resolved=False,
        rewards=[],
    )


def _start_event_subflow(
    room_state: RoomState,
    payload: dict[str, object],
    *,
    stage: str,
    option_key: str,
    options: list[str],
    effect: dict[str, object],
    result: str,
    result_text: str,
) -> RoomState:
    payload["pending_effect"] = dict(effect)
    payload["pending_result"] = result
    payload["pending_result_text"] = result_text
    payload[option_key] = options
    return RoomState(
        schema_version=room_state.schema_version,
        room_id=room_state.room_id,
        room_type=room_state.room_type,
        stage=stage,
        payload=payload,
        is_resolved=False,
        rewards=[],
    )


def _outcome_for_choice(room_state: RoomState, choice_id: str, registry: ContentProviderPort) -> dict[str, object]:
    event_id = room_state.payload.get("event_id")
    if not isinstance(event_id, str):
        raise ValueError("event room is missing event_id")
    event_def = registry.events().get(event_id)
    for outcome in event_def.outcomes:
        if outcome.get("choice_id") == choice_id:
            return dict(outcome)
    raise ValueError(f"choice_id not found for event {event_id}: {choice_id}")


def _effect_int(effect: dict[str, object], key: str, default: int = 0) -> int:
    value = effect.get(key, default)
    if not isinstance(value, int):
        raise ValueError(f"event effect {key} must be an int")
    return value


def _resolve_upgrade_selection(
    *,
    run_state: RunState,
    room_state: RoomState,
    action_id: str,
    payload: dict[str, object],
    registry: ContentProviderPort,
) -> EventActionResult:
    if action_id == "cancel":
        return _result(run_state, _waiting_event_room(room_state, payload))
    if not action_id.startswith("upgrade_card:"):
        return _result(run_state, room_state)
    selected_card = action_id.removeprefix("upgrade_card:")
    options = payload.get("upgrade_options")
    if not isinstance(options, list) or selected_card not in options:
        return _result(run_state, room_state)
    base_card_id = card_id_from_instance_id(selected_card)
    upgraded_card_id = registry.cards().get(base_card_id).upgrades_to
    if upgraded_card_id is None:
        return _result(run_state, room_state)
    _old_card_id, suffix = selected_card.split("#", 1)
    upgraded_instance_id = f"{upgraded_card_id}#{suffix}"
    updated_deck = [upgraded_instance_id if card == selected_card else card for card in run_state.deck]
    room = _complete_event_room(
        room_state,
        payload,
        result=str(payload.get("pending_result", "gain_upgrade")),
        result_text=str(payload.get("pending_result_text", "你强化了一张牌。")),
    )
    return _result(replace(run_state, deck=updated_deck), room)


def _resolve_remove_selection(
    *,
    run_state: RunState,
    room_state: RoomState,
    action_id: str,
    payload: dict[str, object],
) -> EventActionResult:
    if action_id == "cancel":
        return _result(run_state, _waiting_event_room(room_state, payload))
    if not action_id.startswith("remove_card:"):
        return _result(run_state, room_state)
    selected_card = action_id.removeprefix("remove_card:")
    candidates = payload.get("remove_candidates")
    if not isinstance(candidates, list) or selected_card not in candidates:
        return _result(run_state, room_state)
    pending_effect = _pending_effect(payload)
    gold_cost = _effect_int(pending_effect, "gold_cost")
    if run_state.gold < gold_cost:
        return _result(run_state, room_state, "金币不足，无法执行该事件选项。")
    updated_run_state = replace(
        run_state,
        gold=run_state.gold - gold_cost,
        deck=[card for card in run_state.deck if card != selected_card],
    )
    room = _complete_event_room(
        room_state,
        payload,
        result=str(payload.get("pending_result", "remove_card")),
        result_text=str(payload.get("pending_result_text", "你移除了一张牌。")),
    )
    return _result(updated_run_state, room)


def event_action(
    *,
    run_state: RunState,
    room_state: RoomState,
    action_id: str,
    registry: ContentProviderPort,
) -> EventActionResult:
    if room_state.room_type != "event":
        raise ValueError("event_action requires an event room")

    payload = dict(room_state.payload)
    if room_state.stage == "select_event_upgrade_card":
        return _resolve_upgrade_selection(
            run_state=run_state,
            room_state=room_state,
            action_id=action_id,
            payload=payload,
            registry=registry,
        )
    if room_state.stage == "select_event_remove_card":
        return _resolve_remove_selection(
            run_state=run_state,
            room_state=room_state,
            action_id=action_id,
            payload=payload,
        )

    if not action_id.startswith("choice:"):
        return _result(run_state, room_state)
    choice_id = action_id.removeprefix("choice:")
    outcome = _outcome_for_choice(room_state, choice_id, registry)
    effect = dict(outcome.get("effect", {})) if isinstance(outcome.get("effect"), dict) else {}
    result = str(outcome.get("result", "nothing"))
    result_text = str(outcome.get("result_text", result))
    payload["choice_id"] = choice_id
    effect_type = effect.get("type")

    if effect_type == "upgrade_card_selection":
        options = _upgrade_options(run_state, registry)
        if not options:
            return _result(
                run_state,
                _complete_event_room(room_state, payload, result="nothing", result_text="当前没有可升级的卡牌。"),
            )
        return _result(
            run_state,
            _start_event_subflow(
                room_state,
                payload,
                stage="select_event_upgrade_card",
                option_key="upgrade_options",
                options=options,
                effect=effect,
                result=result,
                result_text=result_text,
            ),
        )
    if effect_type == "remove_card_selection":
        candidates = list(run_state.deck)
        if not candidates:
            return _result(
                run_state,
                _complete_event_room(room_state, payload, result="nothing", result_text="当前没有可移除的卡牌。"),
            )
        return _result(
            run_state,
            _start_event_subflow(
                room_state,
                payload,
                stage="select_event_remove_card",
                option_key="remove_candidates",
                options=candidates,
                effect=effect,
                result=result,
                result_text=result_text,
            ),
        )
    if effect_type == "heal":
        gold_cost = _effect_int(effect, "gold_cost")
        heal_amount = _effect_int(effect, "heal_amount")
        if run_state.gold < gold_cost:
            return _result(run_state, room_state, "金币不足，无法执行该事件选项。")
        updated_run_state = replace(
            run_state,
            gold=run_state.gold - gold_cost,
            current_hp=min(run_state.max_hp, run_state.current_hp + heal_amount),
        )
        return _result(
            updated_run_state,
            _complete_event_room(room_state, payload, result=result, result_text=result_text),
        )
    if effect_type == "heal_percent":
        heal_percent = _effect_int(effect, "heal_percent")
        heal_amount = max(0, (run_state.max_hp * heal_percent) // 100)
        updated_run_state = replace(
            run_state,
            current_hp=min(run_state.max_hp, run_state.current_hp + heal_amount),
        )
        return _result(
            updated_run_state,
            _complete_event_room(room_state, payload, result=result, result_text=result_text),
        )
    if effect_type == "increase_max_hp":
        amount = _effect_int(effect, "amount")
        updated_run_state = replace(
            run_state,
            max_hp=run_state.max_hp + amount,
            current_hp=min(run_state.max_hp + amount, run_state.current_hp + amount),
        )
        return _result(
            updated_run_state,
            _complete_event_room(room_state, payload, result=result, result_text=result_text),
        )
    if effect_type == "gain_gold_and_lose_hp":
        gold_amount = _event_gold_bonus(run_state, _effect_int(effect, "gain_gold"))
        updated_run_state = replace(
            run_state,
            gold=run_state.gold + gold_amount,
            current_hp=max(0, run_state.current_hp - _effect_int(effect, "lose_hp")),
        )
        return _result(
            updated_run_state,
            _complete_event_room(room_state, payload, result=result, result_text=result_text),
        )
    if effect_type == "gain_gold":
        gold_amount = _event_gold_bonus(run_state, _effect_int(effect, "gain_gold"))
        updated_run_state = replace(
            run_state,
            gold=run_state.gold + gold_amount,
        )
        return _result(
            updated_run_state,
            _complete_event_room(room_state, payload, result=result, result_text=result_text),
        )
    if effect_type == "gain_gold_and_add_curse":
        gold_amount = _event_gold_bonus(run_state, _effect_int(effect, "gain_gold"))
        curse_id = str(effect.get("curse_id", ""))
        updated_run_state = replace(run_state, gold=run_state.gold + gold_amount)
        if curse_id:
            updated_run_state = _with_added_card(updated_run_state, curse_id)
        return _result(
            updated_run_state,
            _complete_event_room(room_state, payload, result=result, result_text=result_text),
        )
    if effect_type == "gain_relic_and_reduce_max_hp":
        relic_id = str(effect.get("relic_id", ""))
        max_hp_loss = _effect_int(effect, "lose_max_hp")
        updated_run_state = _with_added_relic(run_state, relic_id) if relic_id else run_state
        next_max_hp = max(1, updated_run_state.max_hp - max_hp_loss)
        updated_run_state = replace(
            updated_run_state,
            max_hp=next_max_hp,
            current_hp=min(updated_run_state.current_hp, next_max_hp),
        )
        return _result(
            updated_run_state,
            _complete_event_room(room_state, payload, result=result, result_text=result_text),
        )
    if effect_type == "gain_relic_and_lose_hp":
        relic_id = str(effect.get("relic_id", ""))
        hp_loss = _effect_int(effect, "lose_hp")
        updated_run_state = _with_added_relic(run_state, relic_id) if relic_id else run_state
        updated_run_state = replace(
            updated_run_state,
            current_hp=max(0, updated_run_state.current_hp - hp_loss),
        )
        return _result(
            updated_run_state,
            _complete_event_room(room_state, payload, result=result, result_text=result_text),
        )
    if effect_type == "gain_relic_and_add_curse":
        relic_id = str(effect.get("relic_id", ""))
        curse_id = str(effect.get("curse_id", ""))
        updated_run_state = _with_added_relic(run_state, relic_id) if relic_id else run_state
        if curse_id:
            updated_run_state = _with_added_card(updated_run_state, curse_id)
        return _result(
            updated_run_state,
            _complete_event_room(room_state, payload, result=result, result_text=result_text),
        )
    if effect_type == "lose_gold":
        gold_loss = _effect_int(effect, "lose_gold")
        updated_run_state = replace(run_state, gold=max(0, run_state.gold - gold_loss))
        return _result(
            updated_run_state,
            _complete_event_room(room_state, payload, result=result, result_text=result_text),
        )
    return _result(
        run_state,
        _complete_event_room(room_state, payload, result=result, result_text=result_text),
    )
