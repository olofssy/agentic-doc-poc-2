"""Deterministic validation of result citations against released evidence."""

from collections.abc import Iterable

from policy_coherence_investigator.retrieval import PolicyClause

from .models import InvestigationResult


class CitationValidationError(ValueError):
    """Raised when a review cites a clause that retrieval did not expose."""


def validate_result_citations(
    result: InvestigationResult,
    retrieved_clauses: Iterable[PolicyClause],
) -> None:
    """Require every structured finding citation to refer to a retrieved clause."""

    available_references = {
        (clause.document.document_id, clause.clause_id) for clause in retrieved_clauses
    }
    cited_references = {
        (citation.document_id, citation.clause_id)
        for finding in result.findings
        for citation in finding.citations
    }
    unavailable_references = cited_references - available_references
    if unavailable_references:
        raise CitationValidationError(
            "review cites clauses that retrieval did not expose: "
            f"{sorted(unavailable_references)}"
        )
