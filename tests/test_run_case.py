from unittest.mock import Mock, call, patch

from evals.evaluator import EvaluationReport
from evals.run_all import run_all_cases
from evals.run_case import CaseRunReport, print_case_report
from policy_coherence_investigator.investigation import (
    CoherenceFinding,
    EvidenceNeed,
    EvidenceNeedKind,
    EvidenceReference,
    FindingCategory,
    InvestigationResult,
)


def test_compact_case_report_prints_summary_and_issues_without_raw_model_json(capsys) -> None:
    report = CaseRunReport(
        case_id="access-offboarding-b",
        architecture="bounded",
        result=InvestigationResult(
            category=FindingCategory.APPARENT_CONFLICT_RESOLVED,
            summary="The rules coexist because their account populations differ.",
            findings=[
                CoherenceFinding(
                    finding_id="scope_distinction",
                    conclusion="The account populations differ.",
                    citations=[
                        EvidenceReference(
                            document_id="identity_definitions_v2",
                            clause_id="IDD-2.5",
                        )
                    ],
                )
            ],
        ),
        retrieved_clauses=(),
        retrieval_count=2,
        retrieval_budget=3,
        termination_reason="decision_complete",
        requested_evidence_needs=(
            EvidenceNeed(
                kind=EvidenceNeedKind.RETRIEVE_POPULATION_POLICY,
                rationale="Identify the policy governing the relevant account population.",
                query="ordinary privileged account population policy",
            ),
        ),
        evaluation=EvaluationReport(("required finding 'x' is missing",)),
    )

    print_case_report(report)

    output = capsys.readouterr().out
    assert "access-offboarding-b: FAIL | bounded | category=apparent_conflict_resolved" in output
    assert (
        "retrievals=2/3 | followups=retrieve_population_policy | "
        "termination=decision_complete"
    ) in output
    assert "summary: The rules coexist because their account populations differ." in output
    assert "issue: required finding 'x' is missing" in output
    assert "{\"category\"" not in output


def test_suite_runner_continues_after_an_execution_error() -> None:
    passing_report = Mock(case_id="access-offboarding-a", passed=True)
    failing_report = Mock(case_id="access-offboarding-c", passed=False)

    with patch(
        "evals.run_all.run_case",
        side_effect=[passing_report, RuntimeError("provider unavailable"), failing_report],
    ) as mocked_run_case:
        suite = run_all_cases(
            ("access-offboarding-a", "access-offboarding-b", "access-offboarding-c"),
            architecture="baseline",
            provider="openai",
        )

    assert suite.case_reports == (passing_report, failing_report)
    assert suite.execution_failures[0].case_id == "access-offboarding-b"
    assert suite.execution_failures[0].error_type == "RuntimeError"
    assert mocked_run_case.call_args_list == [
        call("access-offboarding-a", architecture="baseline", provider="openai"),
        call("access-offboarding-b", architecture="baseline", provider="openai"),
        call("access-offboarding-c", architecture="baseline", provider="openai"),
    ]
