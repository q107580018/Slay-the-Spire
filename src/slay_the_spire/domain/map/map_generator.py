from __future__ import annotations

from collections import defaultdict
from random import Random

from slay_the_spire.content.registries import ActDef, ActMapConfig
from slay_the_spire.domain.models.act_state import ActNodeState, ActState
from slay_the_spire.ports.content_provider import ContentProviderPort

_MAX_WIDTH = 3
_MAX_GENERATION_ATTEMPTS = 50


def _act_def_from_registry(act_id: str, registry: ContentProviderPort) -> ActDef:
    return registry.acts().get(act_id)


def _node_id(row: int, col: int) -> str:
    if row == 0 and col == 0:
        return "start"
    return f"r{row}c{col}"


def _build_layered_topology(config: ActMapConfig, rng: Random) -> dict[tuple[int, int], list[tuple[int, int]]]:
    if config.floor_count < 2:
        raise ValueError("map_config.floor_count must be at least 2")
    if config.starting_columns != 1:
        raise ValueError("only starting_columns=1 is supported in the current prototype")
    if config.min_branch_choices < 1:
        raise ValueError("map_config.min_branch_choices must be at least 1")
    if config.max_branch_choices < config.min_branch_choices:
        raise ValueError("map_config.max_branch_choices must be >= min_branch_choices")

    topology: dict[tuple[int, int], list[tuple[int, int]]] = {}
    layers: list[list[tuple[int, int]]] = [[(0, 0)]]

    for row in range(config.floor_count - 1):
        current_layer = layers[row]
        if row == config.floor_count - 2:
            next_count = 1
        else:
            max_next_count = min(_MAX_WIDTH, len(current_layer) * config.max_branch_choices)
            next_count = rng.randint(1, max_next_count)
        next_layer = [(row + 1, col) for col in range(next_count)]
        layers.append(next_layer)

        desired_edges = [
            rng.randint(config.min_branch_choices, min(config.max_branch_choices, next_count))
            for _ in current_layer
        ]
        while sum(desired_edges) < next_count:
            expandable = [
                index
                for index, edge_count in enumerate(desired_edges)
                if edge_count < min(config.max_branch_choices, next_count)
            ]
            if not expandable:
                raise ValueError("topology generation could not cover the next layer")
            desired_edges[rng.choice(expandable)] += 1

        edge_sets = [set() for _ in current_layer]

        # First guarantee every node in the next layer is reachable.
        for target in next_layer:
            candidates = [
                index
                for index, edge_count in enumerate(desired_edges)
                if len(edge_sets[index]) < edge_count and target not in edge_sets[index]
            ]
            if not candidates:
                raise ValueError("topology generation ran out of edge capacity")
            edge_sets[rng.choice(candidates)].add(target)

        # Then guarantee each current node satisfies the minimum branch count.
        for index, _node in enumerate(current_layer):
            while len(edge_sets[index]) < config.min_branch_choices:
                available_targets = [target for target in next_layer if target not in edge_sets[index]]
                if not available_targets:
                    raise ValueError("topology generation could not satisfy minimum branches")
                edge_sets[index].add(rng.choice(available_targets))

        # Finally add optional branches up to the desired edge count.
        for index, _node in enumerate(current_layer):
            while len(edge_sets[index]) < desired_edges[index]:
                available_targets = [target for target in next_layer if target not in edge_sets[index]]
                if not available_targets:
                    break
                edge_sets[index].add(rng.choice(available_targets))

        for coord, targets in zip(current_layer, edge_sets, strict=True):
            topology[coord] = sorted(targets, key=lambda item: item[1])

    topology[(config.floor_count - 1, 0)] = []
    return topology


def _allowed_room_types(row: int, config: ActMapConfig) -> list[str]:
    rules = config.room_rules
    min_shop = int(rules["min_floor_for_shop"])
    min_rest = int(rules["min_floor_for_rest"])
    min_elite = int(rules["min_floor_for_elite"])
    if row < min(min_shop, min_rest, min_elite):
        return list(rules["early_floors"])
    if row < min_elite:
        return list(rules["mid_floors"])
    return list(rules["late_floors"])


def _assign_room_types(
    topology: dict[tuple[int, int], list[tuple[int, int]]],
    *,
    config: ActMapConfig,
    rng: Random,
) -> list[ActNodeState]:
    nodes_by_coord: dict[tuple[int, int], ActNodeState] = {}
    last_row = config.floor_count - 1

    for (row, col), next_coords in sorted(topology.items()):
        if row == 0:
            room_type = "combat"
        elif row == last_row:
            room_type = config.boss_room_type
        else:
            room_type = rng.choice(_allowed_room_types(row, config))
        nodes_by_coord[(row, col)] = ActNodeState(
            node_id=_node_id(row, col),
            row=row,
            col=col,
            room_type=room_type,
            next_node_ids=[_node_id(target_row, target_col) for target_row, target_col in next_coords],
        )

    _ensure_required_room_type(nodes_by_coord, room_type="shop", min_row=int(config.room_rules["min_floor_for_shop"]), rng=rng)
    _ensure_required_room_type(nodes_by_coord, room_type="rest", min_row=int(config.room_rules["min_floor_for_rest"]), rng=rng)

    return [nodes_by_coord[coord] for coord in sorted(nodes_by_coord)]


def _ensure_required_room_type(
    nodes_by_coord: dict[tuple[int, int], ActNodeState],
    *,
    room_type: str,
    min_row: int,
    rng: Random,
) -> None:
    if any(node.room_type == room_type for node in nodes_by_coord.values()):
        return
    candidates = [
        coord
        for coord, node in nodes_by_coord.items()
        if node.row >= min_row and node.row > 0 and not node.next_node_ids == [] and node.room_type not in {"shop", "rest", "boss"}
    ]
    if not candidates:
        raise ValueError(f"map generation could not place required room_type: {room_type}")
    coord = rng.choice(sorted(candidates))
    node = nodes_by_coord[coord]
    nodes_by_coord[coord] = ActNodeState(
        node_id=node.node_id,
        row=node.row,
        col=node.col,
        room_type=room_type,
        next_node_ids=list(node.next_node_ids),
    )


def _validate_generated_nodes(nodes: list[ActNodeState], *, config: ActMapConfig) -> None:
    if not nodes:
        raise ValueError("generated map must contain nodes")
    by_row: dict[int, list[ActNodeState]] = defaultdict(list)
    for node in nodes:
        by_row[node.row].append(node)
    if max(by_row) != config.floor_count - 1:
        raise ValueError("generated map does not reach the configured final floor")
    if len(by_row[config.floor_count - 1]) != 1:
        raise ValueError("generated map must end with exactly one boss node")
    if any(len(nodes_in_row) > _MAX_WIDTH for nodes_in_row in by_row.values()):
        raise ValueError("generated map exceeds width limit")


def generate_act_state(act_id: str, seed: int, registry: ContentProviderPort) -> ActState:
    act_def = _act_def_from_registry(act_id, registry)
    for attempt in range(_MAX_GENERATION_ATTEMPTS):
        rng = Random(seed + attempt)
        topology = _build_layered_topology(act_def.map_config, rng)
        typed_nodes = _assign_room_types(topology, config=act_def.map_config, rng=rng)
        try:
            _validate_generated_nodes(typed_nodes, config=act_def.map_config)
            return ActState(
                act_id=act_def.id,
                current_node_id="start",
                nodes=typed_nodes,
                visited_node_ids=[],
                enemy_pool_id=act_def.enemy_pool_id,
                elite_pool_id=act_def.elite_pool_id,
                boss_pool_id=act_def.boss_pool_id,
                event_pool_id=act_def.event_pool_id,
            )
        except ValueError:
            if attempt == _MAX_GENERATION_ATTEMPTS - 1:
                raise
    raise ValueError("map generation failed")
