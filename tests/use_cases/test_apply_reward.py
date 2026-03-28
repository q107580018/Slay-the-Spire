from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.run_state import RunState
from slay_the_spire.domain.rewards.reward_generator import _rarity_weights
from slay_the_spire.domain.rewards.reward_generator import generate_boss_rewards, generate_combat_rewards
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
        deck=["strike#1", "strike#2", "strike#3", "strike#4", "defend#5", "defend#6", "defend#7", "defend#8", "bash#9"],
        relics=["burning_blood"],
        potions=[],
        card_removal_count=0,
    )


def test_apply_reward_adds_gold_to_run_state() -> None:
    updated = apply_reward(run_state=_run_state(), reward_id="gold:11", registry=_content_provider())

    assert updated.gold == 110


def test_apply_reward_gold_is_blocked_by_ectoplasm() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "ectoplasm"])

    updated = apply_reward(run_state=run_state, reward_id="gold:11", registry=_content_provider())

    assert updated.gold == run_state.gold


def test_apply_reward_adds_real_card_instance_to_run_state() -> None:
    updated = apply_reward(run_state=_run_state(), reward_id="card:anger", registry=_content_provider())

    assert updated.deck[-1] == "anger#10"


def test_apply_reward_preserves_card_id_with_underscores() -> None:
    updated = apply_reward(run_state=_run_state(), reward_id="card:pommel_strike", registry=_content_provider())

    assert updated.deck[-1] == "pommel_strike#10"


def test_apply_reward_accepts_card_offer_reward_ids() -> None:
    updated = apply_reward(run_state=_run_state(), reward_id="card_offer:anger", registry=_content_provider())

    assert updated.deck[-1] == "anger#10"


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

    updated = apply_reward(run_state=run_state, reward_id="gold:100", registry=_content_provider())

    assert updated.gold == 224


def test_generate_boss_rewards_returns_high_gold_and_three_unique_relics() -> None:
    rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=_run_state(),
        registry=_content_provider(),
    )

    assert rewards["generated_by"] == "boss_reward_generator"
    assert rewards["gold_reward"] == 106
    assert len(rewards["boss_relic_offers"]) == 3
    assert len(set(rewards["boss_relic_offers"])) == 3
    assert set(rewards["boss_relic_offers"]).issubset({"black_blood", "ectoplasm", "coffee_dripper", "fusion_hammer"})
    assert rewards["claimed_gold"] is False
    assert rewards["claimed_relic_id"] is None


def test_generate_boss_rewards_can_offer_fusion_hammer_across_seeds() -> None:
    seen_fusion_hammer = False
    for seed in range(1, 40):
        rewards = generate_boss_rewards(
            room_id="act1:boss",
            seed=seed,
            run_state=_run_state(),
            registry=_content_provider(),
        )
        if "fusion_hammer" in rewards["boss_relic_offers"]:
            seen_fusion_hammer = True
            break

    assert seen_fusion_hammer is True


def test_generate_boss_rewards_is_deterministic_for_same_inputs() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "ectoplasm"])

    first = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=run_state,
        registry=_content_provider(),
    )
    second = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=run_state,
        registry=_content_provider(),
    )

    assert first["boss_relic_offers"] == second["boss_relic_offers"]


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


def test_generate_combat_rewards_from_a_new_run_does_not_offer_rare_cards_in_normal_combat() -> None:
    provider = _content_provider()
    run_state = RunState.new(character_id="ironclad", seed=7)
    run_state = replace(
        run_state,
        current_act_id="act1",
        current_hp=80,
        max_hp=80,
        gold=99,
        deck=["strike#1", "strike#2", "strike#3", "strike#4", "defend#5", "defend#6", "defend#7", "defend#8", "bash#9"],
        relics=["burning_blood"],
    )

    assert run_state.rare_card_reward_offset == -5

    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:hallway_reward",
        run_state=run_state,
        registry=provider,
    )

    card_rewards = [reward.split(":", 1)[1] for reward in rewards if reward.startswith("card_offer:")]
    assert all(provider.cards().get(card_id).rarity != "rare" for card_id in card_rewards)


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


def test_generate_combat_rewards_elite_gold_stays_in_25_to_35_range_and_grants_relic() -> None:
    rewards, _next_rare_offset = generate_combat_rewards(
        room_id="act1:elite_reward",
        run_state=_run_state(),
        registry=_content_provider(),
        room_type="elite",
    )

    gold_reward = rewards[0]
    assert gold_reward.startswith("gold:")
    gold_amount = int(gold_reward.split(":", 1)[1])
    assert 25 <= gold_amount <= 35

    relic_rewards = [reward for reward in rewards if reward.startswith("relic:")]
    assert len(relic_rewards) == 1
    assert relic_rewards[0].split(":", 1)[1] in {"blood_vial", "golden_idol", "guarding_totem"}

    card_rewards = [reward for reward in rewards if reward.startswith("card_offer:")]
    assert len(card_rewards) == 3


def test_generate_combat_rewards_elite_uses_higher_rare_weight_baseline() -> None:
    assert _rarity_weights(offset=0, room_type="combat") == (60, 37, 3)
    assert _rarity_weights(offset=0, room_type="elite") == (50, 40, 10)
    assert _rarity_weights(offset=-5, room_type="combat") == (65, 35, 0)
    assert _rarity_weights(offset=-5, room_type="elite") == (55, 40, 5)


def test_generate_combat_rewards_samples_from_full_ironclad_reward_pool_in_act1() -> None:
    seen_cards: set[str] = set()

    for seed in range(1, 80):
        rewards, _next_rare_offset = generate_combat_rewards(
            room_id="act1:hallway_reward",
            run_state=replace(_run_state(), seed=seed),
            registry=_content_provider(),
        )
        seen_cards.update(reward.split(":", 1)[1] for reward in rewards if reward.startswith("card_offer:"))

    assert "anger" in seen_cards
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
        seen_cards.update(reward.split(":", 1)[1] for reward in rewards if reward.startswith("card_offer:"))

    assert seen_cards
    assert all("combat_reward" in provider.cards().get(card_id).acquisition_tags for card_id in seen_cards)
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
        seen_cards.update(reward.split(":", 1)[1] for reward in rewards if reward.startswith("card_offer:"))

    assert "burn" not in seen_cards
    assert "doubt" not in seen_cards
    assert "injury" not in seen_cards


def test_generate_boss_rewards_filters_owned_relics() -> None:
    run_state = replace(_run_state(), relics=["burning_blood", "ectoplasm"])

    rewards = generate_boss_rewards(
        room_id="act1:boss",
        seed=37,
        run_state=run_state,
        registry=_content_provider(),
    )

    assert "ectoplasm" not in rewards["boss_relic_offers"]


def test_apply_reward_black_blood_replaces_burning_blood() -> None:
    updated = apply_reward(
        run_state=_run_state(),
        reward_id="relic:black_blood",
        registry=_content_provider(),
    )

    assert "burning_blood" not in updated.relics
    assert "black_blood" in updated.relics


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
