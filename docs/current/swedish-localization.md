# Swedish localization

This project is being ported to Swedish so a Swedish audience can read the
corpus, case questions, and demo interfaces without a translation step. This
document is the authority for what gets translated, what stays English, and
the terminology to use consistently across corpora, case fixtures, and
interfaces.

## What stays English

The investigator's structured-output vocabulary must stay English and
stable, independent of corpus language:

- `FindingCategory` and `EvidenceNeedKind` values (`confirmed_conflict`,
  `retrieve_definition`, and so on).
- The finding and scope-distinction identifiers in
  [structured-output-vocabulary.md](structured-output-vocabulary.md).
- `document_id` and `clause_id` values (e.g. `access_control_policy_v4`,
  `ACP-4.2.1`). The clause heading pattern
  (`## <CLAUSE-ID> — <heading>`) only constrains the ID; the heading text
  itself is translated.
- The system prompt in
  [`investigation/prompts.py`](../../src/policy_coherence_investigator/investigation/prompts.py)
  and its decision rules. These are instructions to the model, not content a
  Swedish reader needs to parse, and translating them risks subtly shifting
  carefully tuned wording for no reader benefit.
- `document_type` and `authority_level` values in each corpus's
  `corpus.yaml` (`policy`, `procedure`, `corporate_policy`, `governance`,
  and so on), and `WorkingScope.populations`/`access_types` values
  (`employee`, `contractor`, `ordinary`, `privileged`). Both flow directly
  into the model prompt — `authority_level` is rendered into every
  `<clause ...>` tag in `prompts.py`, and scope values are serialized into
  the `<working_scope>` JSON block — so they are model-facing contract
  values, not pure UI text, even though they also happen to render as UI
  badges and form labels.

These IDs are matched literally by `evaluation.py` against model output and
by oracle fixtures, so translating them would break scoring without
improving anything for a human reader.

## What gets translated

- Corpus documents: every policy Markdown file's title, clause headings, and
  clause body text, plus the `title` field in each corpus's `corpus.yaml`.
- Case questions: the `question` field in each `evals/cases/*/case.yaml`.
- Presentation material: `evals/presentation/cases.yaml` (display names,
  summaries, resolution guides, document/clause role labels).
- Interface chrome: hardcoded strings in `interfaces/*.py` (headings, badge
  labels, notices, CLI help text).

Human-readable labels for every English identifier listed above (finding
categories, evidence-need kinds, finding/scope-distinction IDs, oracle-specific
one-off IDs, `document_type`/`authority_level` values, scope values, and
bounded-investigation termination reasons) are translated separately in
[`interfaces/sv_labels.py`](../../src/policy_coherence_investigator/interfaces/sv_labels.py)
via `humanize_sv()`, which maps each stable ID to a Swedish label for display
only. The ID itself is never changed — e.g. a population checkbox keeps
`value="contractor"` for form submission while showing the label "Konsult".
Unmapped IDs fall back to naive underscore-to-space humanization rather than
raising, so a newly added ID (for example a novel finding ID the model
invents) degrades to readable English until its label is added.

## Terminology

Consistent word choices across corpora, case fixtures, and interfaces:

| Swedish | English | Usage |
| --- | --- | --- |
| Policy | Policy | The overall document or rule set. Used as-is (a standard loanword in Swedish corporate/regulatory writing); not translated to "Riktlinje", which is reserved for non-binding guidance (see below). Keeps a 1:1 match with this project's own `document_type: policy`. |
| Bestämmelse | Clause / Provision | The clause's substantive text — the specific rule or requirement. Preferred over "klausul", which in Swedish leans toward contract/insurance language (sekretessklausul, force majeure-klausul) rather than regulatory provisions. |
| Punkt | Section / Clause reference | The numbered reference itself (e.g. "punkt FAP-6.1") when prose needs to point at a clause by ID. Not yet used in any shipped translation — clause IDs currently render directly with their heading rather than being referenced in framing prose — but this is the word to reach for when that need comes up. |
| Riktlinje | Policy statement / Rule (non-binding) | Reserved for content that reads as a recommendation or principle rather than an absolute requirement (e.g. "bör" instead of "ska" in clause text). Not a document-level synonym for "Policy". |
| personalidentitet | workforce identity | |
| medarbetare | employee | |
| konsult | contractor | |
| avslut / avslutstidpunkt | termination / termination time | |
| inaktivera | disable | |
| privilegierad åtkomst | privileged access | |
| tidsgräns | deadline | |
| granskning(sfråga/skontext) | review (question/context) | |
| hämta / hämtningsmål | retrieve / retrieval target | |
| omfång | scope | |
| rutin | procedure | |
| styrning | governance | |
| täckning(skontroll/slucka) | coverage (check/gap) | |
| avslutsorsak | termination reason | |

## Status

Tracks which corpora and interfaces have been ported. Update this table as
phases land.

| Area | Status |
| --- | --- |
| Lexical/embedding tokenizer (å/ä/ö) | Done |
| Corpus `access-offboarding-a`, `-b`, `-c` | Done |
| Case questions `access-offboarding-a`, `-b`, `-c` | Done |
| Presentation entries `access-offboarding-a`, `-b`, `-c` | Done |
| `interfaces/case_explorer.py` chrome | Done |
| `interfaces/sv_labels.py` (ID → Swedish label map) | Done |
| Document metadata badges (`document_type`, `authority_level` values) | Done (display only; field values stay English, see above) |
| `interfaces/doc_viewer.py` chrome (title, CLI help, print output) | Done |
| `interfaces/workbench.py` chrome (page, form, results, validation errors) | Done |
| `interfaces/investigate.py` chrome (CLI help, `--format text` output) | Done (`--format json` keys are a data contract and stay English) |
| `evals/corpora/access-lifecycle-large` (large benchmark corpus) | Not started |

## Known limitations

- Swedish's heavy use of compound words (e.g. "avslutstidpunkten" as one
  token) means a lexical query written in English idiom does not port
  1:1 — TF/IDF token overlap only matches whole tokens, so translated test
  queries were re-verified empirically against the translated corpus rather
  than assumed correct by translation alone.
- `retrieval/vector.py`'s `DeterministicEmbeddingClient` includes a small
  English-only synonym-alias dictionary (`_normalised_tokens`) used only by
  the offline reproducible-evaluation fake. It has not been extended with
  Swedish aliases; this does not affect the real OpenAI embedding path,
  which is multilingual.
