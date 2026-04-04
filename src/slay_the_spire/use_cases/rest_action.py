from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil

from slay_the_spire.domain.models.cards import card_id_from_instance_id
from slay_the_spire.domain.models.room_state import RoomState
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.rewards.reward_generator import generate_combat_rewards
from slay_the_spire.ports.content_provider import ContentProviderPort


@dataclass(slots=True, frozen=True)
class RestActionResult:
    run_state: RunState
    room_state: RoomState
    message: str | None = None


def _result(
    run_state: RunState, room_state: RoomState, message: str | None = None
) -> RestActionResult:
    return RestActionResult(run_state=run_state, room_state=room_state, message=message)


def _upgrade_options(run_state: RunState, registry: ContentProviderPort) -> list[str]:
    options: list[str] = []
    for card_instance_id in run_state.deck:
        card_def = registry.cards().get(card_id_from_instance_id(card_instance_id))
        if card_def.upgrades_to is not None:
            options.append(card_instance_id)
    return options


def _remove_one_card(run_state: RunState) -> RunState:
    if not run_state.deck:
        return run_state
    return replace(run_state, deck=list(run_state.deck[1:]))


def _remove_selected_card(run_state: RunState, selected_card: str) -> RunState:
    return replace(
        run_state,
        deck=[card for card in run_state.deck if card != selected_card],
    )


def _next_rest_relic_reward(run_state: RunState) -> str:
    rarity_pool_order = ["common", "uncommon", "rare"]
    for pool_id in rarity_pool_order:
        sequence = run_state.relic_sequences.get(pool_id, [])
        position = run_state.relic_sequence_positions.get(pool_id, 0)
        while position < len(sequence):
            relic_id = sequence[position]
            position += 1
            run_state.relic_sequence_positions[pool_id] = position
            if relic_id not in run_state.relics:
                return f"relic:{relic_id}"
        run_state.relic_sequence_positions[pool_id] = position
    return "relic:circlet"


def _rest_heal_amount(run_state: RunState) -> int:
    heal_amount = ceil(run_state.max_hp * 0.3)
    if "regal_pillow" in run_state.relics:
        heal_amount += 15
    if "eternal_feather" in run_state.relics:
        heal_amount += (len(run_state.deck) // 5) * 3
    return heal_amount


def _action_allowed(room_state: RoomState, action_id: str) -> bool:
    actions = room_state.payload.get("actions")
    return isinstance(actions, list) and action_id in actions


def _has_required_rest_relic(run_state: RunState, action_id: str) -> bool:
    required_relic_by_action = {
        "lift": "girya",
        "digestion": "peace_pipe",
        "dig": "shovel",
    }
    required_relic = required_relic_by_action.get(action_id)
    return required_relic is not None and required_relic in run_state.relics


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
        selected_card = action_id.removeprefix("remove_card:")
        options = payload.get("remove_candidates")
        if not isinstance(options, list) or selected_card not in options:
            return _result(run_state, room_state)
        payload.pop("remove_candidates", None)
        return _result(
            _remove_selected_card(run_state, selected_card),
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
        updated_deck = [
            upgraded_instance_id if card == selected_card else card
            for card in run_state.deck
        ]
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
        heal_amount = _rest_heal_amount(run_state)
        healed_hp = min(run_state.max_hp, run_state.current_hp + heal_amount)
        updated_run_state = replace(run_state, current_hp=healed_hp)
        rewards = list(room_state.rewards)
        if "dream_catcher" in run_state.relics:
            dream_rewards, _next_rare_offset = generate_combat_rewards(
                room_id=f"{room_state.room_id}:dream_catcher",
                run_state=updated_run_state,
                registry=registry,
            )
            rewards.extend(
                reward for reward in dream_rewards if reward.startswith("card_offer:")
            )
        return _result(
            updated_run_state,
            RoomState(
                schema_version=room_state.schema_version,
                room_id=room_state.room_id,
                room_type=room_state.room_type,
                stage="completed",
                payload=payload,
                is_resolved=True,
                rewards=rewards,
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
    if action_id == "lift":
        if not _action_allowed(room_state, action_id) or not _has_required_rest_relic(
            run_state, action_id
        ):
            return _result(run_state, room_state)
        current_lifts = run_state.relic_sequence_positions.get("girya_lifts", 0)
        if current_lifts >= 3:
            return _result(run_state, room_state, "该动作已达到次数上限。")
        updated_positions = dict(run_state.relic_sequence_positions)
        updated_positions["girya_lifts"] = current_lifts + 1
        return _result(
            replace(run_state, relic_sequence_positions=updated_positions),
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
    if action_id == "digestion":
        if not _action_allowed(room_state, action_id) or not _has_required_rest_relic(
            run_state, action_id
        ):
            return _result(run_state, room_state)
        if not run_state.deck:
            return _result(run_state, room_state)
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
    if action_id == "dig":
        if not _action_allowed(room_state, action_id) or not _has_required_rest_relic(
            run_state, action_id
        ):
            return _result(run_state, room_state)
        rewards = [*room_state.rewards, _next_rest_relic_reward(run_state)]
        return _result(
            run_state,
            RoomState(
                schema_version=room_state.schema_version,
                room_id=room_state.room_id,
                room_type=room_state.room_type,
                stage="completed",
                payload=payload,
                is_resolved=True,
                rewards=rewards,
            ),
        )
    return _result(run_state, room_state)
