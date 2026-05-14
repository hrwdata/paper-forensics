from pathlib import Path

from paper_forensics.ingest.tex_project import load_tex_project


def test_tex_project_inlines_sections_and_extracts_sentences() -> None:
    main_tex = Path("examples/sample_tex_project/main.tex")
    raw_tex, paragraphs, sentences = load_tex_project(main_tex)
    assert paragraphs
    assert sentences
    assert any(sentence.section == "Introduction" for sentence in sentences)
    assert any("robust framework" in sentence.clean_text.lower() for sentence in sentences)
    assert all(paragraph.raw_char_end >= paragraph.raw_char_start for paragraph in paragraphs)
    assert all(sentence.source_context_char_end >= sentence.source_context_char_start for sentence in sentences)
    assert all(raw_tex[sentence.source_context_char_start : sentence.source_context_char_end].strip() for sentence in sentences)
