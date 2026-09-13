# Day 1 problem brief

## Evidence boundary

This brief translates [MASTER_PLAN.md](../../../univabio-plan/MASTER_PLAN.md), sections 2–4 and 6, into discovery hypotheses. No interviews, observed workflows, prevalence measurements or clinical reviews have occurred in this pack. Every persona and scenario below is fictional. Proposed behavior is not implemented behavior.

For context only, the plan cites [MedlinePlus teach-back](https://medlineplus.gov/ency/patientinstructions/000460.htm) for checking the explanation rather than grading the patient, and [MedlinePlus discharge planning](https://medlineplus.gov/ency/patientinstructions/000867.htm) for topics including medicines, follow-up, contacts and restrictions. These pages were not newly accessed; citations neither validate THREAD nor authorize copying page text into a corpus.

## Persona hypotheses

Primary hypothesis: an adult, nonprofessional family caregiver coordinating transport or an office call for an adult patient after receiving English written instructions. They can read the supported document format but may have limited time, intermittent connectivity or only a phone. They need to establish which instruction a task depends on, not interpret treatment.

Secondary hypothesis: another adult caregiver taking over a discrete coordination responsibility asynchronously. They may have acknowledged a prior version without knowing a replacement exists. Shared devices or message forwarding may obscure who read which version. These constraints are hypotheses, not demographic findings.

Adult patient participant hypothesis: an adult reviewing their own fictional handoff alongside a caregiver, wanting source visibility and control over sharing. Patient participation or access must not be assumed merely because someone calls themselves a caregiver. This scope does not cover pediatric care, professional clinical workflow, emergency decision-making, treatment supervision or impaired-capacity consent questions.

## Job to be done

When I take over a nonclinical coordination task based on written instructions, help me locate its source, see whether that source changed and establish who has reviewed the current version, so I can coordinate the documented next step or prepare a clarification question without treating an unresolved instruction as settled.

## Current workflow hypothesis

1. Receive a packet, pasted message or separately forwarded update.
2. Locate follow-up details and inform another caregiver through conversation or messaging.
3. Assign transport or a call informally; interpret “OK” as acknowledgement.
4. Receive another document; manually compare it and decide whether it replaces anything.
5. Relay differences and check that previous acknowledgements still apply.
6. Contact the appropriate office about unresolved information.

We have not established that people use this sequence, that messages fail, or that software is preferable to a plain document and phone call.

## Proposed workflow hypothesis

1. Open an original synthetic English text case; show import limitations rather than invent missing text (FR-01).
2. Inspect quoted fields and their source/version alongside evidence status (FR-02, FR-03).
3. Assign only eligible nonclinical coordination tasks; medication quotations remain review-only (FR-04).
4. Explicitly identify a claimed replacement relationship; compare affected fields without granting clinical authority to the uploader (FR-05).
5. Mark dependent tasks, acknowledgements and rehearsal records stale; preserve history (FR-06, FR-07).
6. Review the changed wording and rehearse source location or coordination understanding, not clinical competence (FR-08).
7. Export unresolved questions and current version/status for human clarification (FR-09).

Requirements are defined in [scope and acceptance](scope-and-acceptance.md). No step is operational today.

## Falsifiable assumptions

| ID | Hypothesis | Evidence that would weaken or falsify it |
| --- | --- | --- |
| PA-01 | Distinguishing versions is a meaningful coordination difficulty for the target adults. | In fictional walkthroughs participants reliably identify current and conflicting sources using ordinary documents, and cannot identify a useful role for revision review. |
| PA-02 | A version-bound acknowledgement communicates more than a generic “OK.” | Participants repeatedly interpret it as clinical approval or task completion even after neutral explanation. |
| PA-03 | Targeted change review is easier than rereading everything. | Participants prefer whole-document review, miss unchanged context or require more assistance on change-focused tasks. |
| PA-04 | Explicit conflict states help people defer unresolved coordination details. | Participants treat conflict labels or quotations as permission to choose one instruction without clarification. |
| PA-05 | Source-bound rehearsal is acceptable and useful for handoffs. | Participants experience it as a test of their worth, intrusive friction or redundant with reading, and choose not to use it. |
| PA-06 | A coordination-only scope is valuable without medication tracking. | Volunteers consistently need administration/treatment features to find any value; do not expand into those features to rescue the thesis. |

These are discovery criteria, not statistically validated thresholds. Seek counterexamples and preserve disagreement; later comparative usability needs its own protocol.

## Three original fictional scenarios

### S-01 — Replacement appointment

Fictional adults Morgan and Lee coordinate transport. Authored packet v1 says “Follow-up appointment: Thursday at 10:00.” Lee owns transport; Morgan acknowledged v1. Packet v2 says “Follow-up appointment: Friday at 14:00” and is explicitly identified as replacing v1 by the uploader. No actual appointment or medical instruction is represented.

Expected proposed behavior: show both exact spans and the claimed replacement relationship; invalidate the affected transport plan and Morgan's v1 acknowledgement; retain historical events. Request review of v2 and focused source-grounded rehearsal. Do not authenticate the source or silently rewrite a completed event. Trace: FR-02, FR-05–08; INV-01, INV-04–07.

### S-02 — Conflicting sources

Fictional adults Alex and Robin receive two authored notes: “Follow-up appointment: Thursday at 10:00” and “Follow-up appointment: Friday at 14:00.” Neither is identified as a replacement. The Friday note is uploaded last.

Expected proposed behavior: retain both sources; mark the appointment conflicted; withhold actionable scheduling details; allow preparing a question to confirm the appointment with the office. Clicking “I understand” does not resolve the conflict. Trace: FR-03–05, FR-09; INV-02–04, INV-08.

### S-03 — Stale acknowledgement in flight

Fictional caregiver Sam opens v1 while Jo reviews an explicitly linked replacement v2 in another synthetic role. Sam sends acknowledgement of v1 after v2 becomes current for the affected task. This is an authored concurrency requirement, not a demonstrated race test.

Expected proposed behavior: reject the obsolete write, refresh visible version information and require explicit review before a new acknowledgement. Preserve the v1 history and mark v1 rehearsal as needing re-review; do not relabel either as v2. A future local role-switch simulation must not be presented as real synchronization. Trace: FR-06–08, FR-10; INV-05–07, INV-10.

## Validation questions and non-goals

Discovery must ask how adults interpret source authority, acknowledgements, completed transport and unresolved questions; whether they can identify what changed without prompting; and whether document-only comparison suffices. Use the [interview guide](interview-guide.md), including refusal and privacy protections. Recruitment and expert review remain pending.

Non-goals: prove error prevalence or reduced readmissions; measure medication adherence; prescribe or calculate doses; diagnose; infer absent dates; replace clinicians; create a medical chatbot; collect health histories; establish novelty through this fictional exercise. No benefit or market-size claim is justified by the plan alone.
