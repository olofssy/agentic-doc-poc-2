import pytest
from pydantic import ValidationError

from policy_coherence_investigator.investigation.models import (
    CoherenceFinding,
    EvidenceReference,
    FindingCategory,
    InvestigationResult,
)


def _finding(finding_id: str = "deadline_conflict") -> CoherenceFinding:
    return CoherenceFinding(
        finding_id=finding_id,
        conclusion="The two currently effective clauses impose incompatible deadlines.",
        citations=[
            EvidenceReference(document_id="access_control_policy_v4", clause_id="ACP-4.2.1"),
        ],
    )


def test_material_finding_requires_a_clause_citation() -> None:
    with pytest.raises(ValidationError, match="at least 1 item"):
        CoherenceFinding(
            finding_id="uncited_finding",
            conclusion="This finding has no evidence.",
            citations=[],
        )


def test_result_requires_unique_finding_ids() -> None:
    with pytest.raises(ValidationError, match="finding IDs must be unique"):
        InvestigationResult(
            category=FindingCategory.CONFIRMED_CONFLICT,
            summary="A conflict was found.",
            findings=[_finding(), _finding()],
        )


def test_result_preserves_free_text_and_structured_fields() -> None:
    result = InvestigationResult(
        category=FindingCategory.CONFIRMED_CONFLICT,
        summary="A current policy conflict affects contractor access revocation.",
        findings=[_finding()],
        unresolved_questions=["Does a local addendum govern this contractor population?"],
    )

    assert result.category == FindingCategory.CONFIRMED_CONFLICT
    assert result.findings[0].citations[0].clause_id == "ACP-4.2.1"
    assert result.unresolved_questions == [
        "Does a local addendum govern this contractor population?"
    ]
