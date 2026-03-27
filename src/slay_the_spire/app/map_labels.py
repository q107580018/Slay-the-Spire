from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence

from slay_the_spire.domain.models.act_state import ActNodeState, ActState

_ROOM_TYPE_LABELS = {
    "combat": "战斗",
    "elite": "精英",
    "boss": "Boss",
    "event": "事件",
    "shop": "商店",
    "rest": "休息",
}


def format_node_id(node_id: object) -> str:
    if str(node_id) == "start":
        return "起点"
    return str(node_id)


def _node_lookup(act_state: ActState, node_id: object) -> ActNodeState | None:
    if not isinstance(node_id, str):
        return None
    try:
        return act_state.get_node(node_id)
    except KeyError:
        return None


def _base_next_room_label(act_state: ActState, node_id: object) -> str:
    node = _node_lookup(act_state, node_id)
    if node is None:
        return format_node_id(node_id)
    return _ROOM_TYPE_LABELS.get(node.room_type, node.room_type)


def format_next_room_labels(act_state: ActState, node_ids: Sequence[object]) -> list[str]:
    base_labels = [_base_next_room_label(act_state, node_id) for node_id in node_ids]
    counts = Counter(base_labels)
    seen: defaultdict[str, int] = defaultdict(int)
    labels: list[str] = []
    for base_label in base_labels:
        if counts[base_label] > 1:
            seen[base_label] += 1
            labels.append(f"{base_label}（路线{seen[base_label]}）")
            continue
        labels.append(base_label)
    return labels

