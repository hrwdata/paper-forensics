from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class AuditConfig:
    corpus_path: Path | None = None
    output_dir: Path = Path("outputs/latest")
    max_matches: int = 3
    min_sentence_chars: int = 25
    min_tokens_for_overlap: int = 5
    phrase_ngram_range: Tuple[int, int] = (3, 5)
    plagiarism_weights: dict[str, float] = field(
        default_factory=lambda: {
            "vector_similarity": 0.45,
            "lexical_overlap": 0.25,
            "rare_phrase_overlap": 0.25,
            "boilerplate_discount": -0.15,
        }
    )
    ai_weights: dict[str, float] = field(
        default_factory=lambda: {
            "phrase_pattern": 0.35,
            "semantic_thinness": 0.25,
            "style_shift": 0.20,
            "smoothness": 0.10,
            "heuristic_classifier": 0.10,
        }
    )
