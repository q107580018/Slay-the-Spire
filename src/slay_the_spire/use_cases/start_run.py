from __future__ import annotations

from slay_the_spire.content.registries import CharacterDef
from slay_the_spire.domain.map.map_generator import generate_act_state
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.ports.content_provider import ContentProviderPort


def _load_character_def(character_id: str, registry: ContentProviderPort) -> CharacterDef:
    catalog = getattr(registry, "_catalog", None)
    if catalog is None or not hasattr(catalog, "characters"):
        raise TypeError("registry must expose starter character content")
    characters = getattr(catalog, "characters")
    return characters.get(character_id)


def _ensure_act_loaded(character_id: str, registry: ContentProviderPort, seed: int) -> None:
    character = _load_character_def(character_id, registry)
    generate_act_state(character.starting_act_id, seed=seed, registry=registry)


def start_new_run(character_id: str, seed: int, registry: ContentProviderPort) -> RunState:
    character = _load_character_def(character_id, registry)
    _ensure_act_loaded(character_id, registry, seed)
    return RunState(seed=seed, character_id=character.id, current_act_id=character.starting_act_id)
