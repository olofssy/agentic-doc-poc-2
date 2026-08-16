# Repository guidance

- Read `docs/README.md` before using project documentation as requirements.
- Treat `docs/current/` as current project context and `docs/archive/` as history.
- Use `uv` for dependency management and commands.
- Put importable application code in `src/policy_coherence_investigator/`.
- Keep deterministic work—parsing, clause IDs, metadata filtering, date/status
  checks, precedence, exact cross-references, and provenance—outside LLM prompts.
- Keep fast, deterministic tests in `tests/`; put paid or probabilistic evaluation
  in `evals/` and run it explicitly.
- Never expose an evaluation case's hidden oracle, expected outcome, or human
  resolution guide to the agent under test.
- Treat `data/generated/`, `evals/runs/`, `artifacts/`, and `local/` as generated
  or disposable outputs.
- Track source URLs, licences, and checksums under `data/sources/` when external
  material informs a corpus.
- Do not call live model APIs from the deterministic test suite.

## Current implementation focus

Until this focus is explicitly revised, prioritize the bounded policy-coherence
investigator described in `docs/current/short-term-scope.md`.

- Implement an evidence-driven RAG loop that can take multiple retrieval and
  analysis steps when material uncertainty remains.
- Return structured, clause-cited reviews; do not treat free-text output as the
  system's only result contract.
- Do not broaden the current work into production ingestion, general policy
  search, autonomous policy advice, or corpus-wide absence claims.

## Predecessor-project reference

`/Users/olofskogby/Hobby/agentic-doc-poc/` is the structural predecessor of this
project. Before introducing a substantial new seam—especially fixture loading,
hidden-oracle isolation, corpus access, retrieval, evaluation, workflow budgets,
or local interfaces—inspect the comparable predecessor implementation and tests
for reusable safety and observability patterns.

Use the predecessor for inspiration and comparison, not as an implementation
template. Keep this repository's current documentation authoritative, preserve
the policy-coherence domain model, and do not mechanically copy warranty-specific
models, fixed evidence-release behavior, prompts, actions, or outcomes.
