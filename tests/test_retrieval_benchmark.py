from pathlib import Path

from evals.retrieval_benchmark import (
    evaluate_lexical_benchmark,
    load_retrieval_benchmark,
)
from policy_coherence_investigator.retrieval import (
    filter_applicable_clauses,
    load_policy_corpus,
)

CORPUS_DIRECTORY = Path("evals/corpora/access-lifecycle-large")
BENCHMARK_PATH = Path("evals/retrieval_benchmarks/access-lifecycle-large.yaml")


def test_large_corpus_has_intentional_scale_and_parseable_clause_references() -> None:
    corpus = load_policy_corpus(CORPUS_DIRECTORY)

    assert len(corpus.documents) == 24
    assert len(corpus.clauses) == 96


def test_retrieval_benchmark_references_only_current_applicable_clauses() -> None:
    benchmark = load_retrieval_benchmark(BENCHMARK_PATH)
    corpus = load_policy_corpus(CORPUS_DIRECTORY)

    scores = evaluate_lexical_benchmark(benchmark, corpus)

    assert [score.scenario_id for score in scores] == [
        "agency-handover-conflict",
        "sweden-local-deadline",
        "superseded-policy-filter",
    ]
    for scenario in benchmark.scenarios:
        applicable_references = {
            (clause.document.document_id, clause.clause_id)
            for clause in filter_applicable_clauses(
                corpus,
                as_of_date=scenario.as_of_date,
                geography=scenario.geography,
            )
        }
        assert {
            (reference.document_id, reference.clause_id)
            for reference in scenario.required_references
        } <= applicable_references
    superseded_references = {
        (reference.document_id, reference.clause_id)
        for reference in scores[-1].retrieved_references
    }
    assert ("enterprise_identity_policy_v6", "EIP6-3.1") not in superseded_references
