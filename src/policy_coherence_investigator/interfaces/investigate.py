"""Oracle-free command-line interface for a bounded policy investigation."""

from __future__ import annotations

import argparse
import json
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from policy_coherence_investigator.infrastructure import build_chat_model
from policy_coherence_investigator.interfaces.sv_labels import humanize_sv
from policy_coherence_investigator.investigation import (
    EvidenceNeed,
    InvestigationLedger,
    InvestigationResult,
    WorkingScope,
)
from policy_coherence_investigator.retrieval import PolicyClause, load_policy_corpus
from policy_coherence_investigator.workflows import build_bounded_investigation_graph


@dataclass(frozen=True)
class InvestigationRunReport:
    """An oracle-free investigation result suitable for a person or another program."""

    question: str
    corpus_id: str
    result: InvestigationResult | None
    retrieved_clauses: tuple[PolicyClause, ...]
    retrieval_count: int
    retrieval_budget: int
    requested_evidence_needs: tuple[EvidenceNeed, ...]
    termination_reason: str
    ledger: InvestigationLedger | None = None

    def as_dict(self) -> dict[str, object]:
        """Return stable structured output without prompts, hidden data, or raw graph state."""

        return {
            "question": self.question,
            "corpus_id": self.corpus_id,
            "result": self.result.model_dump(mode="json") if self.result is not None else None,
            "investigation": {
                "retrieval_count": self.retrieval_count,
                "retrieval_budget": self.retrieval_budget,
                "termination_reason": self.termination_reason,
                "follow_up_kinds": [
                    evidence_need.kind.value
                    for evidence_need in self.requested_evidence_needs
                ],
                "follow_up_targets": [
                    evidence_need.target
                    for evidence_need in self.requested_evidence_needs
                ],
                "retrieved_clause_references": [
                    {
                        "document_id": clause.document.document_id,
                        "clause_id": clause.clause_id,
                    }
                    for clause in self.retrieved_clauses
                ],
            },
        }


def run_investigation(
    *,
    question: str,
    corpus_directory: Path,
    as_of_date: date,
    geography: str,
    populations: Sequence[str],
    access_types: Sequence[str],
    retrieval_budget: int = 3,
    provider: str | None = None,
) -> InvestigationRunReport:
    """Run a bounded investigation using only the supplied question, scope, and corpus."""

    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("question must not be blank")
    corpus = load_policy_corpus(corpus_directory)
    working_scope = WorkingScope(
        topic=normalized_question,
        populations=list(populations),
        access_types=list(access_types),
        geography=geography,
        as_of_date=as_of_date,
    )
    model = build_chat_model(provider)
    state = build_bounded_investigation_graph(model, corpus).invoke(
        {
            "question": normalized_question,
            "working_scope": working_scope,
            "retrieval_budget": retrieval_budget,
        },
        config={
            "run_name": "interactive_policy_coherence_review",
            "metadata": {"corpus_id": corpus.corpus_id, "architecture": "bounded"},
        },
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
    return InvestigationRunReport(
        question=normalized_question,
        corpus_id=corpus.corpus_id,
        result=result,
        retrieved_clauses=tuple(state.get("retrieved_clauses", ())),
        retrieval_count=len(ledger.retrieval_history) if ledger is not None else 0,
        retrieval_budget=retrieval_budget,
        requested_evidence_needs=tuple(state.get("requested_evidence_needs", ())),
        termination_reason=state.get("termination_reason", "unknown"),
        ledger=ledger,
    )


def print_investigation_report(report: InvestigationRunReport, output_format: str) -> None:
    """Print either machine-readable JSON or a compact human-oriented summary."""

    if output_format == "json":
        print(json.dumps(report.as_dict(), indent=2))
        return
    category = humanize_sv(report.result.category.value) if report.result is not None else "ingen"
    follow_up_kinds = ",".join(
        humanize_sv(evidence_need.kind.value) for evidence_need in report.requested_evidence_needs
    ) or "inga"
    print(
        f"kategori={category} | korpus={report.corpus_id} | "
        f"hämtningar={report.retrieval_count}/{report.retrieval_budget} | "
        f"uppföljningar={follow_up_kinds} | "
        f"avslutsorsak={humanize_sv(report.termination_reason)}"
    )
    if report.result is None:
        print("  sammanfattning: Ingen strukturerad granskning producerades.")
        return
    print(
        f"  sammanfattning: {textwrap.shorten(report.result.summary, width=180, placeholder='…')}"
    )
    for finding in report.result.findings:
        citations = ", ".join(
            f"{citation.document_id}/{citation.clause_id}" for citation in finding.citations
        )
        print(f"  fynd: {humanize_sv(finding.finding_id)} | underlag={citations}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run one explicit, paid, oracle-free policy-coherence investigation."""

    parser = argparse.ArgumentParser(description="Utred en policykoherensfråga.")
    parser.add_argument(
        "--question", required=True, help="Policyfråga i naturligt språk."
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        required=True,
        help="Katalog som innehåller corpus.yaml.",
    )
    parser.add_argument("--as-of", type=date.fromisoformat, required=True, help="ÅÅÅÅ-MM-DD.")
    parser.add_argument(
        "--geography", required=True, help="Granskningens geografi, till exempel global."
    )
    parser.add_argument(
        "--population",
        action="append",
        required=True,
        help="Population i omfånget; upprepa för fler än en.",
    )
    parser.add_argument(
        "--access-type",
        action="append",
        required=True,
        help="Åtkomsttyp i omfånget; upprepa för fler än en.",
    )
    parser.add_argument("--retrieval-budget", type=_positive_int, default=3)
    parser.add_argument("--provider", choices=("openai", "anthropic"))
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)

    load_dotenv()
    report = run_investigation(
        question=args.question,
        corpus_directory=args.corpus,
        as_of_date=args.as_of,
        geography=args.geography,
        populations=args.population,
        access_types=args.access_type,
        retrieval_budget=args.retrieval_budget,
        provider=args.provider,
    )
    print_investigation_report(report, args.format)
    return 0 if report.result is not None else 1


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("måste vara minst 1")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
