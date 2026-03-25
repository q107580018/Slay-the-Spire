from __future__ import annotations

from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort


def _build_card_instance_ids(card_ids: list[str]) -> list[str]:
    return [f"{card_id}#{index}" for index, card_id in enumerate(card_ids, start=1)]


def _ensure_act_loaded(character, registry: ContentProviderPort, seed: int) -> None:
    generate_act_state(character.starting_act_id, seed=seed, registry=registry)


def start_new_run(character_id: str, seed: int, registry: ContentProviderPort) -> RunState:
    character = registry.characters().get(character_id)
    _ensure_act_loaded(character, registry, seed)
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
    )
