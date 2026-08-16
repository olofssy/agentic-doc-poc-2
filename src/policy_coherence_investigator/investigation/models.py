"""Stable, provider-independent contracts for policy-coherence reviews."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FindingCategory(StrEnum):
    """The mutually exclusive outcome categories for an investigation."""

    CONFIRMED_CONFLICT = "confirmed_conflict"
    APPARENT_CONFLICT_RESOLVED = "apparent_conflict_resolved"
    COVERAGE_GAP_OR_INSUFFICIENT_EVIDENCE = "coverage_gap_or_insufficient_evidence"


class EvidenceNeedKind(StrEnum):
    """Permissioned retrieval intents available to a future investigation loop."""

    RETRIEVE_DEFINITION = "retrieve_definition"
    RETRIEVE_POPULATION_POLICY = "retrieve_population_policy"
    RETRIEVE_LOCAL_ADDENDUM = "retrieve_local_addendum"
    RETRIEVE_GOVERNANCE = "retrieve_governance"
    TEST_FINDING = "test_finding"
    ASK_HUMAN = "ask_human"


class StructuredResultModel(BaseModel):
    """Reject undeclared fields in the provider-facing result contract."""

    model_config = ConfigDict(extra="forbid")


class EvidenceReference(StructuredResultModel):
    """A stable citation to a clause in an agent-visible policy document."""

    document_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    clause_id: str = Field(pattern=r"^[A-Z][A-Z0-9]*-\d+(?:\.\d+)*$")


class ScopeAssumption(StructuredResultModel):
    """An explicit interpretation that may later be revised by evidence."""

    assumption_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    statement: str = Field(min_length=1)

    @field_validator("statement")
    @classmethod
    def strip_statement(cls, value: str) -> str:
        return value.strip()


class CoherenceFinding(StructuredResultModel):
    """A material, clause-supported conclusion within a review."""

    finding_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    conclusion: str = Field(min_length=1)
    citations: list[EvidenceReference] = Field(min_length=1)

    @field_validator("conclusion")
    @classmethod
    def strip_conclusion(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def citations_are_unique(self) -> CoherenceFinding:
        citation_keys = {(citation.document_id, citation.clause_id) for citation in self.citations}
        if len(citation_keys) != len(self.citations):
            raise ValueError("finding citations must be unique")
        return self


class EvidenceNeed(StructuredResultModel):
    """A recorded reason for requesting another evidence-gathering action."""

    kind: EvidenceNeedKind
    rationale: str = Field(min_length=1)
    query: str = Field(min_length=1)

    @field_validator("rationale", "query")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class InvestigationResult(StructuredResultModel):
    """The structured response returned to a human policy owner."""

    category: FindingCategory
    summary: str = Field(min_length=1)
    findings: list[CoherenceFinding] = Field(min_length=1)
    scope_assumptions: list[ScopeAssumption] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    next_evidence_need: EvidenceNeed | None = None

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        return value.strip()

    @field_validator("unresolved_questions")
    @classmethod
    def strip_questions(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]

    @model_validator(mode="after")
    def finding_ids_are_unique(self) -> InvestigationResult:
        finding_ids = [finding.finding_id for finding in self.findings]
        if len(set(finding_ids)) != len(finding_ids):
            raise ValueError("finding IDs must be unique")
        return self
