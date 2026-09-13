# ADR-001 — Select THREAD with WARDLIGHT rehearsal

Status: accepted as a Day 1 planning direction, subject to human review and reopen triggers. Not an implementation approval or validated market decision.

## Context and provenance

[MASTER_PLAN.md](../../../univabio-plan/MASTER_PLAN.md), sections 2–3, is the secondary source for the idea tournament and prior competitor inspection. No new market search or independent reviewer was engaged for this pack. The plan's scores were subjective selection estimates, not official judging, measured product quality or win probabilities; this ADR does not repeat scores as evidence.

The competition's reported theme is Artificial Intelligence for Human Health ([official overview](https://univabio.devpost.com)). Its reported equally weighted rubric covers innovation, implementation, health impact/rigor, usability and presentation ([official rules](https://univabio.devpost.com/rules)). These constrain selection but do not prove any idea will score well.

## Eight alternatives considered before the hybrid decision

| Alternative | Potential value (hypothesis) | Main objection and disposition |
| --- | --- | --- |
| 1. Basic THREAD — source-linked discharge organizer | Makes source wording inspectable and coordination visible. | Summary/citations/checklist overlap with existing vendor claims; keep as foundation, not the novelty thesis. |
| 2. WARDLIGHT — interactive caregiver rehearsal | Makes a handoff understandable through practice. | A standalone branching quiz has weak differentiation and risks overstating comprehension; integrate only source/version-bound rehearsal. |
| 3. TRIAL LANTERN — trial-criteria evidence workspace | Connects criteria to evidence, missing data and temporal uncertainty. | Representative records and correct interpretation exceed this budget; a citation is not proof of trial eligibility. Defer, not a casual pivot. |
| 4. SIGNAL ATLAS — symptom timeline/appointment brief | Preserves chronology and uncertainty in an editable brief. | Risks drifting into diagnosis and has a less concrete revision demonstration. Ada already markets symptom assessment; do not claim a new category. Defer. |
| 5. LABEL LENS — allergen label coverage inspection | Could expose uncaptured label regions instead of declaring safety. | Dangerous confusion between not detected and safe to eat; generic OCR is weak novelty. Reject for this scope. |
| 6. ECHO ACCESS — accessible speech-practice feedback | Could provide accessible controls and understandable audio feedback. | Audio metrics do not establish therapeutic appropriateness; expert review/sample dependency is substantial. Defer. |
| 7. SPOONCAST — fatigue/pacing uncertainty journal | Could preserve uncertainty around exertion and fatigue. | Risks becoming a generic tracker; Visible already advertises pacing/energy budgeting. Needs discovery beyond this plan. Defer. |
| 8. BREATHEBENCH — respiratory-audio research explorer | Could expose quality, shift and uncertainty for research. | Dataset access, labeling and leakage controls are prerequisites; stethoscope data do not justify phone-recording claims. Weaker direct user handoff story. Defer. |

All strengths and delivery judgments are hypotheses or planning preferences. Descriptions of existing alternatives are inherited from the plan, not fresh verification: [Ada official app page](https://ada.com/app), [Visible official site](https://www.makevisible.com).

## Competitor correction

The plan reports that [Corti's Patient Discharge Education Agent](https://www.corti.ai/agents/patient-discharge-education-agent) advertises source-anchored explanations, missing/contradictory-document handling, clarification questions and step-by-step checklists. It reports that [Saana](https://saana.app) advertises patient graphs, sourced/versioned outputs, education quizzes and rule-based gates. These are vendor descriptions, not independently verified capabilities or performance findings; URLs are provided directly and were not fetched for Day 1.

Therefore PDF-to-summary, citations, questions about uncertainty, generic caregiver mode, graphs and quizzes are not sufficient differentiation. No market uniqueness or “first ever” claim is defensible here. The master plan's prior inspection does not establish that competitors lack revision invalidation or adaptive rehearsal.

## Decision

Select THREAD + WARDLIGHT as one product: THREAD REHEARSAL, retaining the public working name THREAD. Use source-linked nonclinical handoff coordination as the foundation and integrate focused rehearsal into its actual revision state, rather than build a separate quiz application.

Narrow differentiation hypothesis: an inspectable chain from changed source wording through affected tasks and stale version-bound acknowledgements to targeted re-review, paired eventually with reproducible stale-state evaluation. The replacement-appointment and conflicting-source scenarios offer an understandable failure/recovery demonstration. This is a preference under uncertainty, not evidence of superior health outcomes or a statistically meaningful score advantage.

Consequences: prioritize provenance, explicit replacement semantics, conservative invalidation and acknowledgement history over voice, OCR, graph ornamentation or general medical Q&A. Preserve three state dimensions and review-only medication quotations. Sharing must be real and tested or labeled simulation. A reviewer shortage narrows rigor claims; it never turns AI-generated labels into independent validation.

## What is known versus unresolved

Source-reported facts: competition theme/rubric; vendor marketing descriptions; the existing master plan's selection and schedule. They are not live-rechecked facts in this pack.

Design decisions: one synthetic case, nonclinical tasks, explicit source/version review, integrated rehearsal, no prescribing or medication administration tracking.

Unvalidated hypotheses: adults need this workflow; targeted re-review is understandable; revision invalidation offers useful differentiation; implementation is feasible in the proposed budget; reviewers/model access will be available. Entrant eligibility is unknown and must not be inferred from the selection.

## Reopen triggers and accountable roles

- Before any entry action: entrant cannot confirm student/age/geographic eligibility or organizer conditions conflict with the plan. Entrant/lead pauses competition participation; do not silently invent eligibility.
- Planned Day 2 discovery: direct competitors already offer the same inspectable revision-to-rehearsal chain, or adult discovery finds no valued problem. Product/research lead revisits positioning, compares document-only alternatives and may stop the thesis. Research is not completed today.
- Planned Days 3–4 feasibility: reliable source anchors or a believable invalidation path cannot be demonstrated. Engineering lead narrows to pasted/fixed-format text; reject a pivot into a generic chatbot.
- Review access remains absent at the plan's Day 6 checkpoint. Evaluation lead discloses single-reviewer limitations and reduces health-rigor claims.
- Planned Day 10 correspondence is unreliable. Engineering lead uses conservative document-wide invalidation/manual review and reports usability cost; reconsider if the core handoff benefit disappears.
- Later evidence shows conflict labels or acknowledgements are mistaken for permission to act, or critical fidelity gates fail. Safety/research lead blocks affected paths and revisits the scope instead of polishing over failure.
- Schedule/model constraints prevent a truthful interactive demonstration. Lead/entrant assesses a scoped evidence-review tool, labeled replay where applicable, or withdrawal; no fabricated live behavior.

Roles are responsibilities awaiting assignment, not named team members. [Scope](../day01/scope-and-acceptance.md), [risk register](../day01/risk-register.csv) and [review](../day01/review.md) retain unresolved follow-up work.
