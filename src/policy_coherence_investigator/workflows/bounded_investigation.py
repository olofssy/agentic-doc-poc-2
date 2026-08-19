"""Bounded, evidence-driven policy-coherence investigation workflow."""

from typing import NotRequired, TypedDict, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from policy_coherence_investigator.investigation import (
    EvidenceNeed,
    EvidenceReference,
    InvestigationLedger,
    InvestigationResult,
    WorkingScope,
    apply_review_result,
    initialize_ledger,
    record_retrieval,
)
from policy_coherence_investigator.investigation.prompts import (
    build_fixed_review_messages,
    build_reassessment_messages,
)
from policy_coherence_investigator.investigation.validation import validate_result_citations
from policy_coherence_investigator.retrieval import (
    DEFAULT_RETRIEVAL_LIMIT,
    ClauseRetriever,
    LexicalClauseRetriever,
    PolicyClause,
    PolicyCorpus,
    filter_applicable_clauses,
)

from .investigation_policy import InvestigationRoute, route_next_evidence_need


class BoundedInvestigationState(TypedDict):
    """Observable state for a maximum-three-retrieval policy investigation."""

    question: str
    working_scope: WorkingScope
    retrieval_budget: int
    retrieval_limit: NotRequired[int]
    retrieved_clauses: NotRequired[tuple[PolicyClause, ...]]
    current_result: NotRequired[InvestigationResult]
    final_result: NotRequired[InvestigationResult]
    result_history: NotRequired[list[InvestigationResult]]
    investigation_ledger: NotRequired[InvestigationLedger]
    ledger_history: NotRequired[list[InvestigationLedger]]
    requested_evidence_needs: NotRequired[list[EvidenceNeed]]
    termination_reason: NotRequired[str]


def build_bounded_investigation_graph(
    model: BaseChatModel,
    corpus: PolicyCorpus,
    *,
    retriever: ClauseRetriever | None = None,
) -> CompiledStateGraph:
    """Build a variable-length investigation with deterministic safety and budget controls."""

    selected_retriever = retriever or LexicalClauseRetriever()

    structured_model = cast(
        Runnable[list[BaseMessage], InvestigationResult],
        model.with_structured_output(InvestigationResult),
    )

    def initial_retrieve(state: BoundedInvestigationState) -> dict[str, object]:
        ledger = initialize_ledger(
            question=state["question"],
            working_scope=state["working_scope"],
            retrieval_budget=state["retrieval_budget"],
        )
        if ledger.remaining_retrieval_budget == 0:
            return {
                "investigation_ledger": ledger,
                "termination_reason": "retrieval_budget_exhausted",
            }
        ledger, retrieved_clauses = _retrieve(
            ledger,
            corpus=corpus,
            query=state["question"],
            rationale="Initial retrieval for the policy-coherence question.",
            retrieval_limit=state.get("retrieval_limit", DEFAULT_RETRIEVAL_LIMIT),
            previously_retrieved=(),
            retriever=selected_retriever,
        )
        if not retrieved_clauses:
            return {
                "investigation_ledger": ledger,
                "termination_reason": "no_initial_evidence",
            }
        return {
            "investigation_ledger": ledger,
            "retrieved_clauses": retrieved_clauses,
            "requested_evidence_needs": [],
        }

    def _review(
        messages: list[BaseMessage],
        *,
        ledger: InvestigationLedger,
        retrieved_clauses: tuple[PolicyClause, ...],
        result_history: list[InvestigationResult],
        ledger_history: list[InvestigationLedger],
    ) -> dict[str, object]:
        """Invoke one structured review, validate its citations, and extend both histories."""

        result = structured_model.invoke(messages)
        validate_result_citations(result, retrieved_clauses)
        updated_ledger = apply_review_result(ledger, result)
        return {
            "current_result": result,
            "result_history": [*result_history, result],
            "investigation_ledger": updated_ledger,
            "ledger_history": [*ledger_history, updated_ledger],
        }

    def initial_review(state: BoundedInvestigationState) -> dict[str, object]:
        ledger = state["investigation_ledger"]
        retrieved_clauses = state["retrieved_clauses"]
        messages = build_fixed_review_messages(
            question=state["question"],
            working_scope=ledger.working_scope,
            retrieved_clauses=retrieved_clauses,
        )
        return _review(
            messages,
            ledger=ledger,
            retrieved_clauses=retrieved_clauses,
            result_history=[],
            ledger_history=[],
        )

    def follow_up_retrieve(state: BoundedInvestigationState) -> dict[str, object]:
        ledger = state["investigation_ledger"]
        evidence_need = state["current_result"].next_evidence_need
        if evidence_need is None:
            raise RuntimeError("follow-up retrieval requires an evidence need")
        updated_ledger, new_clauses = _retrieve(
            ledger,
            corpus=corpus,
            query=evidence_need.query,
            rationale=evidence_need.rationale,
            retrieval_limit=state.get("retrieval_limit", DEFAULT_RETRIEVAL_LIMIT),
            previously_retrieved=state.get("retrieved_clauses", ()),
            retriever=selected_retriever,
        )
        requested_needs = [*state.get("requested_evidence_needs", []), evidence_need]
        if not new_clauses:
            return {
                "investigation_ledger": updated_ledger,
                "requested_evidence_needs": requested_needs,
                "termination_reason": "no_new_evidence",
            }
        return {
            "investigation_ledger": updated_ledger,
            "retrieved_clauses": (*state["retrieved_clauses"], *new_clauses),
            "requested_evidence_needs": requested_needs,
        }

    def reassess_review(state: BoundedInvestigationState) -> dict[str, object]:
        ledger = state["investigation_ledger"]
        retrieved_clauses = state["retrieved_clauses"]
        messages = build_reassessment_messages(
            question=state["question"],
            working_scope=ledger.working_scope,
            retrieved_clauses=retrieved_clauses,
            prior_result=state["current_result"],
        )
        return _review(
            messages,
            ledger=ledger,
            retrieved_clauses=retrieved_clauses,
            result_history=state.get("result_history", []),
            ledger_history=state.get("ledger_history", []),
        )

    def finish(state: BoundedInvestigationState) -> dict[str, object]:
        current_result = state.get("current_result")
        reason = state.get("termination_reason") or _termination_reason(state)
        update: dict[str, object] = {"termination_reason": reason}
        if current_result is not None:
            update["final_result"] = current_result
        return update

    def route_after_initial_retrieval(state: BoundedInvestigationState) -> str:
        return "initial_review" if state.get("retrieved_clauses") else "finish"

    def route_after_review(state: BoundedInvestigationState) -> str:
        route = _next_route(state)
        return "follow_up_retrieve" if route == InvestigationRoute.FOLLOW_UP_RETRIEVAL else "finish"

    def route_after_follow_up_retrieval(state: BoundedInvestigationState) -> str:
        return "reassess_review" if not state.get("termination_reason") else "finish"

    builder = StateGraph(BoundedInvestigationState)
    builder.add_node("initial_retrieve", initial_retrieve)
    builder.add_node("initial_review", initial_review)
    builder.add_node("follow_up_retrieve", follow_up_retrieve)
    builder.add_node("reassess_review", reassess_review)
    builder.add_node("finish", finish)
    builder.add_edge(START, "initial_retrieve")
    builder.add_conditional_edges(
        "initial_retrieve",
        route_after_initial_retrieval,
        {"initial_review": "initial_review", "finish": "finish"},
    )
    builder.add_conditional_edges(
        "initial_review",
        route_after_review,
        {"follow_up_retrieve": "follow_up_retrieve", "finish": "finish"},
    )
    builder.add_conditional_edges(
        "follow_up_retrieve",
        route_after_follow_up_retrieval,
        {"reassess_review": "reassess_review", "finish": "finish"},
    )
    builder.add_conditional_edges(
        "reassess_review",
        route_after_review,
        {"follow_up_retrieve": "follow_up_retrieve", "finish": "finish"},
    )
    builder.add_edge("finish", END)
    return builder.compile()


def _retrieve(
    ledger: InvestigationLedger,
    *,
    corpus: PolicyCorpus,
    query: str,
    rationale: str,
    retrieval_limit: int,
    previously_retrieved: tuple[PolicyClause, ...],
    retriever: ClauseRetriever,
) -> tuple[InvestigationLedger, tuple[PolicyClause, ...]]:
    applicable_clauses = filter_applicable_clauses(
        corpus,
        as_of_date=ledger.working_scope.as_of_date,
        geography=ledger.working_scope.geography,
    )
    ranked_results = retriever.rank(
        query,
        applicable_clauses,
        limit=len(applicable_clauses),
    )
    known_references = {
        (clause.document.document_id, clause.clause_id) for clause in previously_retrieved
    }
    new_clauses = tuple(
        result.clause
        for result in ranked_results
        if (result.clause.document.document_id, result.clause.clause_id) not in known_references
    )[:retrieval_limit]
    updated_ledger = record_retrieval(
        ledger,
        query=query,
        rationale=rationale,
        returned_clauses=(_reference_for_clause(clause) for clause in new_clauses),
    )
    return updated_ledger, new_clauses


def _reference_for_clause(clause: PolicyClause) -> EvidenceReference:
    return EvidenceReference(document_id=clause.document.document_id, clause_id=clause.clause_id)


def _next_route(state: BoundedInvestigationState) -> InvestigationRoute:
    ledger = state["investigation_ledger"]
    return route_next_evidence_need(
        state["current_result"].next_evidence_need,
        remaining_retrieval_budget=ledger.remaining_retrieval_budget,
        requested_evidence_needs=state.get("requested_evidence_needs", []),
    )


def _termination_reason(state: BoundedInvestigationState) -> str:
    route = _next_route(state)
    return {
        InvestigationRoute.FINISH_DECISION: "decision_complete",
        InvestigationRoute.FINISH_BUDGET_EXHAUSTED: "retrieval_budget_exhausted",
        InvestigationRoute.FINISH_REPEATED_NEED: "repeated_evidence_need",
        InvestigationRoute.FINISH_HUMAN_ESCALATION: "human_escalation_requested",
    }[route]
