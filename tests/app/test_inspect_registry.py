from slay_the_spire.app.inspect_registry import (
    COMBAT_INSPECT_ROOT_ACTIONS,
    COMBAT_INSPECT_CARD_LIST_MODES,
    SHARED_INSPECT_ROOT_ACTIONS,
    inspect_leaf_title,
)


def test_inspect_registry_exposes_shared_and_combat_root_targets() -> None:
    assert SHARED_INSPECT_ROOT_ACTIONS["inspect_deck"] == ("inspect_deck", "deck", "牌组列表")
    assert SHARED_INSPECT_ROOT_ACTIONS["inspect_potions"] == ("inspect_potions", "potions", "药水列表")
    assert COMBAT_INSPECT_ROOT_ACTIONS["inspect_hand"] == ("inspect_hand", "hand", "手牌列表")
    assert COMBAT_INSPECT_ROOT_ACTIONS["inspect_enemies"] == ("inspect_enemy_list", "enemies", "敌人列表")


def test_inspect_registry_exposes_leaf_titles_and_card_list_modes() -> None:
    assert inspect_leaf_title("inspect_stats") == "角色状态"
    assert inspect_leaf_title("inspect_relics") == "遗物列表"
    assert inspect_leaf_title("inspect_potions") == "药水列表"
    assert inspect_leaf_title("inspect_root") is None
    assert COMBAT_INSPECT_CARD_LIST_MODES == {
        "inspect_hand",
        "inspect_draw_pile",
        "inspect_discard_pile",
        "inspect_exhaust_pile",
    }
