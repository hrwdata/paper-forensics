from __future__ import annotations

from collections import Counter, defaultdict

from paper_forensics.scoring.schemas import AggregateScore, SentenceAudit

AI_TELL_CATEGORY_THRESHOLD = 0.25


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
            "ai_tell_category_totals": {},
            "top_ai_tell_findings": [],
            "top_plagiarism_sentences": [],
            "top_ai_sentences": [],
        }

    plagiarism_scores = [sentence.plagiarism_risk_score for sentence in sentences]
    ai_scores = [sentence.ai_rhetoric_risk_score for sentence in sentences]
    top_plagiarism = sorted(sentences, key=lambda item: item.plagiarism_risk_score, reverse=True)[:5]
    top_ai = sorted(sentences, key=lambda item: item.ai_rhetoric_risk_score, reverse=True)[:5]
    category_totals = _ai_tell_category_totals(sentences)
    return {
        "sentence_count": len(sentences),
        "mean_plagiarism_risk": sum(plagiarism_scores) / len(plagiarism_scores),
        "mean_ai_rhetoric_risk": sum(ai_scores) / len(ai_scores),
        "ai_tell_category_totals": dict(sorted(category_totals.items())),
        "top_ai_tell_findings": _top_ai_tell_findings(top_ai),
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


def _ai_tell_category_totals(items: list[SentenceAudit]) -> Counter[str]:
    totals: Counter[str] = Counter()
    for item in items:
        evidence = item.ai_evidence
        if evidence.empty_transition_score >= AI_TELL_CATEGORY_THRESHOLD:
            totals["empty_transition"] += 1
        if evidence.framework_boilerplate_score >= AI_TELL_CATEGORY_THRESHOLD:
            totals["framework_boilerplate"] += 1
        if evidence.unsupported_confidence_score >= AI_TELL_CATEGORY_THRESHOLD:
            totals["unsupported_confidence"] += 1
        if evidence.balanced_summary_score >= AI_TELL_CATEGORY_THRESHOLD:
            totals["balanced_summary"] += 1
        if evidence.low_specificity_score >= AI_TELL_CATEGORY_THRESHOLD:
            totals["low_specificity"] += 1
    return totals


def _top_ai_tell_findings(items: list[SentenceAudit]) -> list[dict[str, float | str | list[str]]]:
    payload: list[dict[str, float | str | list[str]]] = []
    for item in items:
        payload.append(
            {
                "sentence_id": item.sentence.sentence_id,
                "section": item.sentence.section,
                "text": item.sentence.clean_text,
                "score": item.ai_rhetoric_risk_score,
                "finding_summary": item.ai_evidence.finding_summary,
                "triggered_categories": item.ai_evidence.triggered_categories,
            }
        )
    return payload
