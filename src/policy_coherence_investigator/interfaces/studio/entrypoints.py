"""Server-only compiled graph entry points declared in ``langgraph.json``.

The Agent Server loads this module after reading the local ``.env`` named in its configuration.
Keeping these provider-dependent objects outside ``studio.graphs`` preserves credential-free
imports for the application's deterministic test suite.
"""

from policy_coherence_investigator.interfaces.studio.graphs import build_studio_case_graph

access_offboarding_a = build_studio_case_graph("access-offboarding-a")
access_offboarding_b = build_studio_case_graph("access-offboarding-b")
access_offboarding_c = build_studio_case_graph("access-offboarding-c")
access_offboarding_d = build_studio_case_graph("access-offboarding-d")
