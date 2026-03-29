from random import Random

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
    assert [offer.offer_id for offer in first.neow_offers] == [offer.offer_id for offer in second.neow_offers]


def test_apply_neow_offer_adds_gold_and_keeps_run_replayable() -> None:
    provider = _provider()
    opening = build_opening_state(seed=11, preferred_character_id="ironclad", registry=provider)
    offer = next(item for item in opening.neow_offers if item.reward_kind == "gold")

    updated = apply_neow_offer(opening, offer.offer_id, registry=provider)

    assert updated.run_blueprint is not None
    assert updated.run_blueprint.gold >= 199
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
