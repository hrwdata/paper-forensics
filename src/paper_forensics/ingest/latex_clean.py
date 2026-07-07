from __future__ import annotations

import re
from pathlib import Path


SECTION_COMMANDS = {
    "section": "section",
    "subsection": "subsection",
    "subsubsection": "subsection",
}

BLOCK_ENVIRONMENTS = [
    "equation",
    "equation*",
    "align",
    "align*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "figure",
    "figure*",
    "table",
    "table*",
    "tikzpicture",
    "lstlisting",
    "verbatim",
]

INLINE_PRESERVE_COMMANDS = [
    "emph",
    "textbf",
    "textit",
    "underline",
    "textrm",
    "textsf",
    "texttt",
    "mbox",
    "url",
    "href",
]


def strip_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        kept: list[str] = []
        escape = False
        for char in line:
            if char == "%" and not escape:
                break
            kept.append(char)
            escape = char == "\\"
        lines.append("".join(kept))
    return "\n".join(lines)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_block_environments(text: str) -> str:
    cleaned = text
    for name in BLOCK_ENVIRONMENTS:
        pattern = rf"\\begin\{{{re.escape(name)}\}}.*?\\end\{{{re.escape(name)}\}}"
        cleaned = re.sub(pattern, f"\n[{name.upper()}]\n", cleaned, flags=re.DOTALL)
    return cleaned


def replace_section_markers(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        command = match.group(1)
        title = squeeze_text(match.group(2))
        kind = SECTION_COMMANDS.get(command, command)
        return f"\n[[{kind.upper()}:{title}]]\n"

    pattern = r"\\(section|subsection|subsubsection)\*?\{([^{}]+)\}"
    return re.sub(pattern, repl, text)


def strip_citations(text: str) -> str:
    cleaned = re.sub(r"\\cite\w*\*?(?:\[[^\]]*\])?\{[^{}]*\}", " [CITATION] ", text)
    cleaned = re.sub(r"\\(?:ref|eqref|autoref|cref|Cref)\{[^{}]*\}", " [REF] ", cleaned)
    return cleaned


def unwrap_inline_commands(text: str) -> str:
    cleaned = text
    for command in INLINE_PRESERVE_COMMANDS:
        pattern = rf"\\{command}\*?(?:\[[^\]]*\])?\{{([^{{}}]*)\}}"
        cleaned = re.sub(pattern, r"\1", cleaned)
    return cleaned


def strip_footnotes(text: str) -> str:
    return re.sub(r"\\footnote\{[^{}]*\}", " ", text)


def strip_math(text: str) -> str:
    cleaned = re.sub(r"\$\$.*?\$\$", " [MATH] ", text, flags=re.DOTALL)
    cleaned = re.sub(r"\$(?:\\.|[^$])+\$", " [MATH] ", cleaned)
    cleaned = re.sub(r"\\\[(?:.|\n)*?\\\]", " [MATH] ", cleaned)
    cleaned = re.sub(r"\\\((?:.|\n)*?\\\)", " [MATH] ", cleaned)
    return cleaned


def strip_remaining_commands(text: str) -> str:
    cleaned = re.sub(r"\\item\b", "\n", text)
    cleaned = re.sub(r"\\[a-zA-Z@]+(?:\*?)\[[^\]]*\]", " ", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z@]+\*?\{([^{}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z@]+\*?", " ", cleaned)
    cleaned = cleaned.replace("{", " ").replace("}", " ")
    return cleaned


def squeeze_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_tex_to_text(text: str) -> str:
    cleaned = strip_comments(text)
    cleaned = strip_block_environments(cleaned)
    cleaned = replace_section_markers(cleaned)
    cleaned = strip_citations(cleaned)
    cleaned = strip_footnotes(cleaned)
    cleaned = strip_math(cleaned)
    cleaned = unwrap_inline_commands(cleaned)
    cleaned = strip_remaining_commands(cleaned)
    cleaned = re.sub(r"[~]", " ", cleaned)
    cleaned = re.sub(r"\[[A-Z_]+\]", " ", cleaned)
    return normalize_whitespace(cleaned)


def resolve_include(base_path: Path, target: str) -> Path:
    candidate = (base_path.parent / target).resolve()
    if candidate.suffix:
        return candidate
    return candidate.with_suffix(".tex")
