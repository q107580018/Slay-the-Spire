from __future__ import annotations

import json
from pathlib import Path

import pytest

from slay_the_spire.content.loaders import load_json_file
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.content.registries import CardRegistry, ContentCatalog, EnemyRegistry


def test_registry_rejects_duplicate_ids() -> None:
    registry = CardRegistry()
    registry.register({"id": "strike", "name": "Strike", "cost": 1, "effects": []})

    with pytest.raises(ValueError, match="duplicate"):
        registry.register({"id": "strike", "name": "Strike", "cost": 1, "effects": []})


def test_enemy_registry_rejects_missing_move_table() -> None:
    registry = EnemyRegistry()

    with pytest.raises(ValueError, match="move_table"):
        registry.register({"id": "jaw_worm", "name": "Jaw Worm", "hp": 16})


def test_json_loader_reads_raw_json(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    payload = {"cards": [{"id": "strike", "cost": 1, "effects": []}]}
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert load_json_file(path) == payload


def test_starter_catalog_passes_startup_integrity() -> None:
    catalog = ContentCatalog.from_content_root(Path(__file__).resolve().parents[2] / "content")

    catalog.validate_startup_integrity()
    assert catalog.cards.get("strike").name == "Strike"
    assert catalog.enemies.get("jaw_worm").id == "jaw_worm"
    assert catalog.relics.get("burning_blood").name == "Burning Blood"
    assert catalog.events.get("shining_light").id == "shining_light"
    assert catalog.acts.get("act1").id == "act1"


def test_provider_exposes_registry_accessors() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")

    assert provider.cards().get("bash").name == "Bash"
    assert provider.enemies().get("slime").name == "Green Slime"
    assert provider.relics().get("burning_blood").id == "burning_blood"
    assert provider.events().get("shining_light").text.startswith("A glowing")
    assert provider.acts().get("act1").enemy_pool_id == "act1_basic"
