from pathlib import Path

from evals.retrieval_benchmark import (
    evaluate_lexical_benchmark,
    evaluate_vector_benchmark,
    load_default_benchmark_comparison,
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


def test_provider_free_benchmark_compares_lexical_and_vector_decisive_clause_ranks() -> None:
    lexical, vector = load_default_benchmark_comparison()

    assert lexical.retriever_name == "lexical"
    assert vector.retriever_name == "vector"
    assert vector.embedding_model_id == "deterministic-hashed-token-v1"
    assert vector.index_build_ms is not None
    assert [score.scenario_id for score in lexical.scores] == [
        score.scenario_id for score in vector.scores
    ]
    assert all(score.query_latency_ms >= 0 for score in (*lexical.scores, *vector.scores))
    assert all(
        rank is not None
        for score in vector.scores
        for rank in score.ranks.values()
    )


def test_vector_benchmark_keeps_superseded_clause_out_of_retrieved_references() -> None:
    benchmark = load_retrieval_benchmark(BENCHMARK_PATH)
    corpus = load_policy_corpus(CORPUS_DIRECTORY)

    vector = evaluate_vector_benchmark(benchmark, corpus)

    assert ("enterprise_identity_policy_v6", "EIP6-3.1") not in {
        (reference.document_id, reference.clause_id)
        for score in vector.scores
        for reference in score.retrieved_references
    }
