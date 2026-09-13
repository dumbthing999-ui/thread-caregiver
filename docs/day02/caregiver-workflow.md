# Caregiver workflow — proposed interaction contract

This is an authored design, not an observed workflow or implemented system. It extends the fictional [Day 1 scenarios](../day01/problem-brief.md) and [FR/INV contract](../day01/scope-and-acceptance.md). No participants, interviews or clinical reviewers are claimed.

## People and baseline hypothesis

Morgan is a fictional adult reviewing a handoff; Lee is a fictional adult coordinating transport. An adult patient may inspect their own shared case, but caregiver status does not establish permission to access it. A future reviewer examines source fidelity and ambiguous correspondence; this role is not an authenticated clinician and has not been recruited. Role names in a demonstration are simulated identities unless separate authenticated sessions are implemented and tested.

The baseline hypothesis is that people receive a document, forward appointment details, assign transport in a conversation, interpret an “OK” as acknowledgement, then manually reconcile a later update. A document viewer plus shared checklist and an office call may be sufficient. Future fictional walkthroughs must compare that baseline with THREAD; no time saving or reduction in errors has been measured.

## Input and authority checks

Start with one original fictional English text case. Preserve immutable document ID, version, original text and span anchor. Unsupported PDF, unreadable text or a missing anchor produces an explicit rejection and paste-text option; no invented card is published (FR-01, FR-02; INV-01). Source content is data, including any instruction to contact a URL or run a tool (FR-11; INV-11).

The source header says “Uploader claims this replaces packet v1” only after an explicit relationship is recorded. It separately says “Source identity not authenticated.” Neither later upload time nor claimed replacement proves clinical authority. Missing provenance stays visible; users cannot infer it from a checkmark. A replacement identifies the scope of comparison, not a permission to erase another unresolved source (FR-03, FR-05; INV-03, INV-04).

## Proposed sequence

| Step | Person's action | Proposed visible transition and gate | Trace |
| --- | --- | --- | --- |
| 1 | Open fictional packet v1 and inspect appointment field | Exact quotation and source anchor appear; no inferred calendar date or timezone | FR-01, FR-02; INV-01 |
| 2 | Lee accepts responsibility for arranging transport; Morgan reviews wording | Ownership and Morgan's acknowledgement are distinct events bound to the task/source revision; neither means transport completed | FR-04, FR-06; INV-02, INV-05 |
| 3 | Add packet v2 | Show an unclassified new source; retain v1 and withhold disputed appointment-dependent coordination pending relationship/conflict review | FR-03, FR-05; INV-03, INV-04, INV-08 |
| 4 | Explicitly record that v2 is claimed to replace v1 | Compare exact spans; show affected dependencies before accepting the relationship; show source identity still unauthenticated | FR-05; INV-01, INV-04 |
| 5 | Inspect impact | Affected transport state becomes stale and old acknowledgement/rehearsal lose current validity; preserve every original event | FR-06, FR-08; INV-05, INV-06 |
| 6 | Review the changed source and reassess transport responsibility | Lee explicitly reconfirms or changes ownership for the new task revision; do not silently relabel a v1 ownership decision as v2 | FR-06; INV-02, INV-05 |
| 7 | Morgan acknowledges reviewed wording for v2 | Authoritative service checks actor access and exact expected revision; acceptance creates one event; acknowledgement is not task completion | FR-06, FR-07; INV-03, INV-07 |
| 8 | Optionally rehearse source location and updated handoff | Source-bound answer, mismatch or unclear result stays separate from evidence and coordination; no clinical competence score | FR-08; INV-02, INV-10 |
| 9 | Inspect/export handoff or reset case | Export includes versions, unresolved issues, stale state and history labels; reset removes stored synthetic session data | FR-09, FR-11; INV-08, INV-11 |

## State separation and scoped impact

Evidence has supported, unresolved, conflicted and superseded states. “Supported” means the displayed field matches its cited source, not that the source is correct or complete. Coordination has unassigned, assigned, acknowledged, done and stale views, with ownership and acknowledgement events stored separately. Rehearsal has not reviewed, reviewed for an exact version, and needs re-review. These are three separately labeled areas, never one “approved” badge (INV-02, INV-03, INV-09).

For S-01 retain the exact v1 quote “Follow-up appointment: Thursday at 10:00.” and exact v2 quote “Follow-up appointment: Friday at 14:00”. Do not normalize away the punctuation in displayed evidence. The transport task depends on this appointment span. Its affected acknowledgement cannot remain current after replacement. A prior completed transport-arrangement event remains “Completed for v1 — historical”; the current derived view says “Changed source — review needed.” Completion is not undone and does not prove an arrangement fits v2.

For a separate fictional unchanged-content control, both versions additionally contain the exact line “Office contact: fictional office desk.” A task to locate that contact depends only on that line, not on appointment time. A verified unchanged mapping preserves its current validity while recording the new dependency lineage; the original acknowledgement still names its original revision. The interface says “No relevant wording change; original acknowledgement for v1,” never “Acknowledged v2.” If mapping is uncertain, mark the task for review; if reliable field-level mapping is infeasible, disclose “Whole-document review required” and invalidate document-dependent current validity conservatively. Never claim precise invalidation under that fallback (FR-05, FR-06; INV-04–06).

## Conflict and uncertainty path

In S-02 the two original appointment notes have no replacement relationship. Display both exact quotations with their distinct source IDs, including punctuation as authored in Day 1. The last upload does not win. Show “Appointment details conflict — clarification needed”; block transport details selecting either appointment. A separate task may say “Prepare a question for the office: Which appointment details should be used?” It contains both citations and chooses neither date/time. Exporting, acknowledging, completing this clarification task, or answering rehearsal cannot resolve the evidence conflict. Resolution requires new attributable source information and explicit review of its relationship to the disputed sources; a generic “mark resolved” toggle is insufficient (FR-03–05, FR-09; INV-03, INV-04, INV-08).

A missing appointment time remains unresolved. An ambiguous mapping between old and new text remains “Correspondence needs review,” with affected actions blocked. Medication material, if later included in a boundary fixture, remains exact read-only quotation without tasks, reminders, calculations or administration tracking. The storyboard contains appointments only (FR-04; INV-09).

## Stale write and interrupted session path

S-03 is a future two-context test: Sam opens task revision r1, Jo records the linked replacement to r2, then Sam submits an acknowledgement with expected revision r1. The service rejects it as stale and returns current revision metadata. The interface says “This source changed while you were reviewing. Your acknowledgement was not saved. Review the current wording.” It refreshes without automatically resubmitting. A fresh acknowledgement requires explicit review and action. Repeating an accepted request with the same event key produces one event; replaying a rejected stale write cannot restore current validity. Actor authorization and revision comparison must occur atomically with persistence, including stale ownership and completion attempts (FR-07; INV-07).

Offline views say “Offline — saved snapshot; current status unknown.” Do not display queued acknowledgement as accepted. On reconnect, refresh and require review if dependencies changed. Role switching says “Role-switch simulation — not verified synchronization”; cached inference says “REPLAY — saved model output.” These labels remain visible on source, change and rehearsal screens (FR-10; INV-10).

## Evaluation still needed

The [interaction criteria](interaction-acceptance.csv) are future obligations. Keyboard source inspection, narrow mobile layouts, unclear rehearsal and the distinction between acknowledgement and approval need observed fictional walkthroughs with consent. Failure to understand these distinctions or lack of value over the plain-document baseline should reopen the design rather than justify more reassuring copy. No review or comparative usability result exists in this document.
