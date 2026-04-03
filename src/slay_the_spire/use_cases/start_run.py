from __future__ import annotations

from random import Random

from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort

_RELIC_SEQUENCE_POOL_IDS = ("common", "uncommon", "rare", "shop", "boss")
_REWARDABLE_RELIC_STATUSES = {"implemented", "partial"}


def _build_card_instance_ids(card_ids: list[str]) -> list[str]:
    return [f"{card_id}#{index}" for index, card_id in enumerate(card_ids, start=1)]


def _ensure_act_loaded(character, registry: ContentProviderPort, seed: int) -> None:
    generate_act_state(character.starting_act_id, seed=seed, registry=registry)


def _is_rewardable_relic(*, relic, character_id: str, pool_id: str) -> bool:
    if pool_id not in relic.pools:
        return False
    if relic.implementation_status not in _REWARDABLE_RELIC_STATUSES:
        return False
    return not relic.owner_character_ids or character_id in relic.owner_character_ids


def _build_relic_sequences(
    *, character_id: str, seed: int, registry: ContentProviderPort
) -> tuple[dict[str, list[str]], dict[str, int]]:
    sequences: dict[str, list[str]] = {}
    for pool_id in _RELIC_SEQUENCE_POOL_IDS:
        relic_ids = sorted(
            relic.id
            for relic in registry.relics().all()
            if _is_rewardable_relic(
                relic=relic,
                character_id=character_id,
                pool_id=pool_id,
            )
        )
        Random(f"{seed}:{character_id}:{pool_id}").shuffle(relic_ids)
        sequences[pool_id] = relic_ids
    return sequences, {pool_id: 0 for pool_id in _RELIC_SEQUENCE_POOL_IDS}


def start_new_run(
    character_id: str, seed: int, registry: ContentProviderPort
) -> RunState:
    character = registry.characters().get(character_id)
    _ensure_act_loaded(character, registry, seed)
    relic_sequences, relic_sequence_positions = _build_relic_sequences(
        character_id=character.id,
        seed=seed,
        registry=registry,
    )
    return RunState(
        seed=seed,
        character_id=character.id,
        current_act_id=character.starting_act_id,
        current_hp=80,
        max_hp=80,
        gold=99,
        deck=_build_card_instance_ids(list(character.starter_deck)),
        relics=list(character.starter_relic_ids),
        potions=[],
        card_removal_count=0,
        relic_sequences=relic_sequences,
        relic_sequence_positions=relic_sequence_positions,
    )
