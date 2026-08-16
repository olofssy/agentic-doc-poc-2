from policy_coherence_investigator.investigation import EvidenceNeed, EvidenceNeedKind
from policy_coherence_investigator.workflows.investigation_policy import (
    InvestigationRoute,
    route_next_evidence_need,
)


def _need(kind: EvidenceNeedKind = EvidenceNeedKind.RETRIEVE_DEFINITION) -> EvidenceNeed:
    return EvidenceNeed(
        kind=kind,
        target="workforce_identity_definition",
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


def test_route_rejects_a_repeated_evidence_target_even_when_reworded() -> None:
    first_need = _need()
    reworded_need = EvidenceNeed(
        kind=EvidenceNeedKind.RETRIEVE_DEFINITION,
        target="workforce_identity_definition",
        rationale="A different phrase for the same unresolved applicability question.",
        query="population: contractors; access type: ordinary; unresolved: workforce definition",
    )

    assert route_next_evidence_need(
        reworded_need,
        remaining_retrieval_budget=2,
        requested_evidence_needs=[first_need],
    ) == InvestigationRoute.FINISH_REPEATED_NEED


def test_route_allows_a_different_target_with_the_same_retrieval_kind() -> None:
    contractor_need = EvidenceNeed(
        kind=EvidenceNeedKind.RETRIEVE_POPULATION_POLICY,
        target="contractor_ordinary_access_deadline",
        rationale="The contractor ordinary-access deadline is unresolved.",
        query="contractor ordinary access termination deadline",
    )
    privileged_need = EvidenceNeed(
        kind=EvidenceNeedKind.RETRIEVE_POPULATION_POLICY,
        target="contractor_privileged_access_exception",
        rationale="The contractor privileged-access exception is unresolved.",
        query="contractor privileged access termination exception",
    )

    assert route_next_evidence_need(
        privileged_need,
        remaining_retrieval_budget=1,
        requested_evidence_needs=[contractor_need],
    ) == InvestigationRoute.FOLLOW_UP_RETRIEVAL
