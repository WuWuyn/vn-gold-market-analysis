from __future__ import annotations

import sys
from pathlib import Path


def bootstrap() -> None:
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    for path in (root, src):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)
