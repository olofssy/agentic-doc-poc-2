"""Controlled-corpus loading, filtering, and interchangeable clause retrieval."""

from .contracts import ClauseRetriever, RetrievedClause
from .corpus import (
    CorpusLoadError,
    PolicyClause,
    PolicyCorpus,
    PolicyDocument,
    load_corpus_manifest,
    load_policy_corpus,
)
from .filters import filter_applicable_clauses
from .lexical import LexicalClauseRetriever, rank_clauses, tokenize
from .rendering import render_clause_for_retrieval
from .vector import (
    DeterministicEmbeddingClient,
    EmbeddingClient,
    IndexedClauseVector,
    LocalVectorIndex,
    OpenAIEmbeddingClient,
    VectorClauseRetriever,
    build_vector_retriever,
)

__all__ = [
    "ClauseRetriever",
    "CorpusLoadError",
    "DeterministicEmbeddingClient",
    "EmbeddingClient",
    "IndexedClauseVector",
    "LexicalClauseRetriever",
    "LocalVectorIndex",
    "OpenAIEmbeddingClient",
    "PolicyClause",
    "PolicyCorpus",
    "PolicyDocument",
    "RetrievedClause",
    "filter_applicable_clauses",
    "load_corpus_manifest",
    "load_policy_corpus",
    "rank_clauses",
    "render_clause_for_retrieval",
    "tokenize",
    "VectorClauseRetriever",
    "build_vector_retriever",
]
