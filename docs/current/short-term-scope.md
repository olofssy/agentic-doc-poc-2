# Short-term implementation scope

**Status:** Current implementation directive  
**Date:** 2026-08-16

## Objective

Build a bounded policy-coherence investigator for a controlled, synthetic policy
corpus. It accepts a natural-language question, gathers applicable clause-level
evidence through retrieval, and returns an evidence-cited review for a human
policy owner.

This document narrows near-term implementation work. It complements the
[project inception](project-inception.md), which remains the fuller product and
learning rationale.

## In scope

The first usable vertical slice must:

1. Accept a natural-language question about whether policies coherently govern a
   bounded topic.
2. Retrieve policy evidence through a RAG capability over a controlled corpus.
3. Run a budgeted, evidence-driven investigation loop. After each retrieval and
   analysis step, the investigator assesses whether material uncertainty remains
   and either concludes or requests targeted additional evidence.
4. Allow retrieved evidence to revise the working scope, a provisional finding,
   or the next retrieval need.
5. Return a structured review with:
   - a concise free-text summary;
   - a result category: `confirmed_conflict`,
     `apparent_conflict_resolved`, or
     `coverage_gap_or_insufficient_evidence`;
   - structured findings, scope assumptions, and unresolved questions; and
   - document and clause references supporting every material conclusion.

## Required agentic demonstration

The loop must be capable of both single-pass and multi-step trajectories.

- It may stop after one retrieval when the available evidence is sufficient.
- At least one evaluation case must require multiple search-and-analysis steps.
  A subsequent search must be motivated by a recorded material uncertainty—for
  example unresolved terminology, population-specific applicability, an
  exception, precedence, or a conflict hypothesis—and must be able to change the
  scope, finding, or conclusion.
- The loop must be bounded by an explicit retrieval budget. The initial target is
  no more than three retrieval iterations per investigation.

A fixed `question → search → analyse → done` workflow alone does not satisfy
this scope.

## Near-term boundaries

The first implementation is limited to synthetic Markdown policy corpora and
their deterministic metadata. It does not include:

- production document ingestion or PDF extraction;
- general policy search across unknown corpora;
- autonomous policy approval, legal advice, or compliance certification; or
- a claim that failed retrieval proves a corpus-wide absence.

## Implementation implications

Keep deterministic operations outside prompts: document and clause identity,
metadata validation and filtering, effective-date and supersession checks,
explicit authority and precedence rules, provenance, and citation validation.

The review prompt must apply an explicit obligation-and-applicability comparison
before assigning a result category. It must distinguish a genuine scope
separation from a conflicting permission or duty that applies to the same
population, and treat missing governing support for an in-scope population as a
coverage gap rather than a resolved outcome. Follow-up retrieval kinds are used
at most once per evidence target so reworded requests cannot consume the bounded
budget without pursuing a new evidence direction. A target comprises the
retrieval kind and a stable identifier for the exact missing evidence.

Use hidden evaluation oracles to verify structured outcomes and trajectories.
The oracle, expected result category, and human resolution guide must never be
available to the investigator under test.
