from __future__ import annotations


def heuristic_classifier_score(
    phrase_pattern_score: float,
    semantic_thinness_score: float,
    style_shift_score: float,
) -> float:
    return max(
        0.0,
        min(
            1.0,
            0.5 * phrase_pattern_score + 0.3 * semantic_thinness_score + 0.2 * style_shift_score,
        ),
    )
