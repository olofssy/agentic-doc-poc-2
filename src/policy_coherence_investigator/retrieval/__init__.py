"""Deterministic corpus loading, applicability filtering, and lexical retrieval."""

from .corpus import (
    CorpusLoadError,
    PolicyClause,
    PolicyCorpus,
    PolicyDocument,
    load_corpus_manifest,
    load_policy_corpus,
)
from .filters import filter_applicable_clauses
from .lexical import RetrievedClause, rank_clauses, tokenize

__all__ = [
    "CorpusLoadError",
    "PolicyClause",
    "PolicyCorpus",
    "PolicyDocument",
    "RetrievedClause",
    "filter_applicable_clauses",
    "load_corpus_manifest",
    "load_policy_corpus",
    "rank_clauses",
    "tokenize",
]
