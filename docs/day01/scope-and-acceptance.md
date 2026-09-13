# Scope and acceptance — specification only

Source: [master plan](../../../univabio-plan/MASTER_PLAN.md), sections 4–6 and 9. This document defines intended product behavior and Day 1 document acceptance separately. Every FR/INV below is unimplemented and untested. Nothing is clinical validation.

## In and out

In the proposed product: original fictional English typed text/pasted text; text PDF only after reliable provenance feasibility is established; one active demonstration case; source inspection; explicit replacement links; conservative conflicts/diffs; nonclinical ownership and revision-bound acknowledgement; focused rehearsal; accessible desktop/mobile flow; print/export; reproducible synthetic evaluation. Shared caregiver roles require genuine synchronization or a plainly labeled role-switch simulation.

Medication instructions are review-only source quotations, preserving start/stop/negation and uncertainty. They never become medication tasks, reminders to administer, administration checkboxes, adherence measures or dose/timing calculations. A quotation is not a recommendation to follow it.

Out: real patient inputs in the public demo, diagnosis, treatment selection, drug interactions, prescribing, inferred dosing times, autonomous EHR/pharmacy actions, clinical efficacy claims, unrestricted chatbot, OCR/scanned-document promises, extra languages, native app, custom model training and hospital integration. Notifications and ornamental graph UI are not core. No product implementation belongs in Day 1.

## Functional requirements — future acceptance obligations

| ID | Requirement | Future observable acceptance evidence |
| --- | --- | --- |
| FR-01 | Import supported synthetic text, preserving immutable source identity/version; reject unsupported/unreadable input visibly. | Import fixtures retain exact text; rejected input yields a reason and paste-text option without fabricated extraction. |
| FR-02 | Every displayed instruction field has an inspectable exact quote and source/version anchor. | Field-to-source inspection tests resolve every anchor; missing anchors block card publication. |
| FR-03 | Expose supported, unresolved, conflicted and superseded evidence independently of coordination. | Missing/conflicting fixtures show no invented value and no automatic last-upload-wins resolution. |
| FR-04 | Gate tasks to supported nonclinical coordination and keep medications review-only. | Transport/call fixtures can yield bounded tasks; medication or ambiguous instruction fixtures cannot yield administration actions. Clarification tasks do not authorize the disputed action. |
| FR-05 | Require an explicit claimed replacement link; compare known fields conservatively and route uncertain correspondence to review. | S-01 shows old/new spans and impact; S-02 stays conflicted without a replacement link. Claimed authorship is not displayed as authenticated. |
| FR-06 | Bind ownership, acknowledgements and events to revisions; invalidate affected dependent state and retain historical completion. | Changed, unchanged and uncertain mapping cases demonstrate scoped invalidation or disclosed conservative document-wide fallback; no old event is rewritten. |
| FR-07 | Reject stale concurrent writes with server-side authorization, revision checks and idempotent event handling. | S-03 rejects v1 acknowledgement after v2; retry does not duplicate events; unauthorized actors cannot write. |
| FR-08 | Rehearsal must cite the reviewed version, allow unclear answers and invalidate dependent attempts on change. | Prompts are answerable from quotes; source changes cause needs-re-review; feedback does not grade medical competence or invent guidance. |
| FR-09 | Export source/version, owners, acknowledgement status and unresolved clarification questions without hiding uncertainty. | Print/export preserves conflicts, stale state and source links/identifiers; export is not clinical approval. |
| FR-10 | Distinguish current synchronized state, offline/stale views, simulation and cached model replay. | Future two-context tests support any synchronization claim; simulation/replay are visibly labeled and outages do not show invented success. |
| FR-11 | Provide synthetic-session isolation, bounded input, safe rendering and deletion/reset; treat source instructions as data. | Future security tests reject cross-session access, malicious markup and document-driven actions; reset removes persisted demo data. No sensitive body/token logging. |
| FR-12 | Support keyboard/mobile source review and a reproducible evaluator path with honest limitations. | Future interaction, accessibility, setup and evaluation evidence includes actual denominators, abstentions, failures and configuration, not fabricated metrics. |

## State invariant contract

| ID | Invariant | Related requirements |
| --- | --- | --- |
| INV-01 | Source documents/spans are immutable; every derived field retains quotation, anchor and version. Derived updates create history rather than overwriting source evidence. | FR-01, FR-02, FR-06 |
| INV-02 | Evidence state (supported/unresolved/conflicted/superseded), coordination state (unassigned/assigned/acknowledged/done/stale) and rehearsal state (not reviewed/reviewed for version X/needs re-review) are distinct. | FR-03, FR-06, FR-08 |
| INV-03 | Newest upload, claimed authorship, acknowledgement, task completion or successful rehearsal cannot establish clinical authority or resolve conflicting evidence. | FR-03–06, FR-08 |
| INV-04 | Supersession requires an explicit replacement relationship; uncertain correspondence remains reviewable, never silently merged by a model. Source age alone does not settle authority. | FR-03, FR-05 |
| INV-05 | Every source-dependent acknowledgement and rehearsal attempt refers to an exact revision; changed dependencies invalidate current validity, not historical existence. | FR-06, FR-08 |
| INV-06 | A completed historical task remains recorded as completed at its original revision even if its current derived coordination view becomes stale. | FR-06 |
| INV-07 | A stale revision write cannot restore current validity; retries cannot create duplicate events. Enforce at the authoritative server, not just a disabled button. | FR-07 |
| INV-08 | Unresolved/conflicted actionable details cannot pass the task gate. A clarification question may be coordinated without selecting a disputed instruction. | FR-03, FR-04, FR-09 |
| INV-09 | Medication quotations cannot become administration tracking or inferred treatment; textual provenance proves anchoring only, not correctness or complete extraction. | FR-02, FR-04 |
| INV-10 | Rehearsal correctness means agreement with cited source facts only. Replay, offline state and role simulation cannot be labeled live model output or synchronization. | FR-08, FR-10 |
| INV-11 | Untrusted source content never authorizes tools/network/actions; synthetic sessions are isolated and resettable. | FR-01, FR-11 |

Trace examples and assumptions are in [problem brief](problem-brief.md); corresponding risks and pending work are in [risk register](risk-register.csv) and [backlog](backlog.csv).

## Day 1 exit gate — documentation, not product release

D1-G1: All requested foundation files exist and contain substantive content, with links to the read-only plan and direct official URLs for factual claims.

D1-G2: Adult persona/workflow hypotheses, falsification criteria, three fictional scenarios, FR/INV contracts, eight-alternative comparison and non-goals are explicit.

D1-G3: Eligibility remains unconfirmed; rules provenance/status and deadline/code-PDF ambiguities are recorded; a complete organizer email is clearly NOT SENT.

D1-G4: Consent-based interview preparation, recruitment target, risk owners and external-validation backlog are documented without claiming recruitment or review occurred.

D1-G5: Local links, CSV shape and identifiers are checked using real stdlib execution; review records the exact command/output and limitations. This is document structure verification, not runtime tests.

D1-G6: Self-critique and unresolved blockers are recorded. Human/parent acceptance remains pending. Document readiness can pass while external validation remains pending; it does not confer eligibility, approval or a product go-live decision. No logged-hour or elapsed-budget claim is part of this gate.

## Future product gates — targets only, not Day 1 exit criteria

The master plan proposes: zero observed critical dose/route/polarity/date corruption in locked runs; every field anchored; at least 98% instruction precision; at least 90% clean-case recall; every predefined must-block case blocked and at least 95% annotated ambiguity/conflict recall; all specified revision/concurrency tests passing; every rehearsal item grounded; at least 80% observed success per core interaction task; fresh setup, smoke tests and faithful exports. All are NOT RUN and depend on reviewed synthetic labels and an authorized implementation.

Future evaluation calls for 120 original synthetic packets split into 40 development, 20 validation and 60 locked test packets, with family isolation, baselines and independent review. This pack does not create that corpus. Critical failures block affected features; a fixed opened-test failure becomes regression evidence, not a renewed held-out claim. Abstention and actionable coverage must accompany accuracy. Even passing all targets would not demonstrate medical correctness, real-world safety or clinical benefit. Later review availability, model/provider access and feasibility gates can narrow scope; they cannot justify invented results.
