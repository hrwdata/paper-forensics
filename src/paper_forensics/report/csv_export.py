from __future__ import annotations

import csv
from pathlib import Path

from paper_forensics.scoring.schemas import AuditResult


def write_csv(result: AuditResult, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sentence_id",
                "section",
                "subsection",
                "clean_text",
                "plagiarism_risk_score",
                "ai_rhetoric_risk_score",
                "triggered_phrases",
                "top_match_label",
                "top_match_text",
            ],
        )
        writer.writeheader()
        for sentence in result.sentences:
            top_match = sentence.plagiarism_evidence.top_matches[0] if sentence.plagiarism_evidence.top_matches else None
            writer.writerow(
                {
                    "sentence_id": sentence.sentence.sentence_id,
                    "section": sentence.sentence.section,
                    "subsection": sentence.sentence.subsection,
                    "clean_text": sentence.sentence.clean_text,
                    "plagiarism_risk_score": round(sentence.plagiarism_risk_score, 4),
                    "ai_rhetoric_risk_score": round(sentence.ai_rhetoric_risk_score, 4),
                    "triggered_phrases": "; ".join(sentence.ai_evidence.triggered_phrases),
                    "top_match_label": top_match.source_label if top_match else "",
                    "top_match_text": top_match.matched_text if top_match else "",
                }
            )
