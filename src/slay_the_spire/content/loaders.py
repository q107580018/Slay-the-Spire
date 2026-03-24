from __future__ import annotations

import json
from pathlib import Path

from slay_the_spire.shared.types import JsonValue


def load_json_file(path: str | Path) -> JsonValue:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
