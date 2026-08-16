from datetime import date
from pathlib import Path

from evals.evaluator import evaluate_result
from policy_coherence_investigator.case_data import load_case, load_oracle
from policy_coherence_investigator.investigation import (
    CoherenceFinding,
    EvidenceNeed,
    EvidenceNeedKind,
    EvidenceReference,
    FindingCategory,
    InvestigationResult,
    ScopeAssumption,
    WorkingScope,
    initialize_ledger,
    record_retrieval,
)
from policy_coherence_investigator.retrieval import filter_applicable_clauses, load_policy_corpus

CORPUS_DIRECTORY = Path("evals/corpora/access-offboarding-b")


def test_evaluator_accepts_a_supported_structured_bounded_trajectory() -> None:
    case = load_case("access-offboarding-b")
    oracle = load_oracle("access-offboarding-b")
    corpus = load_policy_corpus(CORPUS_DIRECTORY)
    retrieved_clauses = filter_applicable_clauses(
        corpus,
        as_of_date=case.case.review_context.as_of_date,
        geography=case.case.review_context.geography,
    )
    ledger = initialize_ledger(
        question=case.case.question,
        working_scope=_scope(),
        retrieval_budget=case.case.retrieval_budget,
        scope_assumptions=[_scope_distinction()],
    )
    ledger = record_retrieval(
        ledger,
        query=case.case.question,
        rationale="Initial policy retrieval.",
        returned_clauses=[
            EvidenceReference(document_id=clause.document.document_id, clause_id=clause.clause_id)
            for clause in retrieved_clauses
        ],
    )

    report = evaluate_result(
        case=case,
        oracle=oracle,
        corpus=corpus,
        result=_passing_result(),
        retrieved_clauses=retrieved_clauses,
        ledger=ledger,
        architecture="bounded",
        requested_evidence_needs=[
            EvidenceNeed(
                kind=EvidenceNeedKind.RETRIEVE_DEFINITION,
                rationale="Account types must be distinguished.",
                query="privileged access definition",
            )
        ],
    )

    assert report.passed, report.issues


def test_evaluator_rejects_a_citation_that_retrieval_did_not_expose() -> None:
    case = load_case("access-offboarding-b")
    oracle = load_oracle("access-offboarding-b")
    corpus = load_policy_corpus(CORPUS_DIRECTORY)
    retrieved_clauses = tuple(
        clause
        for clause in filter_applicable_clauses(
            corpus,
            as_of_date=case.case.review_context.as_of_date,
            geography=case.case.review_context.geography,
        )
        if clause.clause_id != "HOP-7.3"
    )

    report = evaluate_result(
        case=case,
        oracle=oracle,
        corpus=corpus,
        result=_passing_result(),
        retrieved_clauses=retrieved_clauses,
        ledger=None,
        architecture="baseline",
    )

    assert "result cites clauses that were not retrieved" in report.issues


def _scope() -> WorkingScope:
    return WorkingScope(
        topic="access revocation after termination",
        populations=["employee", "contractor"],
        access_types=["ordinary", "privileged"],
        geography="global",
        as_of_date=date(2026, 8, 16),
    )


def _scope_distinction() -> ScopeAssumption:
    return ScopeAssumption(
        assumption_id="ordinary_accounts_vs_privileged_accounts",
        statement="Ordinary and privileged accounts have different scope.",
    )


def _passing_result() -> InvestigationResult:
    return InvestigationResult(
        category=FindingCategory.APPARENT_CONFLICT_RESOLVED,
        summary="The rules coexist because they govern different account types.",
        findings=[
            CoherenceFinding(
                finding_id="ordinary_and_privileged_deadlines_have_distinct_scope",
                conclusion="Immediate revocation governs privileged, not ordinary, accounts.",
                citations=[
                    EvidenceReference(
                        document_id="access_control_policy_v4",
                        clause_id="ACP-4.2.1",
                    ),
                    EvidenceReference(
                        document_id="hr_offboarding_procedure_v3",
                        clause_id="HOP-7.3",
                    ),
                    EvidenceReference(
                        document_id="identity_definitions_v2",
                        clause_id="IDD-2.5",
                    ),
                ],
            )
        ],
        scope_assumptions=[_scope_distinction()],
    )
