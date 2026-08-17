from pathlib import Path

import pytest
from pydantic import ValidationError

from policy_coherence_investigator.case_data import loader
from policy_coherence_investigator.case_data.loader import (
    CaseDataError,
    CaseManifest,
    discover_case_ids,
    load_case,
    load_oracle,
)
from policy_coherence_investigator.retrieval import PolicyDocument


def test_discovers_three_neutral_case_ids() -> None:
    assert discover_case_ids() == [
        "access-offboarding-a",
        "access-offboarding-b",
        "access-offboarding-c",
    ]


def test_case_manifest_rejects_human_or_oracle_fields() -> None:
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CaseManifest.model_validate(
            {
                "case_id": "access-offboarding-z",
                "corpus_id": "access-offboarding-z",
                "question": "Are the policies coherent?",
                "review_context": {
                    "as_of_date": "2026-08-16",
                    "geography": "global",
                    "populations": ["employee"],
                    "access_types": ["ordinary"],
                },
                "retrieval_budget": 3,
                "expected_outcome": "confirmed_conflict",
            }
        )


def test_case_discovery_rejects_an_empty_case_directory(tmp_path: Path) -> None:
    (tmp_path / "evals" / "cases").mkdir(parents=True)

    with pytest.raises(CaseDataError, match="no evaluation cases"):
        discover_case_ids(tmp_path)


@pytest.mark.parametrize("case_id", discover_case_ids())
def test_load_case_exposes_only_agent_visible_case_and_corpus_data(case_id: str) -> None:
    case_input = load_case(case_id)

    assert case_input.case.case_id == case_id
    assert case_input.case.corpus_id == case_input.corpus.corpus_id
    assert case_input.case.retrieval_budget == 3
    assert len(case_input.corpus.documents) == 10
    assert "oracle" not in case_input.model_dump()


def test_load_case_does_not_call_oracle_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_case must not load the hidden oracle")

    monkeypatch.setattr(loader, "load_oracle", fail_if_called)

    loaded_case = loader.load_case("access-offboarding-a")

    assert loaded_case.case.case_id == "access-offboarding-a"


@pytest.mark.parametrize("case_id", discover_case_ids())
def test_each_oracle_requires_an_explicit_evaluator_call(case_id: str) -> None:
    oracle = load_oracle(case_id)

    assert oracle.case_id == case_id
    assert oracle.decisive_clause_sets


def test_oracle_document_references_must_exist_in_its_corpus(tmp_path: Path) -> None:
    case_directory = tmp_path / "evals" / "cases" / "access-offboarding-z"
    corpus_directory = tmp_path / "evals" / "corpora" / "access-offboarding-z" / "policies"
    case_directory.mkdir(parents=True)
    corpus_directory.mkdir(parents=True)
    (case_directory / "case.yaml").write_text(
        """\
case_id: access-offboarding-z
corpus_id: access-offboarding-z
question: Are the policies coherent?
review_context:
  as_of_date: 2026-08-16
  geography: global
  populations: [employee]
  access_types: [ordinary]
retrieval_budget: 3
""",
        encoding="utf-8",
    )
    (case_directory / "oracle.yaml").write_text(
        """\
case_id: access-offboarding-z
acceptable_result_categories: [confirmed_conflict]
decisive_clause_sets:
  - - document_id: unknown_policy
      clause_id: UCP-1.1
""",
        encoding="utf-8",
    )
    (corpus_directory.parent / "corpus.yaml").write_text(
        """\
corpus_id: access-offboarding-z
documents:
  - document_id: access_control_policy_v4
    document_type: policy
    title: Access Control Policy
    path: policies/access-control-policy-v4.md
    effective_from: 2026-01-01
    status: current
    authority_level: corporate_policy
    geography: [global]
""",
        encoding="utf-8",
    )
    (corpus_directory / "access-control-policy-v4.md").write_text(
        "# Access Control Policy\n",
        encoding="utf-8",
    )

    with pytest.raises(CaseDataError, match="absent from the corpus"):
        load_oracle("access-offboarding-z", tmp_path)


def test_case_identifier_cannot_escape_fixture_directory() -> None:
    with pytest.raises(CaseDataError, match="case ID is invalid"):
        load_case("../access-offboarding-a")


def test_corpus_document_path_cannot_escape_its_corpus() -> None:
    with pytest.raises(ValidationError, match="document path must stay within its corpus"):
        PolicyDocument(
            document_id="access_control_policy_v4",
            document_type="policy",
            title="Access Control Policy",
            path="../oracle.yaml",
            effective_from="2026-01-01",
            status="current",
            authority_level="corporate_policy",
            geography=["global"],
        )
