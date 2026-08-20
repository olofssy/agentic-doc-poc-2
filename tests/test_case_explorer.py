from pathlib import Path

from policy_coherence_investigator.interfaces.case_explorer import (
    DEFAULT_PRESENTATION_CATALOG,
    load_explorer_cases,
    load_presentation_catalog,
    render_explorer_page,
)

PRESENTATION_CATALOG = Path("evals/presentation/cases.yaml")


def test_presentation_catalog_describes_every_discoverable_case() -> None:
    catalog = load_presentation_catalog(PRESENTATION_CATALOG)

    assert {case.case_id for case in catalog.cases} == {
        "access-offboarding-a",
        "access-offboarding-b",
        "access-offboarding-c",
        "access-offboarding-d",
    }
    assert all(case.capability_tags for case in catalog.cases)
    assert all(case.resolution_guide for case in catalog.cases)


def test_default_catalog_path_resolves_the_shipped_presentation_material() -> None:
    assert DEFAULT_PRESENTATION_CATALOG == PRESENTATION_CATALOG.resolve()


def test_explorer_loads_oracle_data_only_for_human_demo_notes() -> None:
    explorer_case = next(
        case
        for case in load_explorer_cases()
        if case.presentation.case_id == "access-offboarding-a"
    )

    assert explorer_case.oracle.acceptable_result_categories[0] == "confirmed_conflict"
    assert explorer_case.oracle.decisive_clause_sets[0][0].clause_id == "ACP-4.2.1"


def test_explorer_renders_oracle_notes_and_keeps_policy_documents_collapsed() -> None:
    page = render_explorer_page(load_explorer_cases(), "access-offboarding-a")

    assert "Demo evaluation notes" in page
    assert "Decisive evidence" in page
    assert "Scope resolver" in page
    assert "Excluded by status" in page
    assert "Outside review geography" in page
    assert "Retrieval target: policy rule" in page
    assert "Retrieval target: term definition" in page
    assert '<details class="policy-document">' in page
    assert '<details class="policy-document" open>' not in page
    assert "oracle.yaml" not in page


def test_retrieval_role_is_visible_in_a_collapsed_document_header() -> None:
    page = render_explorer_page(load_explorer_cases(), "access-offboarding-a")

    header_start = page.index("Access Control Policy")
    role_start = page.index("Retrieval target: policy rule", header_start)
    document_body_start = page.index('<div class="document-body">', header_start)

    assert header_start < role_start < document_body_start


def test_explorer_renders_the_human_resolution_guide_without_opening_documents() -> None:
    page = render_explorer_page(load_explorer_cases(), "access-offboarding-c")

    assert "Human resolution guide" in page
    assert "not that no contractor policy exists" in page
    assert page.index("Human resolution guide") < page.index("Policy corpus")
