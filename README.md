# Policy coherence investigator

An observable agentic RAG learning project that investigates whether a controlled
corpus of corporate policies coherently answers a policy-owner question.

The initial domain is employee and contractor access revocation during offboarding.
The investigator will retrieve applicable clauses, account for scope and policy
precedence, and provide evidence-cited findings for human review.

## Project status

The repository currently contains the tooling and documentation shell. Domain
models, synthetic evaluation cases, retrieval, and workflows will be introduced
incrementally.

## Local development

This project uses Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run ruff check .
```

Copy `.env.example` to `.env` and set a provider key only when running an
explicit live evaluation. The deterministic test suite must not call model APIs.

## Documentation

Read [docs/README.md](docs/README.md) for the documentation authority map.
