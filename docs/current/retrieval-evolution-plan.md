# Retrieval evolution plan

**Status:** Proposed next implementation plan
**Date:** 2026-08-17

## Purpose

The current investigator is retrieval-augmented: it supplies policy clauses to
the model and requires clause citations in return. Its retriever is deliberately
a deterministic lexical TF/IDF-like baseline, not an embedding or vector
retriever.

The `access-lifecycle-large` benchmark now gives semantic retrieval a concrete,
measurable problem. Its agency-handover scenario uses user language such as
“agency worker” and “workspace credential”, while decisive enterprise policy
uses “employment-affiliated security principal” and “verified separation
event”. The lexical baseline retrieves the direct contractor policy but misses
some terminology bridges and governing obligations at its configured top-k.

This document defines the next retrieval steps. The existing small cases remain
fast end-to-end regressions; the large corpus measures retrieval quality before
and after each change.

## Current retrieval boundary

```text
question or targeted follow-up query
        |
        v
deterministic applicability filter
  - status and effective date
  - geography
        |
        v
lexical clause ranking
        |
        v
retrieved clause references and content
        |
        v
bounded LLM investigation and citation validation
```

The applicability filter, clause identity, provenance, retrieval budget, and
citation validation are deterministic controls. They must remain deterministic
as vector and hybrid retrieval are introduced.

## Step 1 — vector retrieval baseline

### Objective

Add semantic, clause-level retrieval behind the existing retrieval boundary.
The result should be a comparable vector baseline, not a production vector
database project.

### Intended shape

```text
corpus Markdown
  -> stable clause parser
  -> searchable clause rendering
  -> embedding client
  -> vectors keyed by document_id and clause_id
  -> local vector index

question or follow-up query
  -> deterministic applicability filter
  -> query embedding
  -> cosine-similarity ranking over eligible clause vectors
  -> existing investigation workflow
```

Each indexed record should contain:

- the stable `document_id` and `clause_id`;
- a content hash and embedding-model identifier for cache invalidation;
- the rendered text used for embedding, normally document title, document type,
  clause heading, and clause body; and
- metadata needed to map the vector back to the already validated corpus.

For the current corpus sizes, an in-memory cosine-similarity index is sufficient.
It is simpler to inspect and test than an approximate-nearest-neighbour service.
Generated vectors and local caches belong under an ignored generated/local path;
they are not source fixtures.

### Interface and ownership

Introduce a retrieval protocol so lexical and vector implementations receive the
same validated query, applicable clause candidates, and limit, and return the
same ranked-clause contract. The workflow must not know whether a result came
from keyword matching or vector similarity.

The implementation should include:

1. a clause renderer used consistently for indexing and diagnostics;
2. an embedding-client protocol, with a deterministic fake for offline tests;
3. a real configured embedding client selected only in explicit, paid commands;
4. a local vector-index builder/cache; and
5. a vector retriever that ranks only already-applicable clauses.

The provider and model choice remain configurable. An API embedding client is a
pragmatic initial experiment, but the client protocol keeps a local model or a
different provider possible later. Offline tests must not create embeddings over
the network.

### Required evaluation

Run vector retrieval against the same scenarios in
`evals/retrieval_benchmarks/access-lifecycle-large.yaml`. Report, at minimum:

- decisive-clause recall and rank at each scenario's top-k;
- the retrieved clause IDs, including excluded/superseded safeguards;
- index build time, query latency, embedding model identifier, and estimated
  embedding/query cost where available; and
- comparison with the existing lexical baseline.

The vector baseline succeeds as an implementation step when it is reproducible,
preserves deterministic filtering and provenance, and produces a transparent
comparison. It does not need to outperform lexical retrieval on every query.

### Relation to production RAG

After this step, the system is a small but production-shaped semantic RAG
prototype: it has stable chunks, embeddings, metadata-aware retrieval,
provenance, citations, evaluations, and a user-facing command. It is not a
production RAG platform. It still lacks durable ingestion and re-indexing jobs,
document-management integration, access-control propagation, tenant isolation,
operational monitoring, high-availability behaviour, and real-document parsing.

## Step 2 — hybrid retrieval comparison

Combine lexical and vector ranks behind the same retrieval protocol, initially
with a transparent fusion method such as reciprocal-rank fusion. Keep both raw
component ranks and the fused rank observable in the retrieval ledger or
benchmark report.

Hybrid retrieval is the likely target for this domain:

- lexical ranking is strong for exact policy terms, dates, names, and clause IDs;
- vector ranking helps with user-policy terminology mismatches; and
- deterministic filters still constrain both result sets before fusion.

Do not add a model-based reranker until lexical, vector, and hybrid retrieval
have been compared. A reranker adds cost and another probabilistic component;
the benchmark should establish whether fusion alone is enough first.

## Step 3 — repeated end-to-end evaluation

Add an explicit paid trial runner for repeated small-case evaluations. It should
run a selected provider/model and architecture a configurable number of times,
write sanitized run records under ignored `evals/runs/`, and report:

- pass rate by case and overall;
- category, finding, scope, citation, and trajectory failure frequencies;
- retrieval-count and termination-reason distributions; and
- model/provider, latency, token or cost data where available.

This separates retrieval quality from model and trajectory stability. Do not run
these paid trials from the deterministic test suite.

## Step 4 — promote the large corpus to end-to-end agentic cases

Once a retrieval strategy has demonstrated acceptable benchmark behaviour, add
neutral user-question manifests and hidden end-to-end oracles over the large
corpus. Start with a small number of cases that require different behaviours:

1. a semantic terminology bridge that reveals a genuine conflict;
2. a local-addendum and governance trajectory that resolves an apparent
   conflict; and
3. a qualified coverage-gap trajectory.

Each case must preserve the existing separation between agent-visible question
and corpus data, evaluator-only expectations, and optional human presentation
material. This step should follow retrieval comparison; otherwise an end-to-end
failure would conflate retriever weakness with reasoning or trajectory weakness.

## Decision rule

Do not expand into production ingestion, general policy search, or autonomous
policy advice during these steps. Choose the next retriever based on benchmark
evidence, then use repeated end-to-end trials to decide whether further prompt,
workflow, or corpus changes are warranted.
