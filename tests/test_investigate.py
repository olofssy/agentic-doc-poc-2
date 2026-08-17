from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

from policy_coherence_investigator.interfaces.investigate import (
    InvestigationRunReport,
    print_investigation_report,
    run_investigation,
)
from policy_coherence_investigator.investigation import (
    CoherenceFinding,
    EvidenceReference,
    FindingCategory,
    InvestigationLedger,
    InvestigationResult,
    RetrievalRecord,
    WorkingScope,
)
from policy_coherence_investigator.retrieval import load_policy_corpus

CORPUS_DIRECTORY = Path("evals/corpora/access-offboarding-a")


def test_run_investigation_uses_the_supplied_question_and_scope_without_an_oracle() -> None:
    result = _result()
    graph = Mock()
    graph.invoke.return_value = {
        "final_result": result,
        "retrieved_clauses": (),
        "investigation_ledger": _ledger(),
        "requested_evidence_needs": (),
        "termination_reason": "decision_complete",
    }

    with (
        patch(
            "policy_coherence_investigator.interfaces.investigate.build_chat_model"
        ) as model_factory,
        patch(
            "policy_coherence_investigator.interfaces.investigate.build_bounded_investigation_graph",
            return_value=graph,
        ),
    ):
        report = run_investigation(
            question=" Do contractor offboarding policies conflict? ",
            corpus_directory=CORPUS_DIRECTORY,
            as_of_date=date(2026, 8, 16),
            geography="global",
            populations=("contractor",),
            access_types=("ordinary",),
            provider="openai",
        )

    assert report.result == result
    assert report.question == "Do contractor offboarding policies conflict?"
    model_factory.assert_called_once_with("openai")
    initial_state = graph.invoke.call_args.args[0]
    assert initial_state["question"] == "Do contractor offboarding policies conflict?"
    assert initial_state["working_scope"].populations == ["contractor"]
    assert initial_state["working_scope"].access_types == ["ordinary"]
    assert report.retrieval_count == 1
    assert report.ledger == _ledger()


def test_json_report_contains_the_structured_result_and_concise_metadata(capsys) -> None:
    corpus = load_policy_corpus(CORPUS_DIRECTORY)
    clause = corpus.clauses[0]
    report = InvestigationRunReport(
        question="Do contractor offboarding policies conflict?",
        corpus_id=corpus.corpus_id,
        result=_result(),
        retrieved_clauses=(clause,),
        retrieval_count=1,
        retrieval_budget=3,
        requested_evidence_needs=(),
        termination_reason="decision_complete",
    )

    print_investigation_report(report, "json")

    output = capsys.readouterr().out
    assert '"category": "confirmed_conflict"' in output
    assert '"retrieval_count": 1' in output
    assert f'"document_id": "{clause.document.document_id}"' in output
    assert "oracle" not in output


def _result() -> InvestigationResult:
    return InvestigationResult(
        category=FindingCategory.CONFIRMED_CONFLICT,
        summary="The current contractor access deadlines conflict.",
        findings=[
            CoherenceFinding(
                finding_id="incompatible_contractor_revocation_deadlines",
                conclusion="A contractor may retain access beyond the mandatory deadline.",
                citations=[
                    EvidenceReference(
                        document_id="access_control_policy_v4",
                        clause_id="ACP-4.2.1",
                    )
                ],
            )
        ],
    )


def _ledger() -> InvestigationLedger:
    return InvestigationLedger(
        question="Do contractor offboarding policies conflict?",
        working_scope=WorkingScope(
            topic="Do contractor offboarding policies conflict?",
            populations=["contractor"],
            access_types=["ordinary"],
            geography="global",
            as_of_date=date(2026, 8, 16),
        ),
        retrieval_history=[
            RetrievalRecord(
                iteration=1,
                query="contractor offboarding policies",
                rationale="Initial retrieval.",
            )
        ],
        remaining_retrieval_budget=2,
    )
