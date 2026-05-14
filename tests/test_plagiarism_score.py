from pathlib import Path

from paper_forensics.config import AuditConfig
from paper_forensics.ingest.tex_project import load_tex_project
from paper_forensics.plagiarism.corpus_index import LiteratureCorpusIndex
from paper_forensics.plagiarism.score import PlagiarismScorer
from paper_forensics.scoring.schemas import SentenceRecord


def test_plagiarism_score_flags_local_overlap() -> None:
    _, _, sentences = load_tex_project(Path("examples/sample_tex_project/main.tex"))
    target = next(sentence for sentence in sentences if "vector similarity against candidate source passages" in sentence.clean_text)
    scorer = PlagiarismScorer(
        corpus_index=LiteratureCorpusIndex(Path("examples/corpus")),
        config=AuditConfig(corpus_path=Path("examples/corpus")),
    )
    score, evidence = scorer.score_sentence(target)
    assert score > 0.45
    assert evidence.top_matches
    assert "similar_paper" in evidence.top_matches[0].source_label


def test_plagiarism_config_controls_overlap_thresholds(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    text = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
    (corpus_dir / "match.txt").write_text(text, encoding="utf-8")
    sentence = SentenceRecord(
        sentence_id="demo.par_001.sent_001",
        clean_text=text,
        raw_tex_fragment=text,
        raw_tex_context=text,
        source_context_char_start=0,
        source_context_char_end=len(text),
        source_file="demo.tex",
        section="Demo",
        subsection="",
        paragraph_id="demo.par_001",
        paragraph_index=1,
        sentence_index=1,
        char_start=0,
        char_end=len(text),
    )
    config = AuditConfig(
        corpus_path=corpus_dir,
        min_tokens_for_overlap=11,
        phrase_ngram_range=(5, 5),
    )
    scorer = PlagiarismScorer(
        corpus_index=LiteratureCorpusIndex(
            corpus_dir,
            phrase_ngram_range=config.phrase_ngram_range,
            min_tokens_for_overlap=config.min_tokens_for_overlap,
        ),
        config=config,
    )

    score, evidence = scorer.score_sentence(sentence)

    assert evidence.top_matches
    assert evidence.lexical_overlap_score == 0.0
    assert evidence.rare_phrase_overlap_score == 0.0
    assert score < 0.5
