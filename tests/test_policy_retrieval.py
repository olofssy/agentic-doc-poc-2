from datetime import date
from pathlib import Path

import pytest

from policy_coherence_investigator.retrieval import (
    CorpusLoadError,
    DeterministicEmbeddingClient,
    LocalVectorIndex,
    build_vector_retriever,
    filter_applicable_clauses,
    load_policy_corpus,
    rank_clauses,
    render_clause_for_retrieval,
    tokenize,
)

CORPUS_DIRECTORY = Path("evals/corpora/access-offboarding-a")


def test_load_policy_corpus_parses_documents_and_stable_clause_ids() -> None:
    corpus = load_policy_corpus(CORPUS_DIRECTORY)

    assert corpus.corpus_id == "access-offboarding-a"
    assert len(corpus.documents) == 10
    assert {(clause.document.document_id, clause.clause_id) for clause in corpus.clauses} >= {
        ("access_control_policy_v4", "ACP-4.2.1"),
        ("contractor_management_policy_v2", "CMP-6.4"),
        ("identity_definitions_v2", "IDD-2.1"),
    }


def test_applicability_filter_excludes_superseded_and_out_of_scope_documents() -> None:
    corpus = load_policy_corpus(CORPUS_DIRECTORY)

    global_clauses = filter_applicable_clauses(
        corpus,
        as_of_date=date(2026, 8, 16),
        geography="global",
    )

    global_references = {
        (clause.document.document_id, clause.clause_id) for clause in global_clauses
    }
    assert ("access_control_policy_v3", "ACP-3.9.1") not in global_references
    assert ("nordic_access_addendum_v1", "NAA-2.4") not in global_references
    assert ("access_control_policy_v4", "ACP-4.2.1") in global_references


def test_applicability_filter_includes_a_matching_local_addendum() -> None:
    corpus = load_policy_corpus(CORPUS_DIRECTORY)

    sweden_clauses = filter_applicable_clauses(
        corpus,
        as_of_date=date(2026, 8, 16),
        geography="sweden",
    )

    assert ("nordic_access_addendum_v1", "NAA-2.4") in {
        (clause.document.document_id, clause.clause_id) for clause in sweden_clauses
    }


def test_lexical_ranking_returns_a_decisive_contractor_clause_before_near_misses() -> None:
    corpus = load_policy_corpus(CORPUS_DIRECTORY)
    clauses = filter_applicable_clauses(
        corpus,
        as_of_date=date(2026, 8, 16),
        geography="global",
    )

    results = rank_clauses(
        "contractor corporate-system access five calendar days after termination",
        clauses,
        limit=3,
    )

    assert results[0].clause.document.document_id == "contractor_management_policy_v2"
    assert results[0].clause.clause_id == "CMP-6.4"
    assert {result.clause.clause_id for result in results}.isdisjoint({"FAP-6.1", "RWP-5.2"})


def test_lexical_ranking_is_stable_and_returns_nothing_without_matching_terms() -> None:
    corpus = load_policy_corpus(CORPUS_DIRECTORY)
    clauses = filter_applicable_clauses(
        corpus,
        as_of_date=date(2026, 8, 16),
        geography="global",
    )

    first = rank_clauses("privileged access termination", clauses, limit=3)
    second = rank_clauses("privileged access termination", clauses, limit=3)

    assert first == second
    assert rank_clauses("turbine gearbox vibration", clauses) == ()


def test_tokenize_normalizes_case_and_clause_identifier_punctuation() -> None:
    assert tokenize("ACP-4.2.1 / CMP-6.4") == ("acp", "4", "2", "1", "cmp", "6", "4")


def test_vector_retriever_ranks_only_pre_filtered_clauses_with_stable_provenance() -> None:
    corpus = load_policy_corpus(CORPUS_DIRECTORY)
    retriever, _ = build_vector_retriever(corpus.clauses, DeterministicEmbeddingClient())
    applicable = filter_applicable_clauses(
        corpus,
        as_of_date=date(2026, 8, 16),
        geography="global",
    )

    results = retriever.rank(
        "contractor corporate-system access five calendar days after termination",
        applicable,
        limit=len(applicable),
    )

    eligible_references = {
        (clause.document.document_id, clause.clause_id) for clause in applicable
    }
    assert results
    assert {
        (result.clause.document.document_id, result.clause.clause_id) for result in results
    } <= eligible_references
    assert ("access_control_policy_v3", "ACP-3.9.1") not in {
        (result.clause.document.document_id, result.clause.clause_id) for result in results
    }


def test_vector_index_cache_reuses_matching_content_and_rebuilds_after_a_change(
    tmp_path: Path,
) -> None:
    corpus = load_policy_corpus(CORPUS_DIRECTORY)
    client = DeterministicEmbeddingClient()
    cache_path = tmp_path / "vectors.json"

    first = LocalVectorIndex.load_or_build(corpus.clauses, client, cache_path=cache_path)
    second = LocalVectorIndex.load_or_build(corpus.clauses, client, cache_path=cache_path)
    changed_clauses = (*corpus.clauses[:-1],)
    rebuilt = LocalVectorIndex.load_or_build(changed_clauses, client, cache_path=cache_path)

    assert cache_path.is_file()
    assert second == first
    assert len(rebuilt.records) == len(corpus.clauses) - 1
    assert first.records[0].rendered_text == render_clause_for_retrieval(corpus.clauses[0])
    assert first.records[0].embedding_model_id == client.model_id


def test_corpus_loader_rejects_policy_content_without_a_stable_clause_heading(
    tmp_path: Path,
) -> None:
    (tmp_path / "policies").mkdir()
    (tmp_path / "corpus.yaml").write_text(
        """\
corpus_id: malformed-corpus
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
    (tmp_path / "policies" / "access-control-policy-v4.md").write_text(
        "# Access Control Policy\n\nNo clause locator is present.\n",
        encoding="utf-8",
    )

    with pytest.raises(CorpusLoadError, match="no stable clause headings"):
        load_policy_corpus(tmp_path)
