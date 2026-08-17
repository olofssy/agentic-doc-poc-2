from datetime import date
from unittest.mock import patch

import pytest

from policy_coherence_investigator.interfaces.case_explorer import load_explorer_cases
from policy_coherence_investigator.interfaces.investigate import InvestigationRunReport
from policy_coherence_investigator.interfaces.workbench import (
    WorkbenchRequest,
    default_workbench_request,
    parse_workbench_request,
    render_workbench_page,
    run_workbench_investigation,
)


def test_selected_case_prefills_scope_but_leaves_a_single_shot_question_empty() -> None:
    selected_case = load_explorer_cases()[1]

    request = default_workbench_request(selected_case)

    assert request.case_id == "access-offboarding-b"
    assert request.question == ""
    assert request.as_of_date == date(2026, 8, 16)
    assert request.geography == "global"
    assert request.populations == ("employee", "contractor")
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
            "access_type": ["ordinary", "privileged"],
        },
        cases,
    )

    assert request.populations == ("contractor",)
    assert request.access_types == ("ordinary", "privileged")

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


def test_case_selection_renders_its_own_human_review_question() -> None:
    cases = load_explorer_cases()

    case_a_page = render_workbench_page(cases, "access-offboarding-a")
    case_b_page = render_workbench_page(cases, "access-offboarding-b")

    assert "Do workforce and contractor policies impose incompatible" in case_a_page
    assert "Do the ordinary-employee and privileged-account" in case_b_page
    assert "Do workforce and contractor policies impose incompatible" not in case_b_page
