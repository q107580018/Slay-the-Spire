from __future__ import annotations

from slay_the_spire.domain.models.room_state import RoomState


def claim_reward(*, room_state: RoomState, reward_id: str) -> RoomState:
    if room_state.room_type != "reward":
        raise ValueError("claim_reward requires a reward room")
    claimed_reward_ids = room_state.payload.get("claimed_reward_ids")
    if claimed_reward_ids is not None:
        return room_state
    if reward_id not in room_state.rewards:
        raise ValueError(f"reward_id not found in room rewards: {reward_id}")
    payload = dict(room_state.payload)
    payload["claimed_reward_ids"] = [reward_id]
    payload["action_committed"] = True
    remaining_rewards = [reward for reward in room_state.rewards if reward != reward_id]
    return RoomState(
        schema_version=room_state.schema_version,
        room_id=room_state.room_id,
        room_type=room_state.room_type,
        stage="completed",
        payload=payload,
        is_resolved=True,
        rewards=remaining_rewards,
    )
