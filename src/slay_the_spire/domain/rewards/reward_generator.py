from __future__ import annotations

from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.rng import rng_for_room

_BOSS_RELIC_OFFERS = ("black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer")
_ELITE_RELIC_OFFERS = ("blood_vial", "golden_idol", "guarding_totem")
_COMMON_RARITY = "common"
_UNCOMMON_RARITY = "uncommon"
_RARE_RARITY = "rare"
_COMBAT_ROOM_TYPE = "combat"
_ELITE_ROOM_TYPE = "elite"
_SUPPORTED_ROOM_TYPES = frozenset({_COMBAT_ROOM_TYPE, _ELITE_ROOM_TYPE})


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
        if "combat_reward" not in card.acquisition_tags:
            continue
        if card.rarity not in cards_by_rarity:
            continue
        cards_by_rarity[card.rarity].append(card.id)
    return cards_by_rarity


def _normalize_room_type(room_type: str) -> str:
    if room_type not in _SUPPORTED_ROOM_TYPES:
        raise ValueError(f"unsupported reward room_type: {room_type}")
    return room_type


def _rarity_weights(offset: int, room_type: str = _COMBAT_ROOM_TYPE) -> tuple[int, int, int]:
    normalized_room_type = _normalize_room_type(room_type)
    rare_bonus = 10 if normalized_room_type == _ELITE_ROOM_TYPE else 0
    base_common = 60 - rare_bonus
    base_uncommon = 37
    base_rare = 3 + rare_bonus
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


def _roll_rarity(*, rng, rare_offset: int, room_type: str = _COMBAT_ROOM_TYPE) -> str:
    common_weight, uncommon_weight, rare_weight = _rarity_weights(rare_offset, room_type=room_type)
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


def _combat_gold_reward(*, room_type: str, seed: int, room_id: str) -> int:
    rng = rng_for_room(seed=seed, room_id=room_id, category="reward:gold")
    if room_type == _ELITE_ROOM_TYPE:
        return rng.randint(25, 35)
    return rng.randint(10, 20)


def _elite_relic_reward(
    *,
    run_state: RunState,
    registry: ContentProviderPort,
    seed: int,
    room_id: str,
) -> str | None:
    available_relic_ids = {relic.id for relic in registry.relics().all()}
    candidate_ids = [
        relic_id
        for relic_id in _ELITE_RELIC_OFFERS
        if relic_id in available_relic_ids and relic_id not in run_state.relics
    ]
    if not candidate_ids:
        return None
    rng = rng_for_room(seed=seed, room_id=room_id, category="reward:elite_relic")
    return f"relic:{rng.choice(sorted(candidate_ids))}"


def generate_combat_rewards(
    *,
    room_id: str,
    run_state: RunState,
    registry: ContentProviderPort,
    room_type: str = _COMBAT_ROOM_TYPE,
) -> tuple[list[str], int]:
    normalized_room_type = _normalize_room_type(room_type)
    normalized_seed = _require_seed(run_state.seed)
    gold_amount = _combat_gold_reward(room_type=normalized_room_type, seed=normalized_seed, room_id=room_id)
    rng = rng_for_room(seed=normalized_seed, room_id=room_id, category="reward:card")
    cards_by_rarity = _rewardable_cards_by_rarity(run_state=run_state, registry=registry)

    rewards = [f"gold:{gold_amount}"]
    if normalized_room_type == _ELITE_ROOM_TYPE:
        elite_relic_reward = _elite_relic_reward(
            run_state=run_state,
            registry=registry,
            seed=normalized_seed,
            room_id=room_id,
        )
        if elite_relic_reward is not None:
            rewards.append(elite_relic_reward)
    taken_card_ids: set[str] = set()
    next_rare_offset = run_state.rare_card_reward_offset
    for _ in range(3):
        rolled_rarity = _roll_rarity(rng=rng, rare_offset=next_rare_offset, room_type=normalized_room_type)
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
