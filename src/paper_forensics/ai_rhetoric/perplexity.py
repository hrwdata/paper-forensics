from __future__ import annotations


def pseudo_perplexity_score(_: str) -> float:
    """Placeholder hook for future LM-backed perplexity.

    The MVP keeps the workflow fully offline and dependency-light, so this returns 0.
    """

    return 0.0
