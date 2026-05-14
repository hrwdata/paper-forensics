from __future__ import annotations

from dataclasses import dataclass

from paper_forensics.config import AuditConfig
from paper_forensics.plagiarism.boilerplate import boilerplate_discount
from paper_forensics.plagiarism.corpus_index import LiteratureCorpusIndex
from paper_forensics.plagiarism.lexical_overlap import lexical_overlap_score, overlapping_phrases
from paper_forensics.scoring.schemas import MatchEvidence, PlagiarismEvidence, SentenceRecord


@dataclass
class PlagiarismScorer:
    corpus_index: LiteratureCorpusIndex | None
    config: AuditConfig

    def score_sentence(self, sentence: SentenceRecord) -> tuple[float, PlagiarismEvidence]:
        if self.corpus_index is None or not self.corpus_index.sentences:
            evidence = PlagiarismEvidence(
                vector_similarity_score=0.0,
                lexical_overlap_score=0.0,
                rare_phrase_overlap_score=0.0,
                boilerplate_discount=0.0,
                top_matches=[],
            )
            return 0.0, evidence

        candidates = self.corpus_index.top_matches(sentence.clean_text, k=self.config.max_matches)
        evidence_matches: list[MatchEvidence] = []
        max_vector = 0.0
        max_lexical = 0.0
        max_rare = 0.0

        min_n, max_n = self.config.phrase_ngram_range
        for corpus_sentence, vector_score in candidates:
            lexical_score = lexical_overlap_score(
                sentence.clean_text,
                corpus_sentence.text,
                min_tokens=self.config.min_tokens_for_overlap,
            )
            phrases = overlapping_phrases(
                sentence.clean_text,
                corpus_sentence.text,
                min_n=min_n,
                max_n=max_n,
                min_tokens=self.config.min_tokens_for_overlap,
            )
            rare_score = self._rare_phrase_overlap(phrases)
            evidence_matches.append(
                MatchEvidence(
                    source_path=corpus_sentence.source_path,
                    source_label=corpus_sentence.source_label,
                    matched_text=corpus_sentence.text,
                    vector_similarity=vector_score,
                    lexical_overlap=lexical_score,
                    rare_phrase_overlap=rare_score,
                    overlapping_phrases=phrases[:5],
                )
            )
            max_vector = max(max_vector, vector_score)
            max_lexical = max(max_lexical, lexical_score)
            max_rare = max(max_rare, rare_score)

        discount = boilerplate_discount(sentence.clean_text)
        weights = self.config.plagiarism_weights
        raw_score = (
            weights["vector_similarity"] * max_vector
            + weights["lexical_overlap"] * max_lexical
            + weights["rare_phrase_overlap"] * max_rare
            + weights["boilerplate_discount"] * discount
        )
        score = _clamp(raw_score)
        evidence = PlagiarismEvidence(
            vector_similarity_score=max_vector,
            lexical_overlap_score=max_lexical,
            rare_phrase_overlap_score=max_rare,
            boilerplate_discount=discount,
            top_matches=evidence_matches,
        )
        return score, evidence

    def _rare_phrase_overlap(self, phrases: list[str]) -> float:
        if not phrases or self.corpus_index is None:
            return 0.0
        scores: list[float] = []
        total_docs = max(len(self.corpus_index.sentences), 1)
        for phrase in phrases:
            frequency = self.corpus_index.phrase_document_frequency.get(phrase, 1)
            rarity = 1.0 - min(1.0, frequency / total_docs)
            length_bonus = min(1.0, len(phrase.split()) / 5.0)
            scores.append(0.5 * rarity + 0.5 * length_bonus)
        return max(scores) if scores else 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
