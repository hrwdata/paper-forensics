from pathlib import Path

from paper_forensics.ai_rhetoric.score import AIRhetoricScorer
from paper_forensics.config import AuditConfig
from paper_forensics.ingest.tex_project import load_tex_project


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
    assert evidence.semantic_thinness_score > 0.2
