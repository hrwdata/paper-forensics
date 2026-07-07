from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from paper_forensics.ingest.latex_clean import clean_tex_to_text, resolve_include, strip_comments
from paper_forensics.nlp.sentence_split import split_sentences
from paper_forensics.scoring.schemas import SentenceRecord, portable_path


SECTION_PATTERN = re.compile(r"\[\[(SECTION|SUBSECTION):([^\]]+)\]\]")


@dataclass
class ParagraphChunk:
    paragraph_id: str
    section: str
    subsection: str
    source_file: str
    raw_tex: str
    clean_text: str
    paragraph_index: int
    raw_char_start: int
    raw_char_end: int


@dataclass
class RawBlock:
    text: str
    start: int
    end: int


def load_tex_project(main_tex_path: Path, min_sentence_chars: int = 25) -> tuple[str, list[ParagraphChunk], list[SentenceRecord]]:
    inlined = _inline_tex(main_tex_path.resolve(), visited=set())
    raw_text = _extract_document_body(strip_comments(inlined))
    paragraph_chunks = extract_paragraphs(raw_text)
    sentences = extract_sentences(paragraph_chunks, min_sentence_chars=min_sentence_chars)
    return raw_text, paragraph_chunks, sentences


def _inline_tex(path: Path, visited: set[Path]) -> str:
    if path in visited:
        return ""
    visited.add(path)
    raw = path.read_text(encoding="utf-8")
    lines = [f"[[SOURCE:{portable_path(path)}]]\n"]
    pattern = re.compile(r"\\(input|include)\{([^}]+)\}")
    cursor = 0
    for match in pattern.finditer(raw):
        lines.append(raw[cursor : match.start()])
        include_path = resolve_include(path, match.group(2))
        if include_path.exists():
            lines.append(_inline_tex(include_path, visited))
        cursor = match.end()
    lines.append(raw[cursor:])
    return "".join(lines)


def extract_paragraphs(raw_tex: str) -> list[ParagraphChunk]:
    paragraphs: list[ParagraphChunk] = []
    section = "Untitled"
    subsection = ""
    source_file = ""
    paragraph_index = 0

    for block in _split_blocks(raw_tex):
        stripped = block.text.strip()
        if not stripped:
            continue
        source_markers = re.findall(r"\[\[SOURCE:(.+?)\]\]", stripped)
        if source_markers:
            source_file = source_markers[-1].strip()
            stripped = re.sub(r"\[\[SOURCE:.+?\]\]", "", stripped).strip()
            if not stripped:
                continue

        cleaned_block = clean_tex_to_text(stripped)
        if not cleaned_block:
            continue

        markers = SECTION_PATTERN.findall(cleaned_block)
        if markers:
            for kind, title in markers:
                if kind == "SECTION":
                    section = title.strip() or "Untitled"
                    subsection = ""
                else:
                    subsection = title.strip()
            cleaned_block = SECTION_PATTERN.sub("", cleaned_block).strip()
            if not cleaned_block:
                continue

        if len(cleaned_block) < 20:
            continue

        paragraph_index += 1
        section_index = _slug_index(section)
        paragraph_id = f"{section_index}.par_{paragraph_index:03d}"
        paragraphs.append(
            ParagraphChunk(
                paragraph_id=paragraph_id,
                section=section,
                subsection=subsection,
                source_file=source_file,
                raw_tex=stripped,
                clean_text=cleaned_block,
                paragraph_index=paragraph_index,
                raw_char_start=block.start,
                raw_char_end=block.end,
            )
        )
    return paragraphs


def extract_sentences(paragraphs: list[ParagraphChunk], min_sentence_chars: int = 25) -> list[SentenceRecord]:
    records: list[SentenceRecord] = []
    section_counts: dict[str, int] = {}

    for paragraph in paragraphs:
        section_key = _slug_index(paragraph.section)
        section_counts.setdefault(section_key, 0)
        sentence_texts = split_sentences(paragraph.clean_text)
        search_cursor = 0
        for idx, sentence in enumerate(sentence_texts, start=1):
            sentence = sentence.strip()
            if len(sentence) < min_sentence_chars:
                continue
            section_counts[section_key] += 1
            char_start = paragraph.clean_text.find(sentence, search_cursor)
            if char_start < 0:
                char_start = paragraph.clean_text.find(sentence)
            char_end = char_start + len(sentence)
            search_cursor = max(char_end, search_cursor)
            sentence_id = f"{section_key}.par_{paragraph.paragraph_index:03d}.sent_{idx:03d}"
            records.append(
                SentenceRecord(
                    sentence_id=sentence_id,
                    clean_text=sentence,
                    raw_tex_fragment=_approximate_raw_fragment(paragraph.raw_tex, sentence),
                    raw_tex_context=paragraph.raw_tex,
                    source_context_char_start=paragraph.raw_char_start,
                    source_context_char_end=paragraph.raw_char_end,
                    source_file=paragraph.source_file,
                    section=paragraph.section,
                    subsection=paragraph.subsection,
                    paragraph_id=paragraph.paragraph_id,
                    paragraph_index=paragraph.paragraph_index,
                    sentence_index=idx,
                    char_start=max(char_start, 0),
                    char_end=max(char_end, 0),
                )
            )
    return records


def _split_blocks(text: str) -> list[RawBlock]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks: list[RawBlock] = []
    for match in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|$)", normalized, flags=re.DOTALL):
        blocks.append(RawBlock(text=match.group(0), start=match.start(), end=match.end()))
    return blocks


def _slug_index(section: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", section.lower()).strip("_")
    return slug or "untitled"


def _approximate_raw_fragment(raw_tex: str, sentence: str) -> str:
    squeezed_raw = re.sub(r"\s+", " ", raw_tex).strip()
    if len(squeezed_raw) <= 240:
        return squeezed_raw
    if sentence in squeezed_raw:
        return sentence
    return squeezed_raw[:240] + "..."


def _extract_document_body(text: str) -> str:
    match = re.search(r"\\begin\{document\}(.*)\\end\{document\}", text, flags=re.DOTALL)
    return match.group(1) if match else text
