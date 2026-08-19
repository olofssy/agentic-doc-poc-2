"""Print a compact, provider-free lexical and vector retrieval comparison."""

from __future__ import annotations

import argparse

from policy_coherence_investigator.retrieval import OpenAIEmbeddingClient, load_policy_corpus

from .retrieval_benchmark import (
    DEFAULT_BENCHMARK_PATH,
    REPOSITORY_ROOT,
    RetrievalBenchmarkRun,
    evaluate_lexical_benchmark,
    evaluate_vector_benchmark,
    load_default_benchmark_comparison,
    load_retrieval_benchmark,
)


def main(argv: list[str] | None = None) -> int:
    """Run the local benchmark; paid embeddings require two explicit flags."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding-provider", choices=("deterministic", "openai"))
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    parser.add_argument("--allow-paid-embeddings", action="store_true")
    args = parser.parse_args(argv)

    if args.embedding_provider == "openai":
        if not args.allow_paid_embeddings:
            parser.error("--embedding-provider openai requires --allow-paid-embeddings")
        _print_paid_comparison(args.embedding_model)
        return 0

    for run in load_default_benchmark_comparison():
        _print_run(run)
    return 0


def _print_paid_comparison(model_id: str) -> None:
    benchmark = load_retrieval_benchmark(DEFAULT_BENCHMARK_PATH)
    corpus = load_policy_corpus(REPOSITORY_ROOT / "evals" / "corpora" / benchmark.corpus_id)
    lexical = RetrievalBenchmarkRun(
        retriever_name="lexical",
        embedding_model_id=None,
        index_build_ms=None,
        estimated_embedding_cost=None,
        estimated_query_cost=None,
        scores=evaluate_lexical_benchmark(benchmark, corpus),
    )
    vector = evaluate_vector_benchmark(
        benchmark,
        corpus,
        embedding_client=OpenAIEmbeddingClient(model_id=model_id),
    )
    for run in (lexical, vector):
        _print_run(run)


def _print_run(run: RetrievalBenchmarkRun) -> None:
    details = [f"retriever={run.retriever_name}"]
    if run.embedding_model_id is not None:
        details.append(f"embedding_model={run.embedding_model_id}")
    if run.index_build_ms is not None:
        details.append(f"index_build_ms={run.index_build_ms:.2f}")
    if run.estimated_embedding_cost is not None:
        details.append(f"estimated_embedding_cost={run.estimated_embedding_cost:.6f}")
    if run.estimated_query_cost is not None:
        details.append(f"estimated_query_cost={run.estimated_query_cost:.6f}")
    print(" | ".join(details))
    for score in run.scores:
        retrieved_count = sum(
            rank is not None and rank <= score.top_k for rank in score.ranks.values()
        )
        print(
            f"  {score.scenario_id}: recall={retrieved_count}/{len(score.required_references)} "
            f"at@{score.top_k} query_ms={score.query_latency_ms:.2f}"
        )
        retrieved_ids = ", ".join(
            f"{reference.document_id}/{reference.clause_id}"
            for reference in score.retrieved_references
        )
        print(f"    retrieved: {retrieved_ids or 'none'}")
        for reference in score.required_references:
            rank = score.ranks[(reference.document_id, reference.clause_id)]
            print(f"    {reference.document_id}/{reference.clause_id}: rank={rank or 'not-ranked'}")


if __name__ == "__main__":
    raise SystemExit(main())
