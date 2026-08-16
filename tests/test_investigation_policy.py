from policy_coherence_investigator.investigation import EvidenceNeed, EvidenceNeedKind
from policy_coherence_investigator.workflows.investigation_policy import (
    InvestigationRoute,
    route_next_evidence_need,
)


def _need(kind: EvidenceNeedKind = EvidenceNeedKind.RETRIEVE_DEFINITION) -> EvidenceNeed:
    return EvidenceNeed(
        kind=kind,
        rationale="The unresolved term materially affects applicability.",
        query="workforce identity definition",
    )


def test_route_finishes_when_no_further_evidence_is_needed() -> None:
    assert route_next_evidence_need(
        None,
        remaining_retrieval_budget=2,
        requested_evidence_needs=[],
    ) == InvestigationRoute.FINISH_DECISION


def test_route_stops_for_human_escalation_and_exhausted_budget() -> None:
    assert route_next_evidence_need(
        _need(EvidenceNeedKind.ASK_HUMAN),
        remaining_retrieval_budget=2,
        requested_evidence_needs=[],
    ) == InvestigationRoute.FINISH_HUMAN_ESCALATION
    assert route_next_evidence_need(
        _need(),
        remaining_retrieval_budget=0,
        requested_evidence_needs=[],
    ) == InvestigationRoute.FINISH_BUDGET_EXHAUSTED


def test_route_rejects_an_identical_repeated_evidence_need() -> None:
    need = _need()

    assert route_next_evidence_need(
        need,
        remaining_retrieval_budget=2,
        requested_evidence_needs=[need],
    ) == InvestigationRoute.FINISH_REPEATED_NEED
