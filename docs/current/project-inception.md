# Policy coherence investigator — project inception

**Status:** Proposed new learning project  
**Date:** 2026-08-16  
**Working name:** Policy coherence investigator

## Purpose

Build a small, observable agentic RAG system that investigates whether a set of corporate policies coherently addresses a user question.

The system should retrieve the clauses that are applicable to the question, distinguish genuine contradictions from differences in scope or precedence, identify material coverage gaps, and produce an evidence-cited review for a human policy owner.

This is a learning project, but the use case should remain plausible in a commercial setting. Its central technical goal is to create honest pressure for both retrieval-augmented generation and agentic investigation rather than adding either capability decoratively to a fixed workflow.

## Why this project

The preceding warranty-investigation project provided a realistic document-heavy workflow, but its relevant dossier was usually known at the start. RAG became useful only after expanding the domain to manuals, service bulletins, and historical cases, which in turn demanded substantially more synthetic data and domain realism.

Policy coherence makes retrieval part of the core problem from the first useful version:

- Relevant evidence is distributed across policies, standards, procedures, definitions, and local addenda.
- Users and documents may use different terminology.
- Applicability depends on population, system, geography, effective date, authority, and exceptions.
- A retrieved clause may reveal a new distinction that changes the scope or motivates another search.
- Superseded or subordinate policies may appear relevant while changing the conclusion.
- Failure to retrieve a policy is not proof that no policy exists.

Policies are also comparatively economical to synthesize. Their realism comes primarily from clause content, scope, definitions, authority, effective dates, and version relationships rather than complex physical evidence or failure mechanisms.

## Product framing

The product is:

> A question-driven investigator that retrieves applicable policy clauses, distinguishes genuine contradictions from scope-specific differences, identifies coverage gaps, and produces a cited review for human policy owners.

The first version is not a general policy search engine and not a one-shot document comparison tool. It investigates a bounded question against a controlled corpus and exposes how its scope, evidence, and provisional findings change along the way.

Useful result categories are:

1. **Confirmed conflict** — concurrently applicable rules make incompatible demands.
2. **Apparent conflict resolved** — the clauses can coexist because of scope, definitions, precedence, or another supported distinction.
3. **Coverage gap or insufficient evidence** — an in-scope category is not adequately governed by the available corpus, or the evidence is too weak to decide.

The third category must be qualified carefully: retrieval failure alone cannot establish a corpus-wide absence.

## Initial policy domain

Start with the employee and contractor access lifecycle, particularly access revocation during offboarding.

Example review question:

> Do our policies coherently define when employee, contractor, and privileged access must be disabled after termination?

The initial corpus may contain:

- access-control policy;
- HR offboarding procedure;
- contractor-management policy;
- privileged-access standard;
- identity-management procedure;
- remote-work policy;
- emergency-access procedure;
- policy-governance or definitions document;
- local or subsidiary addendum; and
- realistic but weakly related distractors.

This domain provides clear comparison dimensions:

| Dimension | Examples |
| --- | --- |
| Population | Employee, contractor, vendor, administrator |
| Account or access type | Ordinary, privileged, shared service, physical, application |
| Trigger | Notice, termination decision, termination time, last working day |
| Deadline | Immediate, four hours, 24 hours, five business days |
| Responsible party | Manager, HR, service desk, IAM team |
| Exception | Investigation, legal hold, emergency account |
| Applicability | Geography, business unit, worker type, system class |
| Governance | Authority, effective date, version, supersession |

Keeping the first domain narrow makes findings and evaluation criteria more precise than a broad question such as whether all corporate policies are coherent.

## Why the system should be agentic

A pipeline that embeds documents, retrieves the top clauses, and asks a model to compare them is a useful RAG workflow, but it is not the intended experiment.

The investigator should maintain evolving investigation state and choose its next action based on the most consequential unresolved issue. Retrieved evidence may invalidate the initial interpretation, split the question into sub-scopes, resolve a provisional conflict, or expose a new gap.

The agentic behavior lies in deciding:

- which ambiguity materially affects the question;
- whether to expand, narrow, or branch the working scope;
- which missing evidence would best test a provisional finding;
- whether another retrieval is worth the remaining budget;
- when the evidence supports a conclusion;
- when to report qualified uncertainty; and
- when to ask a focused human question or escalate.

The following are not sufficient demonstrations of agenticity:

- always performing a fixed number of searches;
- always following every explicit cross-reference;
- using an LLM inside an otherwise predetermined graph; or
- letting the model search again without recording a reason or an evidence need.

Explicit cross-reference traversal is graph navigation and should be deterministic when the reference is known. The model should decide whether resolving the referenced subject is material to the investigation.

## Scope is evolving investigation state

The model should interpret the user's request initially, but scope resolution does not end there. The initial interpretation should be recorded as explicit assumptions rather than silently treated as fact.

For a question such as “Are our access-termination policies coherent?”, the initial scope might be:

- topic: access revocation after termination;
- population: all workers;
- systems: all corporate systems;
- geography: global;
- time: currently effective policies; and
- concern: deadlines, responsibilities, and exceptions.

Retrieval may reveal that “worker” excludes contractors, privileged accounts have a separate standard, a local addendum overrides the global rule, or “termination” has multiple policy meanings. Each discovery can revise the scope and the retrieval plan.

Some scope and applicability operations should remain deterministic, including effective-date filtering, explicit geography or business-unit metadata filters, known supersession relationships, and an encoded policy hierarchy.

## Iterative evidence discovery

The investigation loop should be driven by explicit evidence states and triggers rather than an unstructured instruction to search more.

Candidate triggers include:

1. **Unresolved terminology** — a retrieved clause introduces a term whose relation to the user's language is unclear.
2. **Scope-dependent apparent conflict** — incompatible wording is found, but the clauses' populations, systems, or triggers may differ.
3. **Exception or precedence uncertainty** — an exception, addendum, or authority rule may change which clause controls.
4. **Missing support for an in-scope category** — evidence exists for some relevant populations or account types but not others.
5. **Version or authority ambiguity** — contradictory clauses may not be concurrently valid or equally authoritative.
6. **Emerging conflict hypothesis** — a provisional finding, such as inconsistent ownership assignments, motivates a targeted query.

A useful investigation state may contain:

```text
question
working_scope
scope_assumptions
candidate_findings
evidence_ledger
unresolved_terms
unresolved_conflicts
open_questions
retrieval_history
remaining_budget
```

The evidence-sufficiency decision should choose among meaningful actions:

- retrieve a definition;
- retrieve a population- or system-specific policy;
- retrieve an applicable local addendum;
- retrieve governance, authority, or version information;
- test a specific conflict or gap hypothesis;
- stop with a supported conclusion;
- stop with a qualified coverage-gap finding; or
- ask a focused human question or escalate.

## Proposed investigation shape

```text
interpret initial scope
        |
        v
retrieve candidate clauses
        |
        v
normalize obligations and applicability
        |
        v
assess findings and evidence sufficiency
        |
        +----------------+--------------------+
        |                |                    |
        v                v                    v
 supported result   resolvable gap     material ambiguity
        |                |                    |
        v                v                    v
      report       plan next query     ask human/escalate
                         |
                         +----> retrieve again
```

The loop must be bounded by retrieval iterations, token or cost limits, and reviewer attention. A budget of up to three retrieval iterations is sufficient for the first experiment, provided cases require different numbers and kinds of actions.

## Example investigation trajectory

User question:

> Are our offboarding access policies coherent?

1. Initial retrieval finds an HR procedure requiring employee access to be disabled within 24 hours and an access-control policy requiring workforce access to be disabled immediately.
2. The investigator records a possible conflict but notices that “employee” and “workforce” may differ in scope.
3. A targeted definitions retrieval establishes that workforce includes employees and contractors and reveals a separate privileged-access standard.
4. The investigator revises the hypothesis and retrieves the privileged-access material to determine whether “immediate” was read without sufficient context.
5. The new evidence shows that immediate revocation applies only to privileged access, while ordinary employee access has a 24-hour deadline.
6. The final review resolves the apparent employee-policy conflict but reports contractor timing as unresolved if no applicable current clause was found.

This trajectory is valuable because retrieved evidence changes both the hypothesis and the next retrieval action.

## Division of responsibility

Keep deterministic work outside model prompts.

Deterministic code should handle:

- document and clause identifiers;
- parsing and metadata validation;
- current and superseded version filtering;
- effective-date comparisons;
- explicit metadata filters;
- exact cross-reference traversal;
- encoded authority hierarchy;
- citation existence and source-span validation; and
- provenance and retrieval-history recording.

The model should handle:

- interpreting the user's question and proposing initial scope;
- mapping ambiguous or inconsistent terminology;
- extracting and comparing obligations in context;
- forming conflict and coverage hypotheses;
- recognizing when a discovered distinction is material;
- choosing the next evidence need;
- revising findings when evidence contradicts them; and
- deciding when uncertainty requires qualification or escalation.

## Initial corpus and synthetic cases

Begin with 10–15 short Markdown documents:

- approximately five directly relevant policies or procedures;
- two governance or definition documents;
- one local addendum; and
- several realistic distractors.

Every clause should have a stable identifier and metadata sufficient to evaluate status, scope, authority, and provenance. The corpus should contain enough terminology mismatch and scoped applicability to require retrieval without depending on noisy PDF extraction in the first slice.

Create at least three paired evaluation cases around the same review question:

### Confirmed conflict

An HR procedure permits contractor access for five days after termination, while a concurrently applicable access standard requires revocation within 24 hours for all workforce identities.

### Apparent conflict resolved

One-hour revocation applies only to privileged accounts; a 24-hour rule applies to ordinary employee accounts. The investigator should not report a contradiction.

### Coverage gap or insufficient evidence

Current policies govern employees but do not establish a contractor offboarding deadline. The investigator should search for contractor-specific material and, if still unresolved, report a qualified gap rather than claim that no policy exists.

Additional cases can later cover shared service accounts, local overrides, inconsistent responsibility assignments, ambiguous authority, and silently superseded policies.

## Evaluation approach

Define hidden case oracles before implementing the investigator. An oracle should identify decisive clauses, acceptable conclusions, material scope distinctions, required or acceptable follow-up retrievals, and unsafe unsupported claims. It must never be exposed to the agent under test.

Evaluate retrieval and reasoning separately so that failures can be attributed correctly.

Suggested metrics include:

- recall of oracle-designated decisive clauses;
- citation precision and source-span validity;
- superseded-document citation rate;
- confirmed-conflict precision and recall;
- false-conflict rate caused by ignored scope;
- coverage-gap detection;
- correct next-retrieval selection;
- hypothesis-revision behavior;
- escalation accuracy;
- retrieval iterations, latency, token use, and cost; and
- stability across repeated runs.

Trajectory evaluation should verify that actions were motivated by recorded unresolved issues, not merely that the final prose happened to match the oracle.

## Suggested delivery order

### 1. Corpus model and hidden evaluation oracle

Define typed models for documents, clauses, metadata, scope, obligations, evidence, findings, and permitted actions. Create the first paired corpus variants and their hidden oracles.

### 2. Thin retrieval-to-review slice

Index clause-level Markdown content, retrieve candidate clauses for one question, and produce a cited review. Establish deterministic provenance and metadata filtering before adding a loop.

### 3. Scope and evidence ledger

Make assumptions, normalized obligations, candidate findings, unresolved issues, and retrieval history visible in persisted state.

### 4. Bounded investigation loop

Add evidence-sufficiency assessment, targeted query planning, variable-length retrieval, explicit budgets, and stop or escalation conditions.

### 5. Comparative evaluation

Compare the agentic investigator with a fixed retrieve-and-compare baseline. Separate retrieval failures, reasoning failures, and trajectory inefficiency.

### 6. Human review and corpus realism

Add focused clarification or escalation, checkpointed resume behavior, and a small reviewer interface. Introduce noisier documents or PDFs only after the evidence loop is stable.

## Non-goals for the first version

- Reviewing every corporate policy domain
- Proving corpus-wide absence from failed retrieval
- Autonomous policy approval, legal advice, or compliance certification
- Replacing policy owners, HR, security, compliance, or legal review
- Building a production document-management system
- Solving PDF extraction or multimodal ingestion before the reasoning loop works
- Following every document reference indiscriminately
- Multi-agent role-play without real information or authority boundaries
- An unbounded autonomous search

## Success criteria

The first version is successful if it demonstrates, with repeatable evaluation, that:

1. RAG is necessary to discover the decisive clauses rather than merely reduce prompt size.
2. Retrieved evidence can revise scope, invalidate a provisional finding, and change the next retrieval action.
3. The investigator distinguishes true conflicts from scope-specific differences.
4. It reports uncertainty and possible coverage gaps without treating retrieval failure as proof of absence.
5. Every material conclusion is supported by valid clause-level citations.
6. Its variable, evidence-driven trajectory provides measurable value over a fixed retrieve-and-compare workflow.

## Open design decisions

The next project should decide, without blocking initial corpus work:

- the embedding and retrieval implementation;
- whether normalized obligations are produced at ingestion time, investigation time, or both;
- how policy authority and overrides are represented when precedence is not fully explicit;
- the exact evidence-sufficiency and stopping contract;
- the human clarification and escalation interface; and
- which fixed baseline best tests whether agentic behavior adds value.

