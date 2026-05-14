from __future__ import annotations

import math
from collections import Counter

from paper_forensics.nlp.token_features import tokenize


class SentenceVectorIndex:
    def __init__(self, texts: list[str]) -> None:
        self.texts = texts
        if texts:
            self.document_count = len(texts)
            self.document_frequency = self._build_document_frequency(texts)
            self.vectors = [self._vectorize(text) for text in texts]
        else:
            self.document_count = 0
            self.document_frequency = {}
            self.vectors = []

    def top_matches(self, query: str, k: int = 3) -> list[tuple[int, float]]:
        if not self.texts:
            return []
        query_vector = self._vectorize(query)
        ranked = [
            (idx, _cosine_similarity(query_vector, vector))
            for idx, vector in enumerate(self.vectors)
        ]
        ranked.sort(key=lambda item: item[1], reverse=True)
        return [(idx, score) for idx, score in ranked[:k] if score > 0]

    def _build_document_frequency(self, texts: list[str]) -> dict[str, int]:
        frequencies: dict[str, int] = {}
        for text in texts:
            for token in set(_features(text)):
                frequencies[token] = frequencies.get(token, 0) + 1
        return frequencies

    def _vectorize(self, text: str) -> dict[str, float]:
        features = _features(text)
        counts = Counter(features)
        total = sum(counts.values()) or 1
        vector: dict[str, float] = {}
        for token, count in counts.items():
            tf = count / total
            df = self.document_frequency.get(token, 0)
            idf = math.log((1 + self.document_count) / (1 + df)) + 1.0
            vector[token] = tf * idf
        return vector


def _features(text: str) -> list[str]:
    tokens = tokenize(text)
    features = list(tokens)
    for n in (2, 3):
        if len(tokens) < n:
            continue
        for idx in range(0, len(tokens) - n + 1):
            features.append("_".join(tokens[idx : idx + n]))
    return features


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    shared = set(left) & set(right)
    numerator = sum(left[token] * right[token] for token in shared)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)
