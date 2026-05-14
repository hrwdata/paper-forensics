from __future__ import annotations

import json
from pathlib import Path


def load_phrase_rules() -> dict[str, list[str]]:
    data_path = Path(__file__).resolve().parent.parent / "data" / "ai_phrase_lexicon.json"
    return json.loads(data_path.read_text(encoding="utf-8"))


def match_phrases(text: str, rules: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    lowered = text.lower()
    phrases: list[str] = []
    categories: list[str] = []
    for category, entries in rules.items():
        matched = [entry for entry in entries if entry in lowered]
        if matched:
            categories.append(category)
            phrases.extend(matched)
    return sorted(set(phrases)), sorted(set(categories))
