from datetime import date

import pytest

from policy_coherence_investigator.investigation import (
    CoherenceFinding,
    EvidenceNeed,
    EvidenceNeedKind,
    EvidenceReference,
    FindingCategory,
    FindingState,
    InvestigationResult,
    ScopeAssumption,
    WorkingScope,
    apply_review_result,
    initialize_ledger,
    record_retrieval,
    revise_scope,
)


def _scope(populations: list[str] | None = None) -> WorkingScope:
    return WorkingScope(
        topic="access revocation after termination",
        populations=populations or ["employee"],
        access_types=["ordinary", "privileged"],
        geography="global",
        as_of_date=date(2026, 8, 16),
    )


def test_ledger_records_retrieval_provenance_and_enforces_the_budget() -> None:
    ledger = initialize_ledger(
        question="Are access-termination policies coherent?",
        working_scope=_scope(),
        retrieval_budget=1,
    )

    ledger = record_retrieval(
        ledger,
        query="employee access termination deadline",
        rationale="Establish the ordinary-account rule before comparing obligations.",
        returned_clauses=[
            EvidenceReference(document_id="access_control_policy_v4", clause_id="ACP-4.2.1")
        ],
    )

    assert ledger.remaining_retrieval_budget == 0
    assert ledger.retrieval_history[0].iteration == 1
    assert ledger.retrieval_history[0].returned_clauses[0].clause_id == "ACP-4.2.1"
    with pytest.raises(ValueError, match="budget is exhausted"):
        record_retrieval(
            ledger,
            query="another query",
            rationale="This should not run.",
            returned_clauses=[],
        )


def test_scope_revision_preserves_prior_assumptions() -> None:
    ledger = initialize_ledger(
        question="Are access-termination policies coherent?",
        working_scope=_scope(),
        retrieval_budget=3,
        scope_assumptions=[
            ScopeAssumption(
                assumption_id="employee_scope",
                statement="The question initially concerns employees.",
            )
        ],
    )

    revised = revise_scope(
        ledger,
        working_scope=_scope(["employee", "contractor"]),
        new_assumptions=[
            ScopeAssumption(
                assumption_id="contractor_scope",
                statement="A retrieved definition shows contractors are workforce identities.",
            )
        ],
    )

    assert revised.working_scope.populations == ["employee", "contractor"]
    assert [assumption.assumption_id for assumption in revised.scope_assumptions] == [
        "employee_scope",
        "contractor_scope",
    ]


def test_ledger_projects_structured_findings_without_losing_clause_provenance() -> None:
    ledger = initialize_ledger(
        question="Are access-termination policies coherent?",
        working_scope=_scope(["employee", "contractor"]),
        retrieval_budget=3,
    )
    result = InvestigationResult(
        category=FindingCategory.CONFIRMED_CONFLICT,
        summary="Two current clauses impose incompatible contractor deadlines.",
        findings=[
            CoherenceFinding(
                finding_id="incompatible_contractor_revocation_deadlines",
                conclusion="The workforce and contractor deadlines conflict.",
                citations=[
                    EvidenceReference(
                        document_id="access_control_policy_v4",
                        clause_id="ACP-4.2.1",
                    ),
                    EvidenceReference(
                        document_id="contractor_management_policy_v2",
                        clause_id="CMP-6.4",
                    ),
                ],
            )
        ],
        unresolved_questions=["Does a local addendum change the applicable deadline?"],
        next_evidence_need=EvidenceNeed(
            kind=EvidenceNeedKind.RETRIEVE_LOCAL_ADDENDUM,
            target="contractor_access_local_addendum",
            rationale="Local precedence may resolve the apparent conflict.",
            query="contractor access termination local addendum",
        ),
    )

    updated = apply_review_result(ledger, result)

    candidate = updated.candidate_findings[0]
    assert candidate.state == FindingState.SUPPORTED
    assert candidate.finding.citations[1].clause_id == "CMP-6.4"
    assert updated.open_questions == ["Does a local addendum change the applicable deadline?"]
    assert updated.next_evidence_need == result.next_evidence_need
