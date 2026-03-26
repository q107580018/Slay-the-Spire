from __future__ import annotations

SHARED_INSPECT_ROOT_ACTIONS: dict[str, tuple[str, str, str]] = {
    "inspect_stats": ("inspect_stats", "stats", "角色状态"),
    "inspect_deck": ("inspect_deck", "deck", "牌组列表"),
    "inspect_relics": ("inspect_relics", "relics", "遗物列表"),
    "inspect_potions": ("inspect_potions", "potions", "药水列表"),
}

COMBAT_INSPECT_ROOT_ACTIONS: dict[str, tuple[str, str, str]] = {
    "inspect_hand": ("inspect_hand", "hand", "手牌列表"),
    "inspect_draw_pile": ("inspect_draw_pile", "draw_pile", "抽牌堆列表"),
    "inspect_discard_pile": ("inspect_discard_pile", "discard_pile", "弃牌堆列表"),
    "inspect_exhaust_pile": ("inspect_exhaust_pile", "exhaust_pile", "消耗堆列表"),
    "inspect_enemies": ("inspect_enemy_list", "enemies", "敌人列表"),
}

INSPECT_LEAF_TITLES: dict[str, str] = {
    "inspect_stats": "角色状态",
    "inspect_relics": "遗物列表",
    "inspect_potions": "药水列表",
}

COMBAT_INSPECT_CARD_LIST_MODES = frozenset(
    {
        "inspect_hand",
        "inspect_draw_pile",
        "inspect_discard_pile",
        "inspect_exhaust_pile",
    }
)


def inspect_leaf_title(mode: str) -> str | None:
    return INSPECT_LEAF_TITLES.get(mode)
