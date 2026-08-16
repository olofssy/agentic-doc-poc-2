"""Deterministic applicability filters for policy clauses."""

from datetime import date

from .corpus import PolicyClause, PolicyCorpus


def filter_applicable_clauses(
    corpus: PolicyCorpus,
    *,
    as_of_date: date,
    geography: str,
) -> tuple[PolicyClause, ...]:
    """Return clauses from current, effective documents applicable in one geography."""

    normalized_geography = geography.strip().lower()
    if not normalized_geography:
        raise ValueError("geography must not be blank")

    return tuple(
        clause
        for clause in corpus.clauses
        if clause.document.status == "current"
        and clause.document.effective_from <= as_of_date
        and _applies_in_geography(clause, normalized_geography)
    )


def _applies_in_geography(clause: PolicyClause, geography: str) -> bool:
    document_geographies = {value.lower() for value in clause.document.geography}
    return "global" in document_geographies or geography in document_geographies
