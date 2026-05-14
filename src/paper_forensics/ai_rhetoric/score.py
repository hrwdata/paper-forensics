from __future__ import annotations

from dataclasses import dataclass

from paper_forensics.ai_rhetoric.classifier import heuristic_classifier_score
from paper_forensics.ai_rhetoric.phrase_rules import load_phrase_rules, match_phrases
from paper_forensics.ai_rhetoric.style_shift import smoothness_score, style_shift_score
from paper_forensics.config import AuditConfig
from paper_forensics.nlp.token_features import abstract_word_ratio, content_ratio, starts_with_discourse_marker, tokenize
from paper_forensics.scoring.schemas import AIRhetoricEvidence, SentenceRecord


@dataclass
class AIRhetoricScorer:
    config: AuditConfig

    def __post_init__(self) -> None:
        self.rules = load_phrase_rules()

    def score_sentence(self, sentence: SentenceRecord, neighbors: list[SentenceRecord]) -> tuple[float, AIRhetoricEvidence]:
        triggered_phrases, triggered_categories = match_phrases(sentence.clean_text, self.rules)
        phrase_pattern = min(1.0, len(triggered_phrases) / 3.0)
        thinness = semantic_thinness_score(sentence.clean_text)
        shift = style_shift_score(sentence.clean_text, [neighbor.clean_text for neighbor in neighbors])
        smooth = smoothness_score(sentence.clean_text, [neighbor.clean_text for neighbor in neighbors])
        classifier = heuristic_classifier_score(phrase_pattern, thinness, shift)

        weights = self.config.ai_weights
        score = (
            weights["phrase_pattern"] * phrase_pattern
            + weights["semantic_thinness"] * thinness
            + weights["style_shift"] * shift
            + weights["smoothness"] * smooth
            + weights["heuristic_classifier"] * classifier
        )
        score = max(0.0, min(1.0, score))
        evidence = AIRhetoricEvidence(
            triggered_phrases=triggered_phrases,
            triggered_categories=triggered_categories,
            phrase_pattern_score=phrase_pattern,
            semantic_thinness_score=thinness,
            style_shift_score=shift,
            smoothness_score=smooth,
            heuristic_classifier_score=classifier,
            content_ratio=content_ratio(sentence.clean_text),
            abstract_word_ratio=abstract_word_ratio(sentence.clean_text),
        )
        return score, evidence


def semantic_thinness_score(text: str) -> float:
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    content = content_ratio(text)
    abstract_ratio = abstract_word_ratio(text)
    discourse_bonus = 0.15 if starts_with_discourse_marker(text) else 0.0
    length_bonus = 0.1 if len(tokens) >= 18 else 0.0
    vague_bonus = 0.1 if any(token in {"framework", "important", "valuable", "significant"} for token in tokens) else 0.0
    thinness = (1.0 - content) * 0.45 + abstract_ratio * 0.45 + discourse_bonus + length_bonus + vague_bonus
    return max(0.0, min(1.0, thinness))
