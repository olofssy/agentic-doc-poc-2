# Learning notes

## Tool freedom degrees

An LLM can recommend an action without being allowed to execute it. In this project, the
initial assessment produces a structured recommendation such as
`request_inspection_report`; deterministic graph code validates that recommendation before
the evidence environment releases anything.

This gives the model limited decision freedom—choosing the next useful evidence—while the
application keeps execution authority. A fully tool-calling agent would let the model invoke
one of its bound tools, usually with model-chosen arguments, and then decide whether to call
more tools. That is useful when evidence paths genuinely vary, but requires stronger controls
for permissions, arguments, repeated calls, budgets, and failures.

The bounded approach is intentional for the first loop. It isolates whether the model chose a
useful next action from whether the system safely revealed only permitted evidence. The same
boundary remains valuable when a future action can affect a business system rather than merely
read a synthetic inspection report.

## Workflow-to-agentic spectrum: two separate axes

"Agentic" and "unconstrained tool freedom" get talked about as one spectrum, but they're
separable, and the policy-coherence investigator's bounded architecture is the proof.

**Axis 1 — decision quality.** Does the model choose its next move from evolving state, revise
a plan on new evidence, and stop or escalate on its own judgment, rather than a fixed number of
steps happening regardless of what was found? This is what makes something agentic. A graph can
be entirely finite and static and still be agentic by this test.

**Axis 2 — action-surface breadth.** How many distinct action kinds exist, how varied are they,
how free are their arguments, can several be combined or chained per turn, and what authority do
they carry? This is what "broad tool freedom" actually varies. It is orthogonal to axis 1: a
broad tool-calling agent can still be entirely scripted (always call the same tool in the same
order), and a narrow, single-field decision can still be genuinely agentic.

The bounded workflow (`bounded_investigation.py`) demonstrates the split concretely. Its only
real branch point each turn is one optional field, `next_evidence_need`. Its topology reduces to
exactly two shapes: `initial_review -> finish`, or `initial_review -> (loop: retrieve ->
reassess_review) -> finish`. That already satisfies axis 1 in full: the model decides whether the
remaining evidence budget is worth spending, and can always choose to stop (that choice is never
overridden), though its choice to continue can be vetoed by deterministic guardrails (budget
exhausted, a repeated `(kind, target)` pair, or a retrieval that returned nothing new).

Axis 2, though, is much narrower than the six `EvidenceNeedKind` values suggest. Only
`ask_human` is actually routed differently; the other five (`retrieve_definition`,
`retrieve_population_policy`, `retrieve_local_addendum`, `retrieve_governance`, `test_finding`)
all fall through to the same lexical retrieval call. So there are really only three live
outcomes per turn (retrieve again, escalate, or conclude), and only one real "action"
(retrieve). `test_finding` is a label, not yet a distinct mechanism.

## Tool invocation mode: not an agentic-ness lever, but a breadth lever

Follow-up question worth recording: is the *mechanism* by which the model expresses its decision
(a structured-output field the graph inspects, vs. a native tool call the model emits) itself a
useful differentiator on the workflow↔agentic axis?

No — it sits on axis 2, not axis 1. The bounded workflow is proof that axis 1 doesn't need tool
calls at all: a plain Pydantic field, deterministically routed, is already a genuinely
state-driven decision loop. Conversely, a tool-calling agent that always calls the same tool in
the same sequence is not more agentic for having done so through a `tool_calls` array instead of
a field. What invocation mode *does* change is how much axis-2 breadth is easy to reach: native
tool-calling generally allows more than one action per turn, a registry that can grow without a
new hand-written enum value, and freer model-chosen arguments than a schema fixed at
design time.

Concrete options surveyed, roughly smallest to largest step away from the current design:

1. Keep structured output, but replace the single optional field with a typed list of actions
   (a Pydantic discriminated union), so more than one thing can be requested per turn.
2. Give each `EvidenceNeedKind` its own argument shape instead of sharing `target`/`query`, so
   `test_finding` becomes an actual distinct action rather than a relabeled retrieval.
3. Real tool-calling within LangGraph (`model.bind_tools([...])` plus a `ToolNode`, or the
   prebuilt `create_react_agent`) — LangGraph supports this natively; the current design chose
   structured output deliberately, not because the framework required it.
4. Tool-calling without LangGraph, driving the provider's native tool-use loop directly — trades
   away the state persistence and graph-canvas visualization LangGraph currently provides.
5. Free-text ReAct parsing (`Thought:/Action:/Observation:`) — mentioned only to rule out; it
   gives up the schema validation this project's design otherwise leans on entirely.

The implication for a third architecture: reach for tool-calling to deliberately test axis 2
(does a broader, more composable action surface change outcomes), not to chase "more agentic" —
axis 1 is already satisfied. Options 1 and 2 are worth trying before 3, since they change only
the action vocabulary while holding the invocation mechanism constant, keeping the comparison
attributable to one variable at a time — the same principle behind harmonizing `working_scope`
and the retriever between the baseline and bounded architectures.

## Narrow tools vs. flexible broad tools

Axis 2 (action-surface breadth) has a further split worth naming precisely: **closed,
pre-validated actions** — a fixed argument shape checked at the call boundary, like a
`document_id` or a `(kind, target)` pair — versus **general-purpose execution primitives**, whose
argument is unconstrained text (a shell command, a raw SQL query) that can do an effectively
unbounded number of things, freely composed (`grep | sed | sort`, arbitrary joins). Every narrow
tool discussed above (`lookup_document_metadata`, `check_precedence`, ...) is the first kind. A
bash terminal or a read-only SQL runner is squarely the second, and "flexible broad tools" is a
fair name for it — it matches the predecessor docs' own "broad tool-freedom agent... may accept
open-ended string arguments and compose tools in unforeseen ways."

The appeal is real: a query primitive expresses filter/join combinations nobody predicted at
design time. `filter_applicable_clauses` only knows about date and geography today; "clauses
mentioning both X and Y, excluding ones already cited" needs a bespoke tool otherwise.

The blocker is concrete, not generic caution: this project's entire evaluation methodology rests
on one invariant — `load_oracle` is never given to the agent under test. `evals/cases/<id>/`
holds `oracle.yaml` in the same directory as `case.yaml`, on disk. A bash tool with filesystem
access, or a SQL connection that can also reach an oracle table, doesn't weaken that boundary — it
removes it, and "read-only" doesn't help, since the oracle is itself readable data. Schema
validation, the mechanism protecting every other tool in this codebase, doesn't constrain an
arbitrary shell string or SQL query; that needs a different control layer entirely (OS-level
sandboxing, a DB connection scoped away from oracle tables, output-size and time limits), which
nothing here currently implements.

A middle ground: a **constrained query DSL** — `query_clauses(filters: list[Filter])` where
`Filter` is a validated Pydantic model (`field`/`operator`/`value` drawn from an allowlist)
instead of a raw string. It gets most of the ad hoc composability without any raw string ever
reaching an interpreter, and stays scoped to the already-permission-filtered clause set. Sketched
as a future idea in
[the retrieval evolution plan](../current/retrieval-evolution-plan.md#future-idea-constrained-query-dsl-for-evidence-requests-not-scheduled).
