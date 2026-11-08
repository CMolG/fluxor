#!/usr/bin/env python3
"""Deterministic metrics for the CEET smoke test.

No model calls. Every metric is reproducible from the output text alone:
- structure: required sections present, length within bounds;
- vocabulary: required phrases present (whole words), similarity to a voice corpus;
- task quality: planted defects found, forbidden phrases avoided.

What these numbers are: regression checks that a pack still produces output with the expected
structure and vocabulary, and a separate check that known defects are caught. What they are not: a
measure of whether an output decides the way the person would. That is fidelity, measured per
person against their own consistency (`scripts/fidelity.py`, `references/fidelity.md`).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable


WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z'-]+")


def tokenize(text: str) -> list[str]:
    """Lower-case word tokens. Keeps apostrophes inside words."""
    return [w.lower() for w in WORD_RE.findall(text)]


def section_count(text: str) -> int:
    """Count Markdown headings (lines starting with `#`)."""
    return sum(1 for line in text.splitlines() if line.lstrip().startswith("#"))


def word_count(text: str) -> int:
    return len(tokenize(text))


def phrase_pattern(phrase: str) -> re.Pattern:
    """A phrase as whole words: `lock` does not match `block`, and a space in the phrase also
    matches a hyphen (`feature flag` matches `feature-flag`)."""
    parts = [re.escape(p) for p in re.split(r"[\s-]+", phrase.strip().lower()) if p]
    return re.compile(r"(?<![a-z0-9])" + r"[\s-]+".join(parts) + r"(?![a-z0-9])", re.I)


def has_phrase(text: str, phrase: str) -> bool:
    return bool(phrase_pattern(phrase).search(text))


def required_phrase_hits(text: str, phrases: Iterable[str]) -> dict[str, bool]:
    """Return {phrase: present} for each required phrase, matched as whole words."""
    return {phrase: has_phrase(text, phrase) for phrase in phrases}


def required_section_hits(text: str, sections: Iterable[str]) -> dict[str, bool]:
    """Return {section: present} treating each entry as a heading substring."""
    headings = [
        line.lstrip("# ").strip().lower()
        for line in text.splitlines()
        if line.lstrip().startswith("#")
    ]
    return {section: any(section.lower() in h for h in headings) for section in sections}


def defect_hits(text: str, defects: Iterable[dict]) -> dict[str, bool]:
    """Return {defect id: found}: a planted defect counts as found when any of its `detect`
    phrases appears. A crude detector: read the misses by hand before trusting a number."""
    return {d["id"]: any(has_phrase(text, p) for p in d.get("detect", [])) for d in defects}


def forbidden_hits(text: str, phrases: Iterable[str]) -> list[str]:
    found = []
    for phrase in phrases:
        if phrase == "!":
            if "!" in re.sub(r"!\[", "", text):
                found.append(phrase)
        elif has_phrase(text, phrase):
            found.append(phrase)
    return found


STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on",
    "for", "with", "is", "are", "was", "were", "be", "as", "at", "by",
    "this", "that", "it", "its", "from", "you", "your", "we", "our",
    "they", "their", "i", "my", "me", "have", "has", "had", "will",
    "would", "should", "can", "could", "may", "might", "do", "does",
    "did", "not", "no", "so", "than", "then", "there", "these", "those",
    "what", "which", "who", "when", "where", "how", "all", "any", "some",
    "one", "two", "three", "more", "less", "very", "also", "just",
    "only", "even", "into", "out", "up", "down", "over", "under",
}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _tf_vector(tokens: list[str]) -> dict[str, float]:
    """Term-frequency vector with stopwords removed and length-normalized."""
    filtered = [t for t in tokens if t not in STOPWORDS and len(t) > 2]
    if not filtered:
        return {}
    counts = Counter(filtered)
    total = sum(counts.values())
    return {term: count / total for term, count in counts.items()}


def voice_alignment(output: str, corpus: str) -> float:
    """Cosine similarity of length-normalized TF vectors (stopwords removed) between an output and a
    voice corpus. Vocabulary overlap, confounded by topic: a diagnostic, never evidence that an
    output sounds like a person."""
    output_tokens = tokenize(output)
    corpus_tokens = tokenize(corpus)
    if not output_tokens or not corpus_tokens:
        return 0.0
    return round(cosine(_tf_vector(output_tokens), _tf_vector(corpus_tokens)), 4)


def score_output(text: str, criteria: dict, corpus: str | None = None) -> dict:
    """Apply every metric defined in `criteria` to `text` and return a flat dict."""
    phrase_results = required_phrase_hits(text, criteria.get("requiredPhrases", []))
    section_results = required_section_hits(text, criteria.get("requiredSections", []))
    defects = defect_hits(text, criteria.get("seededDefects", []))
    forbidden = forbidden_hits(text, criteria.get("forbiddenPhrases", []))
    words = word_count(text)
    min_words, max_words = criteria.get("minWords"), criteria.get("maxWords")

    def share(results: dict) -> float | None:
        return round(sum(results.values()) / len(results), 4) if results else None

    return {
        "wordCount": words,
        "sectionCount": section_count(text),
        "lengthWithinBounds": (min_words is None or words >= min_words) and (max_words is None or words <= max_words),
        "phraseCoverage": share(phrase_results) if phrase_results else 1.0,
        "phraseHits": phrase_results,
        "sectionCoverage": share(section_results) if section_results else 1.0,
        "sectionHits": section_results,
        "defectRecall": share(defects),
        "defectHits": defects,
        "forbiddenHits": forbidden,
        "voiceAlignment": voice_alignment(text, corpus) if corpus else None,
    }
