# Live evaluation runners

These commands invoke a configured model provider and can consume tokens. They
are intentionally separate from `pytest`.

Run one case with the bounded investigator:

```bash
uv run python -m evals.run_case access-offboarding-b --provider openai
```

Run the fixed retrieve-and-compare baseline against the same case:

```bash
uv run python -m evals.run_case access-offboarding-b --architecture baseline --provider openai
```

Run every case sequentially:

```bash
uv run python -m evals.run_all --provider openai
```

The runner loads the hidden oracle only after workflow completion. Output is
deliberately compact: case ID, pass/fail status, architecture, result category,
retrieval count, termination reason, a shortened summary, and actionable issues.
It never prints raw prompts, oracle contents, or full model JSON by default.
