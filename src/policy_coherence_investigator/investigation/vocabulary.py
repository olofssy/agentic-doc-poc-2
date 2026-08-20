"""Public stable identifiers and meanings for recurring review concepts."""

FINDING_ID_DESCRIPTIONS = {
    "incompatible_contractor_revocation_deadlines": (
        "Concurrently applicable policies prescribe incompatible contractor-access "
        "revocation deadlines."
    ),
    "ordinary_and_privileged_deadlines_have_distinct_scope": (
        "Ordinary and privileged account deadlines coexist because each governs a "
        "distinct, evidence-supported account scope."
    ),
    "contractor_offboarding_deadline_insufficiently_governed": (
        "The retrieved evidence does not adequately govern a contractor offboarding deadline."
    ),
    "incompatible_partner_assignee_revocation_deadlines": (
        "Concurrently applicable policies prescribe incompatible partner-assignee access "
        "revocation deadlines."
    ),
}

SCOPE_DISTINCTION_ID_DESCRIPTIONS = {
    "contractors_are_workforce_identities": (
        "Contractors are within the stated workforce-identity population for the cited "
        "policy context."
    ),
    "ordinary_accounts_vs_privileged_accounts": (
        "The cited evidence distinguishes ordinary accounts from privileged accounts."
    ),
    "employee_and_contractor_coverage": (
        "The cited evidence distinguishes or jointly governs employee and contractor coverage."
    ),
    "partner_assignees_are_workforce_identities": (
        "Partner assignees are within the stated workforce-identity population for the cited "
        "policy context."
    ),
}

FINDING_ID_CATALOG = tuple(FINDING_ID_DESCRIPTIONS)
SCOPE_DISTINCTION_ID_CATALOG = tuple(SCOPE_DISTINCTION_ID_DESCRIPTIONS)
