"""Reviewable state for a policy investigation, derived from rather than replacing evidence."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .models import (
    CoherenceFinding,
    EvidenceNeed,
    EvidenceReference,
    InvestigationResult,
    ScopeAssumption,
)
from .scope import WorkingScope


class FindingState(StrEnum):
    """The current state of one policy-coherence finding in the ledger."""

    PROVISIONAL = "provisional"
    SUPPORTED = "supported"
    RESOLVED = "resolved"
    GAP_OR_INSUFFICIENT_EVIDENCE = "gap_or_insufficient_evidence"


class NormalizedObligation(BaseModel):
    """A policy obligation extracted in context and linked to its source clause."""

    model_config = ConfigDict(extra="forbid")

    obligation_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    population: str = Field(min_length=1)
    access_type: str = Field(min_length=1)
    trigger: str = Field(min_length=1)
    required_action: str = Field(min_length=1)
    deadline: str | None = None
    responsible_party: str | None = None
    evidence: EvidenceReference


class CandidateFinding(BaseModel):
    """A cited finding whose state can change as evidence is discovered."""

    model_config = ConfigDict(extra="forbid")

    finding: CoherenceFinding
    state: FindingState


class RetrievalRecord(BaseModel):
    """One motivated retrieval action and the clauses it exposed."""

    model_config = ConfigDict(extra="forbid")

    iteration: int = Field(ge=1)
    query: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    returned_clauses: list[EvidenceReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def clause_references_are_unique(self) -> RetrievalRecord:
        references = {
            (reference.document_id, reference.clause_id) for reference in self.returned_clauses
        }
        if len(references) != len(self.returned_clauses):
            raise ValueError("retrieval record clause references must be unique")
        return self


class InvestigationLedger(BaseModel):
    """Observable investigation state; prior model statements are never source evidence."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    working_scope: WorkingScope
    scope_assumptions: list[ScopeAssumption] = Field(default_factory=list)
    normalized_obligations: list[NormalizedObligation] = Field(default_factory=list)
    candidate_findings: list[CandidateFinding] = Field(default_factory=list)
    unresolved_terms: list[str] = Field(default_factory=list)
    unresolved_conflicts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    retrieval_history: list[RetrievalRecord] = Field(default_factory=list)
    next_evidence_need: EvidenceNeed | None = None
    remaining_retrieval_budget: int = Field(ge=0)

    @model_validator(mode="after")
    def retrieval_iterations_are_contiguous(self) -> InvestigationLedger:
        expected_iterations = list(range(1, len(self.retrieval_history) + 1))
        actual_iterations = [record.iteration for record in self.retrieval_history]
        if actual_iterations != expected_iterations:
            raise ValueError("retrieval iterations must be contiguous and start at one")
        return self


def initialize_ledger(
    *,
    question: str,
    working_scope: WorkingScope,
    retrieval_budget: int,
    scope_assumptions: Iterable[ScopeAssumption] = (),
) -> InvestigationLedger:
    """Create an empty, budgeted ledger before any policy evidence is retrieved."""

    return InvestigationLedger(
        question=question,
        working_scope=working_scope,
        scope_assumptions=list(scope_assumptions),
        remaining_retrieval_budget=retrieval_budget,
    )


def record_retrieval(
    ledger: InvestigationLedger,
    *,
    query: str,
    rationale: str,
    returned_clauses: Iterable[EvidenceReference],
) -> InvestigationLedger:
    """Append one retrieval record and consume exactly one bounded retrieval iteration."""

    if ledger.remaining_retrieval_budget == 0:
        raise ValueError("retrieval budget is exhausted")

    record = RetrievalRecord(
        iteration=len(ledger.retrieval_history) + 1,
        query=query,
        rationale=rationale,
        returned_clauses=list(returned_clauses),
    )
    return _replace_ledger(
        ledger,
        retrieval_history=[*ledger.retrieval_history, record],
        remaining_retrieval_budget=ledger.remaining_retrieval_budget - 1,
    )


def revise_scope(
    ledger: InvestigationLedger,
    *,
    working_scope: WorkingScope,
    new_assumptions: Iterable[ScopeAssumption] = (),
) -> InvestigationLedger:
    """Record an evidence-motivated scope revision without discarding prior assumptions."""

    assumptions = _unique_assumptions([*ledger.scope_assumptions, *new_assumptions])
    return _replace_ledger(
        ledger,
        working_scope=working_scope,
        scope_assumptions=assumptions,
    )


def apply_review_result(
    ledger: InvestigationLedger,
    result: InvestigationResult,
) -> InvestigationLedger:
    """Project one structured review into reviewable state without treating it as evidence."""

    finding_state = {
        "confirmed_conflict": FindingState.SUPPORTED,
        "apparent_conflict_resolved": FindingState.RESOLVED,
        "coverage_gap_or_insufficient_evidence": FindingState.GAP_OR_INSUFFICIENT_EVIDENCE,
    }[result.category.value]
    candidate_findings = [
        CandidateFinding(finding=finding, state=finding_state) for finding in result.findings
    ]
    assumptions = _unique_assumptions([*ledger.scope_assumptions, *result.scope_assumptions])
    open_questions = _unique_text([*ledger.open_questions, *result.unresolved_questions])
    return _replace_ledger(
        ledger,
        working_scope=result.revised_working_scope or ledger.working_scope,
        scope_assumptions=assumptions,
        candidate_findings=candidate_findings,
        open_questions=open_questions,
        next_evidence_need=result.next_evidence_need,
    )


def _replace_ledger(ledger: InvestigationLedger, **changes: object) -> InvestigationLedger:
    return InvestigationLedger.model_validate({**ledger.model_dump(), **changes})


def _unique_assumptions(assumptions: Iterable[ScopeAssumption]) -> list[ScopeAssumption]:
    seen_ids: set[str] = set()
    unique: list[ScopeAssumption] = []
    for assumption in assumptions:
        if assumption.assumption_id not in seen_ids:
            seen_ids.add(assumption.assumption_id)
            unique.append(assumption)
    return unique


def _unique_text(values: Iterable[str]) -> list[str]:
    seen_values: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen_values:
            seen_values.add(normalized)
            unique.append(normalized)
    return unique
