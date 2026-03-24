from typing import Protocol


class RendererPort(Protocol):
    def render(self, text: str) -> None: ...
