# Suggested project layout for the policy coherence investigator

**Status:** Bootstrap guidance for a new repository  
**Source project:** `agentic-doc-poc`  
**Target working name:** `policy-coherence-investigator`

## Purpose of this document

This document describes the reusable shape of the current `agentic-doc-poc` repository and adapts it for the policy coherence investigator described in `policy-coherence-investigator-inception.md`.

The goal is to preserve the parts of the current project that have worked well:

- a Python `src/` package managed with `uv`;
- typed boundaries around model inputs, outputs, tools, and graph state;
- deterministic policy, parsing, validation, filtering, and provenance outside prompts;
- LangGraph workflows with observable state and explicit budgets;
- fast offline tests separated from paid probabilistic evaluations;
- strict isolation of hidden evaluation oracles;
- synthetic cases stored as readable Markdown and YAML;
- LangSmith tracing and LangGraph Studio debugging;
- small local browser interfaces for inspecting cases and maintaining project notes; and
- clear separation between tracked sources, generated data, local downloads, and run artifacts.

This is not a recommendation to copy warranty-specific models, prompts, actions, or outcomes. Copy the architectural seams and development practices, then introduce policy-specific types deliberately.

## Important terminology correction: LangSmith, not Langfuse

The current repository does **not** use Langfuse. It uses:

- the `langsmith` Python package for tracing;
- `LANGSMITH_*` environment variables;
- LangGraph's local Agent Server; and
- LangSmith Studio for graph visualization and interactive debugging.

If the intention is to use the same tooling, the new project should retain LangSmith. Adding Langfuse would be a separate observability decision requiring a new dependency, configuration, and instrumentation path; it should not be described as something inherited from this repository.

## Recommended top-level layout

```text
policy-coherence-investigator/
├── .env.example
├── .gitignore
├── .python-version
├── AGENTS.md
├── README.md
├── langgraph.json
├── pyproject.toml
├── uv.lock
│
├── src/
│   └── policy_coherence_investigator/
│       ├── __init__.py
│       ├── case_data/
│       │   ├── __init__.py
│       │   └── loader.py
│       ├── evidence/
│       │   ├── __init__.py
│       │   ├── actions.py
│       │   ├── agent_tools.py
│       │   ├── environment.py
│       │   ├── reference_search.py
│       │   └── virtual_workspace.py
│       ├── infrastructure/
│       │   ├── __init__.py
│       │   └── llm.py
│       ├── interfaces/
│       │   ├── __init__.py
│       │   ├── case_explorer.py
│       │   ├── project_summary.py
│       │   └── studio/
│       │       ├── __init__.py
│       │       ├── entrypoints.py
│       │       └── graphs.py
│       ├── investigation/
│       │   ├── __init__.py
│       │   ├── ledger.py
│       │   ├── prompts.py
│       │   ├── result.py
│       │   └── scope.py
│       ├── retrieval/
│       │   ├── __init__.py
│       │   ├── corpus.py
│       │   ├── filters.py
│       │   └── lexical.py
│       └── workflows/
│           ├── __init__.py
│           ├── baseline_review.py
│           ├── bounded_investigation.py
│           ├── investigation_policy.py
│           └── autonomous_investigation.py
│
├── tests/
│   ├── test_case_discovery.py
│   ├── test_case_explorer.py
│   ├── test_corpus.py
│   ├── test_evaluator.py
│   ├── test_filters.py
│   ├── test_investigation_graph.py
│   ├── test_investigation_ledger.py
│   ├── test_investigation_policy.py
│   ├── test_llm_factory.py
│   ├── test_project_summary.py
│   ├── test_retrieval.py
│   ├── test_run_all.py
│   ├── test_run_case.py
│   ├── test_scope.py
│   └── test_studio_graphs.py
│
├── evals/
│   ├── README.md
│   ├── __init__.py
│   ├── case_discovery.py
│   ├── evaluator.py
│   ├── evidence_environment.py
│   ├── run_all.py
│   ├── run_case.py
│   ├── cases/
│   │   ├── access-offboarding-a/
│   │   │   ├── case.yaml
│   │   │   └── oracle.yaml
│   │   ├── access-offboarding-b/
│   │   │   ├── case.yaml
│   │   │   └── oracle.yaml
│   │   └── access-offboarding-c/
│   │       ├── case.yaml
│   │       └── oracle.yaml
│   ├── corpora/
│   │   ├── access-offboarding-a/
│   │   │   ├── corpus.yaml
│   │   │   └── policies/
│   │   │       ├── access-control-policy.md
│   │   │       ├── contractor-management-policy.md
│   │   │       ├── hr-offboarding-procedure.md
│   │   │       ├── identity-definitions.md
│   │   │       ├── privileged-access-standard.md
│   │   │       └── ...
│   │   ├── access-offboarding-b/
│   │   └── access-offboarding-c/
│   ├── presentation/
│   │   └── cases.yaml
│   └── runs/
│       └── .gitkeep                 # optional; run contents ignored
│
├── tools/
│   └── synthetic_data/
│       ├── README.md
│       └── ...
│
├── data/
│   ├── generated/
│   │   └── .gitkeep
│   └── sources/
│       └── ...                      # URL, licence, checksum, intended use
│
├── docs/
│   ├── README.md                    # documentation authority map
│   ├── current/
│   │   └── project-inception.md
│   ├── archive/
│   └── human-zone/
│       ├── devlog.md
│       ├── learning-notes.md
│       ├── project-summary.md
│       └── assets/
│
├── artifacts/                       # ignored reproducible outputs
└── local/                           # ignored downloads and caches
```

The first commit does not need every listed file. Create directories and modules when a concrete slice needs them, but preserve the boundaries from the beginning.

## How this maps from the current repository

| Current area | Reusable responsibility | Policy-coherence adaptation |
| --- | --- | --- |
| `case_data/` | Safe loading of agent-visible fixtures, with hidden oracle loading exposed separately | Load a neutral case manifest and its policy corpus without reading the oracle |
| `investigation/result.py` | Provider-native structured output contract | Define review category, findings, citations, unresolved issues, and next evidence action |
| `investigation/ledger.py` | Reviewable state derived from results without becoming source evidence itself | Track working scope, assumptions, normalized obligations, candidate conflicts, gaps, and open questions |
| `investigation/prompts.py` | Prompt construction separate from graph wiring | Build initial-scope, reassessment, and final-review messages |
| `evidence/environment.py` | Protocol for controlled evidence release | Define a capability boundary for retrieval and document access |
| `evidence/actions.py` | Permissioned action vocabulary | Use typed actions such as retrieving definitions, population-specific policies, local addenda, or governance material |
| `evidence/virtual_workspace.py` | Hermetic in-memory agent workspace | Expose only authorized logical policy paths, never raw fixture or oracle paths |
| `evidence/reference_search.py` | Search-first gate; a document must be returned by search before full read | Enforce retrieve-then-read behavior for policy clauses and documents |
| `retrieval/corpus.py` | Manifest validation and path containment | Load policy documents, clause IDs, metadata, and content safely |
| `retrieval/lexical.py` | Small deterministic retrieval baseline | Keep as a baseline before adding embeddings or hybrid retrieval |
| `workflows/` | LangGraph state, model nodes, deterministic routing, budgets, and stop conditions | Implement fixed baseline, bounded agentic loop, and optionally autonomous comparator |
| `infrastructure/llm.py` | Provider selection behind one factory | Retain direct OpenAI and Anthropic support through environment configuration |
| `interfaces/studio/` | Case-specific zero-input graphs for Studio | Expose neutral evaluation cases without loading hidden expectations |
| `interfaces/case_explorer.py` | Read-only local corpus browser using separate human presentation metadata | Show question, corpus, decisive/near-miss explanations, and agent-visible sources to a human |
| `interfaces/project_summary.py` | Local Markdown editor and preview | Reuse nearly unchanged after renaming paths and page text |
| `tests/` | Offline, deterministic behavior and boundary checks | Test loaders, filters, routing, citation validation, scope normalization, and oracle isolation |
| `evals/` | Paid trajectory runners and hidden deterministic scoring | Score retrieval, reasoning, citations, revisions, gaps, escalation, and trajectory efficiency |

## Application package boundaries

### `case_data/`

This is the fixture-loading boundary, not the domain model layer.

Follow the current repository's central safety property:

- `load_case(...)` loads only agent-visible inputs and corpus references;
- `load_oracle(...)` is a separate, explicit evaluation-only call; and
- graph builders, prompts, model tools, Studio entrypoints, and the case explorer must not retain or indirectly expose the hidden oracle.

Validate all relative paths and reject paths that escape the selected case or corpus directory.

### `investigation/`

Keep stable, typed policy-investigation concepts here. Likely initial models are:

- `ReviewQuestion`;
- `WorkingScope` and `ScopeAssumption`;
- `PolicyApplicability`;
- `NormalizedObligation`;
- `EvidenceReference` with document and clause locators;
- `CoherenceFinding`;
- `FindingCategory`, such as confirmed conflict, apparent conflict resolved, or coverage gap;
- `EvidenceNeed` or `NextAction`;
- `InvestigationLedger`; and
- `InvestigationResult`.

Use Pydantic validators for structural invariants such as unique finding IDs, valid result/category combinations, non-empty citations where required, and valid scope transitions. Do not ask the model to remember invariants that code can enforce.

The ledger should be reviewable investigation state, not a substitute for source documents. A prior model statement is not evidence merely because it appears in the ledger.

### `retrieval/`

Keep corpus loading, tokenization, ranking, metadata filters, and deterministic applicability checks independent of LangGraph and provider clients.

The current repository uses a small deterministic TF/IDF-like lexical ranker over ten documents. That is useful as:

- an offline testable retrieval implementation;
- a fixed baseline for the agentic comparison; and
- a way to establish the corpus and evaluation contracts before introducing embeddings.

It is not an embedding-based production RAG stack. The new project can later place embedding or hybrid retrieval behind the same retrieval interface without changing case loading or evaluation semantics.

For policy coherence, deterministic pre- or post-retrieval filtering should cover encoded metadata such as:

- current versus superseded status;
- effective date;
- geography and business unit;
- document authority;
- explicit supersession and override relationships; and
- exact cross-references.

Record raw ranked results as well as filtered results so retrieval failures can be diagnosed.

### `evidence/`

Treat every model-requested action or tool call as untrusted input.

The current repository uses two useful patterns:

1. A bounded workflow recommends one action from a permissioned vocabulary; deterministic routing validates it before an environment releases evidence.
2. An autonomous workflow receives capability-scoped tools over an in-memory virtual workspace and an opaque search session.

Both patterns prevent the agent from reading arbitrary fixture paths or reaching the hidden oracle. Preserve the following controls:

- logical paths rather than host filesystem paths;
- explicit allowed operations;
- typed normal failures rather than uncaught tool exceptions;
- output-size bounds;
- search-first access to reference documents;
- no repeated action or read unless repetition is intentionally supported;
- model-turn, tool-call, retrieval, and token budgets; and
- a complete action/audit history.

### `workflows/`

Keep LangGraph nodes thin. They should coordinate typed domain functions, model calls, and controlled capabilities rather than contain parsing, filtering, scoring, or large prompt strings inline.

For this project, three graph shapes are useful:

1. **Fixed retrieve-and-compare baseline** — one retrieval strategy followed by one structured comparison. This establishes whether the agentic loop adds measurable value.
2. **Bounded policy-coherence investigation** — interpret scope, retrieve, normalize, assess sufficiency, choose a targeted next evidence need, revise, and stop or escalate under a budget.
3. **Capability-scoped autonomous comparator** — an optional one-node LangGraph whose internal tool loop is model-directed, guarded by deterministic tool validation and budgets.

Do not equate a visually complex graph with agenticity. The important observable is whether evidence changes the working scope, hypothesis, or next action.

The graph state should retain at least:

```text
case_id
question
working_scope
scope_assumptions
candidate_findings
evidence_ledger
unresolved_terms
unresolved_conflicts
open_questions
retrieval_history
result_history
remaining_budget
termination_reason
```

### `infrastructure/`

The current `llm.py` is deliberately small: it selects a direct provider from `LLM_PROVIDER` and reads the provider-specific model name from the environment.

Retain this seam so workflows depend on `BaseChatModel`, not on OpenAI- or Anthropic-specific clients. Keep provider construction outside deterministic modules and outside Studio graph-builder imports that tests need to load without credentials.

### `interfaces/`

Delivery interfaces should remain thin and should never become the only place business rules exist.

The current repository has three reusable interfaces:

- explicit evaluation CLIs in `evals/`;
- LangGraph Studio graph entrypoints; and
- local HTTP interfaces for case browsing and Markdown editing.

The browser tools use Python's standard-library `ThreadingHTTPServer`, inline HTML/CSS/JavaScript, and no front-end build chain. This is appropriate for a small local learning project.

## Evaluation-case organization

### Preserve three separate audiences

The current repository deliberately separates three kinds of case information:

| Information | Intended reader | Location | May reach the agent? |
| --- | --- | --- | --- |
| Question, corpus pointer, and other neutral input | Agent and runner | `case.yaml` | Yes |
| Expected findings, decisive evidence, permitted conclusions, and failure constraints | Evaluator only | `oracle.yaml` | No |
| Descriptive title, capability tags, and resolution guide | Human case explorer | `evals/presentation/cases.yaml` | No |

Keep neutral case IDs such as `access-offboarding-a`. Do not name fixture directories `real-conflict` or `coverage-gap`, because filenames are part of the environment and can leak the expected answer.

### Suggested `case.yaml`

```yaml
case_id: access-offboarding-a
corpus_id: access-offboarding-a
question: >
  Do our currently effective policies coherently define when employee,
  contractor, and privileged access must be disabled after termination?
review_context:
  as_of_date: 2026-08-16
  geography: global
retrieval_budget: 3
```

Only include information the real investigator would legitimately receive. Avoid descriptive summaries that reveal which clause is decisive.

### Suggested corpus manifest

```yaml
corpus_id: access-offboarding-a
documents:
  - document_id: access_control_policy_v4
    document_type: policy
    title: Access Control Policy
    path: policies/access-control-policy-v4.md
    effective_from: 2026-01-01
    status: current
    authority_level: corporate_policy
    geography: [global]
  - document_id: hr_offboarding_procedure_v3
    document_type: procedure
    title: HR Offboarding Procedure
    path: policies/hr-offboarding-procedure-v3.md
    effective_from: 2025-10-01
    status: current
    authority_level: procedure
    geography: [global]
```

Use stable clause IDs inside the Markdown documents, for example `ACP-4.2.1`. A material conclusion should cite a document ID plus a clause locator, not merely the document title.

### Suggested hidden `oracle.yaml`

```yaml
case_id: access-offboarding-a
acceptable_result_categories:
  - confirmed_conflict
decisive_clause_sets:
  - [ACP-4.2.1, HOP-7.3]
required_findings:
  - finding_id: incompatible_employee_revocation_deadlines
    required_evidence:
      - document_id: access_control_policy_v4
        clause_id: ACP-4.2.1
      - document_id: hr_offboarding_procedure_v3
        clause_id: HOP-7.3
forbidden_findings:
  - contractor_coverage_confirmed
acceptable_follow_up_needs:
  - retrieve_population_definitions
required_scope_distinctions:
  - ordinary_accounts_vs_privileged_accounts
```

The exact schema should be typed and validated in `case_data/loader.py`. The oracle should express evidence and acceptable outcomes, not force one exact chain of graph node names. That keeps evaluation architecture-neutral enough to compare a fixed workflow with a more autonomous investigator.

### Evaluation dimensions

Adapt the current deterministic evaluator to check:

- acceptable final result category;
- required and forbidden findings;
- required document-and-clause citations;
- citations only to evidence actually retrieved or otherwise exposed;
- use of currently effective rather than superseded material;
- decisive-clause recall;
- false conflicts caused by ignored scope;
- acceptable next retrieval or clarification choices;
- required scope distinctions;
- supported hypothesis revision;
- qualified rather than absolute gap language where absence is unproven;
- termination reason and budget compliance; and
- unexpected, redundant, or missing retrieval actions.

Free-form prose can remain ungraded initially. The machine-checked evidence trail should live in structured fields.

### Tests versus evals

Keep the existing hard boundary:

- `tests/` contains fast deterministic tests and fake-model graph tests;
- `evals/` contains paid, probabilistic, or trajectory-level evaluation;
- `pytest` must never call a live model API; and
- live evaluation is invoked explicitly and may return a non-zero exit status when a case fails.

The suite runner should continue after an individual case failure, report every case, and fail overall unless all required cases pass. Run cases sequentially at first so traces, rate limits, and spend remain easy to interpret.

## Human-facing visualiser interfaces

The current repository contains two small local browser interfaces in addition to LangGraph Studio.

### Evaluation case explorer

`interfaces/case_explorer.py` serves a read-only corpus browser. It joins:

- agent-visible case and corpus material; and
- a separate human-only presentation catalog containing explanations and capability tags.

It never imports hidden oracle data and never calls a model. For the new project, adapt it to show:

- the review question;
- agent-visible policy documents and clause IDs;
- document metadata such as status, authority, scope, and effective dates;
- human-only labels for decisive documents and near misses;
- the intended reasoning capability exercised by each case; and
- a human resolution guide clearly marked as unavailable to the agent.

Suggested command and port:

```bash
uv run policy-coherence-cases
# Open http://127.0.0.1:8765
```

Keep the explorer read-only. It is a demonstration and corpus-inspection surface, not the evaluation runner.

### Project-summary editor and preview

`interfaces/project_summary.py` serves a local Markdown editor with live preview and optional image upload for `docs/human-zone/project-summary.md`. It is independent of model calls and eval execution.

It can be copied with mostly textual and package-path changes:

```bash
uv run policy-coherence-summary
# Open http://127.0.0.1:8767
```

The implementation writes Markdown atomically, escapes user-provided content, restricts image types and sizes, and serves assets only from the summary asset directory. Preserve those controls.

### LangGraph Studio

LangGraph Studio is the graph visualizer and interactive execution debugger. The current pattern is:

1. `langgraph.json` declares package dependencies, graph entrypoints, and `.env`.
2. `interfaces/studio/entrypoints.py` creates provider-dependent compiled graph objects only when the Agent Server loads the module.
3. `interfaces/studio/graphs.py` builds a zero-input graph for a selected synthetic case.
4. The Studio graph loads agent-visible input through `load_case(...)` and never calls `load_oracle(...)`.

Start it with:

```bash
uv sync
uv run langgraph dev
```

The command starts the local Agent Server, normally at `http://127.0.0.1:2024`, and prints the Studio URL. Each submitted graph run uses the configured model provider and therefore consumes model tokens.

A first `langgraph.json` could be:

```json
{
  "dependencies": ["."],
  "graphs": {
    "access-offboarding-a": "./src/policy_coherence_investigator/interfaces/studio/entrypoints.py:access_offboarding_a",
    "access-offboarding-b": "./src/policy_coherence_investigator/interfaces/studio/entrypoints.py:access_offboarding_b",
    "access-offboarding-c": "./src/policy_coherence_investigator/interfaces/studio/entrypoints.py:access_offboarding_c"
  },
  "env": ".env"
}
```

Enumerating a few graphs explicitly is fine for the first corpus. If case count grows substantially, consider one graph that accepts a validated case ID rather than maintaining many entrypoint variables.

## Observability

### LangSmith tracing

The current LangGraph and LangChain model integrations emit LangSmith traces without custom graph instrumentation. Use run names and metadata to distinguish architecture, case, and experiment:

```python
config={
    "run_name": "bounded_policy_coherence_investigation",
    "metadata": {
        "case_id": case_id,
        "architecture": "bounded_agentic",
        "corpus_version": corpus_id,
    },
}
```

Useful trace inspection targets are:

- graph route and state changes;
- model and tool calls;
- retrieval queries and returned clause IDs;
- latency, token count, and estimated traced cost;
- unnecessary or repeated retrieval;
- unsupported claims;
- whether new evidence caused scope or finding revision; and
- why the investigator stopped or escalated.

Traces contain prompts, document contents, and model responses by default. Use only synthetic policies unless masking and organizational data-handling requirements have been addressed. Set tracing off when it is not wanted.

## Suggested `.env.example`

Copy the current provider pattern and rename the LangSmith project:

```dotenv
# Select one direct provider for local development: openai or anthropic.
LLM_PROVIDER=openai

OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6

# Optional LangSmith tracing. Use your own LangSmith key even if the LLM key is shared.
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=policy-coherence-investigator-dev
```

Commit `.env.example`; ignore `.env`. Keep secrets out of fixtures, traces, Markdown documents, and shell examples.

Model identifiers are defaults, not domain contracts. The new repository should be able to change them through environment variables without source edits.

## Suggested Python and dependency setup

The current repository uses Python 3.12, `uv`, the `uv_build` backend, and a committed `uv.lock`.

Suggested `.python-version`:

```text
3.12
```

Suggested initial `pyproject.toml` shape:

```toml
[project]
name = "policy-coherence-investigator"
version = "0.1.0"
description = "An agentic RAG proof of concept for cross-policy coherence investigation"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "langchain-anthropic>=1.3.0",
    "langchain-openai>=1.1.0",
    "langgraph>=1.2.11",
    "langsmith>=0.11.0",
    "pydantic>=2.13.0",
    "python-dotenv>=1.1.0",
    "pyyaml>=6.0",
]

[project.scripts]
policy-coherence-cases = "policy_coherence_investigator.interfaces.case_explorer:main"
policy-coherence-summary = "policy_coherence_investigator.interfaces.project_summary:main"

[build-system]
requires = ["uv_build>=0.12.4,<0.13.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "langgraph-cli[inmem]>=0.4.31",
    "pytest>=8.3",
    "ruff>=0.12",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["B", "E", "F", "I", "UP"]

[tool.ruff.lint.isort]
known-first-party = ["policy_coherence_investigator", "evals"]
```

These constraints reflect the current repository as of this document. Let `uv` resolve and lock a compatible set for the new repository rather than copying `.venv` or manually transplanting installed packages.

Basic commands:

```bash
uv sync
uv run pytest
uv run ruff check .
```

Suggested paid evaluation commands:

```bash
uv run python -m evals.run_case access-offboarding-a --provider openai
uv run python -m evals.run_all --provider openai
```

Use `--provider anthropic` for a cross-provider run. Keep these commands separate from `pytest` because they consume tokens and are probabilistic.

## `.gitignore` and output policy

Carry forward the existing Python, virtual-environment, test-cache, editor, and OS exclusions. At minimum, retain:

```gitignore
.env
.langgraph_api/
.venv/
.pytest_cache/
.ruff_cache/
__pycache__/
*.py[codz]
.DS_Store

local/
data/generated/*
!data/generated/.gitkeep
evals/runs/
artifacts/
```

Commit:

- source code and deterministic tests;
- synthetic source fixtures required to reproduce evaluation cases;
- `uv.lock`;
- `.env.example` without secrets;
- corpus manifests and stable clause metadata;
- source provenance manifests; and
- current planning and evaluation documentation.

Do not commit:

- `.env` or credentials;
- `.venv`;
- LangGraph local server state under `.langgraph_api/`;
- local downloads and caches;
- paid eval run outputs unless a specific reviewed artifact is intentionally promoted; or
- reproducible generated corpora that can be recreated from tracked tooling and seeds.

## Data and synthetic-generation conventions

Retain the current four-way distinction:

| Location | Purpose | Tracked? |
| --- | --- | --- |
| `evals/corpora/` | Small canonical synthetic corpora required by checked-in eval cases | Yes |
| `tools/synthetic_data/` | Generators and validation utilities | Yes |
| `data/generated/` | Reproducible bulk outputs | Directory placeholder only by default |
| `local/` | Downloads, caches, and private local material | No |

If external public material informs synthetic policy language, record source name, provider, source URL, licence, checksum where practical, local path, and intended use under `data/sources/`. Do not quietly embed third-party text into fixtures without provenance and licence review.

Synthetic generation tools may import typed application models from `src/`, but importable production code should not depend on `tools/`.

## Documentation organization

Copy the documentation authority convention:

- `docs/README.md` is the map explaining which documents are authoritative;
- `docs/current/` contains current requirements, plans, and implementation context;
- `docs/archive/` preserves superseded snapshots as history, not requirements; and
- `docs/human-zone/` contains informal notes and human-maintained summaries.

When the new repository is created, move or copy the inception document to something like:

```text
docs/current/project-inception.md
```

Then list it in `docs/README.md`. Avoid leaving multiple unlabelled inception documents that appear equally authoritative.

## Suggested `AGENTS.md` principles

Adapt the current repository guidance to the new package and domain:

```markdown
# Repository guidance

- Read `docs/README.md` before using project documentation as requirements.
- Treat `docs/current/` as current project context and `docs/archive/` as historical only.
- Use `uv` for dependency management and commands.
- Put importable application code in `src/policy_coherence_investigator/`; keep delivery interfaces thin.
- Keep deterministic work—parsing, clause IDs, metadata filtering, date/status checks, explicit precedence, exact cross-references, and provenance—outside LLM prompts.
- Put synthetic generation tooling in `tools/synthetic_data/`, sharing typed domain models from `src/` when useful.
- Put fast deterministic tests in `tests/`. Put paid, probabilistic, or trajectory-level evaluation in `evals/` and run it explicitly.
- Never expose an evaluation case's hidden oracle, expected outcome, or human resolution guide to the agent under test.
- Treat `data/generated/`, `evals/runs/`, `artifacts/`, and `local/` as reproducible or disposable outputs.
- Track source URLs, licences, and checksums under `data/sources/`.
- Do not call live model APIs from the deterministic test suite.
```

## Bootstrap order

### 1. Create the package and tooling shell

Create `pyproject.toml`, `.python-version`, `.gitignore`, `.env.example`, `AGENTS.md`, `README.md`, the `src/` package, `tests/`, `evals/`, and the documentation map. Run `uv sync`, an empty or smoke `pytest` suite, and Ruff.

### 2. Define typed corpus and result contracts

Implement policy document metadata, stable clause references, working scope, normalized obligations, findings, evidence needs, and final result categories before graph prompts. Add deterministic validation tests.

### 3. Build the first three neutral evaluation cases

Create paired corpora for a confirmed conflict, a resolved apparent conflict, and a coverage gap. Define the hidden oracles before tuning retrieval or prompts. Add the human presentation catalog separately.

### 4. Implement corpus loading and a lexical baseline

Validate manifests and paths, parse stable clause IDs, apply deterministic status/scope filters, and implement reproducible lexical ranking. Test decisive-clause retrieval and near-miss behavior offline.

### 5. Implement a fixed retrieve-and-compare baseline

Produce structured, cited results using one predetermined retrieval pass. This provides the comparison point required to show whether agentic investigation is worthwhile.

### 6. Add the bounded evidence-discovery loop

Persist scope assumptions, evidence needs, candidate findings, retrieval history, and budgets. Let the model choose consequential next evidence needs while deterministic code validates actions and enforces limits.

### 7. Add explicit eval runners and observability

Load the hidden oracle only after graph invocation, score the structured result and trajectory, emit LangSmith metadata, and keep paid runs outside `pytest`.

### 8. Add Studio and local browser interfaces

Expose the first cases in LangGraph Studio, adapt the read-only case explorer, and copy the project-summary editor if it remains useful.

### 9. Consider embedding retrieval and an autonomous comparator

Only after the corpus contracts and lexical baseline are stable, add embeddings or hybrid retrieval behind the existing interface. Add the capability-scoped autonomous graph when there is a specific comparison question to answer.

## What should not be copied blindly

- **Warranty domain enums and finding IDs:** replace them with policy-coherence concepts; do not rename them mechanically.
- **Evidence-release actions:** policy investigation needs retrieval intents and scope-resolution actions, not inspection reports or operating logs.
- **Causal-hypothesis ledger:** redesign it around obligations, applicability, conflicts, gaps, and scope assumptions.
- **Case-specific LangGraph entrypoints:** start with three neutral policy cases and expand only as needed.
- **Current lexical retrieval as the final RAG design:** retain it as a deterministic baseline, not as an unquestioned production choice.
- **Exact graph topology:** reuse the state and safety principles, while allowing evidence sufficiency to drive variable trajectories.
- **Current evaluator's limited prose checks:** it intentionally scores structured fields, not semantic writing quality. Preserve that initially, then add carefully justified semantic evaluation only if needed.
- **The current README's `uv run agentic-doc-poc` hello-world command:** the current `pyproject.toml` does not declare that console script. In the new project, keep documented commands synchronized with `[project.scripts]`.
- **A claim that Langfuse is already integrated:** it is not; the inherited observability stack is LangSmith.

## Bootstrap success criteria

The new repository has successfully copied the useful shape of this project when:

1. `uv sync`, `uv run pytest`, and `uv run ruff check .` succeed from a fresh checkout.
2. `.env.example` documents both direct model providers and optional LangSmith tracing without containing secrets.
3. One neutral case can run in LangGraph Studio without loading its oracle.
4. The local case explorer can display the corpus and human resolution guide without either entering an agent prompt.
5. Deterministic tests prove oracle isolation, path containment, metadata filtering, citation validity, routing, and budgets without network access.
6. A paid single-case runner invokes the model, loads the oracle only after graph completion, and reports structured retrieval and reasoning failures separately.
7. The same cases can compare a fixed retrieve-and-compare baseline with the bounded agentic investigator.
8. Generated outputs, local downloads, credentials, and Agent Server state remain untracked.

