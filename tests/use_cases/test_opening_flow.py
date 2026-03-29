from dataclasses import replace
from copy import deepcopy
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


def test_build_opening_state_generates_repeatable_neow_offers_for_same_seed() -> None:
    provider = _provider()

    first = build_opening_state(seed=7, preferred_character_id="ironclad", registry=provider)
    second = build_opening_state(seed=7, preferred_character_id="ironclad", registry=provider)

    assert first.selected_character_id == "ironclad"
    assert first.run_blueprint is not None
    assert first.neow_offers == second.neow_offers


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
