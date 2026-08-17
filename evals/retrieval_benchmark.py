"""Deterministic retrieval-only measurement for controlled policy corpora."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from policy_coherence_investigator.investigation import EvidenceReference
from policy_coherence_investigator.retrieval import (
    PolicyCorpus,
    filter_applicable_clauses,
    load_policy_corpus,
    rank_clauses,
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


def evaluate_lexical_benchmark(
    benchmark: RetrievalBenchmark,
    corpus: PolicyCorpus,
) -> tuple[RetrievalScenarioScore, ...]:
    """Measure the deterministic lexical baseline without involving a model provider."""

    if benchmark.corpus_id != corpus.corpus_id:
        raise ValueError("benchmark corpus_id must match the loaded corpus")

    scores: list[RetrievalScenarioScore] = []
    for scenario in benchmark.scenarios:
        applicable_clauses = filter_applicable_clauses(
            corpus,
            as_of_date=scenario.as_of_date,
            geography=scenario.geography,
        )
        all_ranked = rank_clauses(
            scenario.question,
            applicable_clauses,
            limit=len(applicable_clauses),
        )
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
            )
        )
    return tuple(scores)


def load_default_lexical_scores() -> tuple[RetrievalScenarioScore, ...]:
    """Load the tracked large corpus and measure the current lexical baseline."""

    benchmark = load_retrieval_benchmark()
    corpus = load_policy_corpus(REPOSITORY_ROOT / "evals" / "corpora" / benchmark.corpus_id)
    return evaluate_lexical_benchmark(benchmark, corpus)
