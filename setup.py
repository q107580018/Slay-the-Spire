from __future__ import annotations

import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = Path(__file__).resolve().parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from slay_the_spire.build_content import packaged_content_root, source_content_root, sync_packaged_content_tree


class build_py(_build_py):
    def run(self) -> None:
        target_root = packaged_content_root(ROOT)
        sync_packaged_content_tree(
            source_root=source_content_root(ROOT),
            target_root=target_root,
        )
        try:
            super().run()
        finally:
            if target_root.exists():
                import shutil

                shutil.rmtree(target_root)


setup(cmdclass={"build_py": build_py})
