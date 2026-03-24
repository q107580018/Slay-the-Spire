from typing import Protocol


class InputPort(Protocol):
    def read(self, prompt: str = "") -> str: ...
