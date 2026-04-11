from __future__ import annotations

from dataclasses import dataclass


RewardPayloadValue = str | int | bool


@dataclass(slots=True, frozen=True)
class RewardAction:
    kind: str
    payload: dict[str, RewardPayloadValue]


def _noop_action(reward_id: str) -> RewardAction:
    return RewardAction(kind="noop", payload={"original_reward_id": reward_id})


def _parse_payload_int(value: str) -> int | None:
    if not value:
        return None
    if value.startswith("-"):
        digits = value[1:]
        if not digits.isdigit():
            return None
        return int(value)
    if not value.isdigit():
        return None
    return int(value)


def _parse_card_target_action(
    kind: str, payload_text: str, reward_id: str
) -> RewardAction:
    if not payload_text:
        return _noop_action(reward_id)
    parts = payload_text.split(":")
    if len(parts) > 2:
        return _noop_action(reward_id)
    card_instance_id = parts[0]
    if not card_instance_id or card_instance_id.count("#") != 1:
        return _noop_action(reward_id)
    payload: dict[str, RewardPayloadValue] = {"card_instance_id": card_instance_id}
    if len(parts) == 2:
        target_card_id = parts[1]
        if not target_card_id:
            return _noop_action(reward_id)
        payload["target_card_id"] = target_card_id
    return RewardAction(kind=kind, payload=payload)


def parse_reward_action(reward_id: str) -> RewardAction:
    if not isinstance(reward_id, str) or not reward_id:
        return _noop_action(str(reward_id))

    if reward_id == "skip":
        return RewardAction(kind="skip", payload={})

    if ":" not in reward_id:
        return _noop_action(reward_id)

    prefix, payload_text = reward_id.split(":", 1)
    if prefix == "gold":
        amount = _parse_payload_int(payload_text)
        if amount is None:
            return _noop_action(reward_id)
        return RewardAction(kind="gold", payload={"amount": amount})
    if prefix == "relic" and payload_text:
        return RewardAction(kind="relic", payload={"relic_id": payload_text})
    if prefix == "potion" and payload_text:
        return RewardAction(kind="potion", payload={"potion_id": payload_text})
    if prefix == "card" and payload_text:
        return RewardAction(kind="card", payload={"card_id": payload_text})
    if prefix == "card_offer" and payload_text:
        return RewardAction(kind="card_offer", payload={"card_id": payload_text})
    if prefix == "event" and payload_text:
        return RewardAction(kind="event", payload={"event_id": payload_text})
    if prefix == "remove":
        return _parse_card_target_action("remove", payload_text, reward_id)
    if prefix == "upgrade":
        return _parse_card_target_action("upgrade", payload_text, reward_id)
    if prefix == "transform":
        return _parse_card_target_action("transform", payload_text, reward_id)
    if prefix == "duplicate":
        return _parse_card_target_action("duplicate", payload_text, reward_id)
    if prefix == "skip":
        payload: dict[str, RewardPayloadValue] = {}
        if payload_text:
            payload["detail"] = payload_text
        return RewardAction(kind="skip", payload=payload)
    return _noop_action(reward_id)
