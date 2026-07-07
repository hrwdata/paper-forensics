import json
from pathlib import Path

from paper_forensics.audit import run_audit
from paper_forensics.config import AuditConfig


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
