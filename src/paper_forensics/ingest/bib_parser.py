from __future__ import annotations

import re
from pathlib import Path


def parse_bib_titles(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return [
        re.sub(r"\s+", " ", title).strip()
        for title in re.findall(r"title\s*=\s*\{([^{}]+)\}", text, flags=re.IGNORECASE)
    ]
