"""Load evaluation fixtures without leaking hidden oracle data into agent inputs."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from policy_coherence_investigator.investigation.models import EvidenceReference, FindingCategory
from policy_coherence_investigator.retrieval.corpus import (
    CorpusManifest,
    load_corpus_manifest,
    load_policy_corpus,
)

CASE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class CaseDataError(ValueError):
    """Raised when evaluation fixture data is malformed or escapes its boundary."""


class StrictFixtureModel(BaseModel):
    """Reject fields that do not belong to a declared fixture contract."""

    model_config = ConfigDict(extra="forbid")


class ReviewContext(StrictFixtureModel):
    as_of_date: date
    geography: str = Field(min_length=1)
    populations: list[str] = Field(min_length=1)
    access_types: list[str] = Field(min_length=1)

    @field_validator("geography")
    @classmethod
    def strip_geography(cls, value: str) -> str:
        return value.strip()

    @field_validator("populations", "access_types")
    @classmethod
    def normalize_scope_values(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("review-context scope values must be unique")
        if not normalized:
            raise ValueError("review-context scope values must not be blank")
        return normalized


class CaseManifest(StrictFixtureModel):
    case_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    corpus_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    question: str = Field(min_length=1)
    review_context: ReviewContext
    retrieval_budget: int = Field(ge=1, le=3)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return value.strip()


class CaseInput(StrictFixtureModel):
    """Only data a future investigator is allowed to receive for a case."""

    case: CaseManifest
    corpus: CorpusManifest

    @model_validator(mode="after")
    def corpus_matches_case(self) -> CaseInput:
        if self.case.corpus_id != self.corpus.corpus_id:
            raise ValueError("case and corpus IDs must match")
        return self


class CaseOracle(StrictFixtureModel):
    """Evaluator-only expectations. Never pass this model to an investigator."""

    case_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    acceptable_result_categories: list[FindingCategory] = Field(min_length=1)
    decisive_clause_sets: list[list[EvidenceReference]] = Field(min_length=1)
    required_findings: list[str] = Field(default_factory=list)
    forbidden_findings: list[str] = Field(default_factory=list)
    required_scope_distinctions: list[str] = Field(default_factory=list)
    acceptable_follow_up_needs: list[str] = Field(default_factory=list)


def discover_case_ids(repository_root: Path = REPOSITORY_ROOT) -> list[str]:
    """Return neutral case IDs without reading case content or hidden oracles."""

    cases_directory = repository_root / "evals" / "cases"
    if not cases_directory.is_dir():
        raise CaseDataError(f"evaluation cases directory is missing: {cases_directory}")
    case_ids = sorted(
        path.name
        for path in cases_directory.iterdir()
        if path.is_dir() and CASE_ID_PATTERN.fullmatch(path.name) and (path / "case.yaml").is_file()
    )
    if not case_ids:
        raise CaseDataError(f"no evaluation cases with case.yaml were found: {cases_directory}")
    return case_ids


def load_case(case_id: str, repository_root: Path = REPOSITORY_ROOT) -> CaseInput:
    """Load agent-visible case and corpus data, never the hidden oracle."""

    case_directory = _case_directory(case_id, repository_root)
    case = _load_yaml_model(case_directory / "case.yaml", CaseManifest)
    corpus_directory = _safe_child(repository_root / "evals" / "corpora", case.corpus_id)
    corpus = load_corpus_manifest(corpus_directory)
    return CaseInput(case=case, corpus=corpus)


def load_oracle(case_id: str, repository_root: Path = REPOSITORY_ROOT) -> CaseOracle:
    """Load evaluator-only expected outcomes through an explicit call."""

    case_directory = _case_directory(case_id, repository_root)
    oracle = _load_yaml_model(case_directory / "oracle.yaml", CaseOracle)
    if oracle.case_id != case_id:
        raise CaseDataError("oracle case_id must match its directory name")
    loaded_case = load_case(case_id, repository_root)
    known_document_ids = {document.document_id for document in loaded_case.corpus.documents}
    referenced_document_ids = {
        reference.document_id
        for clause_set in oracle.decisive_clause_sets
        for reference in clause_set
    }
    unknown_document_ids = referenced_document_ids - known_document_ids
    if unknown_document_ids:
        raise CaseDataError(
            "oracle references document IDs absent from the corpus: "
            f"{sorted(unknown_document_ids)}"
        )
    corpus_directory = _safe_child(
        repository_root / "evals" / "corpora", loaded_case.case.corpus_id
    )
    known_clause_references = {
        (clause.document.document_id, clause.clause_id)
        for clause in load_policy_corpus(corpus_directory).clauses
    }
    unknown_clause_references = {
        (reference.document_id, reference.clause_id)
        for clause_set in oracle.decisive_clause_sets
        for reference in clause_set
        if (reference.document_id, reference.clause_id) not in known_clause_references
    }
    if unknown_clause_references:
        raise CaseDataError(
            "oracle references clauses absent from the corpus: "
            f"{sorted(unknown_clause_references)}"
        )
    return oracle


def _case_directory(case_id: str, repository_root: Path) -> Path:
    if not CASE_ID_PATTERN.fullmatch(case_id):
        raise CaseDataError("case ID is invalid")
    return _safe_child(repository_root / "evals" / "cases", case_id)


def _safe_child(parent: Path, relative_path: str) -> Path:
    resolved_parent = parent.resolve()
    resolved_path = (parent / relative_path).resolve()
    if not resolved_path.is_relative_to(resolved_parent):
        raise CaseDataError("fixture path escapes its permitted directory")
    return resolved_path


def _load_yaml_model(path: Path, model_type: type[BaseModel]) -> Any:
    if not path.is_file():
        raise CaseDataError(f"required fixture file is missing: {path.name}")
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(content, dict):
            raise CaseDataError(f"fixture file must contain a mapping: {path.name}")
        return model_type.model_validate(content)
    except (OSError, yaml.YAMLError, ValueError) as error:
        if isinstance(error, CaseDataError):
            raise
        raise CaseDataError(f"invalid fixture file {path.name}: {error}") from error
