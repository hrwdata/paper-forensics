from __future__ import annotations

import json
from pathlib import Path


def load_phrase_rules() -> dict[str, list[str]]:
    data_path = Path(__file__).resolve().parent.parent / "data" / "ai_phrase_lexicon.json"
    return json.loads(data_path.read_text(encoding="utf-8"))


def match_phrase_details(text: str, rules: dict[str, list[str]]) -> dict[str, list[str]]:
    lowered = text.lower()
    return {
        category: sorted({entry for entry in entries if entry in lowered})
        for category, entries in rules.items()
    }


def match_phrases(text: str, rules: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    details = match_phrase_details(text, rules)
    phrases: list[str] = []
    categories: list[str] = []
    for category, matched in details.items():
        if matched:
            categories.append(category)
            phrases.extend(matched)
    return sorted(set(phrases)), sorted(set(categories))
