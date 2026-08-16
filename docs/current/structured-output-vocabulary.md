# Structured-output vocabulary

This project exposes a small public vocabulary for recurring policy-coherence
conclusions. Evaluation cases may use these identifiers, and the review prompt
supplies them to the model. They are therefore implementation contracts, not
hidden evaluator details.

Use a listed identifier only when its stated meaning is supported by the
retrieved evidence. A concise snake_case identifier remains valid for a
finding or scope distinction not covered below.

The investigator must record a listed scope identifier when its supported
coverage, inclusion, exclusion, or distinction materially affects the result.
These records are not limited to mutually exclusive scopes.

## Finding identifiers

- `incompatible_contractor_revocation_deadlines`: concurrently applicable
  policies prescribe incompatible contractor-access revocation deadlines.
- `ordinary_and_privileged_deadlines_have_distinct_scope`: ordinary and
  privileged account deadlines coexist because each governs a distinct,
  evidence-supported account scope.
- `contractor_offboarding_deadline_insufficiently_governed`: the retrieved
  evidence does not adequately govern a contractor offboarding deadline.

## Scope-distinction identifiers

- `contractors_are_workforce_identities`: contractors are within the stated
  workforce identity population for the cited policy context.
- `ordinary_accounts_vs_privileged_accounts`: the cited evidence distinguishes
  ordinary accounts from privileged accounts.
- `employee_and_contractor_coverage`: the cited evidence distinguishes or
  jointly governs employee and contractor coverage.
