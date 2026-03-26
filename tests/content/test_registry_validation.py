from __future__ import annotations

import json
from pathlib import Path

import pytest

from slay_the_spire.content.catalog import ContentCatalog
from slay_the_spire.content.loaders import load_json_file
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.content.registries import CardRegistry, EnemyRegistry


def _content_roots() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[2]
    return (root / "content", root / "src" / "slay_the_spire" / "data" / "content")


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


@pytest.mark.parametrize("content_root", _content_roots())
def test_provider_exposes_registry_accessors(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    assert provider.characters().get("ironclad").name == "铁甲战士"
    assert provider.cards().get("bash").name == "重击"
    assert provider.enemies().get("slime").name == "绿史莱姆"
    assert provider.enemies().get("hexaghost").name == "六火幽魂"
    assert provider.cards().get("burn").playable is False
    assert provider.cards().get("burn").can_appear_in_shop is False
    assert provider.relics().get("burning_blood").id == "burning_blood"
    assert provider.events().get("shining_light").text.startswith("一道圣洁的光")
    assert provider.acts().get("act1").boss_pool_id == "act1_bosses"


@pytest.mark.parametrize("content_root", _content_roots())
def test_starter_catalog_passes_startup_integrity(content_root: Path) -> None:
    catalog = ContentCatalog.from_content_root(content_root)

    assert catalog.cards.get("strike").name == "打击"
    assert catalog.enemies.get("jaw_worm").id == "jaw_worm"
    assert catalog.relics.get("burning_blood").name == "燃烧之血"
    assert catalog.events.get("shining_light").id == "shining_light"
    assert catalog.events.get("the_cleric").id == "the_cleric"
    assert catalog.events.get("world_of_goop").id == "world_of_goop"
    assert catalog.events.get("living_wall").id == "living_wall"
    assert catalog.events.get("big_fish").id == "big_fish"
    assert catalog.events.get("golden_shrine").id == "golden_shrine"
    assert catalog.events.get("golden_idol").id == "golden_idol"
    assert catalog.events.get("the_ssssserpent").id == "the_ssssserpent"
    assert catalog.cards.get("doubt").id == "doubt"
    assert catalog.cards.get("injury").id == "injury"
    assert catalog.relics.get("golden_idol").id == "golden_idol"
    assert catalog.acts.get("act1").id == "act1"


@pytest.mark.parametrize("content_root", _content_roots())
def test_content_catalog_loads_potion_pools(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    assert provider.potions().all()


@pytest.mark.parametrize("content_root", _content_roots())
def test_act_registry_accepts_map_config_instead_of_static_nodes(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)
    act = provider.acts().get("act1")

    assert act.map_config.floor_count == 13
    assert act.map_config.starting_columns == 1
    assert act.map_config.boss_room_type == "boss"
    assert act.map_config.room_rules["min_floor_for_shop"] == 2
