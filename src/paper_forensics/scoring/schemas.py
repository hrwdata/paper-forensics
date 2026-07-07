from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SentenceRecord:
    sentence_id: str
    clean_text: str
    raw_tex_fragment: str
    raw_tex_context: str
    source_context_char_start: int
    source_context_char_end: int
    source_file: str
    section: str
    subsection: str
    paragraph_id: str
    paragraph_index: int
    sentence_index: int
    char_start: int
    char_end: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MatchEvidence:
    source_path: str
    source_label: str
    matched_text: str
    vector_similarity: float
    lexical_overlap: float
    rare_phrase_overlap: float
    overlapping_phrases: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PlagiarismEvidence:
    vector_similarity_score: float
    lexical_overlap_score: float
    rare_phrase_overlap_score: float
    boilerplate_discount: float
    top_matches: list[MatchEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["top_matches"] = [match.to_dict() for match in self.top_matches]
        return payload


@dataclass
class AIRhetoricEvidence:
    triggered_phrases: list[str]
    triggered_categories: list[str]
    phrase_pattern_score: float
    semantic_thinness_score: float
    style_shift_score: float
    smoothness_score: float
    heuristic_classifier_score: float
    content_ratio: float
    abstract_word_ratio: float
    empty_transition_score: float
    framework_boilerplate_score: float
    unsupported_confidence_score: float
    balanced_summary_score: float
    low_specificity_score: float
    finding_summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SentenceAudit:
    sentence: SentenceRecord
    plagiarism_risk_score: float
    ai_rhetoric_risk_score: float
    plagiarism_evidence: PlagiarismEvidence
    ai_evidence: AIRhetoricEvidence

    def to_dict(self) -> dict[str, Any]:
        return {
            "sentence": self.sentence.to_dict(),
            "plagiarism_risk_score": self.plagiarism_risk_score,
            "ai_rhetoric_risk_score": self.ai_rhetoric_risk_score,
            "plagiarism_evidence": self.plagiarism_evidence.to_dict(),
            "ai_evidence": self.ai_evidence.to_dict(),
        }


@dataclass
class AggregateScore:
    label: str
    mean_plagiarism_risk: float
    mean_ai_rhetoric_risk: float
    max_plagiarism_risk: float
    max_ai_rhetoric_risk: float
    sentence_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditResult:
    input_path: str
    corpus_path: str | None
    sentences: list[SentenceAudit]
    paragraphs: list[AggregateScore]
    sections: list[AggregateScore]
    document_summary: dict[str, Any]
    raw_tex_source: str = ""
    generated_files: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_path": self.input_path,
            "corpus_path": self.corpus_path,
            "sentences": [sentence.to_dict() for sentence in self.sentences],
            "paragraphs": [paragraph.to_dict() for paragraph in self.paragraphs],
            "sections": [section.to_dict() for section in self.sections],
            "document_summary": self.document_summary,
            "raw_tex_source": self.raw_tex_source,
            "generated_files": self.generated_files,
        }


def resolve_output_path(path: Path) -> str:
    return portable_path(path)


def portable_path(path: str | Path | None) -> str:
    if path is None:
        return ""
    candidate = Path(path)
    if not candidate.is_absolute():
        return str(candidate)
    try:
        return str(candidate.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(candidate)
