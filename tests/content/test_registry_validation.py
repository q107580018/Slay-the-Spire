from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from slay_the_spire.content.catalog import ContentCatalog
from slay_the_spire.content.loaders import load_json_file
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.content.registries import CardRegistry, EncounterRegistry, EnemyRegistry


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
    assert provider.cards().get("bloodletting").name == "放血"
    assert provider.cards().get("true_grit").name == "坚毅"
    assert provider.cards().get("shrug_it_off").name == "耸肩无视"
    assert provider.cards().get("armaments").name == "武装"
    assert provider.cards().get("terror").name == "恐怖"
    assert provider.cards().get("inflame").name == "燃烧"
    assert provider.cards().get("metallicize").name == "金属化"
    assert provider.cards().get("combust").name == "燃烧躯体"
    assert provider.cards().get("terror").cost == 1
    assert provider.cards().get("terror").rarity == "uncommon"
    assert provider.cards().get("terror").effects == [{"type": "vulnerable", "stacks": 2}]
    assert provider.cards().get("terror_plus").cost == 1
    assert provider.cards().get("terror_plus").rarity == "uncommon"
    assert provider.cards().get("terror_plus").effects == [{"type": "vulnerable", "stacks": 3}]
    assert provider.enemies().get("slime").name == "绿史莱姆"
    assert provider.enemies().get("acid_slime").name == "酸液史莱姆"
    assert provider.enemies().get("hexaghost").name == "六火幽魂"
    assert provider.cards().get("burn").playable is False
    assert provider.cards().get("burn").can_appear_in_shop is False
    assert provider.relics().get("burning_blood").id == "burning_blood"
    assert provider.events().get("shining_light").text.startswith("一道圣洁的光")
    assert provider.acts().get("act1").boss_pool_id == "act1_bosses"


@pytest.mark.parametrize("content_root", _content_roots())
def test_cards_define_rarity_and_upgrades_keep_base_rarity(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)
    allowed_rarities = {"basic", "common", "uncommon", "rare", "curse", "special"}
    allowed_card_types = {"attack", "skill", "power", "status", "curse"}
    allowed_acquisition_tags = {"starter", "combat_reward", "shop", "event", "generated", "status", "curse"}

    for card_def in provider.cards().all():
        assert card_def.rarity in allowed_rarities
        assert card_def.card_type in allowed_card_types
        assert set(card_def.acquisition_tags).issubset(allowed_acquisition_tags)
        if card_def.upgrades_to is not None:
            upgraded = provider.cards().get(card_def.upgrades_to)
            assert upgraded.rarity == card_def.rarity

    assert provider.cards().get("burn").rarity == "special"
    assert provider.cards().get("burn").card_type == "status"
    assert provider.cards().get("burn").acquisition_tags == ["generated", "status"]
    assert provider.cards().get("doubt").rarity == "curse"
    assert provider.cards().get("doubt").card_type == "curse"
    assert provider.cards().get("doubt").acquisition_tags == ["event", "curse"]
    assert provider.cards().get("injury").rarity == "curse"
    assert provider.cards().get("injury").card_type == "curse"
    assert provider.cards().get("injury").acquisition_tags == ["event", "curse"]


@pytest.mark.parametrize("content_root", _content_roots())
def test_registry_loads_act2_definition(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)
    act = provider.acts().get("act2")

    assert act.name == "第二幕"
    assert act.event_pool_id == "act2_events"


@pytest.mark.parametrize("content_root", _content_roots())
def test_registry_loads_extended_act_map_schema(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    act1 = provider.acts().get("act1")
    act2 = provider.acts().get("act2")

    assert act1.map_config.floor_count == 16
    assert act1.map_config.fixed_floor_room_types == {
        1: "combat",
        9: "treasure",
        15: "rest",
        16: "boss",
    }
    assert act1.map_config.post_boss_room_type == "boss_chest"
    assert act2.map_config.floor_count == 16
    assert act2.map_config.fixed_floor_room_types == {
        1: "combat",
        9: "treasure",
        15: "rest",
        16: "boss",
    }
    assert act2.map_config.post_boss_room_type == "boss_chest"


@pytest.mark.parametrize("content_root", _content_roots())
def test_boss_relic_catalog_exposes_act1_boss_relic_details(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    black_blood = provider.relics().get("black_blood")
    ectoplasm = provider.relics().get("ectoplasm")
    coffee_dripper = provider.relics().get("coffee_dripper")
    fusion_hammer = provider.relics().get("fusion_hammer")

    assert black_blood.name == "黑色之血"
    assert black_blood.summary == "战斗结束后回复 12 点生命"
    assert black_blood.description == "取代燃烧之血，战斗结束后回复 12 点生命。"
    assert black_blood.replaces_relic_id == "burning_blood"
    assert black_blood.disabled_actions == []
    assert black_blood.blocks_gold_gain is False
    assert black_blood.trigger_hooks == ["on_combat_end"]
    assert black_blood.passive_effects == [{"type": "heal", "amount": 12}]
    assert ectoplasm.name == "虚空质"
    assert ectoplasm.blocks_gold_gain is True
    assert ectoplasm.disabled_actions == ["gain_gold"]
    assert ectoplasm.replaces_relic_id is None
    assert coffee_dripper.name == "咖啡滴滤器"
    assert coffee_dripper.disabled_actions == ["rest_heal"]
    assert coffee_dripper.blocks_gold_gain is False
    assert fusion_hammer.name == "融合之锤"
    assert fusion_hammer.summary == "升级后不再能在休息点锻造卡牌"
    assert fusion_hammer.disabled_actions == ["smith"]
    assert fusion_hammer.blocks_gold_gain is False


@pytest.mark.parametrize("content_root", _content_roots())
def test_boss_relics_do_not_appear_in_shop_pool(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    assert provider.relics().get("black_blood").can_appear_in_shop is False
    assert provider.relics().get("ectoplasm").can_appear_in_shop is False
    assert provider.relics().get("coffee_dripper").can_appear_in_shop is False
    assert provider.relics().get("fusion_hammer").can_appear_in_shop is False


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
def test_provider_exposes_enemy_pool_entry_weights(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    entries = provider.enemy_pool_entries("act1_basic")

    assert entries
    assert all(entry.member_id for entry in entries)
    assert all(entry.weight > 0 for entry in entries)


@pytest.mark.parametrize("content_root", _content_roots())
def test_content_provider_loads_encounter_pool_entries(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    entries = provider.encounter_pool_entries("act1_basic")

    assert any(entry.member_id == "double_slime" for entry in entries)
    assert provider.encounters().get("double_slime").enemy_ids == ["slime", "slime"]


def test_encounter_registry_rejects_empty_enemy_ids() -> None:
    registry = EncounterRegistry()

    with pytest.raises(ValueError, match="enemy_ids must not be empty"):
        registry.register({"id": "empty_room", "name": "空房间", "enemy_ids": []})


@pytest.mark.parametrize("content_root", _content_roots())
def test_catalog_rejects_missing_encounter_pool_referenced_by_act(content_root: Path, tmp_path: Path) -> None:
    copied_root = tmp_path / content_root.name
    shutil.copytree(content_root, copied_root)
    (copied_root / "encounters" / "act1_basic.json").unlink()

    with pytest.raises(ValueError, match="enemy_pool_id must reference a loaded encounter pool"):
        ContentCatalog.from_content_root(copied_root)


@pytest.mark.parametrize("content_root", _content_roots())
def test_catalog_rejects_missing_encounter_pool_referenced_by_non_starting_act(content_root: Path, tmp_path: Path) -> None:
    copied_root = tmp_path / content_root.name
    shutil.copytree(content_root, copied_root)
    acts_path = copied_root / "acts" / "act1_map.json"
    payload = load_json_file(acts_path)
    act_records = payload["acts"]
    act_records.append(
        {
            **act_records[0],
            "id": "act_extra_validation",
            "name": "额外校验幕",
            "boss_pool_id": "act_extra_missing_bosses",
            "next_act_id": None,
        }
    )
    acts_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="boss_pool_id must reference a loaded encounter pool"):
        ContentCatalog.from_content_root(copied_root)


@pytest.mark.parametrize("content_root", _content_roots())
def test_catalog_rejects_duplicate_fixed_floor_keys_after_normalization(content_root: Path, tmp_path: Path) -> None:
    copied_root = tmp_path / content_root.name
    shutil.copytree(content_root, copied_root)
    acts_path = copied_root / "acts" / "act1_map.json"
    payload = load_json_file(acts_path)
    payload["acts"][0]["map_config"]["fixed_floor_room_types"] = {
        "1": "combat",
        "01": "event",
    }
    acts_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate normalized key"):
        ContentCatalog.from_content_root(copied_root)


@pytest.mark.parametrize("content_root", _content_roots())
def test_catalog_rejects_fixed_floor_room_types_out_of_range(content_root: Path, tmp_path: Path) -> None:
    copied_root = tmp_path / content_root.name
    shutil.copytree(content_root, copied_root)
    acts_path = copied_root / "acts" / "act1_map.json"
    payload = load_json_file(acts_path)
    payload["acts"][0]["map_config"]["fixed_floor_room_types"]["17"] = "boss"
    acts_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="must be between 1 and floor_count"):
        ContentCatalog.from_content_root(copied_root)


@pytest.mark.parametrize("content_root", _content_roots())
def test_provider_exposes_event_pool_entry_metadata(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    entries = provider.event_pool_entries("act1_events")

    assert entries
    assert all(entry.member_id for entry in entries)
    assert all(entry.weight > 0 for entry in entries)


@pytest.mark.parametrize("content_root", _content_roots())
def test_act2_event_pool_contains_multiple_distinct_events(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)
    event_ids = {entry.member_id for entry in provider.event_pool_entries("act2_events")}

    assert {"ancient_writing", "masked_bandits", "forgotten_altar"}.issubset(event_ids)


@pytest.mark.parametrize("content_root", _content_roots())
def test_act_registry_accepts_map_config_instead_of_static_nodes(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)
    act = provider.acts().get("act1")

    assert act.map_config.floor_count == 16
    assert act.map_config.starting_columns == 1
    assert act.map_config.boss_room_type == "boss"
    assert act.map_config.fixed_floor_room_types[9] == "treasure"
    assert act.map_config.post_boss_room_type == "boss_chest"
    assert act.map_config.room_rules["min_floor_for_shop"] == 2
