"""Shared, clause-level retrieval contracts.

Applicability is deliberately outside this protocol.  Callers pass only clauses
that have already passed deterministic status, date, and geography checks.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from .corpus import PolicyClause


@dataclass(frozen=True)
class RetrievedClause:
    """One ranked clause and its retriever-specific, reproducible score."""

    clause: PolicyClause
    score: float


class ClauseRetriever(Protocol):
    """Rank already-applicable policy clauses for one query."""

    def rank(
        self,
        query: str,
        clauses: Sequence[PolicyClause],
        *,
        limit: int,
    ) -> tuple[RetrievedClause, ...]:
        """Return at most ``limit`` clauses in deterministic rank order."""
