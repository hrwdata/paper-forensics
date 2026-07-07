from __future__ import annotations

from collections import Counter
from itertools import islice

from paper_forensics.ingest.normalize import normalize_text
from paper_forensics.nlp.token_features import tokenize


def lexical_overlap_score(text_a: str, text_b: str, min_tokens: int = 5) -> float:
    tokens_a = {token for token in tokenize(text_a) if len(token) > 2}
    tokens_b = {token for token in tokenize(text_b) if len(token) > 2}
    if len(tokens_a) < min_tokens or len(tokens_b) < min_tokens:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def ngram_counts(text: str, min_n: int = 3, max_n: int = 5, min_tokens: int = 0) -> Counter[str]:
    tokens = normalize_text(text).split()
    if len(tokens) < min_tokens:
        return Counter()
    counts: Counter[str] = Counter()
    for n in range(min_n, max_n + 1):
        if len(tokens) < n:
            continue
        for idx in range(0, len(tokens) - n + 1):
            gram = " ".join(islice(tokens, idx, idx + n))
            counts[gram] += 1
    return counts

def overlapping_phrases(
    text_a: str,
    text_b: str,
    min_n: int = 3,
    max_n: int = 5,
    min_tokens: int = 0,
) -> list[str]:
    grams_a = set(ngram_counts(text_a, min_n=min_n, max_n=max_n, min_tokens=min_tokens))
    grams_b = set(ngram_counts(text_b, min_n=min_n, max_n=max_n, min_tokens=min_tokens))
    return sorted(grams_a & grams_b, key=len, reverse=True)
