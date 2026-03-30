from __future__ import annotations

import shutil
from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    anchor = Path(__file__).resolve() if start is None else Path(start).resolve()
    search_roots = (anchor, *anchor.parents)
    for candidate in search_roots:
        if (candidate / "pyproject.toml").exists() and (candidate / "content").is_dir():
            return candidate
    raise FileNotFoundError(f"could not locate project root from {anchor}")


def source_content_root(start: Path | None = None) -> Path:
    return repo_root(start) / "content"


def packaged_content_root(start: Path | None = None) -> Path:
    return repo_root(start) / "src" / "slay_the_spire" / "data" / "content"


def sync_packaged_content_tree(*, source_root: Path, target_root: Path) -> None:
    source = Path(source_root)
    target = Path(target_root)
    if not source.is_dir():
        raise FileNotFoundError(f"missing content source root: {source}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
