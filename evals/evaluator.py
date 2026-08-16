"""Deterministic evaluation of structured policy-coherence results and trajectories."""

from collections.abc import Iterable
from dataclasses import dataclass

from policy_coherence_investigator.case_data.loader import CaseInput, CaseOracle
from policy_coherence_investigator.investigation import (
    EvidenceNeed,
    InvestigationLedger,
    InvestigationResult,
)
from policy_coherence_investigator.retrieval import (
    PolicyClause,
    PolicyCorpus,
    filter_applicable_clauses,
)


@dataclass(frozen=True)
class EvaluationReport:
    """Compact machine-readable evaluation outcome with actionable issues."""

    issues: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.issues


def evaluate_result(
    *,
    case: CaseInput,
    oracle: CaseOracle,
    corpus: PolicyCorpus,
    result: InvestigationResult,
    retrieved_clauses: Iterable[PolicyClause],
    ledger: InvestigationLedger | None,
    architecture: str,
    requested_evidence_needs: Iterable[EvidenceNeed] = (),
) -> EvaluationReport:
    """Check result category, findings, citations, scope, and bounded trajectory evidence."""

    issues: list[str] = []
    if result.category not in oracle.acceptable_result_categories:
        issues.append(f"result category {result.category.value!r} is not accepted")

    findings = {finding.finding_id: finding for finding in result.findings}
    for finding_id in oracle.required_findings:
        if finding_id not in findings:
            issues.append(f"required finding {finding_id!r} is missing")
    for finding_id in oracle.forbidden_findings:
        if finding_id in findings:
            issues.append(f"forbidden finding {finding_id!r} is present")

    retrieved_references = {
        (clause.document.document_id, clause.clause_id) for clause in retrieved_clauses
    }
    cited_references = {
        (citation.document_id, citation.clause_id)
        for finding in result.findings
        for citation in finding.citations
    }
    uncited_decisive_sets = [
        {
            (reference.document_id, reference.clause_id)
            for reference in clause_set
        }
        for clause_set in oracle.decisive_clause_sets
    ]
    if not any(decisive_set <= cited_references for decisive_set in uncited_decisive_sets):
        issues.append("no oracle-designated decisive clause set is fully cited")
    if not cited_references <= retrieved_references:
        issues.append("result cites clauses that were not retrieved")

    applicable_references = {
        (clause.document.document_id, clause.clause_id)
        for clause in filter_applicable_clauses(
            corpus,
            as_of_date=case.case.review_context.as_of_date,
            geography=case.case.review_context.geography,
        )
    }
    if not cited_references <= applicable_references:
        issues.append("result cites superseded, future, or geographically inapplicable clauses")

    _evaluate_scope_distinctions(issues, oracle, result, ledger)
    if architecture == "bounded":
        _evaluate_bounded_trajectory(
            issues,
            case,
            oracle,
            ledger,
            requested_evidence_needs,
        )
    return EvaluationReport(tuple(issues))


def _evaluate_scope_distinctions(
    issues: list[str],
    oracle: CaseOracle,
    result: InvestigationResult,
    ledger: InvestigationLedger | None,
) -> None:
    if not oracle.required_scope_distinctions:
        return
    recorded_distinctions = {
        assumption.assumption_id
        for assumption in (
            ledger.scope_assumptions if ledger is not None else result.scope_assumptions
        )
    }
    for distinction in oracle.required_scope_distinctions:
        if distinction not in recorded_distinctions:
            issues.append(f"required scope distinction {distinction!r} is missing")


def _evaluate_bounded_trajectory(
    issues: list[str],
    case: CaseInput,
    oracle: CaseOracle,
    ledger: InvestigationLedger | None,
    requested_evidence_needs: Iterable[EvidenceNeed],
) -> None:
    if ledger is None:
        issues.append("bounded trajectory did not retain an investigation ledger")
        return
    if len(ledger.retrieval_history) > case.case.retrieval_budget:
        issues.append("retrieval budget was exceeded")
    if any(not record.rationale.strip() for record in ledger.retrieval_history):
        issues.append("a retrieval record has no rationale")
    if oracle.acceptable_follow_up_needs:
        actual_needs = {need.kind.value for need in requested_evidence_needs}
        if not actual_needs.intersection(oracle.acceptable_follow_up_needs):
            issues.append("no acceptable follow-up evidence need was recorded")
