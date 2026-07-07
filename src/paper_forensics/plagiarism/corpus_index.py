from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from paper_forensics.ingest.latex_clean import clean_tex_to_text
from paper_forensics.nlp.sentence_split import split_sentences
from paper_forensics.plagiarism.lexical_overlap import ngram_counts
from paper_forensics.plagiarism.semantic_match import SentenceVectorIndex
from paper_forensics.scoring.schemas import portable_path


@dataclass
class CorpusSentence:
    source_path: str
    source_label: str
    text: str


class LiteratureCorpusIndex:
    def __init__(self, root: Path, phrase_ngram_range: tuple[int, int] = (3, 5), min_tokens_for_overlap: int = 5) -> None:
        self.root = root
        self.phrase_ngram_range = phrase_ngram_range
        self.min_tokens_for_overlap = min_tokens_for_overlap
        self.sentences = self._load_sentences(root)
        self.vector_index = SentenceVectorIndex([sentence.text for sentence in self.sentences])
        self.phrase_document_frequency = self._phrase_document_frequency()

    def top_matches(self, query: str, k: int = 3) -> list[tuple[CorpusSentence, float]]:
        matches = self.vector_index.top_matches(query, k=k)
        return [(self.sentences[idx], score) for idx, score in matches]

    def _load_sentences(self, root: Path) -> list[CorpusSentence]:
        sentences: list[CorpusSentence] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".txt", ".tex"}:
                continue
            raw = path.read_text(encoding="utf-8")
            cleaned = clean_tex_to_text(raw) if path.suffix.lower() == ".tex" else raw
            for sentence in split_sentences(cleaned):
                if len(sentence.strip()) < 25:
                    continue
                sentences.append(
                    CorpusSentence(
                        source_path=portable_path(path),
                        source_label=path.stem,
                        text=sentence.strip(),
                    )
                )
        return sentences

    def _phrase_document_frequency(self) -> dict[str, int]:
        document_frequency: dict[str, int] = {}
        min_n, max_n = self.phrase_ngram_range
        for sentence in self.sentences:
            seen = set(
                ngram_counts(
                    sentence.text,
                    min_n=min_n,
                    max_n=max_n,
                    min_tokens=self.min_tokens_for_overlap,
                )
            )
            for phrase in seen:
                document_frequency[phrase] = document_frequency.get(phrase, 0) + 1
        return document_frequency
