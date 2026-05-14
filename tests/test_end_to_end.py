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
    assert "raw_tex_source" in payload
    assert len(payload["generated_files"]) == 3
    html = (output_dir / "report.html").read_text(encoding="utf-8")
    assert "Primary manuscript viewer" in html
    assert "Academic document review workspace" in html
    assert "Flagged sentences" in html
    assert "Review required" in html
