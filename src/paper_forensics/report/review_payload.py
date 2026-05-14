from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from paper_forensics.scoring.schemas import AuditResult, SentenceAudit


def build_review_payload(result: AuditResult) -> dict[str, Any]:
    rows = [_row_payload(sentence, result.raw_tex_source, order=index) for index, sentence in enumerate(result.sentences)]
    rows.sort(key=lambda row: (row["paragraph_index"], row["sentence_index"], row["order"]))
    paragraphs = _paragraph_payload(rows)
    outline = _outline_payload(rows, paragraphs)
    spans = _suspicious_span_payload(paragraphs)
    metrics = _metric_payload(rows, paragraphs, result)
    return {
        "document": {
            "title": _document_title(result),
            "input_path": result.input_path,
            "input_name": Path(result.input_path).name,
            "corpus_path": result.corpus_path,
            "generated_files": {label: _download_link(path) for label, path in result.generated_files.items()},
            "sentence_count": len(rows),
            "paragraph_count": len(paragraphs),
        },
        "summary": result.document_summary,
        "metrics": metrics,
        "rows": rows,
        "paragraphs": paragraphs,
        "outline": outline,
        "suspicious_spans": spans,
        "filters": {
            "sections": [section.label for section in result.sections],
            "default_plagiarism_threshold": 0.45,
            "default_ai_threshold": 0.45,
            "flagged_threshold": 0.6,
        },
        "legend": {
            "plagiarism_label": "Estimated overlap risk",
            "ai_label": "Estimated AI-style risk",
            "caveat": (
                "These scores are heuristic review aids. They are not definitive findings of authorship, plagiarism, "
                "or misconduct."
            ),
        },
    }


def review_payload_json(result: AuditResult) -> str:
    return json.dumps(build_review_payload(result))


def _row_payload(sentence: SentenceAudit, raw_tex_source: str, order: int) -> dict[str, Any]:
    payload = sentence.to_dict()
    record = payload["sentence"]
    top_matches = payload["plagiarism_evidence"]["top_matches"]
    top_match = top_matches[0] if top_matches else None
    line_start, line_end = _line_span(
        raw_tex_source,
        record["source_context_char_start"],
        record["source_context_char_end"],
    )
    plagiarism = round(payload["plagiarism_risk_score"], 3)
    ai_risk = round(payload["ai_rhetoric_risk_score"], 3)
    combined = round(max(plagiarism, ai_risk), 3)
    has_external_match = bool(top_matches and any(match["vector_similarity"] > 0 for match in top_matches))
    has_ai_trigger = bool(payload["ai_evidence"]["triggered_phrases"])
    is_flagged = plagiarism >= 0.6 or ai_risk >= 0.6
    return {
        "order": order,
        "sentence_id": record["sentence_id"],
        "paragraph_id": record["paragraph_id"],
        "paragraph_index": record["paragraph_index"],
        "sentence_index": record["sentence_index"],
        "section": record["section"],
        "subsection": record["subsection"],
        "location_label": _location_label(record["section"], record["subsection"], line_start, line_end),
        "line_start": line_start,
        "line_end": line_end,
        "source_context_label": _line_label(line_start, line_end, prefix="Context "),
        "line_label": _line_label(line_start, line_end),
        "source_file": record["source_file"],
        "clean_text": record["clean_text"],
        "raw_tex_fragment": record["raw_tex_fragment"],
        "raw_tex_context": record["raw_tex_context"],
        "plagiarism_risk_score": plagiarism,
        "ai_rhetoric_risk_score": ai_risk,
        "combined_risk": combined,
        "plagiarism_band": _risk_band(plagiarism),
        "ai_band": _risk_band(ai_risk),
        "combined_band": _risk_band(combined),
        "has_external_match": has_external_match,
        "has_ai_trigger": has_ai_trigger,
        "is_flagged": is_flagged,
        "flag_reason": _flag_reason(plagiarism, ai_risk, has_external_match, has_ai_trigger),
        "summary": _sentence_summary(payload, top_match),
        "triggered_phrases": payload["ai_evidence"]["triggered_phrases"],
        "triggered_categories": payload["ai_evidence"]["triggered_categories"],
        "top_match": top_match,
        "top_matches": top_matches,
        "feature_breakdown": _feature_breakdown(payload),
        "all_data": payload,
    }


def _paragraph_payload(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["paragraph_id"]].append(row)

    paragraphs: list[dict[str, Any]] = []
    for paragraph_id, items in grouped.items():
        ordered = sorted(items, key=lambda row: row["sentence_index"])
        combined = max(row["combined_risk"] for row in ordered)
        paragraphs.append(
            {
                "paragraph_id": paragraph_id,
                "paragraph_index": ordered[0]["paragraph_index"],
                "section": ordered[0]["section"],
                "subsection": ordered[0]["subsection"],
                "line_start": min(row["line_start"] for row in ordered),
                "line_end": max(row["line_end"] for row in ordered),
                "location_label": _location_label(
                    ordered[0]["section"],
                    ordered[0]["subsection"],
                    min(row["line_start"] for row in ordered),
                    max(row["line_end"] for row in ordered),
                ),
                "paragraph_band": _risk_band(combined),
                "combined_risk": round(combined, 3),
                "plagiarism_risk_score": round(max(row["plagiarism_risk_score"] for row in ordered), 3),
                "ai_rhetoric_risk_score": round(max(row["ai_rhetoric_risk_score"] for row in ordered), 3),
                "sentence_ids": [row["sentence_id"] for row in ordered],
                "sentence_count": len(ordered),
                "has_external_match": any(row["has_external_match"] for row in ordered),
                "has_ai_trigger": any(row["has_ai_trigger"] for row in ordered),
                "is_flagged": any(row["is_flagged"] for row in ordered),
                "display_text": " ".join(row["clean_text"] for row in ordered),
                "raw_tex_context": ordered[0]["raw_tex_context"],
                "rows": ordered,
            }
        )
    return sorted(paragraphs, key=lambda item: item["paragraph_index"])


def _outline_payload(rows: list[dict[str, Any]], paragraphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paragraph_lookup = {paragraph["paragraph_id"]: paragraph for paragraph in paragraphs}
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        section = row["section"] or "Untitled"
        entry = grouped.setdefault(
            section,
            {
                "label": section,
                "line_start": row["line_start"],
                "line_end": row["line_end"],
                "sentence_count": 0,
                "flagged_count": 0,
                "paragraph_ids": [],
                "subsections": defaultdict(
                    lambda: {"label": "", "line_start": 10**9, "sentence_count": 0, "flagged_count": 0, "paragraph_ids": []}
                ),
            },
        )
        entry["line_start"] = min(entry["line_start"], row["line_start"])
        entry["line_end"] = max(entry["line_end"], row["line_end"])
        entry["sentence_count"] += 1
        entry["flagged_count"] += int(row["is_flagged"])
        if row["paragraph_id"] not in entry["paragraph_ids"]:
            entry["paragraph_ids"].append(row["paragraph_id"])

        subsection_label = row["subsection"] or ""
        if subsection_label:
            subsection = entry["subsections"][subsection_label]
            subsection["label"] = subsection_label
            subsection["line_start"] = min(subsection["line_start"], row["line_start"])
            subsection["sentence_count"] += 1
            subsection["flagged_count"] += int(row["is_flagged"])
            if row["paragraph_id"] not in subsection["paragraph_ids"]:
                subsection["paragraph_ids"].append(row["paragraph_id"])

    outline: list[dict[str, Any]] = []
    for section in grouped.values():
        paragraph_items = [paragraph_lookup[paragraph_id] for paragraph_id in section["paragraph_ids"]]
        suspicious = sum(1 for paragraph in paragraph_items if paragraph["combined_risk"] >= 0.45)
        subsection_items = []
        for subsection in section["subsections"].values():
            subsection_items.append(
                {
                    "label": subsection["label"],
                    "line_start": subsection["line_start"],
                    "sentence_count": subsection["sentence_count"],
                    "flagged_count": subsection["flagged_count"],
                    "paragraph_ids": subsection["paragraph_ids"],
                }
            )
        subsection_items.sort(key=lambda item: item["line_start"])
        outline.append(
            {
                "label": section["label"],
                "line_start": section["line_start"],
                "line_end": section["line_end"],
                "sentence_count": section["sentence_count"],
                "paragraph_count": len(section["paragraph_ids"]),
                "flagged_count": section["flagged_count"],
                "suspicious_paragraph_count": suspicious,
                "paragraph_ids": section["paragraph_ids"],
                "subsections": subsection_items,
            }
        )
    return sorted(outline, key=lambda item: item["line_start"])


def _suspicious_span_payload(paragraphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for paragraph in paragraphs:
        suspicious = paragraph["combined_risk"] >= 0.45 or paragraph["has_external_match"] or paragraph["has_ai_trigger"]
        if not suspicious:
            if current:
                spans.append(_finalize_span(current))
                current = None
            continue

        if (
            current
            and current["section"] == paragraph["section"]
            and paragraph["paragraph_index"] == current["end_paragraph_index"] + 1
        ):
            current["paragraph_ids"].append(paragraph["paragraph_id"])
            current["sentence_ids"].extend(paragraph["sentence_ids"])
            current["end_paragraph_index"] = paragraph["paragraph_index"]
            current["line_end"] = paragraph["line_end"]
            current["max_combined_risk"] = max(current["max_combined_risk"], paragraph["combined_risk"])
            current["max_plagiarism_risk"] = max(current["max_plagiarism_risk"], paragraph["plagiarism_risk_score"])
            current["max_ai_risk"] = max(current["max_ai_risk"], paragraph["ai_rhetoric_risk_score"])
            current["flagged_count"] += int(paragraph["is_flagged"])
        else:
            if current:
                spans.append(_finalize_span(current))
            current = {
                "section": paragraph["section"],
                "paragraph_ids": [paragraph["paragraph_id"]],
                "sentence_ids": list(paragraph["sentence_ids"]),
                "start_paragraph_index": paragraph["paragraph_index"],
                "end_paragraph_index": paragraph["paragraph_index"],
                "line_start": paragraph["line_start"],
                "line_end": paragraph["line_end"],
                "max_combined_risk": paragraph["combined_risk"],
                "max_plagiarism_risk": paragraph["plagiarism_risk_score"],
                "max_ai_risk": paragraph["ai_rhetoric_risk_score"],
                "flagged_count": int(paragraph["is_flagged"]),
            }
    if current:
        spans.append(_finalize_span(current))
    return spans[:24]


def _finalize_span(span: dict[str, Any]) -> dict[str, Any]:
    start = span["start_paragraph_index"]
    end = span["end_paragraph_index"]
    paragraph_label = f"P{start}" if start == end else f"P{start}-P{end}"
    return {
        "span_id": f"span-{start}-{end}-{span['line_start']}",
        "label": f"{span['section']} · {paragraph_label}",
        "section": span["section"],
        "paragraph_ids": span["paragraph_ids"],
        "sentence_ids": span["sentence_ids"],
        "line_start": span["line_start"],
        "line_end": span["line_end"],
        "line_label": _line_label(span["line_start"], span["line_end"]),
        "max_combined_risk": round(span["max_combined_risk"], 3),
        "max_plagiarism_risk": round(span["max_plagiarism_risk"], 3),
        "max_ai_risk": round(span["max_ai_risk"], 3),
        "flagged_count": span["flagged_count"],
        "paragraph_count": len(span["paragraph_ids"]),
        "band": _risk_band(span["max_combined_risk"]),
    }


def _metric_payload(rows: list[dict[str, Any]], paragraphs: list[dict[str, Any]], result: AuditResult) -> dict[str, Any]:
    flagged_rows = [row for row in rows if row["is_flagged"]]
    external_match_rows = [row for row in rows if row["has_external_match"]]
    trigger_rows = [row for row in rows if row["has_ai_trigger"]]
    return {
        "flagged_sentence_count": len(flagged_rows),
        "external_match_count": len(external_match_rows),
        "triggered_sentence_count": len(trigger_rows),
        "suspicious_span_count": len(_suspicious_span_payload(paragraphs)),
        "max_plagiarism_risk": round(max((row["plagiarism_risk_score"] for row in rows), default=0.0), 3),
        "max_ai_risk": round(max((row["ai_rhetoric_risk_score"] for row in rows), default=0.0), 3),
        "section_count": len(result.sections),
    }


def _document_title(result: AuditResult) -> str:
    return Path(result.input_path).stem.replace("_", " ").replace("-", " ").strip().title() or "Untitled Review"


def _download_link(path: str) -> str:
    return path


def _line_span(raw_tex_source: str, char_start: int, char_end: int) -> tuple[int, int]:
    if not raw_tex_source:
        return 1, 1
    start = max(0, min(char_start, len(raw_tex_source)))
    end = max(start, min(char_end, len(raw_tex_source)))
    return _line_number(raw_tex_source, start), _line_number(raw_tex_source, max(start, end - 1))


def _line_number(text: str, char_index: int) -> int:
    return text.count("\n", 0, max(char_index, 0)) + 1


def _line_label(line_start: int, line_end: int, prefix: str = "") -> str:
    if line_start == line_end:
        return f"{prefix}L{line_start}"
    return f"{prefix}L{line_start}-L{line_end}"


def _location_label(section: str, subsection: str, line_start: int, line_end: int) -> str:
    label = subsection or section or "Untitled"
    return f"{label} · {_line_label(line_start, line_end)}"


def _risk_band(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _flag_reason(plagiarism: float, ai_risk: float, has_external_match: bool, has_ai_trigger: bool) -> str:
    if plagiarism >= 0.6 and ai_risk >= 0.6:
        return "Review required for overlap and style-pattern signals."
    if plagiarism >= 0.6:
        return "Review required for elevated overlap evidence."
    if ai_risk >= 0.6:
        return "Review required for elevated style-pattern signals."
    if has_external_match:
        return "External match evidence is available for review."
    if has_ai_trigger:
        return "Style-pattern triggers are available for review."
    return "No elevated review flag."


def _sentence_summary(payload: dict[str, Any], top_match: dict[str, Any] | None) -> str:
    plagiarism = payload["plagiarism_risk_score"]
    ai_risk = payload["ai_rhetoric_risk_score"]
    phrases = payload["ai_evidence"]["triggered_phrases"]
    if plagiarism >= 0.6 and top_match:
        return f"Elevated overlap signal with strongest local match in {top_match['source_label']}."
    if ai_risk >= 0.6 and phrases:
        return f"Elevated style-pattern signal with triggers such as {', '.join(phrases[:2])}."
    if top_match:
        return f"Overlap evidence available from {top_match['source_label']} for reviewer inspection."
    if phrases:
        return f"Style-pattern triggers detected: {', '.join(phrases[:2])}."
    return "Lower-signal sentence; review only if needed in context."


def _feature_breakdown(payload: dict[str, Any]) -> dict[str, list[dict[str, float | str]]]:
    plagiarism = payload["plagiarism_evidence"]
    ai_evidence = payload["ai_evidence"]
    return {
        "plagiarism": [
            {"label": "Vector similarity", "value": round(plagiarism["vector_similarity_score"], 3)},
            {"label": "Lexical overlap", "value": round(plagiarism["lexical_overlap_score"], 3)},
            {"label": "Rare phrase overlap", "value": round(plagiarism["rare_phrase_overlap_score"], 3)},
            {"label": "Boilerplate discount", "value": round(plagiarism["boilerplate_discount"], 3)},
        ],
        "ai": [
            {"label": "Phrase-pattern score", "value": round(ai_evidence["phrase_pattern_score"], 3)},
            {"label": "Semantic thinness", "value": round(ai_evidence["semantic_thinness_score"], 3)},
            {"label": "Style shift", "value": round(ai_evidence["style_shift_score"], 3)},
            {"label": "Smoothness", "value": round(ai_evidence["smoothness_score"], 3)},
            {"label": "Heuristic classifier", "value": round(ai_evidence["heuristic_classifier_score"], 3)},
            {"label": "Content ratio", "value": round(ai_evidence["content_ratio"], 3)},
            {"label": "Abstract word ratio", "value": round(ai_evidence["abstract_word_ratio"], 3)},
        ],
    }
