# Policy coherence investigator

An observable agentic RAG learning project that investigates whether a controlled
corpus of corporate policies coherently answers a policy-owner question.

The initial domain is employee and contractor access revocation during offboarding.
The investigator will retrieve applicable clauses, account for scope and policy
precedence, and provide evidence-cited findings for human review.

## Project status

The first bounded vertical slice is implemented: synthetic corpora, clause-level
retrieval, structured policy-coherence reviews, and explicit paid evaluation
runners. The next steps focus on improving reliability and usability within the
same controlled-domain boundary.

## Local development

This project uses Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run ruff check .
```

Copy `.env.example` to `.env` and set a provider key only when running an
explicit live evaluation. The deterministic test suite must not call model APIs.

## Investigate a policy question

Run an oracle-free bounded investigation against a controlled corpus:

```bash
uv run policy-coherence-investigator \
  --question "Do contractor offboarding policies conflict?" \
  --corpus evals/corpora/access-offboarding-a \
  --as-of 2026-08-16 \
  --geography global \
  --population employee \
  --population contractor \
  --access-type ordinary \
  --access-type privileged \
  --provider openai
```

It prints a JSON response containing the cited structured result and concise
investigation metadata. Use `--format text` for a compact human-readable view.
This command can consume tokens and never loads an evaluation oracle.

## Browse the evaluation cases

Run the human-only local explorer with:

```bash
uv run policy-coherence-investigator-cases
```

Open `http://127.0.0.1:8766`. It shows the synthetic corpus, collapsed by
default, alongside clearly marked demo evaluation notes. It does not run a
model or evaluation trajectory.

## Documentation

Read [docs/README.md](docs/README.md) for the documentation authority map.
