from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from langchain_core.language_models.chat_models import BaseChatModel

from policy_coherence_investigator.case_data import load_case
from policy_coherence_investigator.interfaces.studio.graphs import build_studio_case_graph
from policy_coherence_investigator.investigation import (
    CoherenceFinding,
    EvidenceReference,
    FindingCategory,
    InvestigationResult,
)
from policy_coherence_investigator.retrieval import (
    filter_applicable_clauses,
    load_policy_corpus,
    rank_clauses,
)

CASE_ID = "access-offboarding-a"
CORPUS_DIRECTORY = Path("evals/corpora") / CASE_ID


def test_studio_case_graph_reaches_a_decision_from_zero_input() -> None:
    case = load_case(CASE_ID)
    final_result = _final_result_citing_top_retrieved_clause(case)
    structured_model = Mock()
    structured_model.invoke.return_value = final_result
    model = Mock(spec=BaseChatModel)
    model.with_structured_output.return_value = structured_model

    graph = build_studio_case_graph(CASE_ID, model=model)
    state = graph.invoke({})

    assert state["question"] == case.case.question
    assert state["working_scope"].populations == case.case.review_context.populations
    assert state["working_scope"].geography == case.case.review_context.geography
    assert state["final_result"] == final_result
    assert state["termination_reason"] == "decision_complete"


def test_studio_case_graph_never_loads_the_hidden_oracle() -> None:
    model = Mock(spec=BaseChatModel)

    with patch("policy_coherence_investigator.case_data.loader.load_oracle") as load_oracle:
        build_studio_case_graph(CASE_ID, model=model)

    load_oracle.assert_not_called()


def test_studio_case_graph_rejects_an_invalid_case_id() -> None:
    with pytest.raises(ValueError, match="case ID is invalid"):
        build_studio_case_graph("../../outside")


def _final_result_citing_top_retrieved_clause(case) -> InvestigationResult:
    """Build a result whose citation matches what real initial retrieval will expose.

    Retrieval is not mocked, so the model's cited clause must be one initial_retrieve
    will actually surface for this case's real question and corpus.
    """
    corpus = load_policy_corpus(CORPUS_DIRECTORY)
    applicable_clauses = filter_applicable_clauses(
        corpus,
        as_of_date=case.case.review_context.as_of_date,
        geography=case.case.review_context.geography,
    )
    ranked = rank_clauses(case.case.question, applicable_clauses, limit=len(applicable_clauses))
    top_clause = ranked[0].clause
    return InvestigationResult(
        category=FindingCategory.APPARENT_CONFLICT_RESOLVED,
        summary="The retrieved rules do not conflict once scope is taken into account.",
        findings=[
            CoherenceFinding(
                finding_id="studio_smoke_test_finding",
                conclusion="The retrieved clause resolves the question without further evidence.",
                citations=[
                    EvidenceReference(
                        document_id=top_clause.document.document_id,
                        clause_id=top_clause.clause_id,
                    )
                ],
            )
        ],
    )
