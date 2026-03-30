from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil

from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort


@dataclass(slots=True, frozen=True)
class RestActionResult:
    run_state: RunState
    room_state: RoomState
    message: str | None = None


def _result(run_state: RunState, room_state: RoomState, message: str | None = None) -> RestActionResult:
    return RestActionResult(run_state=run_state, room_state=room_state, message=message)


def _upgrade_options(run_state: RunState, registry: ContentProviderPort) -> list[str]:
    options: list[str] = []
    for card_instance_id in run_state.deck:
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        if card_def.upgrades_to is not None:
            options.append(card_instance_id)
    return options


def rest_action(
    *,
    run_state: RunState,
    room_state: RoomState,
    action_id: str,
    registry: ContentProviderPort,
) -> RestActionResult:
    if room_state.room_type != "rest":
        raise ValueError("rest_action requires a rest room")

    payload = dict(room_state.payload)
    if room_state.stage == "select_upgrade_card":
        if action_id == "cancel":
            payload.pop("upgrade_options", None)
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
        payload.pop("upgrade_options", None)
        return _result(
            replace(run_state, deck=updated_deck),
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

    if action_id == "rest":
        if "coffee_dripper" in run_state.relics:
            return _result(run_state, room_state, "该动作被遗物效果禁用。")
        heal_amount = ceil(run_state.max_hp * 0.3)
        healed_hp = min(run_state.max_hp, run_state.current_hp + heal_amount)
        return _result(
            replace(run_state, current_hp=healed_hp),
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
    if action_id == "smith":
        if "fusion_hammer" in run_state.relics:
            return _result(run_state, room_state, "该动作被遗物效果禁用。")
        options = _upgrade_options(run_state, registry)
        if not options:
            return _result(run_state, room_state)
        payload["upgrade_options"] = options
        return _result(
            run_state,
            RoomState(
                schema_version=room_state.schema_version,
                room_id=room_state.room_id,
                room_type=room_state.room_type,
                stage="select_upgrade_card",
                payload=payload,
                is_resolved=False,
                rewards=list(room_state.rewards),
            ),
        )
    return _result(run_state, room_state)
