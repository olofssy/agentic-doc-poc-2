"""Read-only local explorer for human demonstrations of evaluation cases.

The explorer intentionally loads the hidden oracle so a demo audience can see
why a case is interesting.  This module is not imported by prompts, workflows,
or evaluation runners; oracle material must never reach the investigator under
test.
"""

from __future__ import annotations

import argparse
import html
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from policy_coherence_investigator.case_data.loader import (
    CaseInput,
    CaseOracle,
    discover_case_ids,
    load_case,
    load_oracle,
)
from policy_coherence_investigator.investigation.models import EvidenceReference
from policy_coherence_investigator.retrieval import PolicyClause, PolicyCorpus, load_policy_corpus
from policy_coherence_investigator.retrieval.corpus import LoadedPolicyDocument

from .sv_labels import humanize_sv

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PRESENTATION_CATALOG = REPOSITORY_ROOT / "evals" / "presentation" / "cases.yaml"


class StrictPresentationModel(BaseModel):
    """Reject undeclared presentation fields to keep demo material reviewable."""

    model_config = ConfigDict(extra="forbid")


class PresentationClauseRole(StrictPresentationModel):
    """Human explanation of why a clause matters in a demonstration."""

    reference: EvidenceReference
    label: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    @field_validator("label", "explanation")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class DocumentRoleKind(StrEnum):
    """Human-facing roles that explain why a document is worth retrieving."""

    POLICY_RULE = "policy_rule"
    TERM_DEFINITION = "term_definition"
    LOCAL_EXCEPTION = "local_exception"
    GOVERNANCE_PRECEDENCE = "governance_precedence"
    CONTEXT_ONLY = "context_only"


class PresentationDocumentRole(StrictPresentationModel):
    """Human explanation of a document's expected role in the investigation."""

    document_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    kind: DocumentRoleKind
    explanation: str = Field(min_length=1)

    @field_validator("explanation")
    @classmethod
    def strip_explanation(cls, value: str) -> str:
        return value.strip()


class PresentationCase(StrictPresentationModel):
    """Human-only descriptive material for one neutral evaluation case."""

    case_id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    display_name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    capability_tags: list[str] = Field(min_length=1)
    resolution_guide: str = Field(min_length=1)
    document_roles: list[PresentationDocumentRole] = Field(default_factory=list)
    clause_roles: list[PresentationClauseRole] = Field(default_factory=list)

    @field_validator("display_name", "summary", "resolution_guide")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def clause_roles_are_unique(self) -> PresentationCase:
        references = [
            (role.reference.document_id, role.reference.clause_id) for role in self.clause_roles
        ]
        if len(references) != len(set(references)):
            raise ValueError("presentation clause roles must not repeat a clause")
        return self

    @model_validator(mode="after")
    def document_roles_are_unique(self) -> PresentationCase:
        document_ids = [role.document_id for role in self.document_roles]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("presentation document roles must not repeat a document")
        return self


class PresentationCatalog(StrictPresentationModel):
    """The complete human-facing case-explorer catalog."""

    cases: list[PresentationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def case_ids_are_unique(self) -> PresentationCatalog:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("presentation catalog case IDs must be unique")
        return self


@dataclass(frozen=True)
class ExplorerCase:
    """All human-readable material for one case, including its evaluation oracle."""

    presentation: PresentationCase
    case_input: CaseInput
    corpus: PolicyCorpus
    oracle: CaseOracle


def load_presentation_catalog(
    path: Path = DEFAULT_PRESENTATION_CATALOG,
) -> PresentationCatalog:
    """Load the human-only case descriptions."""

    if not path.is_file():
        raise ValueError(f"presentation catalog does not exist: {path}")
    try:
        return PresentationCatalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (OSError, yaml.YAMLError, ValueError) as error:
        raise ValueError(f"invalid presentation catalog: {path}") from error


def load_explorer_cases(
    repository_root: Path = REPOSITORY_ROOT,
    catalog_path: Path = DEFAULT_PRESENTATION_CATALOG,
) -> tuple[ExplorerCase, ...]:
    """Join presentation, corpus, and oracle material for the human-only explorer."""

    root = repository_root.resolve()
    catalog = load_presentation_catalog(catalog_path)
    discovered_case_ids = set(discover_case_ids(root))
    catalog_case_ids = {case.case_id for case in catalog.cases}
    if catalog_case_ids != discovered_case_ids:
        missing = sorted(discovered_case_ids - catalog_case_ids)
        unknown = sorted(catalog_case_ids - discovered_case_ids)
        raise ValueError(
            "presentation catalog and discoverable cases differ; "
            f"missing={missing}, unknown={unknown}"
        )

    explorer_cases: list[ExplorerCase] = []
    for presentation in catalog.cases:
        case_input = load_case(presentation.case_id, root)
        corpus_directory = root / "evals" / "corpora" / case_input.case.corpus_id
        corpus = load_policy_corpus(corpus_directory)
        explorer_case = ExplorerCase(
            presentation=presentation,
            case_input=case_input,
            corpus=corpus,
            oracle=load_oracle(presentation.case_id, root),
        )
        _validate_presentation_roles(explorer_case)
        explorer_cases.append(explorer_case)
    return tuple(explorer_cases)


def render_explorer_page(
    cases: tuple[ExplorerCase, ...], selected_case_id: str | None,
) -> str:
    """Render a self-contained, read-only page with collapsed policy documents."""

    selected_case = next(
        (case for case in cases if case.presentation.case_id == selected_case_id), cases[0]
    )
    sidebar = "".join(render_case_link(case, case is selected_case) for case in cases)
    return f"""<!doctype html>
<html lang="sv">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Fallutforskare för policykoherens</title>
  <style>
    :root {{ color-scheme: light; font-family: ui-sans-serif, system-ui, sans-serif;
      color: #18202a; background: #f7f8fa; }}
    body {{ margin: 0; }}
    main {{ display: grid; grid-template-columns: minmax(250px, 320px) 1fr; min-height: 100vh; }}
    nav {{ padding: 28px 18px; background: #172b3a; color: #eff6f8; }}
    nav h1 {{ margin: 0 0 8px; font-size: 1.25rem; }}
    nav p {{ color: #c8d7dd; font-size: .9rem; line-height: 1.5; }}
    .case-link {{ display: block; margin: 8px 0; padding: 12px; border-radius: 8px;
      color: inherit; text-decoration: none; }}
    .case-link:hover, .case-link.current {{ background: #284b61; }}
    .case-link span, .case-link small {{ display: block; }}
    .case-link small {{ margin-top: 4px; color: #c8d7dd; }}
    article {{ max-width: 980px; padding: 40px clamp(24px, 5vw, 72px); }}
    h2 {{ margin: 0; font-size: clamp(1.8rem, 4vw, 2.7rem); line-height: 1.12; }}
    h3 {{ margin-top: 38px; }}
    h4 {{ margin: 18px 0 7px; }}
    .eyebrow {{ color: #496d81; font-size: .75rem; font-weight: 700; letter-spacing: .07em;
      text-transform: uppercase; }}
    .summary {{ font-size: 1.1rem; line-height: 1.55; }}
    .notice {{ padding: 14px 16px; border-left: 4px solid #a45e14; background: #fff5e5;
      line-height: 1.45; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 14px; }}
    .card {{ padding: 16px; border: 1px solid #d7e0e5; border-radius: 8px; background: white; }}
    .card h4 {{ margin: 0 0 8px; }}
    .card p {{ margin: 0; line-height: 1.5; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }}
    .badge {{ display: inline-block; padding: 3px 7px; border-radius: 999px; font-size: .74rem;
      font-weight: 700; letter-spacing: .02em; }}
    .badge.current {{ color: #135e3b; background: #d9f2e4; }}
    .badge.superseded, .badge.excluded {{ color: #5f4a16; background: #f6e7bd; }}
    .badge.decisive {{ color: #5c2b68; background: #f0dff4; }}
    .badge.role {{ color: #174b68; background: #dcecf5; }}
    .badge.retrieval {{ color: #704000; background: #ffe1a8; margin-left: 8px; }}
    .badge.meta {{ color: #47515a; background: #e5e9ec; }}
    details {{ margin: 12px 0; border: 1px solid #d7e0e5; border-radius: 8px; background: white;
      overflow: hidden; }}
    summary {{ cursor: pointer; padding: 14px 16px; font-weight: 700; }}
    .document-body {{ padding: 0 16px 16px; border-top: 1px solid #d7e0e5; }}
    .clause {{ padding: 12px 0; border-top: 1px solid #e6ecef; }}
    .clause:first-child {{ border-top: 0; }}
    .clause p {{ margin: 7px 0 0; white-space: pre-wrap; line-height: 1.5; }}
    ul {{ margin: 8px 0; padding-left: 20px; }}
    li {{ margin: 5px 0; }}
    @media (max-width: 760px) {{ main {{ grid-template-columns: 1fr; }} nav {{ padding: 20px; }}
      article {{ padding: 28px 20px; }} }}
  </style>
</head>
<body>
  <main>
    <nav>
      <h1>Fallutforskare</h1>
      <p>Skrivskyddade syntetiska policykoherensfall för en mänsklig demopublik.</p>
      {sidebar}
    </nav>
    <article>{render_case_details(selected_case)}</article>
  </main>
</body>
</html>"""


def make_request_handler(cases: tuple[ExplorerCase, ...]) -> type[BaseHTTPRequestHandler]:
    """Create a request handler closed over the already-loaded demo case data."""

    class ExplorerRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            selected_case_id = parse_qs(parsed.query).get("case", [None])[0]
            known_case_ids = {case.presentation.case_id for case in cases}
            if selected_case_id is not None and selected_case_id not in known_case_ids:
                self.send_error(HTTPStatus.NOT_FOUND, "Okänt fall")
                return
            page = render_explorer_page(cases, selected_case_id).encode()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, format: str, *args: object) -> None:
            """Keep the local demo server quiet after startup."""

    return ExplorerRequestHandler


def main() -> None:
    """Serve the human-only explorer locally without model calls or evaluation runs."""

    parser = argparse.ArgumentParser(description="Bläddra bland syntetiska policyutvärderingsfall.")
    parser.add_argument("--host", default="127.0.0.1", help="Värdgränssnitt att lyssna på.")
    parser.add_argument("--port", type=int, default=8766, help="TCP-port att lyssna på.")
    args = parser.parse_args()

    cases = load_explorer_cases()
    server = ThreadingHTTPServer((args.host, args.port), make_request_handler(cases))
    print(f"Fallutforskaren körs på http://{args.host}:{args.port}")
    print("Tryck Ctrl+C för att stoppa.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nFallutforskaren stoppad.")
    finally:
        server.server_close()


def _validate_presentation_roles(explorer_case: ExplorerCase) -> None:
    known_document_ids = {
        document.manifest.document_id for document in explorer_case.corpus.documents
    }
    unknown_document_ids = {
        role.document_id
        for role in explorer_case.presentation.document_roles
        if role.document_id not in known_document_ids
    }
    if unknown_document_ids:
        raise ValueError(
            "presentation document roles reference documents absent from the corpus: "
            f"{sorted(unknown_document_ids)}"
        )

    known_references = {
        (clause.document.document_id, clause.clause_id) for clause in explorer_case.corpus.clauses
    }
    unknown_references = {
        (role.reference.document_id, role.reference.clause_id)
        for role in explorer_case.presentation.clause_roles
        if (role.reference.document_id, role.reference.clause_id) not in known_references
    }
    if unknown_references:
        raise ValueError(
            "presentation clause roles reference clauses absent from the corpus: "
            f"{sorted(unknown_references)}"
        )


def render_case_link(explorer_case: ExplorerCase, selected: bool) -> str:
    """Render one case-navigation link for a human-facing local interface."""

    presentation = explorer_case.presentation
    current = " current" if selected else ""
    case_id = html.escape(presentation.case_id, quote=True)
    return (
        f'<a class="case-link{current}" href="/?case={case_id}">'
        f"<span>{html.escape(presentation.display_name)}</span>"
        f"<small>{html.escape(presentation.case_id)}</small></a>"
    )


def render_case_details(explorer_case: ExplorerCase) -> str:
    """Render the selected case, including intentional human-only demo annotations."""

    presentation = explorer_case.presentation
    case = explorer_case.case_input.case
    tags = "".join(f"<li>{html.escape(tag)}</li>" for tag in presentation.capability_tags)
    return f"""
<p class="eyebrow">Fall-ID: {html.escape(case.case_id)}</p>
<h2>{html.escape(presentation.display_name)}</h2>
<p class="summary">{html.escape(presentation.summary)}</p>
<section class="cards">
  <div class="card"><h4>Granskningsfråga</h4><p>{html.escape(case.question)}</p></div>
  <div class="card"><h4>Granskningskontext</h4>
    <p>Per {case.review_context.as_of_date.isoformat()}<br>
    Geografi: {html.escape(case.review_context.geography)}</p></div>
  <div class="card"><h4>Hämtningsbudget</h4><p>{case.retrieval_budget} iterationer</p></div>
  <div class="card"><h4>Testade förmågor</h4><ul>{tags}</ul></div>
</section>
<h3>Mänsklig lösningsguide</h3>
<p class="summary">{html.escape(presentation.resolution_guide)}</p>
{_render_oracle_notes(explorer_case.oracle)}
<h3>Policykorpus</h3>
<p class="notice">Alla policydokument är hopfällda från start. Metadatamärken förklarar
deterministisk tillämplighet; lila märken identifierar orakelutsett avgörande underlag
för denna demo.</p>
{''.join(_render_document(document, explorer_case) for document in explorer_case.corpus.documents)}
"""


def _render_oracle_notes(oracle: CaseOracle) -> str:
    decisive_sets = "".join(
        "<li>" + ", ".join(_render_reference(reference) for reference in clause_set) + "</li>"
        for clause_set in oracle.decisive_clause_sets
    )
    return f"""
<h3>Demoanteckningar för utvärdering</h3>
<p class="notice">Dessa orakelbaserade anteckningar visas endast av denna lokala mänskliga
utforskare. De får aldrig lämnas till den utredare som testas.</p>
<section class="cards">
  <div class="card"><h4>Förväntad resultatkategori</h4>
    <p>{html.escape(_humanize(oracle.acceptable_result_categories[0]))}</p></div>
  <div class="card"><h4>Nödvändig omfångsdistinktion</h4>
    <ul>{_render_humanized_list(oracle.required_scope_distinctions)}</ul></div>
  <div class="card"><h4>Acceptabel uppföljning</h4>
    <ul>{_render_humanized_list(oracle.acceptable_follow_up_needs)}</ul></div>
  <div class="card"><h4>Skyddsregler</h4>
    <ul>{_render_humanized_list(
      oracle.forbidden_findings, prefix="Dra inte slutsatsen: "
    )}</ul></div>
</section>
<h4>Orakelutsedd avgörande bestämmelseuppsättning</h4>
<ul>{decisive_sets}</ul>
"""


def _render_document(document: LoadedPolicyDocument, explorer_case: ExplorerCase) -> str:
    manifest = document.manifest
    applicability_badge = _applicability_badge(
        status=manifest.status,
        effective_from=manifest.effective_from,
        geography=manifest.geography,
        review_date=explorer_case.case_input.case.review_context.as_of_date,
        review_geography=explorer_case.case_input.case.review_context.geography,
    )
    metadata_badges = "".join(
        (
            _badge(manifest.document_type.replace("_", " "), "meta"),
            _badge(manifest.authority_level.replace("_", " "), "meta"),
            _badge(f"Gäller från {manifest.effective_from.isoformat()}", "meta"),
            _badge(", ".join(manifest.geography), "meta"),
            applicability_badge,
        )
    )
    retrieval_role = _document_role(manifest.document_id, explorer_case)
    retrieval_badge = "" if retrieval_role is None else _badge(
        _document_role_label(retrieval_role.kind), "retrieval"
    )
    clauses = "".join(_render_clause(clause, explorer_case) for clause in document.clauses)
    return f"""
<details class="policy-document">
  <summary>
    <span id="{html.escape(manifest.document_id, quote=True)}">{html.escape(manifest.title)}</span>
    <span>({html.escape(manifest.document_id)})</span>{retrieval_badge}</summary>
  <div class="document-body"><div class="badges">{metadata_badges}</div>{clauses}</div>
</details>
"""


def _render_clause(clause: PolicyClause, explorer_case: ExplorerCase) -> str:
    document_id = clause.document.document_id
    clause_id = clause.clause_id
    badges: list[str] = []
    if (document_id, clause_id) in _decisive_references(explorer_case.oracle):
        badges.append(_badge("Avgörande underlag", "decisive"))
    for role in explorer_case.presentation.clause_roles:
        if (role.reference.document_id, role.reference.clause_id) == (document_id, clause_id):
            badges.append(_badge(role.label, "role"))
            badges.append(_badge(role.explanation, "meta"))
    return f"""
<section class="clause" id="{html.escape(f'{document_id}--{clause_id}', quote=True)}">
  <strong>{html.escape(clause_id)} — {html.escape(clause.heading)}</strong>
  <div class="badges">{''.join(badges)}</div>
  <p>{html.escape(clause.content)}</p>
</section>
"""


def _applicability_badge(
    *,
    status: str,
    effective_from: date,
    geography: list[str],
    review_date: date,
    review_geography: str,
) -> str:
    if status == "superseded":
        return _badge("Utesluten på grund av status", "superseded")
    if effective_from > review_date:
        return _badge("Ännu inte i kraft", "excluded")
    if review_geography not in geography:
        return _badge("Utanför granskningsgeografin", "excluded")
    return _badge("Aktuell och inom omfånget", "current")


def _decisive_references(oracle: CaseOracle) -> set[tuple[str, str]]:
    return {
        (reference.document_id, reference.clause_id)
        for clause_set in oracle.decisive_clause_sets
        for reference in clause_set
    }


def _document_role(
    document_id: str, explorer_case: ExplorerCase
) -> PresentationDocumentRole | None:
    return next(
        (
            role
            for role in explorer_case.presentation.document_roles
            if role.document_id == document_id
        ),
        None,
    )


def _document_role_label(kind: DocumentRoleKind) -> str:
    return {
        DocumentRoleKind.POLICY_RULE: "Hämtningsmål: policyregel",
        DocumentRoleKind.TERM_DEFINITION: "Hämtningsmål: termdefinition",
        DocumentRoleKind.LOCAL_EXCEPTION: "Hämtningsmål: lokalt undantag",
        DocumentRoleKind.GOVERNANCE_PRECEDENCE: "Hämtningsmål: styrning / prejudikat",
        DocumentRoleKind.CONTEXT_ONLY: "Endast kontext",
    }[kind]


def _render_reference(reference: EvidenceReference) -> str:
    return html.escape(f"{reference.document_id} / {reference.clause_id}")


def _render_humanized_list(values: list[str], prefix: str = "") -> str:
    if not values:
        return "<li>Inget registrerat</li>"
    return "".join(f"<li>{html.escape(prefix + _humanize(value))}</li>" for value in values)


def _humanize(value: object) -> str:
    return humanize_sv(value)


def _badge(label: str, style: str) -> str:
    return f'<span class="badge {style}">{html.escape(label)}</span>'


if __name__ == "__main__":
    main()
