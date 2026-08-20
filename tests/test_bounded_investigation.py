from datetime import date
from pathlib import Path
from unittest.mock import Mock

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

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
)
from policy_coherence_investigator.retrieval import (
    LexicalClauseRetriever,
    filter_applicable_clauses,
    load_policy_corpus,
    rank_clauses,
)
from policy_coherence_investigator.workflows import build_bounded_investigation_graph
from policy_coherence_investigator.workflows.bounded_investigation import _retrieve

CORPUS_DIRECTORY = Path("evals/corpora/access-offboarding-b")
CORPUS_A_DIRECTORY = Path("evals/corpora/access-offboarding-a")
QUESTION = (
    "Definierar våra gällande policyer samstämmigt när privilegierad åtkomst ska "
    "inaktiveras jämfört med kontonas allmänna hantering efter avslut?"
)


class RecordingStructuredModel:
    """A deterministic model fake that returns a planned investigation trajectory."""

    def __init__(self, results: list[InvestigationResult]) -> None:
        self.results = results
        self.invocations: list[list[BaseMessage]] = []

    def invoke(self, messages: list[BaseMessage]) -> InvestigationResult:
        self.invocations.append(messages)
        return self.results.pop(0)


def test_bounded_graph_retrieves_targeted_new_evidence_and_revises_scope() -> None:
    initial_result, final_result = _multi_step_results()
    structured_model = RecordingStructuredModel([initial_result, final_result])
    model = Mock(spec=BaseChatModel)
    model.with_structured_output.return_value = structured_model
    graph = build_bounded_investigation_graph(model, load_policy_corpus(CORPUS_DIRECTORY))

    state = graph.invoke(
        {
            "question": QUESTION,
            "working_scope": _scope(["employee"]),
            "retrieval_budget": 3,
            "retrieval_limit": 5,
        }
    )

    assert state["final_result"] == final_result
    assert state["termination_reason"] == "decision_complete"
    assert len(state["result_history"]) == 2
    assert len(state["investigation_ledger"].retrieval_history) == 2
    assert state["investigation_ledger"].working_scope.populations == ["employee", "contractor"]
    assert state["requested_evidence_needs"] == [initial_result.next_evidence_need]
    retrieved_references = {
        (clause.document.document_id, clause.clause_id) for clause in state["retrieved_clauses"]
    }
    assert ("identity_definitions_v2", "IDD-2.5") in retrieved_references

    initial_prompt = "\n".join(
        str(message.content) for message in structured_model.invocations[0]
    )
    reassessment_prompt = "\n".join(
        str(message.content) for message in structured_model.invocations[1]
    )
    assert "<prior_assessment>" not in initial_prompt
    assert "<prior_assessment>" in reassessment_prompt
    assert "The prior assessment below is provisional reasoning" in reassessment_prompt


def test_bounded_graph_stops_when_the_initial_retrieval_uses_the_full_budget() -> None:
    initial_result, _ = _multi_step_results()
    structured_model = RecordingStructuredModel([initial_result])
    model = Mock(spec=BaseChatModel)
    model.with_structured_output.return_value = structured_model
    graph = build_bounded_investigation_graph(model, load_policy_corpus(CORPUS_DIRECTORY))

    state = graph.invoke(
        {
            "question": QUESTION,
            "working_scope": _scope(["employee"]),
            "retrieval_budget": 1,
        }
    )

    assert state["final_result"] == initial_result
    assert state["termination_reason"] == "retrieval_budget_exhausted"
    assert len(structured_model.invocations) == 1
    assert state["requested_evidence_needs"] == []


def test_follow_up_retrieval_selects_new_clauses_before_applying_its_limit() -> None:
    corpus = load_policy_corpus(CORPUS_A_DIRECTORY)
    scope = _scope(["employee", "contractor"])
    query = "konsult avslut policyer konflikt åtkomst inaktivering personal privilegierad"
    ranked = rank_clauses(
        query,
        filter_applicable_clauses(
            corpus,
            as_of_date=scope.as_of_date,
            geography=scope.geography,
        ),
        limit=len(corpus.clauses),
    )
    previously_retrieved = tuple(result.clause for result in ranked[:5])
    expected_new_clauses = tuple(result.clause for result in ranked[5:7])
    ledger = initialize_ledger(
        question=QUESTION,
        working_scope=scope,
        retrieval_budget=2,
    )

    updated_ledger, new_clauses = _retrieve(
        ledger,
        corpus=corpus,
        query=query,
        rationale="Look beyond previously retrieved contractor policy clauses.",
        retrieval_limit=2,
        previously_retrieved=previously_retrieved,
        retriever=LexicalClauseRetriever(),
    )

    assert new_clauses == expected_new_clauses
    assert len(new_clauses) == 2
    assert updated_ledger.retrieval_history[0].returned_clauses == [
        EvidenceReference(
            document_id=clause.document.document_id,
            clause_id=clause.clause_id,
        )
        for clause in expected_new_clauses
    ]


def _scope(populations: list[str]) -> WorkingScope:
    return WorkingScope(
        topic="access revocation after termination",
        populations=populations,
        access_types=["ordinary", "privileged"],
        geography="global",
        as_of_date=date(2026, 8, 16),
    )


def _multi_step_results() -> tuple[InvestigationResult, InvestigationResult]:
    initial_result = InvestigationResult(
        category=FindingCategory.COVERAGE_GAP_OR_INSUFFICIENT_EVIDENCE,
        summary=(
            "The retrieved rules need an ordinary-employee rule before their different "
            "deadlines can be compared."
        ),
        findings=[
            CoherenceFinding(
                finding_id="ordinary_employee_deadline_evidence_needed",
                conclusion=(
                    "The initial clauses establish privileged-access deadlines but not an "
                    "ordinary-employee deadline."
                ),
                citations=[
                    EvidenceReference(
                        document_id="privileged_access_standard_v2",
                        clause_id="PAS-3.1",
                    ),
                    EvidenceReference(
                        document_id="access_control_policy_v4",
                        clause_id="ACP-4.2.1",
                    ),
                ],
            )
        ],
        scope_assumptions=[
            ScopeAssumption(
                assumption_id="ordinary_employee_scope_unresolved",
                statement=(
                    "The initial evidence did not establish the ordinary-employee "
                    "deadline."
                ),
            )
        ],
        revised_working_scope=_scope(["employee", "contractor"]),
        next_evidence_need=EvidenceNeed(
            kind=EvidenceNeedKind.RETRIEVE_POPULATION_POLICY,
            target="ordinary_employee_termination_deadline",
            rationale=(
                "An ordinary-employee policy is needed to compare its deadline with the "
                "privileged-access rule."
            ),
            query="HR begär att ordinära medarbetarkonton inaktiveras avslutstidpunkten",
        ),
    )
    final_result = InvestigationResult(
        category=FindingCategory.APPARENT_CONFLICT_RESOLVED,
        summary="The deadlines coexist because they govern ordinary and privileged accounts.",
        findings=[
            CoherenceFinding(
                finding_id="ordinary_and_privileged_deadlines_have_distinct_scope",
                conclusion=(
                    "Immediate revocation applies to privileged access, not ordinary "
                    "employee accounts."
                ),
                citations=[
                    EvidenceReference(
                        document_id="privileged_access_standard_v2",
                        clause_id="PAS-3.1",
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
    )
    return initial_result, final_result
