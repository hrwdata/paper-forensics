from __future__ import annotations

import json
from pathlib import Path

from paper_forensics.scoring.schemas import AuditResult


def write_json(result: AuditResult, path: Path) -> None:
    path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
