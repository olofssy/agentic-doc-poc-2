"""Deterministic retrieval-only measurement for controlled policy corpora."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from time import perf_counter

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from policy_coherence_investigator.investigation import EvidenceReference
from policy_coherence_investigator.retrieval import (
    ClauseRetriever,
    DeterministicEmbeddingClient,
    EmbeddingClient,
    LexicalClauseRetriever,
    PolicyCorpus,
    build_vector_retriever,
    filter_applicable_clauses,
    load_policy_corpus,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_PATH = (
    REPOSITORY_ROOT / "evals" / "retrieval_benchmarks" / "access-lifecycle-large.yaml"
)


class StrictBenchmarkModel(BaseModel):
    """Reject undeclared benchmark fields so expectations remain reviewable."""

    model_config = ConfigDict(extra="forbid")


class RetrievalBenchmarkScenario(StrictBenchmarkModel):
    """One oracle-only retrieval query and its decisive clause references."""

    scenario_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    question: str = Field(min_length=1)
    as_of_date: date
    geography: str = Field(min_length=1)
    top_k: int = Field(ge=1)
    required_references: list[EvidenceReference] = Field(min_length=1)

    @field_validator("question", "geography")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class RetrievalBenchmark(StrictBenchmarkModel):
    """A benchmark corpus and its isolated retrieval expectations."""

    benchmark_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    corpus_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    scenarios: list[RetrievalBenchmarkScenario] = Field(min_length=1)


@dataclass(frozen=True)
class RetrievalScenarioScore:
    """Recall and ranks for one deterministic retrieval scenario."""

    scenario_id: str
    top_k: int
    required_references: tuple[EvidenceReference, ...]
    retrieved_references: tuple[EvidenceReference, ...]
    ranks: dict[tuple[str, str], int | None]
    query_latency_ms: float

    @property
    def recall(self) -> float:
        required = {
            (reference.document_id, reference.clause_id)
            for reference in self.required_references
        }
        retrieved = {
            (reference.document_id, reference.clause_id)
            for reference in self.retrieved_references
        }
        return len(required & retrieved) / len(required)


def load_retrieval_benchmark(path: Path = DEFAULT_BENCHMARK_PATH) -> RetrievalBenchmark:
    """Load retrieval expectations without exposing them to an investigator workflow."""

    try:
        contents = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"unable to load retrieval benchmark: {path}") from error
    return RetrievalBenchmark.model_validate(contents)


@dataclass(frozen=True)
class RetrievalBenchmarkRun:
    """Transparent benchmark result for one interchangeable clause retriever."""

    retriever_name: str
    embedding_model_id: str | None
    index_build_ms: float | None
    estimated_embedding_cost: float | None
    estimated_query_cost: float | None
    scores: tuple[RetrievalScenarioScore, ...]


def evaluate_retrieval_benchmark(
    benchmark: RetrievalBenchmark,
    corpus: PolicyCorpus,
    retriever: ClauseRetriever,
) -> tuple[RetrievalScenarioScore, ...]:
    """Measure one retriever after deterministic applicability filtering."""

    if benchmark.corpus_id != corpus.corpus_id:
        raise ValueError("benchmark corpus_id must match the loaded corpus")

    scores: list[RetrievalScenarioScore] = []
    for scenario in benchmark.scenarios:
        applicable_clauses = filter_applicable_clauses(
            corpus,
            as_of_date=scenario.as_of_date,
            geography=scenario.geography,
        )
        started = perf_counter()
        all_ranked = retriever.rank(
            scenario.question,
            applicable_clauses,
            limit=len(applicable_clauses),
        )
        query_latency_ms = (perf_counter() - started) * 1_000
        ranks = {
            (reference.document_id, reference.clause_id): next(
                (
                    index
                    for index, result in enumerate(all_ranked, start=1)
                    if (
                        result.clause.document.document_id,
                        result.clause.clause_id,
                    )
                    == (reference.document_id, reference.clause_id)
                ),
                None,
            )
            for reference in scenario.required_references
        }
        scores.append(
            RetrievalScenarioScore(
                scenario_id=scenario.scenario_id,
                top_k=scenario.top_k,
                required_references=tuple(scenario.required_references),
                retrieved_references=tuple(
                    EvidenceReference(
                        document_id=result.clause.document.document_id,
                        clause_id=result.clause.clause_id,
                    )
                    for result in all_ranked[: scenario.top_k]
                ),
                ranks=ranks,
                query_latency_ms=query_latency_ms,
            )
        )
    return tuple(scores)


def evaluate_lexical_benchmark(
    benchmark: RetrievalBenchmark,
    corpus: PolicyCorpus,
) -> tuple[RetrievalScenarioScore, ...]:
    """Measure the deterministic lexical baseline without involving a model provider."""

    return evaluate_retrieval_benchmark(benchmark, corpus, LexicalClauseRetriever())


def evaluate_vector_benchmark(
    benchmark: RetrievalBenchmark,
    corpus: PolicyCorpus,
    *,
    embedding_client: EmbeddingClient | None = None,
    cache_path: Path | None = None,
) -> RetrievalBenchmarkRun:
    """Measure the local vector baseline with an offline deterministic embedding fake."""

    if benchmark.corpus_id != corpus.corpus_id:
        raise ValueError("benchmark corpus_id must match the loaded corpus")
    client = embedding_client or DeterministicEmbeddingClient()
    retriever, build_seconds = build_vector_retriever(
        corpus.clauses,
        client,
        cache_path=cache_path,
    )
    return RetrievalBenchmarkRun(
        retriever_name="vector",
        embedding_model_id=client.model_id,
        index_build_ms=build_seconds * 1_000,
        estimated_embedding_cost=None,
        estimated_query_cost=None,
        scores=evaluate_retrieval_benchmark(benchmark, corpus, retriever),
    )


def load_default_lexical_scores() -> tuple[RetrievalScenarioScore, ...]:
    """Load the tracked large corpus and measure the current lexical baseline."""

    benchmark = load_retrieval_benchmark()
    corpus = load_policy_corpus(REPOSITORY_ROOT / "evals" / "corpora" / benchmark.corpus_id)
    return evaluate_lexical_benchmark(benchmark, corpus)


def load_default_benchmark_comparison() -> tuple[RetrievalBenchmarkRun, RetrievalBenchmarkRun]:
    """Compare lexical and provider-free vector baselines on the tracked corpus."""

    benchmark = load_retrieval_benchmark()
    corpus = load_policy_corpus(REPOSITORY_ROOT / "evals" / "corpora" / benchmark.corpus_id)
    lexical_scores = evaluate_lexical_benchmark(benchmark, corpus)
    lexical = RetrievalBenchmarkRun(
        retriever_name="lexical",
        embedding_model_id=None,
        index_build_ms=None,
        estimated_embedding_cost=None,
        estimated_query_cost=None,
        scores=lexical_scores,
    )
    vector = evaluate_vector_benchmark(benchmark, corpus)
    return lexical, vector
