# ruff: noqa: E501
"""Single-shot local workbench joining the case explorer and investigator."""

from __future__ import annotations

import argparse
import html
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

from policy_coherence_investigator.evaluation import EvaluationReport, evaluate_result
from policy_coherence_investigator.interfaces.case_explorer import (
    ExplorerCase,
    load_explorer_cases,
    render_case_details,
    render_case_link,
)
from policy_coherence_investigator.interfaces.investigate import (
    InvestigationRunReport,
    run_investigation,
)
from policy_coherence_investigator.investigation import CoherenceFinding

MAX_REQUEST_BYTES = 16 * 1024


@dataclass(frozen=True)
class WorkbenchRequest:
    """Validated user input for one explicit, paid investigation."""

    case_id: str
    question: str
    as_of_date: date
    geography: str
    populations: tuple[str, ...]
    access_types: tuple[str, ...]
    retrieval_budget: int


def default_workbench_request(explorer_case: ExplorerCase) -> WorkbenchRequest:
    """Return the canonical, editable evaluation inputs for one selected case."""

    case = explorer_case.case_input.case
    return WorkbenchRequest(
        case_id=case.case_id,
        question=case.question,
        as_of_date=case.review_context.as_of_date,
        geography=case.review_context.geography,
        populations=tuple(case.review_context.populations),
        access_types=tuple(case.review_context.access_types),
        retrieval_budget=case.retrieval_budget,
    )


def parse_workbench_request(
    form: Mapping[str, Sequence[str]], cases: tuple[ExplorerCase, ...]
) -> WorkbenchRequest:
    """Validate one browser form without accepting arbitrary corpus paths or scope values."""

    selected_case = _selected_case(cases, _one_value(form, "case"))
    default = default_workbench_request(selected_case)
    question = _one_value(form, "question").strip()
    if not question:
        raise ValueError("Question cannot be blank.")
    try:
        as_of_date = date.fromisoformat(_one_value(form, "as_of"))
    except ValueError as error:
        raise ValueError("As-of date must use YYYY-MM-DD.") from error
    geography = _one_value(form, "geography").strip()
    if not geography:
        raise ValueError("Geography cannot be blank.")
    populations = _scope_values(
        form.get("population", ()), frozenset(default.populations), "population"
    )
    access_types = _scope_values(
        form.get("access_type", ()), frozenset(default.access_types), "access type"
    )
    return WorkbenchRequest(
        case_id=default.case_id,
        question=question,
        as_of_date=as_of_date,
        geography=geography,
        populations=populations,
        access_types=access_types,
        retrieval_budget=default.retrieval_budget,
    )


def run_workbench_investigation(
    request: WorkbenchRequest,
    cases: tuple[ExplorerCase, ...],
    *,
    provider: str | None = None,
) -> InvestigationRunReport:
    """Run against the selected case's controlled corpus using only agent-safe inputs."""

    explorer_case = _selected_case(cases, request.case_id)
    return run_investigation(
        question=request.question,
        corpus_directory=explorer_case.corpus.root,
        as_of_date=request.as_of_date,
        geography=request.geography,
        populations=request.populations,
        access_types=request.access_types,
        retrieval_budget=request.retrieval_budget,
        provider=provider,
    )


def is_canonical_request(request: WorkbenchRequest, explorer_case: ExplorerCase) -> bool:
    """Require exact case inputs before applying the case's hidden evaluation oracle."""

    return request == default_workbench_request(explorer_case)


def evaluate_workbench_report(
    request: WorkbenchRequest,
    explorer_case: ExplorerCase,
    report: InvestigationRunReport,
) -> EvaluationReport | None:
    """Evaluate a completed canonical run without making oracle data available to the model."""

    if not is_canonical_request(request, explorer_case):
        return None
    if report.result is None:
        return EvaluationReport(("workflow completed without a structured final result",))
    return evaluate_result(
        case=explorer_case.case_input,
        oracle=explorer_case.oracle,
        corpus=explorer_case.corpus,
        result=report.result,
        retrieved_clauses=report.retrieved_clauses,
        ledger=report.ledger,
        architecture="bounded",
        requested_evidence_needs=report.requested_evidence_needs,
    )


def render_workbench_page(
    cases: tuple[ExplorerCase, ...],
    selected_case_id: str | None,
    *,
    request: WorkbenchRequest | None = None,
    report: InvestigationRunReport | None = None,
    evaluation: EvaluationReport | None = None,
    error: str | None = None,
) -> str:
    """Render a local human workbench; oracle notes remain page-only, never model input."""

    selected_case = _selected_case(cases, selected_case_id)
    request = request or default_workbench_request(selected_case)
    default_request = default_workbench_request(selected_case)
    canonical_request = is_canonical_request(request, selected_case)
    case_navigation = "".join(render_case_link(case, case is selected_case) for case in cases)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>Policy coherence investigation workbench</title>
  <style>
    :root {{ color: #17202a; background: #eef2f3; font-family: ui-sans-serif, system-ui, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; }}
    main {{ display: grid; grid-template-columns: minmax(480px, 1.25fr) minmax(390px, .9fr); min-height: 100vh; }}
    .explorer {{ min-width: 0; background: #f7f8fa; border-right: 1px solid #cdd8dc; }}
    .explorer-nav {{ padding: 22px 20px 16px; background: #172b3a; color: #eff6f8; }}
    .explorer-nav h1 {{ margin: 0 0 6px; font-size: 1.15rem; }}
    .explorer-nav p {{ margin: 0 0 12px; color: #c8d7dd; font-size: .9rem; line-height: 1.45; }}
    .case-link {{ display: block; margin: 6px 0; padding: 10px; border-radius: 7px; color: inherit; text-decoration: none; }}
    .case-link:hover, .case-link.current {{ background: #284b61; }}
    .case-link span, .case-link small {{ display: block; }}
    .case-link small {{ margin-top: 3px; color: #c8d7dd; }}
    .case-details {{ padding: 28px clamp(20px, 4vw, 48px) 44px; }}
    .case-details h2 {{ margin: 0; font-size: clamp(1.5rem, 3vw, 2.2rem); line-height: 1.15; }}
    .case-details h3 {{ margin-top: 32px; }}
    .case-details h4 {{ margin: 18px 0 7px; }}
    .eyebrow {{ color: #496d81; font-size: .75rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; }}
    .summary {{ font-size: 1.02rem; line-height: 1.55; }}
    .notice {{ padding: 12px 14px; border-left: 4px solid #a45e14; background: #fff5e5; line-height: 1.45; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }}
    .card {{ padding: 14px; border: 1px solid #d7e0e5; border-radius: 8px; background: white; }}
    .card h4 {{ margin: 0 0 7px; }} .card p {{ margin: 0; line-height: 1.5; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }}
    .badge {{ display: inline-block; padding: 3px 7px; border-radius: 999px; font-size: .74rem; font-weight: 700; letter-spacing: .02em; }}
    .badge.current {{ color: #135e3b; background: #d9f2e4; }} .badge.superseded, .badge.excluded {{ color: #5f4a16; background: #f6e7bd; }}
    .badge.decisive {{ color: #5c2b68; background: #f0dff4; }} .badge.role {{ color: #174b68; background: #dcecf5; }}
    .badge.retrieval {{ color: #704000; background: #ffe1a8; margin-left: 8px; }} .badge.meta {{ color: #47515a; background: #e5e9ec; }}
    details {{ margin: 12px 0; border: 1px solid #d7e0e5; border-radius: 8px; background: white; overflow: hidden; }}
    summary {{ cursor: pointer; padding: 14px 16px; font-weight: 700; }}
    .document-body {{ padding: 0 16px 16px; border-top: 1px solid #d7e0e5; }}
    .clause {{ padding: 12px 0; border-top: 1px solid #e6ecef; scroll-margin-top: 18px; }} .clause:first-child {{ border-top: 0; }}
    .clause p {{ margin: 7px 0 0; white-space: pre-wrap; line-height: 1.5; }} ul {{ margin: 8px 0; padding-left: 20px; }} li {{ margin: 5px 0; }}
    .investigator {{ padding: clamp(22px, 4vw, 54px); background: #fff; }}
    .investigator-inner {{ max-width: 680px; margin: 0 auto; }}
    .investigator h2 {{ margin: 0; font-size: clamp(1.6rem, 3vw, 2.35rem); line-height: 1.12; }}
    .lede {{ color: #4d5c63; line-height: 1.5; }}
    form {{ margin-top: 24px; }} label, legend {{ display: block; font-size: .88rem; font-weight: 700; color: #34454d; }}
    textarea, input {{ width: 100%; margin-top: 7px; border: 1px solid #b8c7cc; border-radius: 7px; padding: 10px; font: inherit; color: inherit; background: #fff; }}
    textarea {{ min-height: 135px; resize: vertical; line-height: 1.45; }}
    .fields {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 15px; }}
    fieldset {{ margin: 15px 0 0; padding: 0; border: 0; }} .choices {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .choice {{ display: inline-flex; align-items: center; gap: 6px; border: 1px solid #c9d4d8; border-radius: 999px; padding: 7px 10px; font-weight: 500; }}
    .choice input {{ width: auto; margin: 0; }}
    button {{ margin-top: 20px; border: 0; border-radius: 7px; padding: 11px 15px; background: #126c70; color: white; font: inherit; font-weight: 700; cursor: pointer; }} button:hover {{ background: #09575b; }} button:disabled {{ background: #89969a; cursor: wait; }}
    #investigation-status {{ margin: 10px 0 0; color: #4d5c63; font-size: .9rem; }}
    .comparison {{ margin-top: 18px; padding: 12px 14px; border-radius: 8px; font-size: .92rem; line-height: 1.45; }}
    .comparison.active, .verification.pass {{ color: #135e3b; background: #e6f5eb; border: 1px solid #b9dfc7; }}
    .comparison.inactive {{ color: #5f4a16; background: #fff5e5; border: 1px solid #ead2a5; }}
    .verification {{ margin: 16px 0; padding: 14px; border-radius: 8px; line-height: 1.45; }}
    .verification.fail {{ color: #8b2520; background: #fff0ef; border: 1px solid #edc1bd; }}
    .verification-mark {{ margin-left: 8px; font-size: .82rem; font-weight: 700; }}
    .verification-mark.pass {{ color: #135e3b; }} .verification-mark.fail {{ color: #a12822; }}
    .callout {{ margin-top: 24px; padding: 14px 16px; border-radius: 8px; background: #eef6f6; border: 1px solid #bdd9d8; line-height: 1.45; }}
    .error {{ background: #fff0ef; border-color: #edc1bd; color: #8b2520; }}
    .result {{ margin-top: 28px; padding-top: 26px; border-top: 1px solid #d9e1e4; }} .result h3 {{ margin: 0 0 10px; }}
    .category {{ display: inline-block; padding: 5px 8px; border-radius: 4px; background: #17394b; color: white; font-size: .8rem; font-weight: 700; letter-spacing: .03em; text-transform: uppercase; }}
    .finding {{ margin: 12px 0; padding: 14px; border-left: 4px solid #168184; background: #f3f8f8; }} .finding h4 {{ margin: 0 0 7px; }} .finding p {{ margin: 0; line-height: 1.5; }}
    .citation {{ display: inline-block; margin: 8px 6px 0 0; color: #0b5c79; font: .82rem ui-monospace, SFMono-Regular, monospace; }}
    .metadata {{ color: #55656b; font-size: .9rem; }}
    @media (max-width: 1080px) {{ main {{ grid-template-columns: 1fr; }} .explorer {{ border-right: 0; border-bottom: 1px solid #cdd8dc; }} }}
    @media (max-width: 600px) {{ .fields {{ grid-template-columns: 1fr; }} .case-details, .investigator {{ padding: 24px 18px; }} }}
  </style>
</head>
<body>
  <main>
    <section class="explorer" aria-label="Evaluation case explorer">
      <nav class="explorer-nav"><h1>Case explorer</h1><p>Selecting a case sets the controlled corpus and review defaults for the investigation.</p>{case_navigation}</nav>
      <article class="case-details">{render_case_details(selected_case)}</article>
    </section>
    <section class="investigator" aria-label="Policy coherence investigator">
      <div class="investigator-inner">
        <p class="eyebrow">Selected case: {html.escape(selected_case.case_input.case.case_id)}</p>
        <h2>Investigate a policy question</h2>
        <p class="lede">Edit the question or scope, then run one bounded, evidence-cited review against this case's controlled corpus.</p>
        {_render_form(request, default_request)}
        {_render_comparison_status(canonical_request, report is not None)}
        {_render_error(error)}
        {_render_report(report, selected_case, evaluation)}
      </div>
    </section>
  </main>
  {_render_submission_script()}
</body>
</html>"""


def make_request_handler(
    cases: tuple[ExplorerCase, ...], *, provider: str | None = None
) -> type[BaseHTTPRequestHandler]:
    """Create a local handler that keeps browser display data out of model requests."""

    class WorkbenchRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            selected_case_id = parse_qs(parsed.query).get("case", [None])[0]
            try:
                page = render_workbench_page(cases, selected_case_id)
            except ValueError:
                self.send_error(HTTPStatus.NOT_FOUND, "Unknown case")
                return
            self._send_html(page)

        def do_POST(self) -> None:  # noqa: N802
            if urlparse(self.path).path != "/investigate":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                request = parse_workbench_request(self._read_form(), cases)
                report = run_workbench_investigation(request, cases, provider=provider)
                explorer_case = _selected_case(cases, request.case_id)
                evaluation = evaluate_workbench_report(request, explorer_case, report)
                page = render_workbench_page(
                    cases,
                    request.case_id,
                    request=request,
                    report=report,
                    evaluation=evaluation,
                )
                self._send_html(page)
            except ValueError as error:
                selected_case_id = self._selected_case_id_from_body()
                page = self._render_failure_page(selected_case_id, str(error))
                self._send_html(page, status=HTTPStatus.BAD_REQUEST)
            except Exception:
                page = self._render_failure_page(
                    self._selected_case_id_from_body(),
                    "The investigation could not be completed. Check the configured provider and try again.",
                )
                self._send_html(page, status=HTTPStatus.INTERNAL_SERVER_ERROR)

        def _read_form(self) -> dict[str, list[str]]:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length < 1 or content_length > MAX_REQUEST_BYTES:
                raise ValueError("The submitted form is missing or too large.")
            content_type = self.headers.get("Content-Type", "")
            if content_type.split(";", 1)[0].strip().lower() != "application/x-www-form-urlencoded":
                raise ValueError("Expected a standard form submission.")
            body = self.rfile.read(content_length).decode("utf-8")
            self._last_form = parse_qs(body, keep_blank_values=True)
            return self._last_form

        def _selected_case_id_from_body(self) -> str | None:
            form = getattr(self, "_last_form", {})
            return form.get("case", [None])[0]

        def _render_failure_page(self, selected_case_id: str | None, error: str) -> str:
            try:
                return render_workbench_page(cases, selected_case_id, error=error)
            except ValueError:
                return render_workbench_page(cases, None, error=error)

        def _send_html(self, page: str, *, status: HTTPStatus = HTTPStatus.OK) -> None:
            encoded = page.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            """Keep the local demonstration server quiet after startup."""

    return WorkbenchRequestHandler


def main(argv: Sequence[str] | None = None) -> int:
    """Serve the combined local case explorer and one-shot investigator workbench."""

    parser = argparse.ArgumentParser(description="Run the local policy-coherence workbench.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to listen on.")
    parser.add_argument("--port", type=int, default=8767, help="TCP port to listen on.")
    parser.add_argument("--provider", choices=("openai", "anthropic"))
    args = parser.parse_args(argv)
    load_dotenv()
    cases = load_explorer_cases()
    server = ThreadingHTTPServer(
        (args.host, args.port), make_request_handler(cases, provider=args.provider)
    )
    print(f"Policy coherence workbench running at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPolicy coherence workbench stopped.")
    finally:
        server.server_close()
    return 0


def _render_form(request: WorkbenchRequest, default_request: WorkbenchRequest) -> str:
    return f"""
<form id="investigation-form" method="post" action="/investigate">
  <input type="hidden" name="case" value="{html.escape(request.case_id, quote=True)}">
  <label for="question">Question<textarea id="question" name="question" required placeholder="Ask a policy-coherence question" data-canonical-value="{html.escape(default_request.question, quote=True)}">{html.escape(request.question)}</textarea></label>
  <div class="fields">
    <label for="as_of">As of<input id="as_of" name="as_of" type="date" value="{request.as_of_date.isoformat()}" data-canonical-value="{default_request.as_of_date.isoformat()}" required></label>
    <label for="geography">Geography<input id="geography" name="geography" value="{html.escape(request.geography, quote=True)}" data-canonical-value="{html.escape(default_request.geography, quote=True)}" required></label>
  </div>
  <fieldset><legend>Populations in scope</legend><div class="choices">{_render_choices('population', default_request.populations, request.populations, default_request.populations)}</div></fieldset>
  <fieldset><legend>Access types in scope</legend><div class="choices">{_render_choices('access_type', default_request.access_types, request.access_types, default_request.access_types)}</div></fieldset>
  <button id="investigate-button" type="submit">Investigate</button>
  <p id="investigation-status" role="status" aria-live="polite" hidden>Investigating policy evidence…</p>
</form>"""


def _render_choices(
    name: str,
    values: Sequence[str],
    selected_values: Sequence[str],
    canonical_values: Sequence[str],
) -> str:
    selected = set(selected_values)
    canonical = set(canonical_values)
    return "".join(
        f'<label class="choice"><input type="checkbox" name="{name}" value="{value}"'
        f"{' checked' if value in selected else ''} "
        f'data-canonical-checked="{str(value in canonical).lower()}"> '
        f"{html.escape(value.capitalize())}</label>"
        for value in values
    )


def _render_comparison_status(canonical_request: bool, completed: bool) -> str:
    if canonical_request:
        message = (
            "This case's canonical question and scope are selected. "
            "Its result will be compared with the hidden expected outcome after the run."
            if not completed
            else "This result was compared with the selected case's hidden expected outcome."
        )
        return f'<p class="comparison active" id="comparison-status">✓ {message}</p>'
    return (
        '<p class="comparison inactive" id="comparison-status">Custom inputs selected. The investigator will run, '
        "but this result will not be compared with the case's expected outcome.</p>"
    )


def _render_submission_script() -> str:
    """Disable the submit control while the browser waits for the paid review response."""

    return """<script>
const investigationForm = document.getElementById("investigation-form");
const comparisonStatus = document.getElementById("comparison-status");
const comparisonText = "This case's canonical question and scope are selected. Its result will be compared with the hidden expected outcome after the run.";
const customText = "Custom inputs selected. The investigator will run, but this result will not be compared with the case's expected outcome.";

function updateComparisonStatus() {
  const textMatches = ["question", "as_of", "geography"].every((name) => {
    const input = investigationForm.elements[name];
    return input.value === input.dataset.canonicalValue;
  });
  const scopeMatches = [...investigationForm.querySelectorAll('input[type="checkbox"]')].every((input) => {
    return input.checked === (input.dataset.canonicalChecked === "true");
  });
  const canonical = textMatches && scopeMatches;
  comparisonStatus.className = `comparison ${canonical ? "active" : "inactive"}`;
  comparisonStatus.textContent = canonical ? `✓ ${comparisonText}` : customText;
}

investigationForm.addEventListener("input", updateComparisonStatus);
investigationForm.addEventListener("change", updateComparisonStatus);
investigationForm.addEventListener("submit", () => {
  const button = document.getElementById("investigate-button");
  button.disabled = true;
  button.textContent = "Investigating…";
  document.getElementById("investigation-status").hidden = false;
});
</script>"""


def _render_error(error: str | None) -> str:
    if error is None:
        return ""
    return f'<p class="callout error" role="alert">{html.escape(error)}</p>'


def _render_report(
    report: InvestigationRunReport | None,
    explorer_case: ExplorerCase,
    evaluation: EvaluationReport | None,
) -> str:
    if report is None:
        return ""
    if report.result is None:
        return """<section class="result"><h3>Investigation finished without a structured review</h3>
<p class="metadata">No supported review was produced. See the investigation metadata below.</p>""" + _render_evaluation(evaluation) + _render_metadata(report) + "</section>"
    result = report.result
    show_evaluation = evaluation is not None
    cited_references = {
        (citation.document_id, citation.clause_id)
        for finding in result.findings
        for citation in finding.citations
    }
    expected_citations = (
        _fully_cited_decisive_references(explorer_case, cited_references)
        if show_evaluation
        else set()
    )
    findings = "".join(
        _render_finding(finding, explorer_case, expected_citations, show_evaluation)
        for finding in result.findings
    )
    assumptions = "".join(
        _render_assumption(
            assumption.assumption_id, assumption.statement, explorer_case, show_evaluation
        )
        for assumption in result.scope_assumptions
    )
    questions = "".join(f"<li>{html.escape(question)}</li>" for question in result.unresolved_questions)
    evidence_need = result.next_evidence_need
    next_step = "" if evidence_need is None else (
        f"<section class=\"callout\"><strong>Further evidence requested:</strong> "
        f"{html.escape(evidence_need.rationale)}</section>"
    )
    category_mark = _category_mark(result.category.value, explorer_case) if show_evaluation else ""
    return f"""<section class="result"><p class="category">{html.escape(result.category.value.replace('_', ' '))}</p>{category_mark}
<h3>Review</h3><p class="summary">{html.escape(result.summary)}</p>{_render_evaluation(evaluation)}{findings}
{_render_list_section('Scope assumptions', assumptions)}
{_render_list_section('Unresolved questions', questions)}
{next_step}{_render_metadata(report)}</section>"""


def _render_evaluation(evaluation: EvaluationReport | None) -> str:
    if evaluation is None:
        return ""
    if evaluation.passed:
        return '<section class="verification pass"><strong>✓ Case evaluation passed</strong></section>'
    issues = "".join(f"<li>{html.escape(issue)}</li>" for issue in evaluation.issues)
    return (
        '<section class="verification fail"><strong>✕ Case evaluation needs review</strong>'
        f"<ul>{issues}</ul></section>"
    )


def _category_mark(category: str, explorer_case: ExplorerCase) -> str:
    accepted = {value.value for value in explorer_case.oracle.acceptable_result_categories}
    if category in accepted:
        return '<span class="verification-mark pass">✓ Expected category</span>'
    return '<span class="verification-mark fail">✕ Unexpected category</span>'


def _render_finding(
    finding: CoherenceFinding,
    explorer_case: ExplorerCase,
    expected_citations: set[tuple[str, str]],
    show_evaluation: bool,
) -> str:
    finding_id = finding.finding_id
    if not show_evaluation:
        mark = ""
    elif finding_id in explorer_case.oracle.required_findings:
        mark = '<span class="verification-mark pass">✓ Expected finding</span>'
    elif finding_id in explorer_case.oracle.forbidden_findings:
        mark = '<span class="verification-mark fail">✕ Forbidden finding</span>'
    else:
        mark = ""
    citations = "".join(
        _render_citation(citation.document_id, citation.clause_id, expected_citations)
        for citation in finding.citations
    )
    return f"""<section class="finding"><h4>{html.escape(finding_id.replace('_', ' '))}{mark}</h4>
<p>{html.escape(finding.conclusion)}</p><div>{citations}</div></section>"""


def _render_assumption(
    assumption_id: str,
    statement: str,
    explorer_case: ExplorerCase,
    show_evaluation: bool,
) -> str:
    mark = (
        '<span class="verification-mark pass">✓ Expected scope distinction</span>'
        if show_evaluation and assumption_id in explorer_case.oracle.required_scope_distinctions
        else ""
    )
    return f"<li>{html.escape(statement)}{mark}</li>"


def _fully_cited_decisive_references(
    explorer_case: ExplorerCase, cited_references: set[tuple[str, str]]
) -> set[tuple[str, str]]:
    for clause_set in explorer_case.oracle.decisive_clause_sets:
        references = {(reference.document_id, reference.clause_id) for reference in clause_set}
        if references <= cited_references:
            return references
    return set()


def _render_citation(
    document_id: str,
    clause_id: str,
    expected_citations: set[tuple[str, str]],
) -> str:
    target = f"{document_id}--{clause_id}"
    expected = (
        '<span class="verification-mark pass">✓ Expected evidence</span>'
        if (document_id, clause_id) in expected_citations
        else ""
    )
    return f'<a class="citation" href="#{html.escape(target, quote=True)}">{html.escape(document_id)} / {html.escape(clause_id)}</a>{expected}'


def _render_list_section(title: str, values: str) -> str:
    if not values:
        return ""
    return f"<h4>{title}</h4><ul>{values}</ul>"


def _render_metadata(report: InvestigationRunReport) -> str:
    follow_ups = ", ".join(
        f"{need.kind.value} ({need.target})" for need in report.requested_evidence_needs
    ) or "none"
    return f"""<p class="metadata">Corpus: {html.escape(report.corpus_id)} · Retrievals: {report.retrieval_count}/{report.retrieval_budget} · Termination: {html.escape(report.termination_reason)}<br>Follow-up evidence: {html.escape(follow_ups)}</p>"""


def _selected_case(cases: tuple[ExplorerCase, ...], case_id: str | None) -> ExplorerCase:
    if case_id is None:
        return cases[0]
    for explorer_case in cases:
        if explorer_case.case_input.case.case_id == case_id:
            return explorer_case
    raise ValueError("Unknown case.")


def _one_value(form: Mapping[str, Sequence[str]], name: str) -> str:
    values = form.get(name, ())
    if len(values) != 1:
        raise ValueError(f"Expected exactly one {name.replace('_', ' ')} value.")
    return values[0]


def _scope_values(
    values: Sequence[str], allowed_values: frozenset[str], label: str
) -> tuple[str, ...]:
    normalized = tuple(value.strip().lower() for value in values if value.strip())
    if not normalized:
        raise ValueError(f"Choose at least one {label}.")
    if len(set(normalized)) != len(normalized) or not set(normalized) <= allowed_values:
        raise ValueError(f"Invalid {label} selection.")
    return normalized


if __name__ == "__main__":
    raise SystemExit(main())
