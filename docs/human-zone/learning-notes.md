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
