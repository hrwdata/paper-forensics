from __future__ import annotations

from dataclasses import dataclass

from paper_forensics.ai_rhetoric.classifier import heuristic_classifier_score
from paper_forensics.ai_rhetoric.phrase_rules import load_phrase_rules, match_phrase_details
from paper_forensics.ai_rhetoric.style_shift import smoothness_score, style_shift_score
from paper_forensics.config import AuditConfig
from paper_forensics.nlp.token_features import abstract_word_ratio, content_ratio, starts_with_discourse_marker, tokenize
from paper_forensics.scoring.schemas import AIRhetoricEvidence, SentenceRecord

FINDING_SUMMARY_THRESHOLD = 0.25
CANONICAL_TRIGGER_CATEGORIES = {
    "balanced_but_empty_summary": "balanced_summary",
    "empty_transition": "empty_transition",
    "framework_boilerplate": "framework_boilerplate",
    "novelty_inflation": "unsupported_confidence",
    "unsupported_confidence": "unsupported_confidence",
}

LOW_SPECIFICITY_TOKENS = {
    "approach",
    "comprehensive",
    "crucial",
    "effective",
    "facilitates",
    "framework",
    "highlights",
    "important",
    "insight",
    "illustrates",
    "leverages",
    "methodology",
    "multiple",
    "noteworthy",
    "novel",
    "perspective",
    "promising",
    "robust",
    "significant",
    "substantial",
    "valuable",
    "various",
}

@dataclass
class AIRhetoricScorer:
    config: AuditConfig

    def __post_init__(self) -> None:
        self.rules = load_phrase_rules()

    def score_sentence(self, sentence: SentenceRecord, neighbors: list[SentenceRecord]) -> tuple[float, AIRhetoricEvidence]:
        matched_details = match_phrase_details(sentence.clean_text, self.rules)
        triggered_phrases = _matched_phrases(matched_details)
        triggered_categories = _canonical_trigger_categories(matched_details)
        empty_transition = _category_phrase_score(matched_details, "empty_transition")
        framework_boilerplate = _category_phrase_score(matched_details, "framework_boilerplate")
        unsupported_confidence = max(
            _category_phrase_score(matched_details, "unsupported_confidence"),
            _category_phrase_score(matched_details, "novelty_inflation"),
        )
        balanced_summary = _category_phrase_score(matched_details, "balanced_but_empty_summary")
        low_specificity = low_specificity_score(sentence.clean_text)
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
            empty_transition_score=empty_transition,
            framework_boilerplate_score=framework_boilerplate,
            unsupported_confidence_score=unsupported_confidence,
            balanced_summary_score=balanced_summary,
            low_specificity_score=low_specificity,
            finding_summary=build_finding_summary(
                {
                    "empty_transition": empty_transition,
                    "framework_boilerplate": framework_boilerplate,
                    "unsupported_confidence": unsupported_confidence,
                    "balanced_summary": balanced_summary,
                    "low_specificity": low_specificity,
                }
            ),
        )
        return score, evidence


def semantic_thinness_score(text: str) -> float:
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    content = content_ratio(text)
    abstract_ratio = abstract_word_ratio(text)
    low_specificity = low_specificity_score(text)
    discourse_bonus = 0.15 if starts_with_discourse_marker(text) else 0.0
    length_bonus = 0.1 if len(tokens) >= 18 else 0.0
    thinness = (1.0 - content) * 0.25 + abstract_ratio * 0.25 + low_specificity * 0.35 + discourse_bonus + length_bonus
    return max(0.0, min(1.0, thinness))


def low_specificity_score(text: str) -> float:
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    abstract_ratio = abstract_word_ratio(text)
    content = content_ratio(text)
    vague_hits = sum(token in LOW_SPECIFICITY_TOKENS for token in tokens)
    vague_ratio = vague_hits / len(tokens)
    low_specificity = abstract_ratio * 1.3 + max(0.0, 0.7 - content) * 0.6 + min(0.35, vague_ratio * 1.8)
    return max(0.0, min(1.0, low_specificity))


def _category_phrase_score(details: dict[str, list[str]], category: str) -> float:
    return min(1.0, len(details.get(category, ())) / 2.0)


def _matched_phrases(details: dict[str, list[str]]) -> list[str]:
    return sorted({phrase for matched in details.values() for phrase in matched})


def _canonical_trigger_categories(details: dict[str, list[str]]) -> list[str]:
    categories = {
        CANONICAL_TRIGGER_CATEGORIES.get(category, category)
        for category, matched in details.items()
        if matched
    }
    return sorted(categories)


def build_finding_summary(category_scores: dict[str, float]) -> str:
    ranked = sorted(category_scores.items(), key=lambda item: (-item[1], item[0]))
    visible = [(label, score) for label, score in ranked if score >= FINDING_SUMMARY_THRESHOLD]
    if not visible and ranked and ranked[0][1] > 0:
        visible = [ranked[0]]
    return "|".join(f"{label}={score:.2f}" for label, score in visible)
