"""
verifier.py
-----------
Lightweight but meaningful claim verifier using keyword-overlap NLI scoring.

This replaces the all-neutral stub with a heuristic that:
  1. Tokenizes the claim and each evidence snippet into significant words
  2. Computes word-overlap (Jaccard-style) between claim and evidence
  3. Scans for negation patterns to detect contradiction
  4. Aggregates across evidence pieces:
       - max overlap ≥ 0.55 → 'supported'
       - negation phrase detected with overlap ≥ 0.35 → 'refuted'
       - otherwise → 'not_enough_info'

No GPU or heavy models required – runs in pure Python.
"""

from __future__ import annotations
import re
from typing import List, Dict, Tuple

# Words that add no signal for overlap matching
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "on", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "from", "up", "down", "out", "off", "over", "under",
    "again", "further", "then", "once", "and", "or", "but", "if", "while",
    "although", "because", "as", "until", "that", "which", "who", "whom",
    "this", "these", "those", "i", "me", "my", "we", "our", "you", "your",
    "he", "she", "it", "they", "his", "her", "its", "their", "what", "so",
    "no", "not", "nor", "just", "also", "its", "s", "said", "says",
}

_NEGATION_PATTERNS = [
    r"\bnot\b", r"\bnever\b", r"\bno\b", r"\bdenied?\b", r"\bdenies\b",
    r"\bfalse\b", r"\bincorrect\b", r"\bmisleading\b", r"\buntrue\b",
    r"\bwrong\b", r"\bdisputed?\b", r"\bfailed\b", r"\bdebunked?\b",
    r"\bcontradicts?\b", r"\brefuted?\b",
]

_NEGATION_RE = re.compile("|".join(_NEGATION_PATTERNS), re.IGNORECASE)


def _tokenize(text: str) -> set:
    """Lowercase, strip punctuation, remove stopwords."""
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def _overlap_score(claim_tokens: set, evidence_tokens: set) -> float:
    """Jaccard-based overlap between claim and evidence token sets."""
    if not claim_tokens or not evidence_tokens:
        return 0.0
    intersection = claim_tokens & evidence_tokens
    union = claim_tokens | evidence_tokens
    return len(intersection) / len(union)


def _has_negation(text: str) -> bool:
    return bool(_NEGATION_RE.search(text))


def nli_scores(premise: str, hypothesis: str) -> Dict[str, float]:
    """
    Heuristic NLI scoring.

    Returns probabilities for entailment / neutral / contradiction
    based on keyword overlap and negation detection.
    """
    claim_tokens = _tokenize(hypothesis)
    ev_tokens = _tokenize(premise)

    overlap = _overlap_score(claim_tokens, ev_tokens)
    negated = _has_negation(premise)

    if negated and overlap >= 0.30:
        # Evidence discusses the same topic but uses negation language
        entailment = max(0.0, overlap * 0.2)
        contradiction = min(0.95, overlap * 1.4)
        neutral = max(0.0, 1.0 - entailment - contradiction)
    elif overlap >= 0.50:
        entailment = min(0.95, overlap * 1.2)
        contradiction = max(0.0, 0.1 - overlap * 0.1)
        neutral = max(0.0, 1.0 - entailment - contradiction)
    else:
        # Low overlap – treat as neutral
        entailment = overlap * 0.4
        contradiction = 0.05
        neutral = max(0.0, 1.0 - entailment - contradiction)

    return {
        "entailment": round(entailment, 4),
        "neutral": round(neutral, 4),
        "contradiction": round(contradiction, 4),
    }


def aggregate_verdict_from_evidence(
    claim: str,
    evidences: List[Dict],
    entail_thresh: float = 0.55,
    contra_thresh: float = 0.55,
) -> Tuple[str, List[Dict]]:
    """
    Aggregate a verdict for a claim given a list of evidence documents.

    Returns:
        ('supported' | 'refuted' | 'not_enough_info', evidence_results)
    """
    evidence_results: List[Dict] = []
    max_entail = 0.0
    max_contra = 0.0

    for ev in evidences:
        premise = (ev.get("content") or "")[:2000]
        scores = nli_scores(premise, claim)

        max_entail = max(max_entail, scores["entailment"])
        max_contra = max(max_contra, scores["contradiction"])

        evidence_results.append({
            "title": ev.get("title"),
            "url": ev.get("url"),
            "scores": scores,
        })

    # Verdict logic: contradiction takes priority over entailment
    if max_contra >= contra_thresh:
        verdict = "refuted"
    elif max_entail >= entail_thresh:
        verdict = "supported"
    else:
        verdict = "not_enough_info"

    return verdict, evidence_results
