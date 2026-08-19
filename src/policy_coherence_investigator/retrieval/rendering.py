"""Stable text rendering for clause embeddings and retrieval diagnostics."""

from .corpus import PolicyClause


def render_clause_for_retrieval(clause: PolicyClause) -> str:
    """Render the validated, provenance-bearing text indexed for one clause."""

    return "\n".join(
        (clause.document.title, clause.document.document_type, clause.heading, clause.content)
    )
