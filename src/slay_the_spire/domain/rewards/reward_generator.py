from __future__ import annotations

from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.rng import rng_for_room

_BOSS_RELIC_OFFERS = ("black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer")
_COMMON_RARITY = "common"
_UNCOMMON_RARITY = "uncommon"
_RARE_RARITY = "rare"


def _room_hash(room_id: str) -> int:
    if not isinstance(room_id, str):
        raise TypeError("room_id must be a string")
    if not room_id:
        raise ValueError("room_id must not be empty")
    return sum(ord(ch) for ch in room_id)


def _require_seed(seed: object) -> int:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an int")
    return seed


def _rewardable_cards_by_rarity(
    *,
    run_state: RunState,
    registry: ContentProviderPort,
) -> dict[str, list[str]]:
    del run_state
    cards_by_rarity = {
        _COMMON_RARITY: [],
        _UNCOMMON_RARITY: [],
        _RARE_RARITY: [],
    }
    for card in registry.cards().all():
        if card.rarity not in cards_by_rarity:
            continue
        cards_by_rarity[card.rarity].append(card.id)
    return cards_by_rarity


def _rarity_weights(offset: int) -> tuple[int, int, int]:
    base_common = 60
    base_uncommon = 37
    base_rare = 3
    if offset <= 0:
        rare = base_rare + offset
        uncommon = base_uncommon
        if rare < 0:
            uncommon += rare
            rare = 0
        common = 100 - rare - uncommon
        return common, uncommon, rare

    common = base_common - offset
    uncommon = base_uncommon
    if common < 0:
        uncommon += common
        common = 0
    rare = 100 - common - uncommon
    return common, uncommon, rare


def _roll_rarity(*, rng, rare_offset: int) -> str:
    common_weight, uncommon_weight, rare_weight = _rarity_weights(rare_offset)
    roll = rng.randint(1, common_weight + uncommon_weight + rare_weight)
    if roll <= rare_weight:
        return _RARE_RARITY
    if roll <= rare_weight + uncommon_weight:
        return _UNCOMMON_RARITY
    return _COMMON_RARITY


def _fallback_rarity_order(target_rarity: str) -> tuple[str, ...]:
    if target_rarity == _RARE_RARITY:
        return (_RARE_RARITY, _UNCOMMON_RARITY, _COMMON_RARITY)
    if target_rarity == _UNCOMMON_RARITY:
        return (_UNCOMMON_RARITY, _COMMON_RARITY, _RARE_RARITY)
    return (_COMMON_RARITY, _UNCOMMON_RARITY, _RARE_RARITY)


def _sample_card_offer(
    *,
    rolled_rarity: str,
    cards_by_rarity: dict[str, list[str]],
    taken_card_ids: set[str],
    rng,
) -> tuple[str, str]:
    for rarity in _fallback_rarity_order(rolled_rarity):
        available = [card_id for card_id in cards_by_rarity[rarity] if card_id not in taken_card_ids]
        if not available:
            continue
        return rng.choice(available), rarity
    raise ValueError("reward card pool must contain at least one available card")


def generate_combat_rewards(
    *,
    room_id: str,
    run_state: RunState,
    registry: ContentProviderPort,
) -> tuple[list[str], int]:
    normalized_seed = _require_seed(run_state.seed)
    gold_amount = 10 + (normalized_seed % 10)
    rng = rng_for_room(seed=normalized_seed, room_id=room_id, category="reward:card")
    cards_by_rarity = _rewardable_cards_by_rarity(run_state=run_state, registry=registry)

    rewards = [f"gold:{gold_amount}"]
    taken_card_ids: set[str] = set()
    next_rare_offset = run_state.rare_card_reward_offset
    for _ in range(3):
        rolled_rarity = _roll_rarity(rng=rng, rare_offset=next_rare_offset)
        card_id, actual_rarity = _sample_card_offer(
            rolled_rarity=rolled_rarity,
            cards_by_rarity=cards_by_rarity,
            taken_card_ids=taken_card_ids,
            rng=rng,
        )
        taken_card_ids.add(card_id)
        rewards.append(f"card_offer:{card_id}")
        if actual_rarity == _COMMON_RARITY:
            next_rare_offset = min(next_rare_offset + 1, 40)
        elif actual_rarity == _RARE_RARITY:
            next_rare_offset = -5
    return rewards, next_rare_offset


def generate_boss_rewards(
    *,
    room_id: str,
    seed: int,
    run_state: RunState,
    registry: ContentProviderPort,
) -> dict[str, object]:
    _room_hash(room_id)
    normalized_seed = _require_seed(seed)
    available_relic_ids = {relic.id for relic in registry.relics().all()}
    boss_pool = [
        relic_id
        for relic_id in _BOSS_RELIC_OFFERS
        if relic_id in available_relic_ids and relic_id not in run_state.relics
    ]
    rng = rng_for_room(seed=normalized_seed, room_id=room_id, category="reward:boss")
    rng.shuffle(boss_pool)
    return {
        "generated_by": "boss_reward_generator",
        "gold_reward": 90 + (normalized_seed % 21),
        "claimed_gold": False,
        "boss_relic_offers": boss_pool[:3],
        "claimed_relic_id": None,
    }
