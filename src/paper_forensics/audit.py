from __future__ import annotations

from pathlib import Path

from paper_forensics.ai_rhetoric.score import AIRhetoricScorer
from paper_forensics.config import AuditConfig
from paper_forensics.ingest.tex_project import load_tex_project
from paper_forensics.plagiarism.corpus_index import LiteratureCorpusIndex
from paper_forensics.plagiarism.score import PlagiarismScorer
from paper_forensics.report.csv_export import write_csv
from paper_forensics.report.html_report import write_html_report
from paper_forensics.report.json_export import write_json
from paper_forensics.scoring.aggregate import aggregate_by_paragraph, aggregate_by_section, document_summary
from paper_forensics.scoring.schemas import AuditResult, SentenceAudit, portable_path


def run_audit(input_path: Path, config: AuditConfig) -> AuditResult:
    raw_tex_source, _, sentences = load_tex_project(input_path, min_sentence_chars=config.min_sentence_chars)
    corpus_index = (
        LiteratureCorpusIndex(
            config.corpus_path,
            phrase_ngram_range=config.phrase_ngram_range,
            min_tokens_for_overlap=config.min_tokens_for_overlap,
        )
        if config.corpus_path
        else None
    )
    plagiarism_scorer = PlagiarismScorer(corpus_index=corpus_index, config=config)
    ai_scorer = AIRhetoricScorer(config=config)

    audited_sentences: list[SentenceAudit] = []
    for idx, sentence in enumerate(sentences):
        neighbors = sentences[max(0, idx - 2) : idx] + sentences[idx + 1 : idx + 3]
        plagiarism_score, plagiarism_evidence = plagiarism_scorer.score_sentence(sentence)
        ai_score, ai_evidence = ai_scorer.score_sentence(sentence, neighbors)
        audited_sentences.append(
            SentenceAudit(
                sentence=sentence,
                plagiarism_risk_score=plagiarism_score,
                ai_rhetoric_risk_score=ai_score,
                plagiarism_evidence=plagiarism_evidence,
                ai_evidence=ai_evidence,
            )
        )

    paragraph_scores = aggregate_by_paragraph(audited_sentences)
    section_scores = aggregate_by_section(audited_sentences)
    summary = document_summary(audited_sentences)

    result = AuditResult(
        input_path=portable_path(input_path),
        corpus_path=portable_path(config.corpus_path) if config.corpus_path else None,
        sentences=audited_sentences,
        paragraphs=paragraph_scores,
        sections=section_scores,
        document_summary=summary,
        raw_tex_source=raw_tex_source,
    )

    config.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = config.output_dir / "audit.json"
    csv_path = config.output_dir / "audit.csv"
    html_path = config.output_dir / "report.html"
    result.generated_files = {
        "json": "audit.json",
        "csv": "audit.csv",
        "html": "report.html",
    }
    write_json(result, json_path)
    write_csv(result, csv_path)
    write_html_report(result, html_path)
    return result
