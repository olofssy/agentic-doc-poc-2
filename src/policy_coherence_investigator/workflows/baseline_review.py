"""Fixed retrieve-and-compare baseline for policy-coherence evaluation."""

from datetime import date
from typing import NotRequired, TypedDict, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from policy_coherence_investigator.investigation.models import InvestigationResult
from policy_coherence_investigator.investigation.prompts import build_fixed_review_messages
from policy_coherence_investigator.investigation.validation import validate_result_citations
from policy_coherence_investigator.retrieval import (
    PolicyClause,
    PolicyCorpus,
    filter_applicable_clauses,
    rank_clauses,
)


class FixedReviewState(TypedDict):
    """Input, retrieved evidence, and result for the one-pass baseline."""

    question: str
    as_of_date: date
    geography: str
    retrieval_limit: NotRequired[int]
    retrieved_clauses: NotRequired[tuple[PolicyClause, ...]]
    result: NotRequired[InvestigationResult]


def build_fixed_review_graph(
    model: BaseChatModel,
    corpus: PolicyCorpus,
) -> CompiledStateGraph:
    """Build one fixed retrieval pass followed by one structured model comparison."""

    structured_model = cast(
        Runnable[list[BaseMessage], InvestigationResult],
        model.with_structured_output(InvestigationResult),
    )

    def retrieve_and_review(state: FixedReviewState) -> dict[str, object]:
        applicable_clauses = filter_applicable_clauses(
            corpus,
            as_of_date=state["as_of_date"],
            geography=state["geography"],
        )
        ranked_clauses = rank_clauses(
            state["question"],
            applicable_clauses,
            limit=state.get("retrieval_limit", 5),
        )
        retrieved_clauses = tuple(result.clause for result in ranked_clauses)
        messages = build_fixed_review_messages(
            question=state["question"],
            retrieved_clauses=retrieved_clauses,
        )
        result = structured_model.invoke(messages)
        validate_result_citations(result, retrieved_clauses)
        return {"retrieved_clauses": retrieved_clauses, "result": result}

    builder = StateGraph(FixedReviewState)
    builder.add_node("retrieve_and_review", retrieve_and_review)
    builder.add_edge(START, "retrieve_and_review")
    builder.add_edge("retrieve_and_review", END)
    return builder.compile()
