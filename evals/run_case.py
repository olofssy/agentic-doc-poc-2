"""Explicit paid runner for one policy-coherence evaluation case."""

import argparse
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

from evals.evaluator import EvaluationReport, evaluate_result
from policy_coherence_investigator.case_data import load_case, load_oracle
from policy_coherence_investigator.case_data.loader import CaseInput
from policy_coherence_investigator.infrastructure import build_chat_model
from policy_coherence_investigator.investigation import (
    Architecture,
    EvidenceNeed,
    InvestigationLedger,
    InvestigationResult,
    WorkingScope,
)
from policy_coherence_investigator.retrieval import (
    PolicyClause,
    PolicyCorpus,
    load_policy_corpus,
)
from policy_coherence_investigator.workflows import (
    build_bounded_investigation_graph,
    build_fixed_review_graph,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CaseRunReport:
    """One paid run and its deterministic post-run evaluation."""

    case_id: str
    architecture: Architecture
    result: InvestigationResult | None
    retrieved_clauses: tuple[PolicyClause, ...]
    retrieval_count: int
    retrieval_budget: int
    termination_reason: str
    requested_evidence_needs: tuple[EvidenceNeed, ...]
    evaluation: EvaluationReport

    @property
    def passed(self) -> bool:
        return self.result is not None and self.evaluation.passed


@dataclass(frozen=True)
class ArchitectureRun:
    """One architecture's raw graph outcome, before oracle-based evaluation."""

    result: InvestigationResult | None
    retrieved_clauses: tuple[PolicyClause, ...]
    ledger: InvestigationLedger | None
    retrieval_count: int
    termination_reason: str
    requested_evidence_needs: tuple[EvidenceNeed, ...]


def run_case(
    case_id: str,
    *,
    architecture: Architecture = Architecture.BOUNDED,
    provider: str | None = None,
) -> CaseRunReport:
    """Invoke one architecture, then load the hidden oracle only for evaluation."""

    if architecture not in Architecture:
        raise ValueError(f"unsupported architecture: {architecture!r}")
    case = load_case(case_id)
    corpus = load_policy_corpus(_corpus_directory(case.case.corpus_id))
    model = build_chat_model(provider)

    run = (
        _run_baseline_architecture(model, corpus, case)
        if architecture == Architecture.BASELINE
        else _run_bounded_architecture(model, corpus, case)
    )

    # The graph has completed; only the evaluator may now inspect hidden expectations.
    oracle = load_oracle(case_id)
    evaluation = (
        evaluate_result(
            case=case,
            oracle=oracle,
            corpus=corpus,
            result=run.result,
            retrieved_clauses=run.retrieved_clauses,
            ledger=run.ledger,
            architecture=architecture,
            requested_evidence_needs=run.requested_evidence_needs,
        )
        if run.result is not None
        else EvaluationReport(("workflow completed without a structured final result",))
    )
    return CaseRunReport(
        case_id=case.case.case_id,
        architecture=architecture,
        result=run.result,
        retrieved_clauses=run.retrieved_clauses,
        retrieval_count=run.retrieval_count,
        retrieval_budget=case.case.retrieval_budget,
        termination_reason=run.termination_reason,
        requested_evidence_needs=run.requested_evidence_needs,
        evaluation=evaluation,
    )


def _run_baseline_architecture(
    model: BaseChatModel,
    corpus: PolicyCorpus,
    case: CaseInput,
) -> ArchitectureRun:
    """Invoke the fixed retrieve-and-compare baseline for one case."""

    state = build_fixed_review_graph(model, corpus).invoke(
        {
            "question": case.case.question,
            "as_of_date": case.case.review_context.as_of_date,
            "geography": case.case.review_context.geography,
        },
        config=_run_config(case.case.case_id, Architecture.BASELINE),
    )
    return ArchitectureRun(
        result=InvestigationResult.model_validate(state["result"]),
        retrieved_clauses=tuple(state["retrieved_clauses"]),
        ledger=None,
        retrieval_count=1,
        termination_reason="fixed_review_complete",
        requested_evidence_needs=(),
    )


def _run_bounded_architecture(
    model: BaseChatModel,
    corpus: PolicyCorpus,
    case: CaseInput,
) -> ArchitectureRun:
    """Invoke the bounded, evidence-driven investigation for one case."""

    state = build_bounded_investigation_graph(model, corpus).invoke(
        {
            "question": case.case.question,
            "working_scope": _initial_working_scope(
                case.case.question,
                case.case.review_context,
            ),
            "retrieval_budget": case.case.retrieval_budget,
        },
        config=_run_config(case.case.case_id, Architecture.BOUNDED),
    )
    result = (
        InvestigationResult.model_validate(state["final_result"])
        if "final_result" in state
        else None
    )
    ledger = (
        InvestigationLedger.model_validate(state["investigation_ledger"])
        if "investigation_ledger" in state
        else None
    )
    return ArchitectureRun(
        result=result,
        retrieved_clauses=tuple(state.get("retrieved_clauses", ())),
        ledger=ledger,
        retrieval_count=len(ledger.retrieval_history) if ledger is not None else 0,
        termination_reason=state.get("termination_reason", "unknown"),
        requested_evidence_needs=tuple(state.get("requested_evidence_needs", ())),
    )


def print_case_report(report: CaseRunReport) -> None:
    """Print one compact report without exposing the hidden oracle or raw model payload."""

    status = "PASS" if report.passed else "FAIL"
    category = report.result.category.value if report.result is not None else "none"
    follow_up_kinds = ",".join(
        evidence_need.kind.value for evidence_need in report.requested_evidence_needs
    ) or "none"
    print(
        f"{report.case_id}: {status} | {report.architecture} | category={category} | "
        f"retrievals={report.retrieval_count}/{report.retrieval_budget} | "
        f"followups={follow_up_kinds} | "
        f"termination={report.termination_reason}"
    )
    if report.result is not None:
        print(f"  summary: {textwrap.shorten(report.result.summary, width=180, placeholder='…')}")
    for issue in report.evaluation.issues:
        print(f"  issue: {issue}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run one paid case with concise human-readable output."""

    parser = argparse.ArgumentParser(description="Run one policy-coherence evaluation case.")
    parser.add_argument("case_id", help="Neutral directory ID under evals/cases.")
    parser.add_argument("--provider", choices=("openai", "anthropic"))
    parser.add_argument(
        "--architecture",
        type=Architecture,
        choices=tuple(Architecture),
        default=Architecture.BOUNDED,
    )
    args = parser.parse_args(argv)

    load_dotenv()
    report = run_case(args.case_id, architecture=args.architecture, provider=args.provider)
    print_case_report(report)
    return 0 if report.passed else 1


def _corpus_directory(corpus_id: str) -> Path:
    return REPOSITORY_ROOT / "evals" / "corpora" / corpus_id


def _initial_working_scope(question: str, review_context) -> WorkingScope:
    """Use only the agent-visible question and context for the initial narrow-domain scope."""

    return WorkingScope(
        topic=question,
        populations=review_context.populations,
        access_types=review_context.access_types,
        geography=review_context.geography,
        as_of_date=review_context.as_of_date,
    )


def _run_config(case_id: str, architecture: Architecture) -> dict[str, object]:
    return {
        "run_name": f"{architecture}_policy_coherence_review",
        "metadata": {"case_id": case_id, "architecture": architecture},
    }


if __name__ == "__main__":
    raise SystemExit(main())
