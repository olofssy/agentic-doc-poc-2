from datetime import date
from unittest.mock import patch

import pytest

from evals.evaluator import EvaluationReport
from policy_coherence_investigator.interfaces.case_explorer import load_explorer_cases
from policy_coherence_investigator.interfaces.investigate import InvestigationRunReport
from policy_coherence_investigator.interfaces.workbench import (
    WorkbenchRequest,
    default_workbench_request,
    evaluate_workbench_report,
    is_canonical_request,
    parse_workbench_request,
    render_workbench_page,
    run_workbench_investigation,
)


def test_selected_case_prefills_the_canonical_question_and_scope() -> None:
    selected_case = load_explorer_cases()[1]

    request = default_workbench_request(selected_case)

    assert request.case_id == "access-offboarding-b"
    assert request.question == selected_case.case_input.case.question
    assert request.as_of_date == date(2026, 8, 16)
    assert request.geography == "global"
    assert request.populations == ("employee",)
    assert request.access_types == ("ordinary", "privileged")


def test_request_accepts_editable_scope_but_rejects_unknown_scope_values() -> None:
    cases = load_explorer_cases()
    request = parse_workbench_request(
        {
            "case": ["access-offboarding-c"],
            "question": ["Do contractor offboarding policies conflict?"],
            "as_of": ["2026-08-16"],
            "geography": ["global"],
            "population": ["contractor"],
            "access_type": ["ordinary"],
        },
        cases,
    )

    assert request.populations == ("contractor",)
    assert request.access_types == ("ordinary",)

    with pytest.raises(ValueError, match="Invalid population"):
        parse_workbench_request(
            {
                "case": ["access-offboarding-c"],
                "question": ["A question"],
                "as_of": ["2026-08-16"],
                "geography": ["global"],
                "population": ["vendor"],
                "access_type": ["ordinary"],
            },
            cases,
        )


def test_workbench_passes_only_the_selected_case_corpus_and_form_values_to_the_run() -> None:
    cases = load_explorer_cases()
    request = WorkbenchRequest(
        case_id="access-offboarding-c",
        question="Do contractor offboarding policies conflict?",
        as_of_date=date(2026, 8, 16),
        geography="global",
        populations=("contractor",),
        access_types=("ordinary",),
        retrieval_budget=3,
    )
    expected_report = InvestigationRunReport(
        question=request.question,
        corpus_id="access-offboarding-c",
        result=None,
        retrieved_clauses=(),
        retrieval_count=0,
        retrieval_budget=3,
        requested_evidence_needs=(),
        termination_reason="no_initial_evidence",
    )

    with patch(
        "policy_coherence_investigator.interfaces.workbench.run_investigation",
        return_value=expected_report,
    ) as run:
        report = run_workbench_investigation(request, cases, provider="openai")

    assert report == expected_report
    assert run.call_args.kwargs == {
        "question": request.question,
        "corpus_directory": cases[2].corpus.root,
        "as_of_date": request.as_of_date,
        "geography": request.geography,
        "populations": request.populations,
        "access_types": request.access_types,
        "retrieval_budget": request.retrieval_budget,
        "provider": "openai",
        "retriever_name": request.retriever,
    }


def test_workbench_renders_case_explorer_and_single_submission_panel() -> None:
    page = render_workbench_page(load_explorer_cases(), "access-offboarding-a")

    assert "Demo evaluation notes" in page
    assert "Investigate a policy question" in page
    assert 'method="post" action="/investigate"' in page
    assert "Human resolution guide" in page
    assert "employee" in page
    assert "contractor" in page
    assert "Case explorer" in page
    assert "Ask a policy-coherence question" in page
    assert "Investigating policy evidence…" in page
    assert 'button:disabled' in page
    assert "hidden expected outcome after the run" in page
    assert 'id="comparison-status"' in page
    assert "updateComparisonStatus" in page


def test_review_question_and_workbench_default_share_the_case_definition() -> None:
    cases = load_explorer_cases()
    selected_case = cases[0]

    page = render_workbench_page(cases, selected_case.case_input.case.case_id)

    assert selected_case.case_input.case.question in page
    assert (
        selected_case.case_input.case.question
        == default_workbench_request(selected_case).question
    )


def test_selected_cases_have_distinct_canonical_questions_and_scope_defaults() -> None:
    cases = load_explorer_cases()
    case_a, case_b, case_c, case_d = (default_workbench_request(case) for case in cases)

    assert len({case_a.question, case_b.question, case_c.question, case_d.question}) == 4
    assert case_a.populations == ("contractor",)
    assert case_b.populations == ("employee",)
    assert case_c.populations == ("employee", "contractor")
    assert case_d.populations == ("partner_assignee",)
    assert case_a.access_types == ("ordinary",)
    assert case_b.access_types == ("ordinary", "privileged")
    assert case_c.access_types == ("ordinary",)
    assert case_d.access_types == ("ordinary",)


def test_expected_outcome_comparison_requires_the_untouched_case_inputs() -> None:
    selected_case = load_explorer_cases()[0]
    canonical = default_workbench_request(selected_case)
    custom = WorkbenchRequest(
        case_id=canonical.case_id,
        question="Do contractor offboarding policies conflict?",
        as_of_date=canonical.as_of_date,
        geography=canonical.geography,
        populations=canonical.populations,
        access_types=canonical.access_types,
        retrieval_budget=canonical.retrieval_budget,
    )
    report = InvestigationRunReport(
        question=canonical.question,
        corpus_id=selected_case.corpus.corpus_id,
        result=None,
        retrieved_clauses=(),
        retrieval_count=0,
        retrieval_budget=canonical.retrieval_budget,
        requested_evidence_needs=(),
        termination_reason="no_initial_evidence",
    )

    assert is_canonical_request(canonical, selected_case)
    assert not is_canonical_request(custom, selected_case)
    assert evaluate_workbench_report(custom, selected_case, report) is None
    assert evaluate_workbench_report(canonical, selected_case, report) == EvaluationReport(
        ("workflow completed without a structured final result",)
    )


def test_retriever_choice_does_not_affect_canonical_status() -> None:
    selected_case = load_explorer_cases()[0]
    canonical = default_workbench_request(selected_case)
    vector_choice = WorkbenchRequest(
        case_id=canonical.case_id,
        question=canonical.question,
        as_of_date=canonical.as_of_date,
        geography=canonical.geography,
        populations=canonical.populations,
        access_types=canonical.access_types,
        retrieval_budget=canonical.retrieval_budget,
        retriever="vector",
    )

    assert canonical.retriever == "lexical"
    assert is_canonical_request(vector_choice, selected_case)


def test_parse_workbench_request_reads_and_validates_the_retriever_choice() -> None:
    cases = load_explorer_cases()
    base_form = {
        "case": ["access-offboarding-c"],
        "question": ["Do contractor offboarding policies conflict?"],
        "as_of": ["2026-08-16"],
        "geography": ["global"],
        "population": ["contractor"],
        "access_type": ["ordinary"],
    }

    request = parse_workbench_request({**base_form, "retriever": ["vector"]}, cases)
    assert request.retriever == "vector"

    assert parse_workbench_request(base_form, cases).retriever == "lexical"

    with pytest.raises(ValueError, match="Invalid retrieval method"):
        parse_workbench_request({**base_form, "retriever": ["embedding"]}, cases)


def test_workbench_form_offers_a_retrieval_method_toggle() -> None:
    page = render_workbench_page(load_explorer_cases(), "access-offboarding-a")

    assert 'name="retriever" value="lexical"' in page
    assert 'name="retriever" value="vector"' in page
    assert "Retrieval method" in page


def test_completed_canonical_run_renders_its_evaluation_status() -> None:
    selected_case = load_explorer_cases()[0]
    request = default_workbench_request(selected_case)
    report = InvestigationRunReport(
        question=request.question,
        corpus_id=selected_case.corpus.corpus_id,
        result=None,
        retrieved_clauses=(),
        retrieval_count=0,
        retrieval_budget=request.retrieval_budget,
        requested_evidence_needs=(),
        termination_reason="no_initial_evidence",
    )

    page = render_workbench_page(
        load_explorer_cases(),
        request.case_id,
        request=request,
        report=report,
        evaluation=EvaluationReport(()),
    )

    assert "Case evaluation passed" in page
