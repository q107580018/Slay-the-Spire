from typing import Protocol


class ContentProviderPort(Protocol):
    def get(self, key: str) -> object: ...
