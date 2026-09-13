# Competitor analysis

The evidence supports a **narrow research continuation**, not a uniqueness claim. Existing offerings overlap with nearly every component. The [matrix](competitor-matrix.csv) distinguishes advertised features, abstract descriptions and unknown implementation; the [source ledger](evidence/sources.jsonl) contains retrieval provenance.

## Closest challenge to the revision claim

**Carionex is the strongest inspected competitor for revision and renewed acknowledgement.** Its care-planning page advertises immutable snapshots, version changes, reread/sign prompts and visibility into changes since a carer's prior sign-off (S06). This directly defeats a claim that changed plans plus renewed acknowledgement are new. Exact imported quotation anchors, affected-task scope, concurrent-write rejection and targeted rehearsal remain unknown from this page. Professional agency users differ from THREAD's family hypothesis, but a different audience alone is weak differentiation. [Carionex care planning](https://www.carionex.co.uk/solutions/care-planning-software).

Rostera further advertises versioned plans, review sign-off, role-specific visit tasks derived from plans and handover records (S07). Linking plans to tasks is also existing territory; the page does not settle obsolete acknowledgement behavior. [Rostera care planning](https://www.rostera.co.uk/solutions/care-planning).

## Education and coordination overlap

Saana is the closest sourced-education competitor: it advertises passage tracing, versioned outputs and quizzes for an audience including caregivers (S09). Corti advertises source-constrained discharge explanation, missing/conflicting information handling, clarification questions and caregiver-oriented checklists (S08). Therefore citations, conservative uncertainty handling and quizzes cannot carry a novelty claim. Neither page establishes the complete dependency-invalidation behavior sought here. [Saana](https://saana.app/), [Corti](https://corti.ai/agents/patient-discharge-education-agent).

EHRTutor's abstract describes discharge-instruction questions, conversational testing and a concluding summary (S10). MayaRED advertises interactive discharge education, change review and teach-back (S13). These are substantive education alternatives; this research did not replicate outcomes or test either system. [EHRTutor abstract](https://arxiv.org/abs/2310.19212), [MayaRED](https://mayamd.ai/mayared).

ianacare advertises shared calendars, updates and delegated care tasks (S11). Lotsa Helping Hands describes coordinator-created activities, volunteer sign-ups and transport reminders (S12). They challenge the need for another caregiver organizer even without publicly documented source dependencies. [ianacare](https://ianacare.com/caregivers/), [Lotsa Helping Hands](https://caregiver.lotsahelpinghands.com/who-should-create/).

## Strongest argument against THREAD

The proposed product may recombine existing education, plan versioning and coordination features while adding confusing state and review burden. Public marketing omissions do not show a defensible market gap. A source-linked manual checklist with explicit rereview may suffice. Family caregivers may not want quizzes; document-wide rereview might be easier to understand than selective invalidation. No observed users or experiments resolve these objections.

The remaining **hypothesis** is an inspectable chain for a deliberately bounded fictional appointment handoff: exact source revision → affected nonclinical transport/call task → prior acknowledgement visibly obsolete → focused source review and rehearsal, retaining unaffected state and historical completion. Its research value would be a reproducible comparison against manual coordination and an invalidation-disabled ablation, not ownership of any component. If precise dependency mapping fails, disclose document-wide rereview and reassess the diminished contribution.

Missing/conflicting instructions remain unresolved, and replacement links never authenticate authority. Medication stays read-only. These are THREAD design constraints, not evidence of competitor inferiority. The [differentiation gate](../decisions/ADR-002-differentiation-gate.md) names the conditions that would reopen selection.
