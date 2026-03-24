from typing import Protocol, TypeVar

ContentT = TypeVar("ContentT")


class ContentProviderPort(Protocol[ContentT]):
    def get(self, key: str) -> ContentT: ...
