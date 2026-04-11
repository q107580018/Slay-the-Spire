from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.rewards import reward_generator as reward_generator_module
from slay_the_spire.domain.rewards.reward_generator import _rarity_weights
from slay_the_spire.domain.rewards.reward_generator import (
    generate_boss_rewards,
    generate_combat_rewards,
)
from slay_the_spire.use_cases.apply_reward import apply_reward


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def _run_state() -> RunState:
    return RunState(
        seed=7,
        character_id="ironclad",
        current_act_id="act1",
        current_hp=80,
        max_hp=80,
        gold=99,
        deck=[
            "strike#1",
            "strike#2",
            "strike#3",
            "strike#4",
            "defend#5",
            "defend#6",
            "defend#7",
            "defend#8",
            "bash#9",
        ],
        relics=["burning_blood"],
        potions=[],
        card_removal_count=0,
    )


@pytest.mark.guardrail
def test_apply_reward_adds_gold_to_run_state() -> None:
    updated = apply_reward(
        run_state=_run_state(), reward_id="gold:11", registry=_content_provider()
    )

    assert updated.gold == 110


def test_apply_reward_gold_is_blocked_by_ectoplasm() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "ectoplasm"])

    updated = apply_reward(
        run_state=run_state, reward_id="gold:11", registry=_content_provider()
    )

    assert updated.gold == run_state.gold


def test_apply_reward_adds_real_card_instance_to_run_state() -> None:
    updated = apply_reward(
        run_state=_run_state(), reward_id="card:anger", registry=_content_provider()
    )

    assert updated.deck[-1] == "anger#10"


def test_apply_reward_allows_repeated_circlet_rewards() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "circlet"])

    updated = apply_reward(
        run_state=run_state, reward_id="relic:circlet", registry=_content_provider()
    )

    assert updated.relics == ["burning_blood", "circlet", "circlet"]


def test_apply_reward_replaces_existing_relic_when_replaces_relic_id_matches() -> None:
    run_state = replace(_run_state(), relics=["ring_of_the_snake"])

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:ring_of_the_serpent",
        registry=_content_provider(),
    )

    assert updated.relics == ["ring_of_the_serpent"]


def test_apply_reward_keeps_other_relics_when_replacing_starting_relic() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "golden_idol"])

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:black_blood",
        registry=_content_provider(),
    )

    assert updated.relics == ["golden_idol", "black_blood"]


def test_apply_reward_preserves_card_id_with_underscores() -> None:
    updated = apply_reward(
        run_state=_run_state(),
        reward_id="card:pommel_strike",
        registry=_content_provider(),
    )

    assert updated.deck[-1] == "pommel_strike#10"


@pytest.mark.guardrail
def test_apply_reward_accepts_card_offer_reward_ids() -> None:
    updated = apply_reward(
        run_state=_run_state(),
        reward_id="card_offer:anger",
        registry=_content_provider(),
    )

    assert updated.deck[-1] == "anger#10"


def test_apply_reward_card_offer_grants_ceramic_fish_gold_bonus() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "ceramic_fish"])

    updated = apply_reward(
        run_state=run_state,
        reward_id="card_offer:anger",
        registry=_content_provider(),
    )

    assert updated.deck[-1] == "anger#10"
    assert updated.gold == run_state.gold + 9


def test_apply_reward_card_offer_ceramic_fish_bonus_is_blocked_by_ectoplasm() -> None:
    run_state = replace(
        _run_state(),
        relics=["burning_blood", "ceramic_fish", "ectoplasm"],
    )

    updated = apply_reward(
        run_state=run_state,
        reward_id="card_offer:anger",
        registry=_content_provider(),
    )

    assert updated.deck[-1] == "anger#10"
    assert updated.gold == run_state.gold


def test_apply_reward_gold_uses_golden_idol_bonus() -> None:
    run_state = _run_state()
    run_state = RunState(
        seed=run_state.seed,
        character_id=run_state.character_id,
        current_act_id=run_state.current_act_id,
        current_hp=run_state.current_hp,
        max_hp=run_state.max_hp,
        gold=run_state.gold,
        deck=list(run_state.deck),
        relics=[*run_state.relics, "golden_idol"],
        potions=list(run_state.potions),
        card_removal_count=run_state.card_removal_count,
    )

    updated = apply_reward(
        run_state=run_state, reward_id="gold:100", registry=_content_provider()
    )

    assert updated.gold == 224


@pytest.mark.guardrail
def test_generate_boss_rewards_returns_three_unique_relics() -> None:
    run_state = replace(
        _run_state(),
        relic_sequences={
            "boss": ["astrolabe", "black_star", "busted_crown", "coffee_dripper"],
        },
        relic_sequence_positions={"boss": 0},
    )
    rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=run_state,
        registry=_content_provider(),
    )

    assert rewards["generated_by"] == "boss_reward_generator"
    assert rewards["boss_relic_offers"] == ["astrolabe", "black_star", "busted_crown"]
    assert rewards["claimed_relic_id"] is None
    assert run_state.relic_sequence_positions["boss"] == 3


def test_generate_boss_rewards_can_offer_fusion_hammer_across_seeds() -> None:
    run_state = replace(
        _run_state(),
        relic_sequences={"boss": ["fusion_hammer", "astrolabe", "black_star"]},
        relic_sequence_positions={"boss": 0},
    )

    rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=1,
        run_state=run_state,
        registry=_content_provider(),
    )

    assert rewards["boss_relic_offers"] == ["fusion_hammer", "astrolabe", "black_star"]


def test_generate_boss_rewards_is_deterministic_for_same_inputs() -> None:
    first_run_state = replace(
        _run_state(),
        relics=["burning_blood", "black_star"],
        relic_sequences={
            "boss": ["black_star", "coffee_dripper", "ectoplasm", "fusion_hammer"],
        },
        relic_sequence_positions={"boss": 0},
    )
    second_run_state = replace(
        _run_state(),
        relics=["burning_blood", "black_star"],
        relic_sequences={
            "boss": ["black_star", "coffee_dripper", "ectoplasm", "fusion_hammer"],
        },
        relic_sequence_positions={"boss": 0},
    )

    first = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=first_run_state,
        registry=_content_provider(),
    )
    second = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=second_run_state,
        registry=_content_provider(),
    )

    assert first["boss_relic_offers"] == second["boss_relic_offers"]


@pytest.mark.guardrail
def test_generate_combat_rewards_returns_gold_and_three_unique_card_offers() -> None:
    rewards, next_rare_offset = generate_combat_rewards(
        room_id="act1:hallway_reward",
        run_state=_run_state(),
        registry=_content_provider(),
    )

    assert rewards[0].startswith("gold:")
    card_rewards = [reward for reward in rewards if reward.startswith("card_offer:")]
    assert len(card_rewards) == 3
    assert len(set(card_rewards)) == 3
    assert isinstance(next_rare_offset, int)


def test_question_card_adds_one_more_card_reward_offer() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "question_card"])

    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:question_card_reward",
        run_state=run_state,
        registry=_content_provider(),
    )

    card_rewards = [reward for reward in rewards if reward.startswith("card_offer:")]

    assert len(card_rewards) == 4
    assert len(set(card_rewards)) == 4


def test_white_beast_statue_adds_potion_reward_after_combat() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "white_beast_statue"])

    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:white_beast_reward",
        run_state=run_state,
        registry=_content_provider(),
    )

    potion_rewards = [reward for reward in rewards if reward.startswith("potion:")]

    assert len(potion_rewards) == 1
    assert potion_rewards[0] != "potion:circlet"


def test_prayer_wheel_adds_one_more_card_reward_offer_for_normal_combat() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "prayer_wheel"])

    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:prayer_wheel_reward",
        run_state=run_state,
        registry=_content_provider(),
    )

    assert len([reward for reward in rewards if reward.startswith("card_offer:")]) == 4


def test_sozu_blocks_white_beast_statue_potion_reward() -> None:
    run_state = replace(
        _run_state(), relics=["burning_blood", "white_beast_statue", "sozu"]
    )

    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:sozu_reward",
        run_state=run_state,
        registry=_content_provider(),
    )

    assert not [reward for reward in rewards if reward.startswith("potion:")]


def test_apply_reward_sozu_blocks_potion_rewards() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "sozu"])

    updated = apply_reward(
        run_state=run_state,
        reward_id="potion:fire_potion",
        registry=_content_provider(),
    )

    assert updated.potions == []


def test_generate_combat_rewards_from_a_new_run_does_not_offer_rare_cards_in_normal_combat() -> (
    None
):
    provider = _content_provider()
    run_state = RunState.new(character_id="ironclad", seed=7)
    run_state = replace(
        run_state,
        current_act_id="act1",
        current_hp=80,
        max_hp=80,
        gold=99,
        deck=[
            "strike#1",
            "strike#2",
            "strike#3",
            "strike#4",
            "defend#5",
            "defend#6",
            "defend#7",
            "defend#8",
            "bash#9",
        ],
        relics=["burning_blood"],
    )

    assert run_state.rare_card_reward_offset == -5

    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:hallway_reward",
        run_state=run_state,
        registry=provider,
    )

    card_rewards = [
        reward.split(":", 1)[1]
        for reward in rewards
        if reward.startswith("card_offer:")
    ]
    assert all(
        provider.cards().get(card_id).rarity != "rare" for card_id in card_rewards
    )


def test_generate_combat_rewards_normal_gold_stays_in_10_to_20_range() -> None:
    for seed in range(1, 80):
        rewards, _next_rare_offset = generate_combat_rewards(
            room_id="act1:hallway_reward",
            run_state=replace(_run_state(), seed=seed),
            registry=_content_provider(),
        )
        gold_reward = rewards[0]
        assert gold_reward.startswith("gold:")
        gold_amount = int(gold_reward.split(":", 1)[1])
        assert 10 <= gold_amount <= 20


@pytest.mark.guardrail
def test_generate_combat_rewards_elite_gold_stays_in_25_to_35_range_and_grants_relic(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        reward_generator_module,
        "_roll_standard_relic_rarity",
        lambda *, seed, room_id: "uncommon",
    )
    run_state = replace(
        _run_state(),
        relic_sequences={"common": [], "uncommon": ["oddly_smooth_stone"], "rare": []},
        relic_sequence_positions={"common": 0, "uncommon": 0, "rare": 0},
    )
    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:elite_reward",
        run_state=run_state,
        registry=_content_provider(),
        room_type="elite",
    )

    gold_reward = rewards[0]
    assert gold_reward.startswith("gold:")
    gold_amount = int(gold_reward.split(":", 1)[1])
    assert 25 <= gold_amount <= 35

    relic_rewards = [reward for reward in rewards if reward.startswith("relic:")]
    assert len(relic_rewards) == 1
    assert relic_rewards[0] == "relic:oddly_smooth_stone"
    assert run_state.relic_sequence_positions == {"common": 0, "uncommon": 1, "rare": 0}

    card_rewards = [reward for reward in rewards if reward.startswith("card_offer:")]
    assert len(card_rewards) == 3


def test_generate_combat_rewards_elite_falls_back_to_circlet_when_standard_sequences_are_empty() -> (
    None
):
    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:elite_reward",
        run_state=replace(
            _run_state(),
            relic_sequences={"common": [], "uncommon": [], "rare": []},
            relic_sequence_positions={"common": 0, "uncommon": 0, "rare": 0},
        ),
        registry=_content_provider(),
        room_type="elite",
    )

    relic_rewards = [reward for reward in rewards if reward.startswith("relic:")]

    assert relic_rewards == ["relic:circlet"]


def test_generate_combat_rewards_elite_uses_higher_rare_weight_baseline() -> None:
    assert _rarity_weights(offset=0, room_type="combat") == (60, 37, 3)
    assert _rarity_weights(offset=0, room_type="elite") == (50, 40, 10)
    assert _rarity_weights(offset=-5, room_type="combat") == (65, 35, 0)
    assert _rarity_weights(offset=-5, room_type="elite") == (55, 40, 5)


def test_generate_combat_rewards_samples_from_full_ironclad_reward_pool_in_act1() -> (
    None
):
    seen_cards: set[str] = set()
    seen_rare_cards: set[str] = set()

    for seed in range(1, 200):
        rewards, _next_rare_offset = generate_combat_rewards(
            room_id="act1:hallway_reward",
            run_state=replace(_run_state(), seed=seed),
            registry=_content_provider(),
        )
        seen_cards.update(
            reward.split(":", 1)[1]
            for reward in rewards
            if reward.startswith("card_offer:")
        )

        rare_rewards, _next_rare_offset = generate_combat_rewards(
            room_id="act1:hallway_reward",
            run_state=replace(_run_state(), seed=seed, rare_card_reward_offset=40),
            registry=_content_provider(),
        )
        seen_rare_cards.update(
            reward.split(":", 1)[1]
            for reward in rare_rewards
            if reward.startswith("card_offer:")
        )

    assert "anger" in seen_cards
    assert "clothesline" in seen_cards
    assert "thunderclap" in seen_cards
    assert "uppercut" in seen_cards
    assert "flame_barrier" in seen_cards
    assert "ghostly_armor" in seen_cards
    assert "disarm" in seen_cards
    assert "entrench" in seen_cards
    assert "demon_form" in seen_rare_cards
    assert "barricade" in seen_rare_cards
    assert "inflame" in seen_cards
    assert "metallicize" in seen_cards
    assert "combust" in seen_cards
    assert "strike" not in seen_cards
    assert "defend" not in seen_cards
    assert "bash" not in seen_cards


def test_generate_combat_rewards_only_samples_cards_tagged_for_combat_rewards() -> None:
    provider = _content_provider()
    seen_cards: set[str] = set()

    for seed in range(1, 40):
        rewards, _next_rare_offset = generate_combat_rewards(
            room_id="act1:hallway_reward",
            run_state=replace(_run_state(), seed=seed),
            registry=provider,
        )
        seen_cards.update(
            reward.split(":", 1)[1]
            for reward in rewards
            if reward.startswith("card_offer:")
        )

    assert seen_cards
    assert all(
        "combat_reward" in provider.cards().get(card_id).acquisition_tags
        for card_id in seen_cards
    )
    assert "burn" not in seen_cards
    assert "doubt" not in seen_cards
    assert "injury" not in seen_cards


def test_generate_combat_rewards_excludes_status_and_curse_cards() -> None:
    seen_cards: set[str] = set()

    for seed in range(1, 80):
        rewards, _next_rare_offset = generate_combat_rewards(
            room_id="act1:hallway_reward",
            run_state=replace(_run_state(), seed=seed),
            registry=_content_provider(),
        )
        seen_cards.update(
            reward.split(":", 1)[1]
            for reward in rewards
            if reward.startswith("card_offer:")
        )

    assert "burn" not in seen_cards
    assert "doubt" not in seen_cards
    assert "injury" not in seen_cards


def test_generate_boss_rewards_filters_owned_relics() -> None:
    run_state = replace(
        _run_state(),
        relics=["burning_blood", "ectoplasm"],
        relic_sequences={
            "boss": ["ectoplasm", "astrolabe", "black_star", "busted_crown"],
        },
        relic_sequence_positions={"boss": 0},
    )

    rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=run_state,
        registry=_content_provider(),
    )

    assert rewards["boss_relic_offers"] == ["astrolabe", "black_star", "busted_crown"]
    assert run_state.relic_sequence_positions["boss"] == 4


def test_generate_boss_rewards_falls_back_to_three_circlets_when_boss_sequence_is_exhausted() -> (
    None
):
    run_state = replace(
        _run_state(),
        relic_sequences={"boss": []},
        relic_sequence_positions={"boss": 0},
    )

    rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=run_state,
        registry=_content_provider(),
    )

    assert rewards["boss_relic_offers"] == ["circlet", "circlet", "circlet"]
    assert run_state.relic_sequence_positions["boss"] == 0


def test_generate_boss_rewards_advances_position_by_offered_relic_count() -> None:
    run_state = replace(
        _run_state(),
        relic_sequences={
            "boss": ["astrolabe", "black_star", "busted_crown", "coffee_dripper"],
        },
        relic_sequence_positions={"boss": 1},
    )

    rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=run_state,
        registry=_content_provider(),
    )

    assert rewards["boss_relic_offers"] == [
        "black_star",
        "busted_crown",
        "coffee_dripper",
    ]
    assert run_state.relic_sequence_positions["boss"] == 4


def test_apply_reward_black_blood_replaces_burning_blood() -> None:
    updated = apply_reward(
        run_state=_run_state(),
        reward_id="relic:black_blood",
        registry=_content_provider(),
    )

    assert "burning_blood" not in updated.relics
    assert "black_blood" in updated.relics


def test_apply_reward_grants_strawberry_max_hp_bonus() -> None:
    run_state = replace(_run_state(), current_hp=70)
    updated = apply_reward(
        run_state=run_state, reward_id="relic:strawberry", registry=_content_provider()
    )

    assert updated.max_hp == 87
    assert updated.current_hp == 77
    assert "strawberry" in updated.relics


def test_apply_reward_grants_pear_max_hp_bonus() -> None:
    run_state = replace(_run_state(), current_hp=60)
    updated = apply_reward(
        run_state=run_state, reward_id="relic:pear", registry=_content_provider()
    )

    assert updated.max_hp == 90
    assert updated.current_hp == 70
    assert "pear" in updated.relics


def test_apply_reward_grants_mango_max_hp_bonus() -> None:
    run_state = replace(_run_state(), current_hp=50)
    updated = apply_reward(
        run_state=run_state, reward_id="relic:mango", registry=_content_provider()
    )

    assert updated.max_hp == 94
    assert updated.current_hp == 64
    assert "mango" in updated.relics


def test_apply_reward_grants_leeches_waffle_max_hp_and_full_heal() -> None:
    run_state = replace(_run_state(), current_hp=50)
    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:leeches_waffle",
        registry=_content_provider(),
    )

    assert updated.max_hp == 87
    assert updated.current_hp == 87
    assert "leeches_waffle" in updated.relics


def test_apply_reward_grants_old_coin_gold_bonus() -> None:
    run_state = _run_state()
    updated = apply_reward(
        run_state=run_state, reward_id="relic:old_coin", registry=_content_provider()
    )

    assert updated.gold == 399
    assert "old_coin" in updated.relics


def test_apply_reward_old_coin_gold_bonus_is_blocked_by_ectoplasm() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "ectoplasm"])

    updated = apply_reward(
        run_state=run_state, reward_id="relic:old_coin", registry=_content_provider()
    )

    assert updated.gold == run_state.gold
    assert "old_coin" in updated.relics


def test_apply_reward_duplicate_strawberry_reward_is_no_op() -> None:
    run_state = replace(
        _run_state(), current_hp=70, relics=["burning_blood", "strawberry"]
    )

    updated = apply_reward(
        run_state=run_state, reward_id="relic:strawberry", registry=_content_provider()
    )

    assert updated == run_state


def test_apply_reward_duplicate_old_coin_reward_is_no_op() -> None:
    run_state = replace(_run_state(), gold=399, relics=["burning_blood", "old_coin"])

    updated = apply_reward(
        run_state=run_state, reward_id="relic:old_coin", registry=_content_provider()
    )

    assert updated == run_state


def test_apply_reward_grants_vajra_permanent_strength_bonus() -> None:
    run_state = _run_state()

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:vajra",
        registry=_content_provider(),
    )

    assert "vajra" in updated.relics
    assert updated.relic_sequence_positions["relic:vajra:strength_bonus"] == 1


def test_apply_reward_grants_oddly_smooth_stone_permanent_dexterity_bonus() -> None:
    run_state = _run_state()

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:oddly_smooth_stone",
        registry=_content_provider(),
    )

    assert "oddly_smooth_stone" in updated.relics
    assert (
        updated.relic_sequence_positions["relic:oddly_smooth_stone:dexterity_bonus"]
        == 1
    )


def test_apply_reward_war_paint_upgrades_two_random_skill_cards() -> None:
    run_state = replace(
        _run_state(),
        deck=["defend#1", "shrug_it_off#1", "bash#1", "armaments#1"],
    )

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:war_paint",
        registry=_content_provider(),
    )

    assert "war_paint" in updated.relics
    upgraded = {card for card in updated.deck if card.endswith("_plus#1")}
    assert upgraded == {"defend_plus#1", "shrug_it_off_plus#1"}


def test_apply_reward_whetstone_upgrades_two_random_attack_cards() -> None:
    run_state = replace(
        _run_state(),
        deck=["strike#1", "bash#1", "defend#1", "anger#1"],
    )

    updated = apply_reward(
        run_state=run_state,
        reward_id="relic:whetstone",
        registry=_content_provider(),
    )

    assert "whetstone" in updated.relics
    upgraded = {card for card in updated.deck if card.endswith("_plus#1")}
    assert upgraded == {"strike_plus#1", "bash_plus#1"}


def test_apply_reward_adds_generic_relic_and_repeated_claim_is_no_op() -> None:
    updated = apply_reward(
        run_state=_run_state(),
        reward_id="relic:coffee_dripper",
        registry=_content_provider(),
    )

    assert updated.relics == ["burning_blood", "coffee_dripper"]

    repeated = apply_reward(
        run_state=updated,
        reward_id="relic:coffee_dripper",
        registry=_content_provider(),
    )

    assert repeated == updated


def test_apply_reward_transform_replaces_target_card_and_preserves_suffix() -> None:
    updated = apply_reward(
        run_state=_run_state(),
        reward_id="transform:strike#1:anger",
        registry=_content_provider(),
    )

    assert "strike#1" not in updated.deck
    assert "anger#1" in updated.deck
    assert len(updated.deck) == len(_run_state().deck)


def test_apply_reward_duplicate_adds_new_instance_without_replacing_original() -> None:
    updated = apply_reward(
        run_state=_run_state(),
        reward_id="duplicate:bash#9",
        registry=_content_provider(),
    )

    assert "bash#9" in updated.deck
    assert updated.deck.count("bash#9") == 1
    assert updated.deck[-1] == "bash#10"


def test_apply_reward_upgrade_remove_and_skip_actions_are_supported() -> None:
    run_state = _run_state()

    upgraded = apply_reward(
        run_state=run_state,
        reward_id="upgrade:strike#1",
        registry=_content_provider(),
    )
    removed = apply_reward(
        run_state=run_state,
        reward_id="remove:defend#5",
        registry=_content_provider(),
    )
    skipped = apply_reward(
        run_state=run_state,
        reward_id="skip:reward_screen",
        registry=_content_provider(),
    )

    assert "strike_plus#1" in upgraded.deck
    assert "strike#1" not in upgraded.deck
    assert "defend#5" not in removed.deck
    assert len(removed.deck) == len(run_state.deck) - 1
    assert skipped == run_state


def test_apply_reward_remove_missing_card_is_no_op() -> None:
    run_state = _run_state()

    updated = apply_reward(
        run_state=run_state,
        reward_id="remove:anger#99",
        registry=_content_provider(),
    )

    assert updated == run_state


def test_apply_reward_upgrade_missing_target_is_no_op() -> None:
    run_state = _run_state()

    updated = apply_reward(
        run_state=run_state,
        reward_id="upgrade:anger#99",
        registry=_content_provider(),
    )

    assert updated == run_state


def test_apply_reward_skip_is_explicit_no_op_for_deck_gold_and_relics() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "golden_idol"])

    updated = apply_reward(
        run_state=run_state,
        reward_id="skip:boss_reward",
        registry=_content_provider(),
    )

    assert updated.deck == run_state.deck
    assert updated.gold == run_state.gold
    assert updated.relics == run_state.relics


def test_apply_reward_noop_unknown_reward_id_is_deterministic() -> None:
    run_state = _run_state()

    first = apply_reward(
        run_state=run_state,
        reward_id="mystery:payload",
        registry=_content_provider(),
    )
    second = apply_reward(
        run_state=run_state,
        reward_id="mystery:payload",
        registry=_content_provider(),
    )

    assert first == run_state
    assert second == run_state
    assert first == second
