from __future__ import annotations

from pathlib import Path

from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.models.run_state import RunState
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


def test_apply_reward_adds_real_card_instance_to_run_state() -> None:
    updated = apply_reward(run_state=_run_state(), reward_id="card:anger", registry=_content_provider())

    assert updated.deck[-1] == "anger#10"


def test_apply_reward_preserves_card_id_with_underscores() -> None:
    updated = apply_reward(run_state=_run_state(), reward_id="card:pommel_strike", registry=_content_provider())

    assert updated.deck[-1] == "pommel_strike#10"


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
