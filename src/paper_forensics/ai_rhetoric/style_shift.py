from __future__ import annotations

import math

from paper_forensics.nlp.token_features import content_ratio, punctuation_entropy, sentence_length


def style_shift_score(current: str, neighbors: list[str]) -> float:
    if not neighbors:
        return 0.0
    current_vec = _style_vector(current)
    neighbor_vecs = [_style_vector(text) for text in neighbors if text.strip()]
    if not neighbor_vecs:
        return 0.0
    centroid = [sum(values) / len(neighbor_vecs) for values in zip(*neighbor_vecs)]
    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(current_vec, centroid)))
    return min(1.0, distance / 18.0)


def smoothness_score(current: str, neighbors: list[str]) -> float:
    window = [text for text in neighbors if text.strip()]
    if not window:
        return 0.0
    lengths = [sentence_length(text) for text in window + [current]]
    mean = sum(lengths) / len(lengths)
    variance = sum((value - mean) ** 2 for value in lengths) / len(lengths)
    return max(0.0, min(1.0, 1.0 - min(variance / 40.0, 1.0)))


def _style_vector(text: str) -> tuple[float, float, float]:
    return (
        float(sentence_length(text)),
        content_ratio(text),
        punctuation_entropy(text),
    )
