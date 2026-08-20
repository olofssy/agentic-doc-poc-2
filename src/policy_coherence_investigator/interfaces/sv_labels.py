"""Swedish display labels for stable English snake_case identifiers.

The investigator's structured-output vocabulary (finding categories, evidence-need
kinds, and the finding/scope-distinction IDs in ``investigation.vocabulary``) stays
English and stable so it keeps matching oracle fixtures and model output. This map
is UI-only: it lets a human-facing local interface show those same IDs in Swedish
without touching the IDs themselves. Unmapped IDs fall back to a naive
underscore-to-space humanisation in ``humanize_sv``.
"""

_LABELS_SV: dict[str, str] = {
    # investigation.models.FindingCategory
    "confirmed_conflict": "Bekräftad konflikt",
    "apparent_conflict_resolved": "Skenbar konflikt löst",
    "coverage_gap_or_insufficient_evidence": "Täckningslucka eller otillräckligt underlag",
    # investigation.models.EvidenceNeedKind
    "retrieve_definition": "Hämta definition",
    "retrieve_population_policy": "Hämta populationspolicy",
    "retrieve_local_addendum": "Hämta lokalt tillägg",
    "retrieve_governance": "Hämta styrningsunderlag",
    "test_finding": "Testfynd",
    # investigation.vocabulary.FINDING_ID_DESCRIPTIONS
    "incompatible_contractor_revocation_deadlines": (
        "Oförenliga tidsgränser för inaktivering av konsultåtkomst"
    ),
    "ordinary_and_privileged_deadlines_have_distinct_scope": (
        "Ordinära och privilegierade tidsgränser har olika omfång"
    ),
    "contractor_offboarding_deadline_insufficiently_governed": (
        "Tidsgränsen för konsultavslut är otillräckligt reglerad"
    ),
    # investigation.vocabulary.SCOPE_DISTINCTION_ID_DESCRIPTIONS
    "contractors_are_workforce_identities": "Konsulter räknas som personalidentiteter",
    "ordinary_accounts_vs_privileged_accounts": (
        "Ordinära konton skiljs från privilegierade konton"
    ),
    "employee_and_contractor_coverage": "Täckning för medarbetare och konsulter",
    # oracle-specific one-off IDs (evals/cases/*/oracle.yaml)
    "contractor_coverage_confirmed": "Konsulttäckning bekräftad",
    "incompatible_employee_revocation_deadlines": (
        "Oförenliga tidsgränser för inaktivering av personalåtkomst"
    ),
    "no_contractor_policy_exists": "Ingen konsultpolicy finns",
}


def humanize_sv(value: object) -> str:
    """Render a stable snake_case identifier as a Swedish UI label.

    Falls back to naive underscore-to-space humanisation for any identifier not
    yet added to ``_LABELS_SV`` (for example a new oracle-specific finding ID),
    so an unmapped ID degrades to readable English rather than raising.
    """

    text = str(value)
    return _LABELS_SV.get(text, text.replace("_", " ").capitalize())
