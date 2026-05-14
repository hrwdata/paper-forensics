from __future__ import annotations

import math
import re
from collections import Counter


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "we",
    "with",
}

ABSTRACT_WORDS = {
    "important",
    "noteworthy",
    "significant",
    "crucial",
    "valuable",
    "robust",
    "framework",
    "approach",
    "methodology",
    "perspective",
    "insight",
    "highlights",
    "demonstrates",
    "illustrates",
    "leverages",
    "facilitates",
    "comprehensive",
    "novel",
    "effective",
    "substantial",
    "promising",
    "various",
    "multiple",
    "important",
}

DISCOURSE_MARKERS = {
    "additionally",
    "furthermore",
    "moreover",
    "consequently",
    "therefore",
    "notably",
    "overall",
    "importantly",
    "specifically",
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def content_ratio(text: str) -> float:
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    content = [token for token in tokens if token not in STOPWORDS]
    return len(content) / len(tokens)


def abstract_word_ratio(text: str) -> float:
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    abstract = [token for token in tokens if token in ABSTRACT_WORDS]
    return len(abstract) / len(tokens)


def punctuation_entropy(text: str) -> float:
    punctuation = [char for char in text if char in ",;:()"]
    if not punctuation:
        return 0.0
    counts = Counter(punctuation)
    total = sum(counts.values())
    entropy = 0.0
    for value in counts.values():
        probability = value / total
        entropy -= probability * math.log(probability, 2)
    return entropy


def sentence_length(text: str) -> int:
    return len(tokenize(text))


def starts_with_discourse_marker(text: str) -> bool:
    tokens = tokenize(text)
    return bool(tokens and tokens[0] in DISCOURSE_MARKERS)
