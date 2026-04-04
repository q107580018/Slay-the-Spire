from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "docs" / "reference" / "sts_huijiwiki" / "sts_huiji_baike_entries_clean.json"
)
OUTPUT = ROOT / "docs" / "reference" / "sts_huijiwiki" / "card_relic_expectations.json"


def _to_snake(text: str) -> str:
    """Convert an English name to snake_case content-ID style."""
    text = text.strip()
    # Replace non-alphanumeric sequences with underscores
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return text.lower().strip("_")


def _extract_relic_id(content_text: str) -> str | None:
    """Extract relic content-ID from '遗物 id: <English Name>' pattern."""
    m = re.search(r"遗物\s+id:\s+([A-Za-z][A-Za-z0-9 ]+?)(?:\n|$)", content_text)
    if m:
        return _to_snake(m.group(1))
    return None


def _extract_card_id(content_text: str) -> str | None:
    """Extract card content-ID from the '英文名称\n<English Name>颜色' pattern.

    For color-variant starter cards (Strike_R, Strike_G, etc.), the content
    may also contain a pattern like '<ChineseName><EnglishId_ColorSuffix>\n<CardType>'.
    The canonical ID strips any _R/_G/_B/_P suffix from the English name.
    """
    # Primary: look for the explicit English name field
    m = re.search(r"英文名称\n([^\n]+)颜色", content_text)
    if m:
        english_name = m.group(1).strip()
        return _to_snake(english_name)

    # Fallback: detect color-variant card pattern like 'FooBar_R\n攻击'
    m = re.search(
        r"([A-Za-z][A-Za-z0-9 ]*?)_[RGBP]\n(?:攻击|技能|能力|诅咒)", content_text
    )
    if m:
        return _to_snake(m.group(1))

    return None


def _normalize_summary(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("。 ", "。")
    return text


def main() -> None:
    entries = json.loads(SOURCE.read_text(encoding="utf-8"))["entries"]
    payload: dict[str, dict] = {"cards": {}, "relics": {}}

    for entry in entries:
        title = str(entry.get("title", "")).strip()
        content = str(entry.get("content_text", "")).strip()
        if not title or not content:
            continue

        # Try relic extraction first (relics have explicit id: pattern)
        relic_id = _extract_relic_id(content)
        if relic_id:
            payload["relics"][relic_id] = {
                "name": title,
                "summary": _normalize_summary(content[:120]),
            }
            continue

        # Try card extraction (cards from 卡牌总览 discovered_from)
        discovered_from = entry.get("discovered_from", [])
        is_card_source = any(src in ("卡牌总览",) for src in discovered_from)
        if not is_card_source:
            continue

        card_id = _extract_card_id(content)
        if card_id:
            # Only keep the first entry per card_id (skip duplicates)
            if card_id not in payload["cards"]:
                payload["cards"][card_id] = {
                    "name": title,
                    "summary": _normalize_summary(content[:120]),
                }

    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"Wrote {len(payload['cards'])} cards and {len(payload['relics'])} relics to {OUTPUT}"
    )


if __name__ == "__main__":
    main()
