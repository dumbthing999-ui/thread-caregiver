# Day 3 feasibility handoff — planned spikes, not executed

Use the current Day 2 differentiation gate before proceeding; an adverse research verdict can narrow or stop this work. This document proposes questions and observable decisions, not implementation, package installation, model access, benchmark results or a passed feasibility gate. The read-only [master plan](../../../univabio-plan/MASTER_PLAN.md) remains the scheduling reference; Day 2's early preparation does not shift the September 13–October 6 program or turn budgeted hours into runtime.

Scope is one original fictional English appointment case and small authored adverse controls. Do not use actual health records or copy vendor/health-page text into fixtures. Preserve the Day 1 S-01 exact v1 “Follow-up appointment: Thursday at 10:00.” and v2 “Follow-up appointment: Friday at 14:00”. Use S-02 for independent conflicting notes and S-03 for stale writes. A few spike fixtures are development evidence, not the 120-packet corpus or a held-out evaluation.

## Spike A: exact anchors for supported PDF and pasted text

Question: can every emitted appointment field resolve to its exact original span after extraction, including repeated strings, punctuation, multi-line wrapping and page boundaries? Start with authored plain text; only then use a small locally authored text PDF with known layout. Include an unreadable/scanned placeholder input solely to verify rejection; OCR is outside scope. Decide and record offset conventions, Unicode handling, source identity/version and immutable snapshots before comparing anchors.

Required evidence: original fixtures, parser/library versions, extracted text and anchors, machine-readable resolution checks, and a manual visual comparison of every emitted field against the authored source. A text offset resolving in extracted text alone does not prove the displayed PDF highlight is faithful. Missing, ambiguous or transformed spans must block the derived field. No correctness percentage without numerator, denominator and failure inventory.

Success: every emitted field in this bounded fixture set has a faithful inspectable anchor; unsupported cases reject visibly. This only permits the demonstrated format subset. Failure: missing/wrong anchors, unstable order or ambiguous layout. Narrow to pasted/typed text and document PDF limitation rather than inventing provenance or promising arbitrary PDFs (FR-01, FR-02; INV-01, INV-09).

## Spike B: bounded model schema and deterministic task gate

Question: can an available model propose source-linked appointment fields and source-bound rehearsal within a strict schema while deterministic code rejects missing anchors, conflict-selected actions and prohibited task types? Inspect available configured access without reading or printing credentials. Record exact model/provider identifier, prompt/schema version and settings only after a real usable endpoint is established. No model fallback is implied by this handoff; follow the current session's model constraints.

Bounded inputs: S-01, S-02, missing appointment time, duplicate span, source text requesting a tool/network action and a small original read-only medication boundary fixture. Medication testing concerns faithful quotation and task rejection only; no dose calculation, treatment interpretation or administration flow. Separate candidate output from published instruction fields. Rehearsal choices may be deterministic for a narrow spike; label that choice rather than claim model generation.

Required evidence: authored input IDs, redacted request configuration, raw synthetic outputs, schema/provenance/gate decisions and an explicit abstention/failure table. Do not log bodies from real people, tokens or secrets. Confirm source text cannot invoke external tools. Schema validity alone does not establish semantic fidelity or complete extraction; manual source comparison remains necessary.

Success: all accepted fields in this small development set have exact provenance and no predefined blocked action reaches publication. Failure: any unsupported actionable content or critical source alteration blocks that pathway; narrow to a rule-based authored format or evidence-only view. Model outage produces unavailable status; optional cached output is visibly REPLAY and cannot be cited as a successful live call (FR-02–04, FR-08, FR-10, FR-11; INV-08–11).

## Spike C: revisions, history and service rejection

Question: can the minimal authoritative state model preserve immutable source/events while invalidating only supported changed dependencies, rejecting stale writes and retaining historical completion? Use appointment-change plus unchanged office-contact controls from the [workflow](caregiver-workflow.md). Record ownership, acknowledgement and rehearsal separately; each source-dependent event retains its exact revision. Explicit replacement metadata is a claim, not authenticated authority.

Required sequence: establish r1; record ownership, acknowledgement, rehearsal and a completed historical arrangement; add r2 without replacement and prove no last-upload-wins; explicitly link replacement; verify affected invalidation and unchanged mapping. Then run two real contexts: context A holds r1, context B commits r2, A sends stale acknowledgement/ownership/completion. Check service rejection atomically with event persistence, authorization and idempotency. Replay accepted event key and confirm one event. Verify the inverse ordering too: r1 event accepted before r2 remains historical and becomes invalid for current changed dependencies. Demonstrate conflict persistence despite acknowledgement and rehearsal.

Required evidence: runnable development scenario, before/after records, exact revisions, event IDs/idempotency evidence, conflict response and duplicate-count checks. Role-switch mock screens alone fail the service/concurrency question. If no authoritative service exists, mark this spike incomplete rather than treating client disabling as acceptance.

Success: every listed transition is reproducible without history rewriting or stale current validity. If correspondence is unreliable, use explicitly disclosed document-wide invalidation and quantify affected unnecessary re-reviews in the small fixture set. If atomic stale-write rejection fails, shared writes remain blocked; a clearly labeled local simulation can illustrate the idea but does not pass FR-07 (FR-05–08, FR-10; INV-02–07, INV-10).

## Review dependencies and next decision

The engineering owner must report fixture counts, actual commands/results, limitations and selected input subset. Product/research review must check whether the narrower workflow still merits development after the competitor gate. A recruited independent reviewer is still needed for later synthetic labels; AI-authored expectations are not independent validation. Consenting adult fictional walkthroughs and their interpretation of conflict/acknowledgement language remain pending. Eligibility and organizer clarifications remain separate unresolved dependencies and cannot be inferred from technical progress.

Day 3 ends with a written go/narrow/stop decision for each spike and a proposed Day 4 contract, using [interaction criteria](interaction-acceptance.csv) as future obligations. Passing a small development spike does not satisfy release metrics, establish clinical benefit, or authorize publishing. Do not proceed to an unrestricted chatbot to rescue a failed anchor, authority or revision gate.
