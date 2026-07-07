import json
from pathlib import Path

from paper_forensics.audit import run_audit
from paper_forensics.config import AuditConfig
from paper_forensics.scoring.aggregate import document_summary
from paper_forensics.scoring.schemas import AIRhetoricEvidence, PlagiarismEvidence, SentenceAudit, SentenceRecord


def test_end_to_end_audit_writes_outputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "report"
    result = run_audit(
        Path("examples/sample_tex_project/main.tex"),
        AuditConfig(corpus_path=Path("examples/corpus"), output_dir=output_dir),
    )
    assert result.sentences
    assert (output_dir / "audit.json").exists()
    assert (output_dir / "audit.csv").exists()
    assert (output_dir / "report.html").exists()
    payload = json.loads((output_dir / "audit.json").read_text(encoding="utf-8"))
    assert payload["document_summary"]["sentence_count"] >= 4
    assert "ai_tell_category_totals" in payload["document_summary"]
    assert "top_ai_tell_findings" in payload["document_summary"]
    assert "raw_tex_source" in payload
    assert len(payload["generated_files"]) == 3
    csv_text = (output_dir / "audit.csv").read_text(encoding="utf-8")
    assert "triggered_categories" in csv_text
    assert "finding_summary" in csv_text
    html = (output_dir / "report.html").read_text(encoding="utf-8")
    assert "Primary manuscript viewer" in html
    assert "AI-assisted tell overview" in html
    assert "AI-assisted tell evidence" in html
    assert "Academic document review workspace" in html
    assert "Flagged sentences" in html
    assert "Review required" in html


def test_document_summary_counts_low_specificity_at_finding_threshold() -> None:
    sentence = SentenceAudit(
        sentence=SentenceRecord(
            sentence_id="test.sent_001",
            clean_text="This sentence is intentionally generic.",
            raw_tex_fragment="This sentence is intentionally generic.",
            raw_tex_context="This sentence is intentionally generic.",
            source_context_char_start=0,
            source_context_char_end=37,
            source_file="test.tex",
            section="Test",
            subsection="",
            paragraph_id="test.par_001",
            paragraph_index=1,
            sentence_index=1,
            char_start=0,
            char_end=37,
        ),
        plagiarism_risk_score=0.0,
        ai_rhetoric_risk_score=0.3,
        plagiarism_evidence=PlagiarismEvidence(
            vector_similarity_score=0.0,
            lexical_overlap_score=0.0,
            rare_phrase_overlap_score=0.0,
            boilerplate_discount=0.0,
            top_matches=[],
        ),
        ai_evidence=AIRhetoricEvidence(
            triggered_phrases=[],
            triggered_categories=[],
            phrase_pattern_score=0.0,
            semantic_thinness_score=0.0,
            style_shift_score=0.0,
            smoothness_score=0.0,
            heuristic_classifier_score=0.0,
            content_ratio=0.7,
            abstract_word_ratio=0.1,
            empty_transition_score=0.0,
            framework_boilerplate_score=0.0,
            unsupported_confidence_score=0.0,
            balanced_summary_score=0.0,
            low_specificity_score=0.3,
            finding_summary="low_specificity=0.30",
        ),
    )

    summary = document_summary([sentence])

    assert summary["ai_tell_category_totals"] == {"low_specificity": 1}
