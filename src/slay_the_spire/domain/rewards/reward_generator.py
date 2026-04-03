from __future__ import annotations

from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort
from slay_the_spire.shared.rng import rng_for_room

_COMMON_RARITY = "common"
_UNCOMMON_RARITY = "uncommon"
_RARE_RARITY = "rare"
_COMBAT_ROOM_TYPE = "combat"
_ELITE_ROOM_TYPE = "elite"
_BOSS_ROOM_TYPE = "boss"
_SUPPORTED_ROOM_TYPES = frozenset(
    {_COMBAT_ROOM_TYPE, _ELITE_ROOM_TYPE, _BOSS_ROOM_TYPE}
)
_FALLBACK_RELIC_ID = "circlet"


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


def _rarity_weights(
    offset: int, room_type: str = _COMBAT_ROOM_TYPE
) -> tuple[int, int, int]:
    normalized_room_type = _normalize_room_type(room_type)
    if normalized_room_type == _ELITE_ROOM_TYPE:
        base_common = 50
        base_uncommon = 40
        base_rare = 10
    else:
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


def _roll_rarity(*, rng, rare_offset: int, room_type: str = _COMBAT_ROOM_TYPE) -> str:
    common_weight, uncommon_weight, rare_weight = _rarity_weights(
        rare_offset, room_type=room_type
    )
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
        available = [
            card_id
            for card_id in cards_by_rarity[rarity]
            if card_id not in taken_card_ids
        ]
        if not available:
            continue
        return rng.choice(available), rarity
    raise ValueError("reward card pool must contain at least one available card")


def _combat_gold_reward(*, room_type: str, seed: int, room_id: str) -> int:
    rng = rng_for_room(seed=seed, room_id=room_id, category="reward:gold")
    if room_type == _ELITE_ROOM_TYPE:
        return rng.randint(25, 35)
    if room_type == _BOSS_ROOM_TYPE:
        return rng.randint(95, 105)
    return rng.randint(10, 20)


def _next_relic_from_sequence(
    *, run_state: RunState, pool_id: str, excluded_relic_ids: set[str] | None = None
) -> str | None:
    sequence = run_state.relic_sequences.get(pool_id, [])
    position = run_state.relic_sequence_positions.get(pool_id, 0)
    excluded = excluded_relic_ids or set()
    while position < len(sequence):
        relic_id = sequence[position]
        position += 1
        run_state.relic_sequence_positions[pool_id] = position
        if relic_id not in run_state.relics and relic_id not in excluded:
            return relic_id
    run_state.relic_sequence_positions[pool_id] = position
    return None


def _roll_standard_relic_rarity(*, seed: int, room_id: str) -> str:
    rng = rng_for_room(seed=seed, room_id=room_id, category="reward:elite_relic_rarity")
    roll = rng.randint(1, 100)
    if roll <= 3:
        return _RARE_RARITY
    if roll <= 40:
        return _UNCOMMON_RARITY
    return _COMMON_RARITY


def _elite_relic_reward(
    *,
    run_state: RunState,
    registry: ContentProviderPort,
    seed: int,
    room_id: str,
) -> str | None:
    del registry
    rolled_rarity = _roll_standard_relic_rarity(seed=seed, room_id=room_id)
    relic_id = None
    for rarity in _fallback_rarity_order(rolled_rarity):
        relic_id = _next_relic_from_sequence(run_state=run_state, pool_id=rarity)
        if relic_id is not None:
            break
    return f"relic:{relic_id or _FALLBACK_RELIC_ID}"


def _card_offer_count(*, run_state: RunState, room_type: str) -> int:
    count = 3
    if "question_card" in run_state.relics:
        count += 1
    if room_type == _COMBAT_ROOM_TYPE and "prayer_wheel" in run_state.relics:
        count += 1
    if "busted_crown" in run_state.relics:
        count -= 2
    return max(1, count)


def _potion_reward(
    *, run_state: RunState, registry: ContentProviderPort, room_id: str
) -> str | None:
    if "sozu" in run_state.relics or "white_beast_statue" not in run_state.relics:
        return None
    potion_ids = [potion.id for potion in registry.potions().all()]
    if not potion_ids:
        return None
    rng = rng_for_room(seed=run_state.seed, room_id=room_id, category="reward:potion")
    return f"potion:{rng.choice(potion_ids)}"


def generate_combat_rewards(
    *,
    room_id: str,
    run_state: RunState,
    registry: ContentProviderPort,
    room_type: str = _COMBAT_ROOM_TYPE,
) -> tuple[list[str], int]:
    normalized_room_type = _normalize_room_type(room_type)
    normalized_seed = _require_seed(run_state.seed)
    gold_amount = _combat_gold_reward(
        room_type=normalized_room_type, seed=normalized_seed, room_id=room_id
    )
    rng = rng_for_room(seed=normalized_seed, room_id=room_id, category="reward:card")
    cards_by_rarity = _rewardable_cards_by_rarity(
        run_state=run_state, registry=registry
    )

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
        if "black_star" in run_state.relics:
            extra_elite_relic_reward = _elite_relic_reward(
                run_state=run_state,
                registry=registry,
                seed=normalized_seed,
                room_id=f"{room_id}:black_star",
            )
            if extra_elite_relic_reward is not None:
                rewards.append(extra_elite_relic_reward)
    taken_card_ids: set[str] = set()
    next_rare_offset = run_state.rare_card_reward_offset
    for _ in range(
        _card_offer_count(run_state=run_state, room_type=normalized_room_type)
    ):
        rolled_rarity = (
            _RARE_RARITY
            if normalized_room_type == _BOSS_ROOM_TYPE
            else _roll_rarity(
                rng=rng, rare_offset=next_rare_offset, room_type=normalized_room_type
            )
        )
        card_id, actual_rarity = _sample_card_offer(
            rolled_rarity=rolled_rarity,
            cards_by_rarity=cards_by_rarity,
            taken_card_ids=taken_card_ids,
            rng=rng,
        )
        taken_card_ids.add(card_id)
        rewards.append(f"card_offer:{card_id}")
        if normalized_room_type == _BOSS_ROOM_TYPE:
            next_rare_offset = -5
        elif actual_rarity == _COMMON_RARITY:
            next_rare_offset = min(next_rare_offset + 1, 40)
        elif actual_rarity == _RARE_RARITY:
            next_rare_offset = -5
    if normalized_room_type != _BOSS_ROOM_TYPE:
        potion_reward = _potion_reward(
            run_state=run_state,
            registry=registry,
            room_id=room_id,
        )
        if potion_reward is not None:
            rewards.append(potion_reward)
    return rewards, next_rare_offset


def generate_boss_rewards(
    *,
    room_id: str,
    seed: int,
    run_state: RunState,
    registry: ContentProviderPort,
) -> dict[str, object]:
    _room_hash(room_id)
    _require_seed(seed)
    del registry
    boss_pool: list[str] = []
    while len(boss_pool) < 3:
        relic_id = _next_relic_from_sequence(
            run_state=run_state,
            pool_id="boss",
            excluded_relic_ids=set(boss_pool),
        )
        if relic_id is None:
            relic_id = _FALLBACK_RELIC_ID
        boss_pool.append(relic_id)
    return {
        "generated_by": "boss_reward_generator",
        "boss_relic_offers": boss_pool,
        "claimed_relic_id": None,
    }
