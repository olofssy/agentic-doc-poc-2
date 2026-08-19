from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from policy_coherence_investigator.infrastructure import build_chat_model
from policy_coherence_investigator.investigation import (
    CitationValidationError,
    CoherenceFinding,
    EvidenceReference,
    FindingCategory,
    InvestigationResult,
    WorkingScope,
)
from policy_coherence_investigator.retrieval import load_policy_corpus
from policy_coherence_investigator.workflows import build_fixed_review_graph

CORPUS_DIRECTORY = Path("evals/corpora/access-offboarding-a")
QUESTION = (
    "Do our currently effective policies coherently define when employee, contractor, "
    "and privileged access must be disabled after termination?"
)


def _scope() -> WorkingScope:
    return WorkingScope(
        topic=QUESTION,
        populations=["employee", "contractor"],
        access_types=["ordinary", "privileged"],
        geography="global",
        as_of_date=date(2026, 8, 16),
    )


class RecordingStructuredModel:
    """A deterministic fake that records only the evidence sent to the model."""

    def __init__(self, result: InvestigationResult) -> None:
        self.result = result
        self.invocations: list[list[BaseMessage]] = []

    def invoke(self, messages: list[BaseMessage]) -> InvestigationResult:
        self.invocations.append(messages)
        return self.result


def test_fixed_review_retrieves_clauses_and_returns_a_valid_structured_result() -> None:
    structured_model = RecordingStructuredModel(_valid_result())
    model = Mock(spec=BaseChatModel)
    model.with_structured_output.return_value = structured_model
    graph = build_fixed_review_graph(model, load_policy_corpus(CORPUS_DIRECTORY))

    state = graph.invoke(
        {
            "question": QUESTION,
            "working_scope": _scope(),
            "retrieval_limit": 5,
        }
    )

    model.with_structured_output.assert_called_once_with(InvestigationResult)
    assert state["result"] == _valid_result()
    retrieved_references = {
        (clause.document.document_id, clause.clause_id) for clause in state["retrieved_clauses"]
    }
    assert {
        ("access_control_policy_v4", "ACP-4.2.1"),
        ("contractor_management_policy_v2", "CMP-6.4"),
    } <= retrieved_references

    prompt = "\n".join(str(message.content) for message in structured_model.invocations[0])
    assert "<clause document_id='access_control_policy_v3'" not in prompt
    assert "<clause document_id='nordic_access_addendum_v1'" not in prompt
    assert "confirmed_conflict" in prompt
    assert "ordinary_and_privileged_deadlines_have_distinct_scope" in prompt
    assert "ordinary_accounts_vs_privileged_accounts" in prompt
    assert "Contractors are within the stated workforce-identity population" in prompt
    assert "A permission to retain access beyond a deadline is incompatible" in prompt
    assert "notification, or later review is" in prompt
    assert "not a disablement deadline" in prompt
    assert "{finding_ids}" not in prompt


def test_fixed_review_rejects_citations_to_clauses_not_retrieved() -> None:
    invalid_result = _valid_result(
        citation=EvidenceReference(
            document_id="nordic_access_addendum_v1",
            clause_id="NAA-2.4",
        )
    )
    structured_model = RecordingStructuredModel(invalid_result)
    model = Mock(spec=BaseChatModel)
    model.with_structured_output.return_value = structured_model
    graph = build_fixed_review_graph(model, load_policy_corpus(CORPUS_DIRECTORY))

    with pytest.raises(CitationValidationError, match="did not expose"):
        graph.invoke(
            {
                "question": QUESTION,
                "working_scope": _scope(),
            }
        )


def test_model_factory_rejects_an_unknown_provider() -> None:
    with pytest.raises(ValueError, match="unsupported LLM_PROVIDER"):
        build_chat_model("unknown")


def _valid_result(citation: EvidenceReference | None = None) -> InvestigationResult:
    contractor_citation = citation or EvidenceReference(
        document_id="contractor_management_policy_v2",
        clause_id="CMP-6.4",
    )
    return InvestigationResult(
        category=FindingCategory.CONFIRMED_CONFLICT,
        summary="Current policies impose incompatible contractor access-revocation deadlines.",
        findings=[
            CoherenceFinding(
                finding_id="incompatible_contractor_revocation_deadlines",
                conclusion=(
                    "The workforce deadline conflicts with the permitted contractor-access period."
                ),
                citations=[
                    EvidenceReference(
                        document_id="access_control_policy_v4",
                        clause_id="ACP-4.2.1",
                    ),
                    contractor_citation,
                ],
            )
        ],
    )
