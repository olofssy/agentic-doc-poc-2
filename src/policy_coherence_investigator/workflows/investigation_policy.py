"""Deterministic routing for a bounded policy-evidence investigation."""

from enum import StrEnum

from policy_coherence_investigator.investigation import EvidenceNeed, EvidenceNeedKind


class InvestigationRoute(StrEnum):
    """The next graph action permitted after one structured review."""

    FOLLOW_UP_RETRIEVAL = "follow_up_retrieval"
    FINISH_DECISION = "finish_decision"
    FINISH_BUDGET_EXHAUSTED = "finish_budget_exhausted"
    FINISH_REPEATED_NEED = "finish_repeated_need"
    FINISH_HUMAN_ESCALATION = "finish_human_escalation"


def route_next_evidence_need(
    evidence_need: EvidenceNeed | None,
    *,
    remaining_retrieval_budget: int,
    requested_evidence_needs: list[EvidenceNeed],
) -> InvestigationRoute:
    """Validate a model-proposed evidence need before it can trigger retrieval."""

    if evidence_need is None:
        return InvestigationRoute.FINISH_DECISION
    if evidence_need.kind == EvidenceNeedKind.ASK_HUMAN:
        return InvestigationRoute.FINISH_HUMAN_ESCALATION
    if remaining_retrieval_budget == 0:
        return InvestigationRoute.FINISH_BUDGET_EXHAUSTED
    if evidence_need in requested_evidence_needs:
        return InvestigationRoute.FINISH_REPEATED_NEED
    return InvestigationRoute.FOLLOW_UP_RETRIEVAL
