"""Rule-based Automated Essay Scoring feature extractor.

This module extracts interpretable lexical, syntactic, cohesion, and grammar
features from an essay and combines a small subset into a transparent weighted
score. It does not use machine learning or LLM-based scoring.
"""

from __future__ import annotations

import re
from typing import Optional

import language_tool_python
import spacy
from lexical_diversity import lex_div as ld
from nltk.tokenize import sent_tokenize
from spacy.tokens import Doc, Token
from wordfreq import zipf_frequency


# Load heavyweight NLP resources once at module import time.
nlp = spacy.load("en_core_web_sm")

try:
    tool: Optional[language_tool_python.LanguageTool] = (
        language_tool_python.LanguageTool("en-US")
    )
except Exception:
    tool = None


AWL_SET = {
    "analyze",
    "approach",
    "area",
    "assess",
    "assume",
    "authority",
    "available",
    "benefit",
    "concept",
    "consistent",
    "context",
    "data",
    "derive",
    "distribute",
    "economy",
    "environment",
    "establish",
    "estimate",
    "evidence",
    "factor",
    "function",
    "identify",
    "indicate",
    "interpret",
    "involve",
    "issue",
    "method",
    "occur",
    "percent",
    "period",
    "policy",
    "principle",
    "proceed",
    "process",
    "require",
    "research",
    "respond",
    "section",
    "significant",
    "similar",
    "source",
    "specific",
    "structure",
    "theory",
    "variable",
}

CLAUSE_DEPENDENCIES = {"ccomp", "xcomp", "advcl"}

CONNECTIVES = {
    "however",
    "therefore",
    "because",
    "although",
    "moreover",
    "thus",
    "also",
    "furthermore",
    "consequently",
    "nevertheless",
    "in addition",
    "for example",
    "for instance",
    "on the other hand",
    "as a result",
}


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide safely and return a default when the denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def dependency_depth(token: Token) -> int:
    """Return the number of dependency hops from a token to the sentence root."""
    depth = 0
    while token.head != token:
        token = token.head
        depth += 1
    return depth


def _alphabetic_words(doc: Doc) -> list[str]:
    """Return lowercased alphabetic spaCy tokens."""
    return [token.text.lower() for token in doc if token.is_alpha]


def _sentence_count(doc: Doc, text: str) -> int:
    """Count sentences from spaCy, with a fallback for very short/raw input."""
    if not text.strip():
        return 0

    sentences = [sent for sent in doc.sents if sent.text.strip()]
    return len(sentences) if sentences else 1


def _average_word_frequency(words: list[str]) -> float:
    """Average Zipf word frequency; lower values suggest rarer vocabulary."""
    frequencies = [zipf_frequency(word, "en") for word in words]
    return safe_divide(sum(frequencies), len(frequencies))


def _mtld(words: list[str]) -> float:
    """Measure of Textual Lexical Diversity, guarded for short essays."""
    if len(words) < 2:
        return 0.0

    try:
        return float(ld.mtld(words))
    except Exception:
        return 0.0


def _awl_ratio(words: list[str]) -> float:
    """Ratio of words that appear in the placeholder Academic Word List set."""
    awl_count = sum(1 for word in words if word in AWL_SET)
    return safe_divide(awl_count, len(words))


def _clause_density(doc: Doc, word_count: int) -> float:
    """Approximate clause density using selected dependency labels."""
    clause_count = sum(1 for token in doc if token.dep_ in CLAUSE_DEPENDENCIES)
    return safe_divide(clause_count, word_count)


def _average_dependency_depth(doc: Doc) -> float:
    """Average dependency tree depth across non-space tokens."""
    tokens = [token for token in doc if not token.is_space]
    depths = [dependency_depth(token) for token in tokens]
    return safe_divide(sum(depths), len(depths))


def _noun_complexity(doc: Doc) -> float:
    """Average number of syntactic children attached to each noun token."""
    nouns = [token for token in doc if token.pos_ == "NOUN"]
    child_counts = [len(list(noun.children)) for noun in nouns]
    return safe_divide(sum(child_counts), len(child_counts))


def _connective_density(text: str, word_count: int) -> float:
    """Count single- and multi-word connectives per 100 words."""
    lowered_text = text.lower()
    connective_count = 0

    for connective in CONNECTIVES:
        pattern = rf"\b{re.escape(connective)}\b"
        connective_count += len(re.findall(pattern, lowered_text))

    return safe_divide(connective_count * 100, word_count)


def _safe_sent_tokenize(text: str) -> list[str]:
    """Use NLTK sentence tokenization with a simple fallback if data is missing."""
    try:
        return sent_tokenize(text)
    except LookupError:
        return [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+", text)
            if part.strip()
        ]


def _word_set(sentence: str) -> set[str]:
    """Return a lowercase alphabetic word set for lexical overlap."""
    return set(re.findall(r"\b[a-zA-Z]+\b", sentence.lower()))


def _lexical_overlap(text: str) -> float:
    """Average Jaccard overlap between adjacent sentence word sets."""
    sentences = _safe_sent_tokenize(text)
    if len(sentences) < 2:
        return 0.0

    overlaps = []
    for first, second in zip(sentences, sentences[1:]):
        first_words = _word_set(first)
        second_words = _word_set(second)
        union = first_words | second_words
        overlaps.append(safe_divide(len(first_words & second_words), len(union)))

    return safe_divide(sum(overlaps), len(overlaps))


def _grammar_errors_per_100(text: str, word_count: int) -> Optional[float]:
    """LanguageTool grammar matches per 100 words, or None if checking fails."""
    if word_count == 0:
        return 0.0

    if tool is None:
        return None

    try:
        matches = tool.check(text)
    except Exception:
        return None

    return safe_divide(len(matches) * 100, word_count)


def extract_features(text: str) -> dict:
    """Extract interpretable rule-based AES features from essay text."""
    cleaned_text = text or ""
    doc = nlp(cleaned_text)
    words = _alphabetic_words(doc)

    word_count = len(words)
    sentence_count = _sentence_count(doc, cleaned_text)

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "mean_sentence_length": safe_divide(word_count, sentence_count),
        "avg_word_freq": _average_word_frequency(words),
        "mtld": _mtld(words),
        "awl_ratio": _awl_ratio(words),
        "clause_density": _clause_density(doc, word_count),
        "dependency_depth": _average_dependency_depth(doc),
        "noun_complexity": _noun_complexity(doc),
        "connective_density": _connective_density(cleaned_text, word_count),
        "lexical_overlap": _lexical_overlap(cleaned_text),
        "grammar_errors_per_100": _grammar_errors_per_100(cleaned_text, word_count),
    }


def normalize(
    value: Optional[float],
    min_val: float,
    max_val: float,
    invert: bool = False,
) -> float:
    """Normalize a value to 0-1, optionally inverting so lower values score higher."""
    if value is None or max_val == min_val:
        return 0.0

    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0.0, min(1.0, normalized))

    if invert:
        return 1.0 - normalized
    return normalized


def compute_score(features: dict) -> float:
    """Compute a transparent weighted score from selected features."""
    score = (
        normalize(features.get("mtld"), 20, 100) * 0.25
        + normalize(features.get("awl_ratio"), 0, 0.20) * 0.30
        + normalize(features.get("avg_word_freq"), 2, 6, invert=True) * 0.20
        + normalize(features.get("grammar_errors_per_100"), 0, 20, invert=True) * 0.25
    )
    return round(score * 100, 2)


def evaluate_essay(text: str) -> dict:
    """Return the weighted score and full feature dictionary for an essay."""
    features = extract_features(text)
    return {
        "score": compute_score(features),
        "features": features,
    }


if __name__ == "__main__":
    sample = (
        "Students benefit from evidence-based writing instruction. "
        "However, effective assessment also requires consistent methods, "
        "because teachers need specific data to identify patterns in student work."
    )
    result = evaluate_essay(sample)
    print(result)
