import io
import zipfile
from pathlib import Path

from paper_forensics.app_server import detect_main_tex, prepare_uploaded_project
from paper_forensics.report.html_report import render_review_workspace


def test_detect_main_tex_prefers_main_document(tmp_path: Path) -> None:
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "appendix.tex").write_text("Appendix text", encoding="utf-8")
    (project_dir / "main.tex").write_text("\\begin{document}Main body\\end{document}", encoding="utf-8")

    assert detect_main_tex(project_dir) == project_dir / "main.tex"


def test_prepare_uploaded_project_extracts_zip_archive(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("paper/main.tex", "\\begin{document}Hello\\end{document}")
        archive.writestr("paper/sections/intro.tex", "Intro")

    root, main_tex = prepare_uploaded_project("paper.zip", buffer.getvalue(), tmp_path / "upload")

    assert root.exists()
    assert main_tex.name == "main.tex"
    assert main_tex.exists()


def test_render_review_workspace_in_app_mode_shows_upload_surface() -> None:
    html = render_review_workspace(initial_payload=None, app_mode=True, app_config={"mode": "app"})
    assert "Attach TeX manuscript or project archive" in html
    assert "Analyze" in html
