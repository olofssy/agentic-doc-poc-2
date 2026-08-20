"""Local, inspectable vector retrieval for controlled policy corpora.

This module intentionally has no default network client.  Offline callers use
``DeterministicEmbeddingClient``; an explicitly configured paid client can be
adapted to ``EmbeddingClient`` by an application boundary.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Protocol

from .contracts import ClauseRetriever, RetrievedClause
from .corpus import PolicyClause
from .rendering import render_clause_for_retrieval

_TOKEN_PATTERN = re.compile(r"[a-z0-9åäö]+")
_CACHE_VERSION = 1


class EmbeddingClient(Protocol):
    """Provider boundary for document and query vector generation."""

    model_id: str

    def embed_documents(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """Embed indexed clause renderings without changing their provenance."""

    def embed_query(self, text: str) -> tuple[float, ...]:
        """Embed one retrieval query."""


@dataclass(frozen=True)
class DeterministicEmbeddingClient:
    """Offline hashed-token embedding fake for reproducible local evaluation.

    It intentionally performs no provider call.  The normalisation aliases are
    small, domain-neutral lexical bridges so tests can exercise vector ranking
    without claiming that this substitute is a production semantic model.
    """

    dimensions: int = 128
    model_id: str = "deterministic-hashed-token-v1"

    def __post_init__(self) -> None:
        if self.dimensions < 1:
            raise ValueError("dimensions must be at least 1")

    def embed_documents(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._embed(text) for text in texts)

    def embed_query(self, text: str) -> tuple[float, ...]:
        return self._embed(text)

    def _embed(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimensions
        for token, frequency in Counter(_normalised_tokens(text)).items():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] % 2 == 0 else -1.0
            vector[bucket] += sign * frequency
        return tuple(vector)


@dataclass
class OpenAIEmbeddingClient:
    """Configured OpenAI embedding adapter for explicitly approved paid commands.

    Constructing this adapter does not contact the provider.  Network use occurs
    only when a caller invokes either embedding method.
    """

    model_id: str = "text-embedding-3-small"
    api_key: str | None = None
    _client: object | None = field(default=None, init=False, repr=False)

    def embed_documents(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        client = self._embedding_client()
        vectors = client.embed_documents(list(texts))  # type: ignore[union-attr]
        return tuple(tuple(float(value) for value in vector) for vector in vectors)

    def embed_query(self, text: str) -> tuple[float, ...]:
        client = self._embedding_client()
        return tuple(float(value) for value in client.embed_query(text))  # type: ignore[union-attr]

    def _embedding_client(self) -> object:
        if self._client is None:
            from langchain_openai import OpenAIEmbeddings

            self._client = OpenAIEmbeddings(model=self.model_id, api_key=self.api_key)
        return self._client


@dataclass(frozen=True)
class IndexedClauseVector:
    """One inspectable vector record keyed by stable clause provenance."""

    document_id: str
    clause_id: str
    content_hash: str
    embedding_model_id: str
    rendered_text: str
    vector: tuple[float, ...]


@dataclass(frozen=True)
class LocalVectorIndex:
    """In-memory cosine-similarity index, optionally persisted as local cache JSON."""

    embedding_model_id: str
    records: tuple[IndexedClauseVector, ...]

    @property
    def vector_dimension(self) -> int:
        return len(self.records[0].vector) if self.records else 0

    @classmethod
    def build(
        cls,
        clauses: Sequence[PolicyClause],
        embedding_client: EmbeddingClient,
    ) -> LocalVectorIndex:
        rendered = tuple(render_clause_for_retrieval(clause) for clause in clauses)
        vectors = embedding_client.embed_documents(rendered)
        if len(vectors) != len(clauses):
            raise ValueError("embedding client returned the wrong number of document vectors")
        records = tuple(
            IndexedClauseVector(
                document_id=clause.document.document_id,
                clause_id=clause.clause_id,
                content_hash=_content_hash(text),
                embedding_model_id=embedding_client.model_id,
                rendered_text=text,
                vector=_validated_vector(vector),
            )
            for clause, text, vector in zip(clauses, rendered, vectors, strict=True)
        )
        _validate_record_dimensions(records)
        return cls(embedding_model_id=embedding_client.model_id, records=records)

    @classmethod
    def load_or_build(
        cls,
        clauses: Sequence[PolicyClause],
        embedding_client: EmbeddingClient,
        *,
        cache_path: Path,
    ) -> LocalVectorIndex:
        """Reuse an exact content/model cache entry or atomically replace it."""

        cached = cls._load(cache_path)
        if cached is not None and cached._matches(clauses, embedding_client.model_id):
            return cached
        index = cls.build(clauses, embedding_client)
        index._write(cache_path)
        return index

    @classmethod
    def _load(cls, cache_path: Path) -> LocalVectorIndex | None:
        try:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if payload.get("version") != _CACHE_VERSION:
                return None
            records = tuple(
                IndexedClauseVector(
                    document_id=record["document_id"],
                    clause_id=record["clause_id"],
                    content_hash=record["content_hash"],
                    embedding_model_id=record["embedding_model_id"],
                    rendered_text=record["rendered_text"],
                    vector=_validated_vector(record["vector"]),
                )
                for record in payload["records"]
            )
            _validate_record_dimensions(records)
            return cls(embedding_model_id=payload["embedding_model_id"], records=records)
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _matches(self, clauses: Sequence[PolicyClause], model_id: str) -> bool:
        expected = tuple(
            (
                clause.document.document_id,
                clause.clause_id,
                _content_hash(render_clause_for_retrieval(clause)),
            )
            for clause in clauses
        )
        actual = tuple(
            (record.document_id, record.clause_id, record.content_hash) for record in self.records
        )
        return self.embedding_model_id == model_id and actual == expected

    def _write(self, cache_path: Path) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": _CACHE_VERSION,
            "embedding_model_id": self.embedding_model_id,
            "records": [asdict(record) for record in self.records],
        }
        temporary_path = cache_path.with_suffix(f"{cache_path.suffix}.tmp")
        temporary_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        temporary_path.replace(cache_path)


@dataclass(frozen=True)
class VectorClauseRetriever(ClauseRetriever):
    """Rank eligible clauses against a local index with cosine similarity."""

    index: LocalVectorIndex
    embedding_client: EmbeddingClient

    def __post_init__(self) -> None:
        if self.index.embedding_model_id != self.embedding_client.model_id:
            raise ValueError("vector index and embedding client model IDs must match")

    def rank(
        self,
        query: str,
        clauses: Sequence[PolicyClause],
        *,
        limit: int,
    ) -> tuple[RetrievedClause, ...]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if not query.strip() or not clauses:
            return ()
        query_vector = _validated_vector(self.embedding_client.embed_query(query))
        if self.index.vector_dimension and len(query_vector) != self.index.vector_dimension:
            raise ValueError("query vector dimension does not match the local vector index")
        records = {
            (record.document_id, record.clause_id): record for record in self.index.records
        }
        scored = tuple(
            RetrievedClause(
                clause=clause,
                score=_cosine_similarity(
                    query_vector,
                    records[(clause.document.document_id, clause.clause_id)].vector,
                ),
            )
            for clause in clauses
            if (clause.document.document_id, clause.clause_id) in records
        )
        return tuple(
            sorted(
                scored,
                key=lambda result: (
                    -result.score,
                    result.clause.document.document_id,
                    result.clause.clause_id,
                ),
            )[:limit]
        )


def build_vector_retriever(
    clauses: Sequence[PolicyClause],
    embedding_client: EmbeddingClient,
    *,
    cache_path: Path | None = None,
) -> tuple[VectorClauseRetriever, float]:
    """Build a local vector retriever and return its measured index-build duration."""

    start = perf_counter()
    index = (
        LocalVectorIndex.load_or_build(clauses, embedding_client, cache_path=cache_path)
        if cache_path is not None
        else LocalVectorIndex.build(clauses, embedding_client)
    )
    retriever = VectorClauseRetriever(index=index, embedding_client=embedding_client)
    return retriever, perf_counter() - start


def _normalised_tokens(text: str) -> Iterable[str]:
    aliases = {
        "agency": "contingent",
        "assignment": "engagement",
        "credential": "identity",
        "credentials": "identity",
        "employee": "employment",
        "employees": "employment",
        "ends": "separation",
        "ending": "separation",
        "handover": "continuity",
        "worker": "employment",
        "workers": "employment",
        "workspace": "identity",
    }
    return (aliases.get(token, token) for token in _TOKEN_PATTERN.findall(text.lower()))


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validated_vector(vector: Sequence[float]) -> tuple[float, ...]:
    result = tuple(float(value) for value in vector)
    if not result:
        raise ValueError("embedding vectors must not be empty")
    if not all(math.isfinite(value) for value in result):
        raise ValueError("embedding vectors must contain only finite values")
    return result


def _validate_record_dimensions(records: Sequence[IndexedClauseVector]) -> None:
    dimensions = {len(record.vector) for record in records}
    if len(dimensions) > 1:
        raise ValueError("all local vector index records must have the same dimension")


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    dot_product = sum(
        left_value * right_value for left_value, right_value in zip(left, right, strict=True)
    )
    return dot_product / (left_norm * right_norm)
