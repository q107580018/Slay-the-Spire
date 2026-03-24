from typing import Protocol


class SaveRepositoryPort(Protocol):
    def load(self) -> object | None: ...

    def save(self, state: object) -> None: ...
