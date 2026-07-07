from pathlib import Path

from paper_forensics.ai_rhetoric.score import AIRhetoricScorer
from paper_forensics.config import AuditConfig
from paper_forensics.ingest.tex_project import load_tex_project
from paper_forensics.scoring.schemas import SentenceRecord


def test_ai_rhetoric_score_flags_boilerplate_phrases() -> None:
    _, _, sentences = load_tex_project(Path("examples/sample_tex_project/main.tex"))
    scorer = AIRhetoricScorer(config=AuditConfig())
    target_index = next(
        idx for idx, sentence in enumerate(sentences) if "important to note" in sentence.clean_text.lower()
    )
    target = sentences[target_index]
    neighbors = sentences[max(0, target_index - 1) : target_index] + sentences[target_index + 1 : target_index + 3]
    score, evidence = scorer.score_sentence(target, neighbors)
    assert score > 0.35
    assert "it is important to note" in evidence.triggered_phrases
    assert evidence.triggered_categories == ["empty_transition", "framework_boilerplate"]
    assert evidence.semantic_thinness_score > 0.2
    assert evidence.framework_boilerplate_score >= 0.5
    assert evidence.low_specificity_score > 0.2
    assert "framework_boilerplate" in evidence.finding_summary


def test_ai_rhetoric_score_flags_unsupported_confidence_language() -> None:
    scorer = AIRhetoricScorer(config=AuditConfig())
    sentence = _sentence("It is evident that this state-of-the-art method clearly demonstrates superior outcomes.")
    score, evidence = scorer.score_sentence(sentence, [])

    assert score > 0.2
    assert evidence.triggered_categories == ["unsupported_confidence"]
    assert evidence.unsupported_confidence_score >= 0.5
    assert "unsupported_confidence" in evidence.finding_summary


def test_ai_rhetoric_score_canonicalizes_balanced_summary_category() -> None:
    scorer = AIRhetoricScorer(config=AuditConfig())
    sentence = _sentence("The results demonstrate that local evidence is easier to inspect than a single label.")
    _, evidence = scorer.score_sentence(sentence, [])

    assert evidence.triggered_categories == ["balanced_summary"]
    assert evidence.triggered_phrases == ["the results demonstrate that"]
    assert "balanced_summary" in evidence.finding_summary


def test_ai_rhetoric_score_keeps_specific_sentence_low_signal() -> None:
    scorer = AIRhetoricScorer(config=AuditConfig())
    sentence = _sentence("The parser records source line spans for each sentence and preserves the section label.")
    score, evidence = scorer.score_sentence(sentence, [])

    assert score < 0.3
    assert evidence.low_specificity_score < 0.2
    assert not evidence.triggered_categories
    assert evidence.finding_summary == ""


def _sentence(text: str) -> SentenceRecord:
    return SentenceRecord(
        sentence_id="test.sent_001",
        clean_text=text,
        raw_tex_fragment=text,
        raw_tex_context=text,
        source_context_char_start=0,
        source_context_char_end=len(text),
        source_file="test.tex",
        section="Test",
        subsection="",
        paragraph_id="test.par_001",
        paragraph_index=1,
        sentence_index=1,
        char_start=0,
        char_end=len(text),
    )
