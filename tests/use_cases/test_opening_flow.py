from dataclasses import replace
from copy import deepcopy
from pathlib import Path
from random import Random

import pytest

from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.use_cases import opening_flow
from slay_the_spire.use_cases.opening_flow import (
    apply_neow_offer,
    build_opening_state,
)


def _provider():
    from slay_the_spire.app.session import default_content_root

    return StarterContentProvider(default_content_root())


def test_default_content_root_prefers_repo_content_directory() -> None:
    from slay_the_spire.app.session import default_content_root

    expected_root = Path(__file__).resolve().parents[2] / "content"

    assert default_content_root() == expected_root


def test_build_opening_state_generates_repeatable_neow_offers_for_same_seed() -> None:
    provider = _provider()

    first = build_opening_state(seed=7, preferred_character_id="ironclad", registry=provider)
    second = build_opening_state(seed=7, preferred_character_id="ironclad", registry=provider)

    assert first.selected_character_id == "ironclad"
    assert first.run_blueprint is not None
    assert first.neow_offers == second.neow_offers


def test_build_opening_state_seed_five_generates_stable_valid_neow_offers() -> None:
    provider = _provider()

    first = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)
    second = build_opening_state(seed=5, preferred_character_id="ironclad", registry=provider)

    assert [offer.offer_id for offer in first.neow_offers] == ["free-1", "free-2", "tradeoff-1", "tradeoff-2"]
    assert first.neow_offers == second.neow_offers
    assert all(
        offer.reward_kind != "relic" or isinstance(offer.reward_payload.get("relic_id"), str)
        for offer in first.neow_offers
    )


def test_apply_neow_offer_adds_gold_and_keeps_run_replayable() -> None:
    provider = _provider()
    opening = build_opening_state(seed=11, preferred_character_id="ironclad", registry=provider)
    offer = next(item for item in opening.neow_offers if item.reward_kind == "gold")

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider)

    assert updated.run_blueprint is not None
    assert updated.run_blueprint.gold == 199
    assert updated.pending_neow_offer_id is None


def test_build_offer_marks_targeted_rewards_with_specific_requires_target_semantics() -> None:
    provider = _provider()
    rng = Random(0)

    upgrade_offer = opening_flow._build_offer("upgrade", "tradeoff", "upgrade_card", provider, rng)
    remove_offer = opening_flow._build_offer("remove", "tradeoff", "remove_card", provider, rng)
    gold_offer = opening_flow._build_offer("gold", "free", "gold", provider, rng)

    assert upgrade_offer.requires_target == "upgrade_card"
    assert remove_offer.requires_target == "remove_card"
    assert gold_offer.requires_target is None


def test_build_offer_curse_bonus_uses_curse_as_cost_and_non_curse_reward() -> None:
    provider = _provider()

    offer = opening_flow._build_offer("curse", "tradeoff", "curse_bonus", provider, Random(0))

    assert offer.cost_kind == "curse"
    cost_card_id = str(offer.cost_payload["card_id"])
    assert provider.cards().get(cost_card_id).card_type == "curse"
    assert offer.reward_kind == "curse_bonus"
    assert offer.reward_payload["reward_type"] in {"gold", "relic", "card"}
    assert offer.summary != "获得诅咒牌"
    assert offer.reward_payload.get("card_id") != cost_card_id


def test_apply_neow_offer_curse_bonus_adds_curse_and_applies_premium_reward() -> None:
    provider = _provider()
    opening = build_opening_state(seed=11, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("curse", "tradeoff", "curse_bonus", provider, Random(0))
    opening = replace(opening, neow_offers=[offer])
    before = opening.run_blueprint

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider)

    assert before is not None
    assert updated.run_blueprint is not None
    cost_card_id = str(offer.cost_payload["card_id"])
    assert f"{cost_card_id}#11" in updated.run_blueprint.deck
    if offer.reward_payload["reward_type"] == "gold":
        assert updated.run_blueprint.gold == before.gold + 250


def test_apply_neow_offer_rejects_duplicate_resolution() -> None:
    provider = _provider()
    opening = build_opening_state(seed=11, preferred_character_id="ironclad", registry=provider)
    offer = next(item for item in opening.neow_offers if item.reward_kind == "gold")

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider)

    with pytest.raises(ValueError, match="already been resolved"):
        apply_neow_offer(updated, offer.offer_id, registry=provider)


def test_apply_neow_offer_blocks_any_other_offer_after_first_resolution() -> None:
    provider = _provider()
    opening = build_opening_state(seed=11, preferred_character_id="ironclad", registry=provider)
    first_offer = opening.neow_offers[0]
    other_offer = next(item for item in opening.neow_offers if item.offer_id != first_offer.offer_id)

    updated = apply_neow_offer(opening, first_offer.offer_id, registry=provider)

    with pytest.raises(ValueError, match="opening neow offer has already been resolved"):
        apply_neow_offer(updated, other_offer.offer_id, registry=provider)


def test_apply_neow_offer_rejects_invalid_target_before_changing_run_state() -> None:
    provider = _provider()
    opening = build_opening_state(seed=11, preferred_character_id="ironclad", registry=provider)
    offer = opening_flow._build_offer("upgrade", "tradeoff", "upgrade_card", provider, Random(0))
    opening = replace(opening, neow_offers=[offer])
    before_run_state = deepcopy(opening.run_blueprint.to_dict()) if opening.run_blueprint is not None else None

    with pytest.raises(ValueError, match="target card is not in deck"):
        apply_neow_offer(opening, offer.offer_id, registry=provider, target_card_instance_id="missing#1")

    assert opening.run_blueprint is not None
    assert opening.run_blueprint.to_dict() == before_run_state
    assert opening.pending_neow_offer_id is None
