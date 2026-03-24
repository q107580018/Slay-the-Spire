from __future__ import annotations

from pathlib import Path

from slay_the_spire.content.provider import StarterContentProvider
from slay_the_spire.domain.map.map_generator import generate_act_state


def _content_provider() -> StarterContentProvider:
    return StarterContentProvider(Path(__file__).resolve().parents[2] / "content")


def test_generate_act_state_is_deterministic_for_same_seed() -> None:
    provider = _content_provider()

    left = generate_act_state("act1", seed=42, registry=provider)
    right = generate_act_state("act1", seed=42, registry=provider)

    assert left.to_dict() == right.to_dict()


def test_generate_act_state_builds_reachable_graph() -> None:
    provider = _content_provider()

    act_state = generate_act_state("act1", seed=7, registry=provider)

    assert act_state.act_id == "act1"
    assert act_state.current_node_id == "start"
    assert act_state.reachable_node_ids == ["hallway"]
    assert act_state.enemy_pool_id == "act1_basic"
    assert act_state.elite_pool_id == "act1_elites"
    assert act_state.event_pool_id == "act1_events"
    assert act_state.boss_pool_id == "act1_elites"
    assert set(act_state.get_node("hallway").next_node_ids) == {"elite", "event"}
    assert {node.node_id for node in act_state.nodes} == {"start", "hallway", "elite", "event", "boss"}
    assert all(node_id in {node.node_id for node in act_state.nodes} for node_id in act_state.reachable_node_ids)
