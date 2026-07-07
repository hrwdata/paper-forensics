from __future__ import annotations

import re


ABBREVIATIONS = {
    "al",
    "cf",
    "dr",
    "eq",
    "e.g",
    "etc",
    "fig",
    "i.e",
    "mr",
    "mrs",
    "ms",
    "prof",
    "sec",
    "st",
    "vs",
}


def split_sentences(paragraph: str) -> list[str]:
    text = re.sub(r"\s+", " ", paragraph).strip()
    if not text:
        return []

    sentences: list[str] = []
    start = 0
    idx = 0
    while idx < len(text):
        char = text[idx]
        if char in ".!?":
            token = _previous_token(text, idx)
            next_char = text[idx + 1] if idx + 1 < len(text) else ""
            if _is_decimal(text, idx) or token in ABBREVIATIONS:
                idx += 1
                continue
            if next_char and next_char not in {" ", '"', "'", ")", "]"}:
                idx += 1
                continue
            sentence = text[start : idx + 1].strip()
            if sentence:
                sentences.append(sentence)
            start = idx + 1
        idx += 1

    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    return [sentence for sentence in sentences if sentence]


def _previous_token(text: str, idx: int) -> str:
    window = text[max(0, idx - 12) : idx]
    token = re.findall(r"([A-Za-z.]+)$", window)
    if not token:
        return ""
    return token[0].lower().strip(".")


def _is_decimal(text: str, idx: int) -> bool:
    before = text[idx - 1] if idx > 0 else ""
    after = text[idx + 1] if idx + 1 < len(text) else ""
    return before.isdigit() and after.isdigit()
