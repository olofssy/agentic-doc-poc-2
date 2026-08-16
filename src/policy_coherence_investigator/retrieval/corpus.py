"""Validated loading and clause parsing for tracked policy corpora."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CLAUSE_HEADING_PATTERN = re.compile(
    r"^##\s+(?P<clause_id>[A-Z][A-Z0-9]*-\d+(?:\.\d+)*)\s+—\s+(?P<heading>.+?)\s*$",
    re.MULTILINE,
)


class CorpusLoadError(ValueError):
    """Raised when a policy corpus is malformed, missing, or unsafe to load."""


class StrictCorpusModel(BaseModel):
    """Reject undeclared metadata fields in a tracked corpus manifest."""

    model_config = ConfigDict(extra="forbid")


class PolicyDocument(StrictCorpusModel):
    """Metadata for one policy source available to deterministic retrieval."""

    document_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    document_type: str = Field(min_length=1)
    title: str = Field(min_length=1)
    path: str = Field(min_length=1)
    effective_from: date
    status: str = Field(pattern=r"^(current|superseded)$")
    authority_level: str = Field(min_length=1)
    geography: list[str] = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def path_is_relative(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("document path must stay within its corpus")
        return value


class CorpusManifest(StrictCorpusModel):
    """The tracked metadata manifest for one controlled policy corpus."""

    corpus_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    documents: list[PolicyDocument] = Field(min_length=1)

    @model_validator(mode="after")
    def document_ids_are_unique(self) -> Self:
        document_ids = [document.document_id for document in self.documents]
        if len(set(document_ids)) != len(document_ids):
            raise ValueError("document IDs must be unique")
        return self


@dataclass(frozen=True)
class PolicyClause:
    """One stable, metadata-bearing clause available for retrieval and citation."""

    document: PolicyDocument
    clause_id: str
    heading: str
    content: str

    @property
    def searchable_text(self) -> str:
        return "\n".join(
            (self.document.title, self.document.document_type, self.heading, self.content)
        )


@dataclass(frozen=True)
class LoadedPolicyDocument:
    """A validated policy source and its parsed clauses."""

    manifest: PolicyDocument
    source_path: Path
    content: str
    clauses: tuple[PolicyClause, ...]


@dataclass(frozen=True)
class PolicyCorpus:
    """A fully loaded, clause-addressable policy corpus."""

    corpus_id: str
    root: Path
    documents: tuple[LoadedPolicyDocument, ...]

    @property
    def clauses(self) -> tuple[PolicyClause, ...]:
        return tuple(clause for document in self.documents for clause in document.clauses)


def load_corpus_manifest(corpus_directory: Path) -> CorpusManifest:
    """Load metadata and validate every document path without reading policy content."""

    root = corpus_directory.resolve()
    if not root.is_dir():
        raise CorpusLoadError(f"policy corpus directory does not exist: {root}")

    manifest_path = root / "corpus.yaml"
    if not manifest_path.is_file():
        raise CorpusLoadError(f"policy corpus manifest does not exist: {manifest_path}")

    try:
        manifest = CorpusManifest.model_validate(_load_yaml(manifest_path))
    except (TypeError, ValueError) as error:
        raise CorpusLoadError(f"invalid policy corpus manifest: {manifest_path}") from error

    for document in manifest.documents:
        _document_path(root, document)
    return manifest


def load_policy_corpus(corpus_directory: Path) -> PolicyCorpus:
    """Load policy content and parse every stable clause heading in the corpus."""

    root = corpus_directory.resolve()
    manifest = load_corpus_manifest(root)
    documents = tuple(_load_document(root, document) for document in manifest.documents)
    _validate_unique_clause_ids(documents)
    return PolicyCorpus(corpus_id=manifest.corpus_id, root=root, documents=documents)


def _load_document(root: Path, manifest: PolicyDocument) -> LoadedPolicyDocument:
    source_path = _document_path(root, manifest)
    content = source_path.read_text(encoding="utf-8")
    clauses = _parse_clauses(content, manifest, source_path)
    return LoadedPolicyDocument(
        manifest=manifest,
        source_path=source_path,
        content=content,
        clauses=clauses,
    )


def _document_path(root: Path, document: PolicyDocument) -> Path:
    source_path = (root / document.path).resolve()
    if not source_path.is_relative_to(root):
        raise CorpusLoadError(f"document path leaves corpus: {document.path!r}")
    if not source_path.is_file():
        raise CorpusLoadError(f"policy document does not exist: {document.path!r}")
    return source_path


def _parse_clauses(
    content: str,
    document: PolicyDocument,
    source_path: Path,
) -> tuple[PolicyClause, ...]:
    matches = tuple(CLAUSE_HEADING_PATTERN.finditer(content))
    if not matches:
        raise CorpusLoadError(f"policy document contains no stable clause headings: {source_path}")

    clauses: list[PolicyClause] = []
    for index, match in enumerate(matches):
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        clause_content = content[content_start:content_end].strip()
        if not clause_content:
            raise CorpusLoadError(
                f"policy clause has no content: {document.document_id}/{match['clause_id']}"
            )
        clauses.append(
            PolicyClause(
                document=document,
                clause_id=match["clause_id"],
                heading=match["heading"].strip(),
                content=clause_content,
            )
        )
    return tuple(clauses)


def _validate_unique_clause_ids(documents: tuple[LoadedPolicyDocument, ...]) -> None:
    clause_ids = [clause.clause_id for document in documents for clause in document.clauses]
    if len(set(clause_ids)) != len(clause_ids):
        raise CorpusLoadError("clause IDs must be unique within a corpus")


def _load_yaml(path: Path) -> object:
    try:
        with path.open(encoding="utf-8") as source:
            return yaml.safe_load(source)
    except (OSError, yaml.YAMLError) as error:
        raise CorpusLoadError(f"unable to load policy corpus manifest: {path}") from error
