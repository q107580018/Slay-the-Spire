from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from slay_the_spire.shared.types import JsonDict


def _require_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("save document must be a mapping")
    return value


def _normalize_json(value: object) -> JsonDict:
    data = _require_mapping(value)
    normalized = json.loads(json.dumps(data))
    if not isinstance(normalized, dict):
        raise TypeError("save document must decode to a JSON object")
    return normalized


class JsonFileSaveRepository:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> JsonDict | None:
        if not self._path.exists():
            return None
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return _normalize_json(raw)

    def save(self, state: Mapping[str, object]) -> None:
        document = _normalize_json(state)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True),
            encoding="utf-8",
        )
