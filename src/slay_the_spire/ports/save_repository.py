from typing import Protocol, TypeVar

StateT = TypeVar("StateT")


class SaveRepositoryPort(Protocol[StateT]):
    def load(self) -> StateT | None: ...

    def save(self, state: StateT) -> None: ...
