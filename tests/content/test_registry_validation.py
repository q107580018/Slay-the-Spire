from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from slay_the_spire.content.catalog import ContentCatalog
from slay_the_spire.content.loaders import load_json_file
from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.content.registries import (
    CardRegistry,
    EncounterRegistry,
    EnemyRegistry,
    RelicRegistry,
)


def _content_roots() -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[2]
    return (root / "content",)


def test_registry_rejects_duplicate_ids() -> None:
    registry = CardRegistry()
    registry.register({"id": "strike", "name": "Strike", "cost": 1, "effects": []})

    with pytest.raises(ValueError, match="duplicate"):
        registry.register({"id": "strike", "name": "Strike", "cost": 1, "effects": []})


def test_enemy_registry_rejects_missing_move_table() -> None:
    registry = EnemyRegistry()

    with pytest.raises(ValueError, match="move_table"):
        registry.register({"id": "jaw_worm", "name": "Jaw Worm", "hp": 16})


def test_card_registry_parses_ethereal_flag() -> None:
    registry = CardRegistry()

    card = registry.register(
        {
            "id": "ghostly_armor",
            "name": "幽魂护甲",
            "cost": 1,
            "rarity": "uncommon",
            "card_type": "skill",
            "ethereal": True,
            "effects": [{"type": "block", "amount": 10}],
        }
    )

    assert card.ethereal is True


def test_card_registry_defaults_ethereal_to_false() -> None:
    registry = CardRegistry()

    card = registry.register(
        {"id": "strike", "name": "Strike", "cost": 1, "effects": []}
    )

    assert card.ethereal is False


def test_card_registry_parses_extended_red_card_fields() -> None:
    registry = CardRegistry()

    card = registry.register(
        {
            "id": "sentinel",
            "name": "哨卫",
            "cost": 1,
            "rarity": "uncommon",
            "effects": [{"type": "block", "amount": 5}],
            "on_exhaust_effects": [{"type": "gain_energy", "amount": 2}],
            "play_condition": "all_attacks_in_hand",
            "cost_reducer": "times_hit_this_combat",
            "innate": True,
        }
    )

    assert card.on_exhaust_effects == [{"type": "gain_energy", "amount": 2}]
    assert card.play_condition == "all_attacks_in_hand"
    assert card.cost_reducer == "times_hit_this_combat"
    assert card.innate is True


def test_card_registry_defaults_extended_fields() -> None:
    registry = CardRegistry()

    card = registry.register(
        {"id": "strike", "name": "Strike", "cost": 1, "effects": []}
    )

    assert card.on_exhaust_effects == []
    assert card.play_condition is None
    assert card.cost_reducer is None
    assert card.innate is False


def test_card_registry_rejects_invalid_play_condition() -> None:
    registry = CardRegistry()

    with pytest.raises(ValueError, match="play_condition"):
        registry.register(
            {
                "id": "sentinel",
                "name": "哨卫",
                "cost": 1,
                "effects": [],
                "play_condition": "anything_goes",
            }
        )


def test_card_registry_rejects_invalid_cost_reducer() -> None:
    registry = CardRegistry()

    with pytest.raises(ValueError, match="cost_reducer"):
        registry.register(
            {
                "id": "clash",
                "name": "交锋",
                "cost": 0,
                "effects": [],
                "cost_reducer": "any_reducer",
            }
        )


def test_card_registry_rejects_invalid_innate_type() -> None:
    registry = CardRegistry()

    with pytest.raises(TypeError, match="innate"):
        registry.register(
            {
                "id": "sentinel",
                "name": "哨卫",
                "cost": 1,
                "effects": [],
                "innate": "yes",
            }
        )


def test_card_registry_rejects_invalid_on_exhaust_effects_type() -> None:
    registry = CardRegistry()

    with pytest.raises(TypeError, match="on_exhaust_effects"):
        registry.register(
            {
                "id": "sentinel",
                "name": "哨卫",
                "cost": 1,
                "effects": [],
                "on_exhaust_effects": "gain_energy",
            }
        )


def test_card_registry_rejects_invalid_on_exhaust_effects_item_shape() -> None:
    registry = CardRegistry()

    with pytest.raises(TypeError, match="on_exhaust_effects item"):
        registry.register(
            {
                "id": "sentinel",
                "name": "哨卫",
                "cost": 1,
                "effects": [],
                "on_exhaust_effects": ["gain_energy"],
            }
        )


def test_json_loader_reads_raw_json(tmp_path: Path) -> None:
    path = tmp_path / "payload.json"
    payload = {"cards": [{"id": "strike", "cost": 1, "effects": []}]}
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert load_json_file(path) == payload


@pytest.mark.parametrize("content_root", _content_roots())
def test_provider_exposes_registry_accessors(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    assert provider.characters().get("ironclad").name == "铁甲战士"
    assert provider.cards().get("bash").name == "痛击"
    assert provider.cards().get("bloodletting").name == "放血"
    assert provider.cards().get("true_grit").name == "坚毅"
    assert provider.cards().get("shrug_it_off").name == "耸肩无视"
    assert provider.cards().get("armaments").name == "武装"
    assert provider.cards().get("terror").name == "恐怖"
    assert provider.cards().get("inflame").name == "燃烧"
    assert provider.cards().get("metallicize").name == "金属化"
    assert provider.cards().get("combust").name == "自燃"
    assert provider.cards().get("battle_trance").name == "战斗专注"
    assert provider.cards().get("battle_trance_plus").name == "战斗专注+"
    assert provider.cards().get("offering").name == "祭品"
    assert provider.cards().get("offering_plus").name == "祭品+"
    assert provider.cards().get("impervious").name == "岿然不动"
    assert provider.cards().get("impervious_plus").name == "岿然不动+"
    assert provider.cards().get("clothesline").name == "金刚臂"
    assert provider.cards().get("thunderclap").name == "闪电霹雳"
    assert provider.cards().get("uppercut").name == "上勾拳"
    assert provider.cards().get("flame_barrier").name == "火焰屏障"
    assert provider.cards().get("ghostly_armor").name == "幽灵铠甲"
    assert provider.cards().get("ghostly_armor").ethereal is True
    assert provider.cards().get("disarm").name == "缴械"
    assert provider.cards().get("entrench").name == "巩固"
    assert provider.cards().get("barricade").name == "壁垒"
    assert provider.cards().get("demon_form").name == "恶魔形态"
    assert provider.cards().get("dropkick").effects == [
        {"type": "dropkick_effect", "amount": 5},
    ]
    assert provider.cards().get("dropkick_plus").effects == [
        {"type": "dropkick_effect", "amount": 8},
    ]
    assert provider.cards().get("berserk").effects == [
        {"type": "vulnerable", "stacks": 2, "target_instance_id": "self"},
        {"type": "add_power", "power_id": "berserk", "amount": 1},
    ]
    assert provider.cards().get("berserk_plus").effects == [
        {"type": "vulnerable", "stacks": 1, "target_instance_id": "self"},
        {"type": "add_power", "power_id": "berserk", "amount": 1},
    ]
    assert provider.cards().get("offering").exhausts is True
    assert provider.cards().get("offering_plus").exhausts is True
    assert provider.cards().get("impervious").rarity == "rare"
    assert provider.cards().get("impervious").exhausts is True
    assert provider.cards().get("impervious_plus").rarity == "rare"
    assert provider.cards().get("impervious_plus").exhausts is True
    assert provider.cards().get("terror").cost == 1
    assert provider.cards().get("terror").rarity == "uncommon"
    assert provider.cards().get("terror").effects == [
        {"type": "vulnerable", "stacks": 2}
    ]
    assert provider.cards().get("terror_plus").cost == 1
    assert provider.cards().get("terror_plus").rarity == "uncommon"
    assert provider.cards().get("terror_plus").effects == [
        {"type": "vulnerable", "stacks": 3}
    ]
    assert provider.enemies().get("slime").name == "绿史莱姆"
    assert provider.enemies().get("acid_slime").name == "酸液史莱姆"
    assert provider.enemies().get("jaw_worm").hp == 40
    assert provider.enemies().get("cultist").name == "邪教徒"
    assert provider.enemies().get("red_louse").name == "红色虱子"
    assert provider.enemies().get("green_louse").name == "绿色虱子"
    assert provider.enemies().get("sentry").name == "哨卫"
    assert provider.enemies().get("looter").name == "劫掠者"
    assert provider.enemies().get("fungi_beast").name == "真菌兽"
    assert provider.enemies().get("fat_gremlin").name == "肥胖地精"
    assert provider.enemies().get("gremlin_wizard").name == "地精法师"
    assert provider.enemies().get("hexaghost").name == "六火幽魂"
    assert provider.cards().get("burn").playable is False
    assert provider.cards().get("burn").acquisition_tags == ["generated", "status"]
    assert provider.potions().get("fire_potion").timing == "in_combat"
    assert provider.potions().get("fire_potion").target == "enemy"
    assert provider.potions().get("block_potion").target == "self"
    assert provider.potions().get("strength_potion").target == "self"
    assert provider.relics().get("burning_blood").id == "burning_blood"
    assert provider.relics().get("frozen_eye").name == "冰冻之眼"
    assert provider.events().get("shining_light").text.startswith("一道圣洁的光")
    assert provider.acts().get("act1").boss_pool_id == "act1_bosses"


@pytest.mark.parametrize("content_root", _content_roots())
def test_cards_define_rarity_and_upgrades_keep_base_rarity(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)
    allowed_rarities = {"basic", "common", "uncommon", "rare", "curse", "special"}
    allowed_card_types = {"attack", "skill", "power", "status", "curse"}
    allowed_acquisition_tags = {
        "starter",
        "combat_reward",
        "shop",
        "event",
        "generated",
        "status",
        "curse",
    }

    for card_def in provider.cards().all():
        assert card_def.rarity in allowed_rarities
        assert card_def.card_type in allowed_card_types
        assert set(card_def.acquisition_tags).issubset(allowed_acquisition_tags)
        assert not hasattr(card_def, "can_appear_in_shop")
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
def test_shop_eligible_cards_are_marked_with_shop_tags(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    shop_card_ids = {
        card.id for card in provider.cards().all() if "shop" in card.acquisition_tags
    }

    assert {
        "anger",
        "pommel_strike",
        "shrug_it_off",
        "whirlwind",
        "twin_strike",
        "inflame",
        "metallicize",
        "combust",
        "battle_trance",
        "offering",
        "impervious",
    }.issubset(shop_card_ids)
    assert "doubt" not in shop_card_ids
    assert "injury" not in shop_card_ids
    assert "burn" not in shop_card_ids


@pytest.mark.parametrize("content_root", _content_roots())
def test_searing_blow_upgrade_chain_uses_sts_damage_formula(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    expected_damages = [12, 16, 21, 27, 34, 42, 51, 61, 72, 84, 97, 111, 126]
    card_id = "searing_blow"

    for index, expected_damage in enumerate(expected_damages):
        card_def = provider.cards().get(card_id)
        assert card_def.name == "灼热攻击" + "+" * index
        assert card_def.effects == [{"type": "damage", "amount": expected_damage}]
        if index < len(expected_damages) - 1:
            assert card_def.upgrades_to is not None
            card_id = card_def.upgrades_to
        else:
            assert card_def.upgrades_to is None


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
    assert fusion_hammer.summary == "每回合开始时获得 1 点能量，休息点不能锻造卡牌"
    assert fusion_hammer.disabled_actions == ["smith"]
    assert fusion_hammer.blocks_gold_gain is False


@pytest.mark.parametrize("content_root", _content_roots())
def test_boss_relics_do_not_appear_in_shop_pool(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    assert provider.relics().get("black_blood").can_appear_in_shop is False
    assert provider.relics().get("ectoplasm").can_appear_in_shop is False
    assert provider.relics().get("coffee_dripper").can_appear_in_shop is False
    assert provider.relics().get("fusion_hammer").can_appear_in_shop is False
    assert provider.relics().get("circlet").can_appear_in_shop is False


@pytest.mark.parametrize(
    ("missing_field", "expected_error"),
    [
        ("rarity", "rarity"),
        ("pools", "pools"),
        ("source_tags", "source_tags"),
        ("owner_character_ids", "owner_character_ids"),
        ("implementation_status", "implementation_status"),
        ("effect_blueprint", "effect_blueprint"),
    ],
)
def test_relic_registry_requires_extended_metadata_fields(
    missing_field: str, expected_error: str
) -> None:
    registry = RelicRegistry()
    payload = {
        "id": "burning_blood",
        "name": "燃烧之血",
        "trigger_hooks": ["on_combat_end"],
        "passive_effects": [{"type": "heal", "amount": 6}],
        "rarity": "starter",
        "pools": ["starter"],
        "source_tags": ["starting_relic"],
        "owner_character_ids": ["ironclad"],
        "implementation_status": "implemented",
        "effect_blueprint": [],
    }
    payload.pop(missing_field)

    with pytest.raises((TypeError, ValueError), match=expected_error):
        registry.register(payload)


def test_relic_registry_rejects_invalid_metadata_enums() -> None:
    registry = RelicRegistry()
    base_payload = {
        "id": "base_relic",
        "name": "坏遗物",
        "trigger_hooks": [],
        "passive_effects": [],
        "pools": ["special"],
        "source_tags": ["test"],
        "owner_character_ids": [],
        "effect_blueprint": [],
    }

    with pytest.raises(ValueError, match="rarity"):
        registry.register(
            {
                **base_payload,
                "id": "bad_rarity",
                "rarity": "legendary",
                "implementation_status": "implemented",
            }
        )

    with pytest.raises(ValueError, match="implementation_status"):
        registry.register(
            {
                **base_payload,
                "id": "bad_status",
                "rarity": "special",
                "implementation_status": "done",
            }
        )


@pytest.mark.parametrize("content_root", _content_roots())
def test_loaded_relic_catalog_exposes_required_metadata(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)
    expected_metadata = {
        "burning_blood": {
            "rarity": "starter",
            "pools": ["starter"],
            "source_tags": ["starting_relic"],
            "owner_character_ids": ["ironclad"],
            "implementation_status": "implemented",
        },
        "blood_vial": {
            "rarity": "common",
            "pools": ["common", "neow"],
            "source_tags": ["standard_pool"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
        },
        "golden_idol": {
            "rarity": "event",
            "pools": ["event"],
            "source_tags": ["event_reward"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
        },
        "guarding_totem": {
            "rarity": "special",
            "pools": ["special"],
            "source_tags": ["special_reward"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
        },
        "circlet": {
            "rarity": "special",
            "pools": ["special"],
            "source_tags": ["fallback"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
        },
        "black_blood": {
            "rarity": "boss",
            "pools": ["boss"],
            "source_tags": ["boss_relic"],
            "owner_character_ids": ["ironclad"],
            "implementation_status": "implemented",
        },
        "ectoplasm": {
            "rarity": "boss",
            "pools": ["boss"],
            "source_tags": ["boss_relic"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
        },
        "coffee_dripper": {
            "rarity": "boss",
            "pools": ["boss"],
            "source_tags": ["boss_relic"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
        },
        "fusion_hammer": {
            "rarity": "boss",
            "pools": ["boss"],
            "source_tags": ["boss_relic"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
        },
        "frozen_eye": {
            "rarity": "shop",
            "pools": ["shop"],
            "source_tags": ["shop"],
            "owner_character_ids": [],
            "implementation_status": "implemented",
        },
    }

    relics = {relic.id: relic for relic in provider.relics().all()}

    assert set(expected_metadata).issubset(relics)

    for relic_id, expected in expected_metadata.items():
        relic = relics[relic_id]
        assert relic.rarity == expected["rarity"]
        assert relic.pools == expected["pools"]
        assert relic.source_tags == expected["source_tags"]
        assert relic.owner_character_ids == expected["owner_character_ids"]
        assert relic.implementation_status == expected["implementation_status"]
        assert relic.effect_blueprint == []


@pytest.mark.parametrize(
    (
        "relic_id",
        "expected_name",
        "expected_summary",
        "expected_description",
        "expected_rarity",
        "expected_pools",
        "expected_source_tags",
        "expected_owner_ids",
    ),
    [
        (
            "face_of_cleric",
            "牧师的脸",
            "每场战斗后你的最大生命值增加 1",
            "每场战斗后，你的最大生命值增加 1。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "gremlin_visage",
            "地精容貌",
            "每场战斗开始时，你拥有 1 层虚弱",
            "每场战斗开始时，你拥有 1 层虚弱。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "nloths_gift",
            "恩洛斯的礼物",
            "使你在怪物奖励中遇见稀有牌的几率变为 3 倍",
            "使你在怪物奖励中遇见稀有牌的几率变为 3 倍。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "ssserpent_head",
            "蛇的头",
            "每次进入？房间时获得 50 金币",
            "每次进入？房间时，获得 50 金币。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "warped_tongs",
            "弯曲铁钳",
            "在你的每个回合开始时，随机升级一张你的手牌（只影响本场战斗）",
            "在你的每个回合开始时，随机升级一张你的手牌（只影响本场战斗）。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "cloak_clasp",
            "斗篷扣",
            "在你的回合结束时，每有一张手牌获得 1 点格挡",
            "在你的回合结束时，每有一张手牌获得 1 点格挡。",
            "rare",
            ["rare", "neow"],
            ["standard_pool"],
            ["watcher"],
        ),
        (
            "damaru",
            "手摇鼓",
            "在你的回合开始时，获得 1 层真言",
            "在你的回合开始时，获得 1 层真言。",
            "common",
            ["common", "neow"],
            ["standard_pool"],
            ["watcher"],
        ),
        (
            "melange",
            "美琅脂",
            "你每次将抽牌堆洗牌时，预见 3",
            "你每次将抽牌堆洗牌时，预见 3。",
            "shop",
            ["shop"],
            ["shop"],
            ["watcher"],
        ),
        (
            "thread_and_needle",
            "针线",
            "在每场战斗开始时，获得 4 层多层护甲",
            "在每场战斗开始时，获得 4 层多层护甲。",
            "rare",
            ["rare", "neow"],
            ["standard_pool"],
            [],
        ),
        (
            "abacus",
            "算盘",
            "你每次将抽牌堆洗牌时，获得 6 点格挡",
            "你每次将抽牌堆洗牌时，获得 6 点格挡。",
            "shop",
            ["shop"],
            ["shop"],
            [],
        ),
        (
            "gambling_chip",
            "赌博筹码",
            "在每场战斗开始时，丢弃任意张牌，然后抽相同数量张牌",
            "在每场战斗开始时，丢弃任意张牌，然后抽相同数量张牌。",
            "rare",
            ["rare", "neow"],
            ["standard_pool"],
            [],
        ),
        (
            "shuriken",
            "手里剑",
            "你每在同一回合内打出 3 张攻击牌，获得 1 点力量",
            "你每在同一回合内打出 3 张攻击牌，获得 1 点力量。",
            "uncommon",
            ["uncommon", "neow"],
            ["standard_pool"],
            [],
        ),
        (
            "runic_capacitor",
            "符文电容器",
            "每场战斗开始时，获得 3 个额外充能球栏位",
            "每场战斗开始时，获得 3 个额外充能球栏位。",
            "shop",
            ["shop"],
            ["shop"],
            [],
        ),
        (
            "the_courier",
            "送货员",
            "商人的卡牌、遗物和药水不再会卖光，并且所有商品打折 20%",
            "商人的卡牌、遗物和药水不再会卖光，并且所有商品打折 20%。",
            "uncommon",
            ["uncommon", "neow"],
            ["standard_pool"],
            [],
        ),
        (
            "neows_lament",
            "涅奥的悲恸",
            "接下来 3 场战斗中的敌人将只有 1 点生命",
            "接下来 3 场战斗中的敌人将只有 1 点生命。",
            "event",
            ["event"],
            ["event_reward"],
            [],
        ),
        (
            "pocketwatch",
            "怀表",
            "若你在某个回合打出的牌少于等于 3 张，则在你的下个回合开始时额外抽 3 张牌",
            "若你在某个回合打出的牌少于等于 3 张，则在你的下个回合开始时额外抽 3 张牌。",
            "rare",
            ["rare", "neow"],
            ["standard_pool"],
            [],
        ),
        (
            "twisted_funnel",
            "扭曲漏斗",
            "在每场战斗开始时，给予所有敌人 4 层中毒",
            "在每场战斗开始时，给予所有敌人 4 层中毒。",
            "shop",
            ["shop"],
            ["shop"],
            ["silent"],
        ),
        (
            "ninja_scroll",
            "忍术卷轴",
            "每场战斗开始时，手牌中增加 3 张小刀",
            "每场战斗开始时，手牌中增加 3 张小刀。",
            "uncommon",
            ["uncommon", "neow"],
            ["standard_pool"],
            ["silent"],
        ),
    ],
)
@pytest.mark.parametrize("content_root", _content_roots())
def test_audited_relic_metadata_matches_local_reference(
    content_root: Path,
    relic_id: str,
    expected_name: str,
    expected_summary: str,
    expected_description: str,
    expected_rarity: str,
    expected_pools: list[str],
    expected_source_tags: list[str],
    expected_owner_ids: list[str],
) -> None:
    provider = StarterContentProvider(content_root)

    relic = provider.relics().get(relic_id)

    assert relic.name == expected_name
    assert relic.summary == expected_summary
    assert relic.description == expected_description
    assert relic.rarity == expected_rarity
    assert relic.pools == expected_pools
    assert relic.source_tags == expected_source_tags
    assert relic.owner_character_ids == expected_owner_ids


@pytest.mark.parametrize("content_root", _content_roots())
def test_missing_audited_relics_are_present(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    assert provider.relics().get("pocketwatch").name == "怀表"
    assert provider.relics().get("twisted_funnel").name == "扭曲漏斗"
    assert provider.relics().get("ninja_scroll").name == "忍术卷轴"


@pytest.mark.parametrize("content_root", _content_roots())
def test_relic_catalog_contains_full_base_game_relic_inventory(
    content_root: Path,
) -> None:
    provider = StarterContentProvider(content_root)

    relic_ids = {relic.id for relic in provider.relics().all()}
    base_game_relic_ids = relic_ids - {"guarding_totem"}

    assert len(base_game_relic_ids) == 179
    assert {
        "akabeko",
        "anchor",
        "bag_of_preparation",
        "oddly_smooth_stone",
        "bird_faced_urn",
        "burning_blood",
        "black_blood",
        "golden_idol",
        "circlet",
        "neows_lament",
        "prismatic_shard",
        "violet_lotus",
        "ring_of_the_serpent",
        "nilrys_codex",
        "pocketwatch",
        "twisted_funnel",
        "ninja_scroll",
    }.issubset(base_game_relic_ids)
    assert "guarding_totem" in relic_ids
    assert "guarding_totem" not in base_game_relic_ids
    assert "gremlin_mask" not in base_game_relic_ids
    assert "gremlin_horned_mask" not in base_game_relic_ids
    assert provider.relics().get("nilrys_codex").rarity == "event"
    assert provider.relics().get("nilrys_codex").pools == ["event"]


@pytest.mark.parametrize("content_root", _content_roots())
def test_all_relics_have_localized_summary_and_description(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    for relic in provider.relics().all():
        assert relic.name
        assert relic.summary
        assert relic.description
        assert relic.pools
        assert relic.effect_blueprint is not None


@pytest.mark.parametrize("content_root", _content_roots())
def test_starter_catalog_passes_startup_integrity(content_root: Path) -> None:
    catalog = ContentCatalog.from_content_root(content_root)

    assert catalog.cards.get("strike").name == "打击（红）"
    assert catalog.enemies.get("jaw_worm").id == "jaw_worm"
    assert catalog.relics.get("burning_blood").name == "燃烧之血"
    assert catalog.relics.get("circlet").name == "圆环"
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

    assert any(entry.member_id == "cultist" for entry in entries)
    assert any(entry.member_id == "single_slime" for entry in entries)
    assert any(entry.member_id == "single_red_louse" for entry in entries)
    assert any(entry.member_id == "gremlin_gang_no_wizard" for entry in entries)
    assert provider.encounters().get("double_slime").enemy_ids == ["slime", "slime"]
    assert provider.encounters().get("three_sentries").enemy_ids == [
        "sentry",
        "sentry",
        "sentry",
    ]
    cultist_entry = next(entry for entry in entries if entry.member_id == "cultist")
    assert cultist_entry.max_combat_count == 2
    late_slime_entry = next(
        entry for entry in entries if entry.member_id == "single_slime"
    )
    assert late_slime_entry.min_combat_count == 3


def test_encounter_registry_rejects_empty_enemy_ids() -> None:
    registry = EncounterRegistry()

    with pytest.raises(ValueError, match="enemy_ids must not be empty"):
        registry.register({"id": "empty_room", "name": "空房间", "enemy_ids": []})


@pytest.mark.parametrize("content_root", _content_roots())
def test_catalog_rejects_missing_encounter_pool_referenced_by_act(
    content_root: Path, tmp_path: Path
) -> None:
    copied_root = tmp_path / content_root.name
    shutil.copytree(content_root, copied_root)
    (copied_root / "encounters" / "act1_basic.json").unlink()

    with pytest.raises(
        ValueError, match="enemy_pool_id must reference a loaded encounter pool"
    ):
        ContentCatalog.from_content_root(copied_root)


@pytest.mark.parametrize("content_root", _content_roots())
def test_catalog_rejects_missing_encounter_pool_referenced_by_non_starting_act(
    content_root: Path, tmp_path: Path
) -> None:
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
    acts_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with pytest.raises(
        ValueError, match="boss_pool_id must reference a loaded encounter pool"
    ):
        ContentCatalog.from_content_root(copied_root)


@pytest.mark.parametrize("content_root", _content_roots())
def test_catalog_rejects_duplicate_fixed_floor_keys_after_normalization(
    content_root: Path, tmp_path: Path
) -> None:
    copied_root = tmp_path / content_root.name
    shutil.copytree(content_root, copied_root)
    acts_path = copied_root / "acts" / "act1_map.json"
    payload = load_json_file(acts_path)
    payload["acts"][0]["map_config"]["fixed_floor_room_types"] = {
        "1": "combat",
        "01": "event",
    }
    acts_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="duplicate normalized key"):
        ContentCatalog.from_content_root(copied_root)


@pytest.mark.parametrize("content_root", _content_roots())
def test_catalog_rejects_fixed_floor_room_types_out_of_range(
    content_root: Path, tmp_path: Path
) -> None:
    copied_root = tmp_path / content_root.name
    shutil.copytree(content_root, copied_root)
    acts_path = copied_root / "acts" / "act1_map.json"
    payload = load_json_file(acts_path)
    payload["acts"][0]["map_config"]["fixed_floor_room_types"]["17"] = "boss"
    acts_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

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
    event_ids = {
        entry.member_id for entry in provider.event_pool_entries("act2_events")
    }

    assert {"ancient_writing", "masked_bandits", "forgotten_altar"}.issubset(event_ids)


@pytest.mark.parametrize("content_root", _content_roots())
def test_act_registry_accepts_map_config_instead_of_static_nodes(
    content_root: Path,
) -> None:
    provider = StarterContentProvider(content_root)
    act = provider.acts().get("act1")

    assert act.map_config.floor_count == 16
    assert act.map_config.starting_columns == 1
    assert act.map_config.boss_room_type == "boss"
    assert act.map_config.fixed_floor_room_types[9] == "treasure"
    assert act.map_config.post_boss_room_type == "boss_chest"
    assert act.map_config.room_rules["min_floor_for_shop"] == 2


@pytest.mark.parametrize("content_root", _content_roots())
def test_provider_exposes_wound_and_dazed_status_cards(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    assert provider.cards().get("wound").card_type == "status"
    assert provider.cards().get("wound").playable is False
    assert provider.cards().get("dazed").card_type == "status"
    assert provider.cards().get("dazed").exhausts is True


@pytest.mark.parametrize("content_root", _content_roots())
def test_provider_exposes_shiv_card(content_root: Path) -> None:
    provider = StarterContentProvider(content_root)

    shiv = provider.cards().get("shiv")

    assert shiv.name == "小刀"
    assert shiv.card_type == "attack"
    assert shiv.cost == 0
    assert shiv.exhausts is True


@pytest.mark.parametrize(
    ("card_id", "expected_name"),
    [
        ("body_slam", "全身撞击"),
        ("clash", "交锋"),
        ("flex", "活动肌肉"),
        ("havoc", "破灭"),
        ("heavy_blade", "重刃"),
        ("iron_wave", "铁斩波"),
        ("perfected_strike", "完美打击"),
        ("warcry", "战吼"),
        ("wild_strike", "狂野打击"),
        ("blood_for_blood", "以血还血"),
        ("burning_pact", "燃烧契约"),
        ("carnage", "残杀"),
        ("dark_embrace", "黑暗之拥"),
        ("dropkick", "飞身踢"),
        ("dual_wield", "双持"),
        ("evolve", "进化"),
        ("feel_no_pain", "无惧疼痛"),
        ("fire_breathing", "火焰吐息"),
        ("infernal_blade", "地狱之刃"),
        ("intimidate", "威吓"),
        ("power_through", "硬撑"),
        ("rage", "狂怒"),
        ("rampage", "暴走"),
        ("reckless_charge", "无谋冲锋"),
        ("rupture", "撕裂"),
        ("searing_blow", "灼热攻击"),
        ("second_wind", "重振精神"),
        ("seeing_red", "盛怒"),
        ("sentinel", "哨卫"),
        ("sever_soul", "断魂斩"),
        ("spot_weakness", "观察弱点"),
        ("berserk", "狂暴"),
        ("shockwave", "震荡波"),
        ("bludgeon", "重锤"),
        ("brutality", "残暴"),
        ("double_tap", "双发"),
        ("exhume", "发掘"),
        ("feed", "狂宴"),
        ("fiend_fire", "恶魔之焰"),
        ("immolate", "燔祭"),
        ("juggernaut", "势不可当"),
        ("limit_break", "突破极限"),
        ("reaper", "死亡收割"),
        ("corruption", "腐化"),
    ],
)
def test_provider_loads_remaining_ironclad_cards(
    card_id: str, expected_name: str
) -> None:
    root = Path(__file__).resolve().parents[2] / "content"
    provider = StarterContentProvider(root)
    assert provider.cards().get(card_id).name == expected_name


@pytest.mark.parametrize("content_root", _content_roots())
def test_implementation_status_matches_code_behavior(content_root: Path) -> None:
    """Guard against status drift: relics marked 'implemented' must have real behavior."""
    provider = StarterContentProvider(content_root)

    # These relics have NO code behavior, NO hooks, NO effects — must NOT be 'implemented'
    must_not_be_implemented = [
        "akabeko",
        "ancient_tea_set",
        "bronze_scales",
        "meat_on_the_bone",
        "mercury_hourglass",
        "oddly_smooth_stone",
        "omamori",
        "orichalcum",
        "potion_belt",
        "abacus",
        "blue_candle",
        "bottled_flame",
        "bottled_lightning",
        "bottled_tornado",
        "darkstone_periapt",
        "frozen_egg_2",
        "gambling_chip",
    ]
    for relic_id in must_not_be_implemented:
        relic = provider.relics().get(relic_id)
        assert relic.implementation_status == "placeholder", (
            f"{relic_id} has no code behavior but is marked '{relic.implementation_status}'"
        )

    # These flavor-only relics have no gameplay effect — "no effect" IS the correct behavior
    flavor_only_implemented = [
        "spirit_poop",
        "cultist_headpiece",
    ]
    for relic_id in flavor_only_implemented:
        relic = provider.relics().get(relic_id)
        assert relic.implementation_status == "implemented", (
            f"{relic_id} is flavor-only (no effect is correct) but is marked '{relic.implementation_status}'"
        )

    # These relics have real code behavior and must stay 'implemented'
    must_be_implemented = [
        "burning_blood",  # on_combat_end hook with heal effect
        "blood_vial",  # on_combat_start hook with heal effect
        "guarding_totem",  # on_combat_start hook with block effect
        "black_blood",  # on_combat_end hook with heal effect
        "anchor",  # hardcoded in turn_flow.py
        "pen_nib",  # hardcoded in play_card.py
        "circlet",  # hardcoded in apply_reward.py
        "sozu",  # hardcoded in multiple use_cases
    ]
    for relic_id in must_be_implemented:
        relic = provider.relics().get(relic_id)
        assert relic.implementation_status == "implemented", (
            f"{relic_id} has real behavior but is marked '{relic.implementation_status}'"
        )
