from __future__ import annotations

from paper_forensics.nlp.token_features import tokenize


COMMON_BOILERPLATE = {
    "in this paper",
    "the remainder of this paper",
    "related work",
    "experimental results",
    "results show",
    "we evaluate",
    "our method",
    "this section",
}


def boilerplate_discount(text: str) -> float:
    lowered = text.lower()
    hits = sum(1 for phrase in COMMON_BOILERPLATE if phrase in lowered)
    token_count = max(len(tokenize(text)), 1)
    return min(0.35, (hits / token_count) * 4.0)
