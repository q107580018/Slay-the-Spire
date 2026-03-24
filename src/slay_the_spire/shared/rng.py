from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class SeededRng:
    seed: int
    _random: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._random = random.Random(self.seed)

    def randint(self, a: int, b: int) -> int:
        return self._random.randint(a, b)

    def random(self) -> float:
        return self._random.random()

    def choice(self, seq: list[T] | tuple[T, ...]) -> T:
        return self._random.choice(seq)

