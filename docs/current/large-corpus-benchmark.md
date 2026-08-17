# Large-corpus retrieval benchmark

## Purpose

`access-lifecycle-large` is a controlled retrieval-stress corpus for the next
retrieval phase. It complements, rather than replaces, the three small
offboarding cases. The small cases remain fast end-to-end regressions; this
corpus measures whether a retrieval strategy can find decisive evidence among
many plausible but irrelevant clauses.

## Design constraints

- 24 Markdown policy documents with 96 stable clause references.
- Clause-level retrieval remains the unit supplied to the investigator.
- All queries use a global, currently effective review context unless a scenario
  explicitly tests local applicability.
- Each benchmark scenario identifies its decisive clause set outside the agent's
  input. The direct investigation CLI never loads these expectations.
- Documents are purposeful: decisive evidence, terminology bridges, authority
  rules, metadata traps, or near-miss distractors. They are not filler text.

## Retrieval pressure

The first scenario deliberately uses user language such as “agency worker” and
“workspace credential”, while its enterprise requirement uses “employment-
affiliated security principal” and “verified separation event”. A lexical
baseline may retrieve the contractor-specific permission while missing the
enterprise deadline or terminology bridge. That is intentional pressure for a
semantic or hybrid retrieval strategy.

The corpus also contains a superseded enterprise policy, Swedish and Nordic
addenda, physical-access and device-return near misses, and emergency-account
exceptions. Deterministic status, geography, and date filtering must remain in
front of any lexical, vector, or hybrid ranking strategy.

## Evaluation sequence

1. Record lexical baseline recall and rank for every decisive clause.
2. Add vector retrieval behind the same clause-level retrieval interface.
3. Add reciprocal-rank fusion or another documented hybrid strategy.
4. Compare retrieval recall, end-to-end evaluation outcome, retrieval iterations,
   latency, and cost. Do not claim an embedding improvement without this
   comparison.
