# Three-act storyboard — fictional appointment handoff

An authored 180-second editorial target, not an official video limit, recording, working UI or usability result. All named adults and source packets are fictional. This specification follows [caregiver workflow](caregiver-workflow.md) and [Day 1 scenarios](../day01/problem-brief.md). Display a persistent “Fictional research prototype” label. Proposed transitions below require future implementation and verification.

## Timed beats

| beat | act | start_seconds | duration_seconds | screen_and_action |
| --- | --- | --- | --- | --- |
| B01 | 1 | 0 | 15 | Import: Morgan opens the original fictional packet v1; text-only boundary and source identity appear. |
| B02 | 1 | 15 | 20 | Source review: Morgan opens the appointment anchor and reads the exact v1 wording. |
| B03 | 1 | 35 | 20 | Handoff: Lee owns transport; Morgan acknowledges v1 and completes an optional v1 source rehearsal; three state areas remain separate. |
| B04 | 2 | 55 | 15 | New source: add v2; it is not automatically authoritative; choose the explicit claimed replacement relationship. |
| B05 | 2 | 70 | 25 | What changed: compare both quotations and show transport plus old acknowledgement and rehearsal needing re-review. |
| B06 | 2 | 95 | 15 | History and unaffected control: retain historical completion; unchanged office-contact task remains distinct. |
| B07 | 2 | 110 | 15 | Race branch: an obsolete v1 acknowledgement is rejected; refresh points to v2 without automatic resubmission. |
| B08 | 3 | 125 | 20 | Focused review: inspect v2; Lee reconfirms ownership; Morgan explicitly acknowledges the new revision. |
| B09 | 3 | 145 | 15 | Rehearsal: source-bound appointment prompt offers an unclear answer and return-to-source path. |
| B10 | 3 | 160 | 20 | Conflict control and export: independent notes remain unresolved; prepare a neutral office question and export versions/status. |

## Act 1: establish the existing handoff

B01–B03 show a single synthetic case. Source identity is “packet v1, text span appointment-1”; an eventual runtime must provide the actual immutable ID and anchor rather than treating this storyboard label as a generated artifact. The exact quote is “Follow-up appointment: Thursday at 10:00.” There is no invented calendar date, travel duration or appointment confirmation.

```text
Fictional research prototype | Role-switch simulation — not verified synchronization
Today's handoff                          [Open source packet v1]
Evidence: Supported by quoted text; source identity not authenticated
  “Follow-up appointment: Thursday at 10:00.”
  packet v1 / appointment-1              [Inspect quotation]
Coordination: Transport arrangements
  Owner: Lee, for task revision r1        [Review responsibility]
  Morgan: reviewed wording for v1         [View acknowledgement event]
Rehearsal: Not reviewed                   [Optional source review]
Textual support is not clinical approval or complete extraction.
```

After the initial not-reviewed view, B03 explicitly shows Morgan selecting the v1 source-matching rehearsal answer and records “Reviewed for packet v1” as a separate seeded fictional event. This establishes the prior attempt invalidated in B05; it is not evidence of real user comprehension.

The acknowledgement control reads “I reviewed this wording — packet v1.” It never says “Approve plan” or “Safe to follow.” Lee's assignment does not complete transport; Morgan's acknowledgement does not assert Lee read it. Opening the source moves focus to a titled panel with its version and highlighted span; closing restores focus to the invoking control. An unsupported file branch shows “This format cannot be read reliably. Paste fictional English text,” and publishes no card.

## Act 2: show replacement and loss of current validity

B04 first shows v2 as a new source, without silently superseding v1. The relationship form offers “Separate source / relationship unknown” by default and an explicit action “Record claimed replacement of packet v1.” It explains that claimed replacement does not authenticate its author; unrelated conflicts remain unresolved. Before committing, the user can cancel and retain both sources.

```text
What changed | packet v1 → packet v2 | Claimed replacement
Source identity not authenticated
Old exact quotation                      New exact quotation
“Follow-up appointment: Thursday at 10:00.”
                                         “Follow-up appointment: Friday at 14:00”
Affected: Transport arrangements          Current view: Review needed
Morgan's v1 acknowledgement: Historical; not current for changed wording
Rehearsal for v1: Needs re-review          [Inspect both sources]
[Review changed wording]                 [View original event history]
```

B05 highlights exact changed spans with text labels “Old” and “New,” not color alone. The punctuation difference remains visible; no fabricated extra text appears in either source. Source evidence, transport state and rehearsal each have their own heading. A model's uncertain correspondence produces “Correspondence needs review,” with withheld task details and no silent merge.

B06 uses the separately authored unchanged line “Office contact: fictional office desk.” in both versions. The contact-location task has no appointment-time dependency; its original revision-bound event remains labeled v1 with a disclosed unchanged mapping. The transport example's earlier completed arrangement remains “Completed for v1 — historical,” while the new revision requires review. This is a demonstration branch with a deliberately seeded historical completion, not a claim that an actual appointment happened.

B07 overlays a proposed obsolete-write result: “This source changed while you were reviewing. Your acknowledgement was not saved.” [Review current wording] opens v2. The explanatory caption says “Future authoritative-service rejection requirement.” Until a real two-context test exists, the scene must be labeled simulated; role switching alone cannot support a synchronization claim.

## Act 3: focused review, rehearsal and conflict control

B08 returns to both old/new quotations, then v2 in context. Lee explicitly reconfirms responsibility for r2; Morgan's separate explicit acknowledgement is bound to r2/v2 only after service acceptance. History retains the old event. Rehearsal remains optional and independent; neither action gives clinical approval.

```text
Rehearse the source | packet v2 / appointment-1
According to this quoted packet, what follow-up wording is shown?
“Follow-up appointment: Friday at 14:00”  [Inspect source]
[Friday at 14:00] [Thursday at 10:00] [Unclear — inspect source]
This checks agreement with the quoted text, not clinical correctness.
```

B09 uses fixed authored choices for the specification; this is not a live model inference. Matching feedback says “Matches the quoted wording in packet v2.” A mismatch says “That does not match this quotation. Review the source or choose unclear.” “Unclear” stores an unclear attempt for v2, offers source review and leaves rehearsal incomplete; it does not issue advice or mark comprehension passed. Any later dependency change marks the attempt needs re-review without rewriting the historical response.

B10 switches to the explicitly separate S-02 control, not another source quietly added to S-01. Reset/navigation announces “Separate fictional conflict case.” Both original S-02 quotes are visible with distinct IDs and no replacement link. The newer upload is not selected. The screen says “Appointment details conflict — clarification needed” and disables any task choosing either time at the authoritative gate. A bounded preparation task reads “Prepare a question for the office: Which appointment details should be used?” Acknowledgement or correct rehearsal leaves the conflict unresolved. Export preview retains both quotes/versions, the unresolved question, task owner and state, plus snapshot/replay labels where relevant.

## Failure and recovery coverage outside the timed cut

These are required interaction branches, not extra seconds hidden in the 180-second sum. An offline interruption displays “Offline — saved snapshot; current status unknown,” retains source inspection and never shows an unsent acknowledgement as accepted. Reconnection refreshes before a fresh explicit write. Model outage says “Extraction unavailable”; a saved result carries “REPLAY — saved model output” throughout. Missing anchors block card publication. Duplicate accepted submissions produce one history event; stale ownership/completion submissions are rejected like acknowledgements. Medication boundaries belong to separate future criteria, with quotation-only rendering and no administration actions; this appointment storyboard introduces no medication scenario.

## Accessible layout and editorial constraints

At a 320 CSS-pixel viewport, stack old and new quotation blocks in reading order, keeping source IDs, state labels and actions visible without page-wide horizontal scrolling. Long literal source text wraps without alteration. Keyboard Tab order follows headings, source controls, review actions and return controls; there is a visible focus indicator, Escape closes non-destructive panels, and source changes are announced without stealing focus. State is communicated by words and structure as well as color. Avoid automatic countdowns and forced rehearsal. Every button's accessible name identifies its action and relevant version. These are future acceptance targets, not tested accessibility conformance.

The final frame says “Authored synthetic scenario. Implementation, user validation and clinical benefit unverified.” A future video may only replace that wording with claims supported by actual evidence. Timing is an editorial allocation, not measured task speed or participant performance.
