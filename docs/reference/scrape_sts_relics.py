from __future__ import annotations

import csv
import json
import re
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

from scrapling.fetchers import Fetcher


BASE_URL = "https://sts.huijiwiki.com"
NAVBOX_URL = f"{BASE_URL}/wiki/%E6%A8%A1%E6%9D%BF:Navbox%E9%81%97%E7%89%A9"
OUTPUT_JSON = Path("sts_relics.json")
OUTPUT_CSV = Path("sts_relics.csv")


def clean(text: str | None) -> str:
    if not text:
        return ""
    text = " ".join(text.split())
    text = re.sub(r"\s+([，。！？：；、）】》〉])", r"\1", text)
    text = re.sub(r"([（【《〈])\s+", r"\1", text)
    text = re.sub(r"([\u4e00-\u9fff])\s+([\u4e00-\u9fff])", r"\1\2", text)
    return text


def extract_relic_links() -> list[str]:
    page = Fetcher.get(NAVBOX_URL)
    links: OrderedDict[str, None] = OrderedDict()

    for anchor in page.css(".navbox a[href]"):
        href = anchor.attrib.get("href", "").strip()
        if not href:
            continue
        if href.startswith("/wiki/"):
            url = urljoin(BASE_URL, href)
        elif href.startswith(BASE_URL):
            url = href
        else:
            continue
        path = unquote(urlparse(url).path)
        if not path.startswith("/wiki/"):
            continue
        if ":" in path.removeprefix("/wiki/"):
            continue
        links[url] = None

    return list(links.keys())


def extract_effect_description(url: str) -> dict[str, str] | None:
    page = Fetcher.get(url)
    if page.status != 200:
        return None

    title = clean(page.css("#firstHeading::text").get()) or clean(page.css("h1::text").get())
    if not title:
        parsed = urlparse(url)
        title = unquote(parsed.path.rsplit("/", 1)[-1])

    rows = page.css("table.infobox tr")
    description = ""

    for row in rows:
        header = clean(row.css("th::text").get())
        if header == "效果中文描述":
            cell = row.css("td").first
            description = clean("".join(cell.css("*::text").getall()) if cell else "")
            break

    if not description:
        return None

    return {
        "name": title,
        "effect_zh": description,
        "url": url,
    }


def main() -> None:
    results: list[dict[str, str]] = []
    for url in extract_relic_links():
        data = extract_effect_description(url)
        if data:
            results.append(data)

    results.sort(key=lambda item: item["name"])

    OUTPUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "effect_zh", "url"])
        writer.writeheader()
        writer.writerows(results)

    print(f"relics={len(results)}")
    print(f"json={OUTPUT_JSON.resolve()}")
    print(f"csv={OUTPUT_CSV.resolve()}")
    for item in results[:10]:
        print(f'{item["name"]}: {item["effect_zh"]}')


if __name__ == "__main__":
    main()
