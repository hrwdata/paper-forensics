from __future__ import annotations

from collections import defaultdict

from paper_forensics.scoring.schemas import AggregateScore, SentenceAudit


def aggregate_by_paragraph(sentences: list[SentenceAudit]) -> list[AggregateScore]:
    grouped: dict[str, list[SentenceAudit]] = defaultdict(list)
    for sentence in sentences:
        grouped[sentence.sentence.paragraph_id].append(sentence)
    return _aggregate(grouped)


def aggregate_by_section(sentences: list[SentenceAudit]) -> list[AggregateScore]:
    grouped: dict[str, list[SentenceAudit]] = defaultdict(list)
    for sentence in sentences:
        grouped[sentence.sentence.section].append(sentence)
    return _aggregate(grouped)


def document_summary(sentences: list[SentenceAudit]) -> dict[str, float | int | list[dict[str, float | str]]]:
    if not sentences:
        return {
            "sentence_count": 0,
            "mean_plagiarism_risk": 0.0,
            "mean_ai_rhetoric_risk": 0.0,
            "top_plagiarism_sentences": [],
            "top_ai_sentences": [],
        }

    plagiarism_scores = [sentence.plagiarism_risk_score for sentence in sentences]
    ai_scores = [sentence.ai_rhetoric_risk_score for sentence in sentences]
    top_plagiarism = sorted(sentences, key=lambda item: item.plagiarism_risk_score, reverse=True)[:5]
    top_ai = sorted(sentences, key=lambda item: item.ai_rhetoric_risk_score, reverse=True)[:5]
    return {
        "sentence_count": len(sentences),
        "mean_plagiarism_risk": sum(plagiarism_scores) / len(plagiarism_scores),
        "mean_ai_rhetoric_risk": sum(ai_scores) / len(ai_scores),
        "top_plagiarism_sentences": _top_payload(top_plagiarism, "plagiarism_risk_score"),
        "top_ai_sentences": _top_payload(top_ai, "ai_rhetoric_risk_score"),
    }


def _aggregate(grouped: dict[str, list[SentenceAudit]]) -> list[AggregateScore]:
    rows: list[AggregateScore] = []
    for label, items in grouped.items():
        plagiarism_scores = [item.plagiarism_risk_score for item in items]
        ai_scores = [item.ai_rhetoric_risk_score for item in items]
        rows.append(
            AggregateScore(
                label=label,
                mean_plagiarism_risk=sum(plagiarism_scores) / len(plagiarism_scores),
                mean_ai_rhetoric_risk=sum(ai_scores) / len(ai_scores),
                max_plagiarism_risk=max(plagiarism_scores),
                max_ai_rhetoric_risk=max(ai_scores),
                sentence_ids=[item.sentence.sentence_id for item in items],
            )
        )
    return sorted(rows, key=lambda row: row.label)


def _top_payload(items: list[SentenceAudit], field_name: str) -> list[dict[str, float | str]]:
    payload: list[dict[str, float | str]] = []
    for item in items:
        payload.append(
            {
                "sentence_id": item.sentence.sentence_id,
                "section": item.sentence.section,
                "text": item.sentence.clean_text,
                "score": getattr(item, field_name),
            }
        )
    return payload
