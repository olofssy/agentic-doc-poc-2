"""Small, deterministic lexical ranking for clause-level policy retrieval."""

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from .corpus import PolicyClause

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RetrievedClause:
    """One ranked clause with a reproducible lexical score."""

    clause: PolicyClause
    score: float


def tokenize(text: str) -> tuple[str, ...]:
    """Normalise case and identifier punctuation into a predictable vocabulary."""

    return tuple(TOKEN_PATTERN.findall(text.lower()))


def rank_clauses(
    query: str,
    clauses: Sequence[PolicyClause],
    *,
    limit: int = 5,
) -> tuple[RetrievedClause, ...]:
    """Rank matching clauses by corpus-local TF/IDF with deterministic tie-breaking."""

    if limit < 1:
        raise ValueError("limit must be at least 1")

    query_terms = Counter(tokenize(query))
    if not query_terms or not clauses:
        return ()

    clause_terms = {
        (clause.document.document_id, clause.clause_id): Counter(tokenize(clause.searchable_text))
        for clause in clauses
    }
    document_frequencies = Counter(
        term for terms in clause_terms.values() for term in terms
    )
    corpus_size = len(clauses)

    scored = tuple(
        RetrievedClause(
            clause=clause,
            score=_score(
                query_terms,
                clause_terms[(clause.document.document_id, clause.clause_id)],
                document_frequencies,
                corpus_size,
            ),
        )
        for clause in clauses
    )
    ranked = sorted(
        scored,
        key=lambda result: (
            -result.score,
            result.clause.document.document_id,
            result.clause.clause_id,
        ),
    )
    return tuple(result for result in ranked if result.score > 0)[:limit]


def _score(
    query_terms: Counter[str],
    clause_terms: Counter[str],
    document_frequencies: Counter[str],
    corpus_size: int,
) -> float:
    return sum(
        query_frequency
        * (1 + math.log(clause_terms[term]))
        * (1 + math.log((corpus_size + 1) / (document_frequencies[term] + 1)))
        for term, query_frequency in query_terms.items()
        if term in clause_terms
    )
