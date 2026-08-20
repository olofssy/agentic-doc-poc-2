
Från SESSION (Codex): 01a00529-38cd-7602-8c04-7fd3f6605a0b - pass1: Plan next graph behavior
Tema: Vad går gränsen mellan loop/cycle graph och "Broad tool-freedom agent"

GRAPH MED MÅNGA ACTIONS:
With 10–20 actions, a good implementation would normally use a generic action dispatcher plus a typed action registry—not 20×20×20 hand-written combinations. The model selects an action from the allowed set; deterministic code validates permissions, arguments, availability, budgets, and result shape; then the loop returns to reassessment.
That is already an agentic system, even though the graph itself is finite and static.

“Broad tool freedom” differs mostly in authority and control surface, not in whether there is a loop. In a broad tool-calling agent, the model may directly emit tool calls, choose arguments, call tools repeatedly, and decide when to stop. In the safer bounded version, the model may still select among 20 actions, but deterministic policy mediates every execution.

Evolution: från loop-graph till open
one permitted action, one loop
→ several typed actions, short bounded loop
→ action registry plus evidence ledger and stop/escalate policy
→ perhaps variable-length supervised investigation

===

The meaningful dimensions are:
How many actions are available, and how varied are they?
Can the model choose the next action based on evolving state?
Can it use action results to revise its plan?
Can it stop or escalate based on its current uncertainty?
How constrained are arguments, permissions, costs, and step budgets?
What external authority do the actions carry?


A “broad tool-freedom” agent simply tends to have a larger, more flexible, higher-authority action surface—perhaps search, databases, messaging, code execution, ticketing, document retrieval, and analysis tools. It may accept open-ended string arguments and compose tools in unforeseen ways. But it can still be bounded and safe; it is not inherently unrestricted.

===

For this project, the natural next version can be agentic without becoming broad:
finite typed action registry
+ model-selected action and arguments
+ bounded reassessment loop
+ evidence ledger
+ deterministic authorization and budgets
+ explicit stop / escalate action

