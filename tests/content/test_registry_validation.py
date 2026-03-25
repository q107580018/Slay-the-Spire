from __future__ import annotations

import json
from pathlib import Path

import pytest

from slay_the_spire.content.catalog import ContentCatalog
from slay_the_spire.content.loaders import load_json_file
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.content.registries import CardRegistry, EnemyRegistry


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


def test_provider_exposes_registry_accessors() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")

    assert provider.characters().get("ironclad").name == "铁甲战士"
    assert provider.cards().get("bash").name == "重击"
    assert provider.enemies().get("slime").name == "绿史莱姆"
    assert provider.relics().get("burning_blood").id == "burning_blood"
    assert provider.events().get("shining_light").text.startswith("发光的牧师")
    assert provider.acts().get("act1").enemy_pool_id == "act1_basic"


def test_starter_catalog_passes_startup_integrity() -> None:
    catalog = ContentCatalog.from_content_root(Path(__file__).resolve().parents[2] / "content")

    assert catalog.cards.get("strike").name == "打击"
    assert catalog.enemies.get("jaw_worm").id == "jaw_worm"
    assert catalog.relics.get("burning_blood").name == "燃烧之血"
    assert catalog.events.get("shining_light").id == "shining_light"
    assert catalog.acts.get("act1").id == "act1"


def test_content_catalog_loads_potion_pools() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")

    assert provider.potions().all()


def test_act_registry_accepts_map_config_instead_of_static_nodes() -> None:
    provider = StarterContentProvider(Path(__file__).resolve().parents[2] / "content")
    act = provider.acts().get("act1")

    assert act.map_config.floor_count == 13
    assert act.map_config.starting_columns == 1
    assert act.map_config.boss_room_type == "boss"
    assert act.map_config.room_rules["min_floor_for_shop"] == 2
