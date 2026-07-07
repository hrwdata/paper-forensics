from pathlib import Path

from paper_forensics.audit import run_audit
from paper_forensics.config import AuditConfig
from paper_forensics.report.review_payload import build_review_payload


def test_review_payload_exposes_outline_spans_and_rows(tmp_path: Path) -> None:
    result = run_audit(
        Path("examples/sample_tex_project/main.tex"),
        AuditConfig(corpus_path=Path("examples/corpus"), output_dir=tmp_path / "artifacts"),
    )

    payload = build_review_payload(result)

    assert payload["document"]["sentence_count"] == len(payload["rows"])
    assert payload["outline"]
    assert payload["suspicious_spans"]
    assert payload["metrics"]["external_match_count"] >= 1
    assert "ai_tell_overview" in payload
    assert "category_totals" in payload["ai_tell_overview"]
    first_row = payload["rows"][0]
    assert "feature_breakdown" in first_row
    assert "ai_tell_summary" in first_row
    assert "ai_tell_subscores" in first_row
    assert "source_context_label" in first_row
    assert first_row["line_start"] <= first_row["line_end"]
