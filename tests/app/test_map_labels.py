from slay_the_spire.app.map_labels import format_next_room_labels
from slay_the_spire.domain.models.act_state import ActNodeState, ActState


def _act_state_with_next_rooms(*room_types: str) -> ActState:
    next_node_ids = [f"r1c{index}" for index in range(len(room_types))]
    return ActState(
        act_id="act1",
        current_node_id="start",
        nodes=[
            ActNodeState(node_id="start", row=0, col=0, room_type="combat", next_node_ids=next_node_ids),
            *[
                ActNodeState(node_id=node_id, row=1, col=index, room_type=room_type, next_node_ids=[])
                for index, (node_id, room_type) in enumerate(zip(next_node_ids, room_types, strict=False))
            ],
        ],
        visited_node_ids=["start"],
    )


def test_format_next_room_labels_uses_room_type_names() -> None:
    act_state = _act_state_with_next_rooms("event", "shop")

    assert format_next_room_labels(act_state, ["r1c0", "r1c1"]) == ["事件", "商店"]


def test_format_next_room_labels_disambiguates_duplicate_room_types() -> None:
    act_state = _act_state_with_next_rooms("combat", "combat")

    assert format_next_room_labels(act_state, ["r1c0", "r1c1"]) == ["战斗（路线1）", "战斗（路线2）"]
