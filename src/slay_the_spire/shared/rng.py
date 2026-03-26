from __future__ import annotations

from dataclasses import dataclass, field
import random
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class SeededRng:
    seed: int
    _random: random.Random = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._random = random.Random(self.seed)

    def randint(self, a: int, b: int) -> int:
        return self._random.randint(a, b)

    def random(self) -> float:
        return self._random.random()

    def choice(self, seq: Sequence[T]) -> T:
        return self._random.choice(seq)


def _seed_key(*parts: object) -> str:
    return ":".join(str(part) for part in parts)


def rng_for_run(*, seed: int, category: str) -> random.Random:
    return random.Random(_seed_key(seed, category))


def rng_for_room(*, seed: int, room_id: str, category: str) -> random.Random:
    return random.Random(_seed_key(seed, room_id, category))
