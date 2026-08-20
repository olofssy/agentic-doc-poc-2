"""Print a compact, provider-free lexical and vector retrieval comparison."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass

from dotenv import load_dotenv

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

    load_dotenv()

    if args.embedding_provider == "openai":
        if not args.allow_paid_embeddings:
            parser.error("--embedding-provider openai requires --allow-paid-embeddings")
        runs = _paid_comparison_runs(args.embedding_model)
    else:
        runs = load_default_benchmark_comparison()

    summaries = [_print_run(run) for run in runs]
    _print_summary_table(summaries)
    return 0


def _paid_comparison_runs(model_id: str) -> tuple[RetrievalBenchmarkRun, RetrievalBenchmarkRun]:
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
    cache_path = (
        REPOSITORY_ROOT / "local" / "vector-cache" / f"{benchmark.benchmark_id}-{model_id}.json"
    )
    vector = evaluate_vector_benchmark(
        benchmark,
        corpus,
        embedding_client=OpenAIEmbeddingClient(model_id=model_id),
        cache_path=cache_path,
    )
    return lexical, vector


@dataclass(frozen=True)
class _RunSummary:
    """Totals for one retriever across every scenario, for the closing table."""

    retriever_name: str
    embedding_model_id: str | None
    hits: int
    required: int
    avg_query_ms: float
    index_build_ms: float | None

    @property
    def recall_percent(self) -> float:
        return (self.hits / self.required * 100) if self.required else 0.0


def _print_run(run: RetrievalBenchmarkRun) -> _RunSummary:
    header = f"=== {run.retriever_name} retriever"
    if run.embedding_model_id is not None:
        header += f" (embedding_model={run.embedding_model_id})"
    header += " ==="
    print(header)
    if run.index_build_ms is not None:
        print(f"  index build: {run.index_build_ms:.1f} ms")

    total_hits = 0
    total_required = 0
    latencies_ms: list[float] = []
    for score in run.scores:
        hits = sum(rank is not None and rank <= score.top_k for rank in score.ranks.values())
        total_hits += hits
        total_required += len(score.required_references)
        latencies_ms.append(score.query_latency_ms)
        print(
            f"  [{score.scenario_id}] recall {hits}/{len(score.required_references)}"
            f" within top-{score.top_k}  (query took {score.query_latency_ms:.1f} ms)"
        )
        for reference in score.required_references:
            rank = score.ranks[(reference.document_id, reference.clause_id)]
            label = f"{reference.document_id}/{reference.clause_id}"
            if rank is None:
                mark, status = "!", "not returned by the retriever (filtered out or scored zero)"
            elif rank <= score.top_k:
                mark, status = "y", f"found at rank {rank}"
            else:
                mark, status = "n", f"rank {rank} — outside top-{score.top_k}"
            print(f"      [{mark}] {label}: {status}")

    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
    print(
        f"  -> {total_hits}/{total_required} required references recalled, "
        f"avg query time {avg_latency:.1f} ms"
    )
    print()
    return _RunSummary(
        retriever_name=run.retriever_name,
        embedding_model_id=run.embedding_model_id,
        hits=total_hits,
        required=total_required,
        avg_query_ms=avg_latency,
        index_build_ms=run.index_build_ms,
    )


def _print_summary_table(summaries: Sequence[_RunSummary]) -> None:
    print("=== summary ===")
    name_width = max((len(summary.retriever_name) for summary in summaries), default=8)
    for summary in summaries:
        model_suffix = f" ({summary.embedding_model_id})" if summary.embedding_model_id else ""
        index_build = (
            f"{summary.index_build_ms:.1f} ms" if summary.index_build_ms is not None else "n/a"
        )
        print(
            f"  {summary.retriever_name:<{name_width}}{model_suffix}: "
            f"recall {summary.hits}/{summary.required} ({summary.recall_percent:.0f}%), "
            f"avg query {summary.avg_query_ms:.1f} ms, index build {index_build}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
