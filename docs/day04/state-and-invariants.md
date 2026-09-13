# State transitions and requirement trace

These are future service obligations for [contract 0.1.0](../../contracts/day04/contract.json), not passing implementation tests. The initial policy is DOCUMENT_WIDE invalidation and whole-case write serialization. Source quotations establish origin only; a replacement assertion establishes a claimed relationship only.

## Separate state dimensions

Evidence state is SUPPORTED, UNRESOLVED, CONFLICTED or SUPERSEDED. Coordination status is UNASSIGNED, ASSIGNED, ACKNOWLEDGED, DONE or STALE, with a separate current validity of CURRENT, STALE or BLOCKED. Ownership and each person's acknowledgement are independent events, even when the UI summarizes them as ACKNOWLEDGED. Rehearsal is NOT_REVIEWED, REVIEWED_FOR_VERSION or NEEDS_REREVIEW, with attempts MATCH, MISMATCH or UNCLEAR stored separately. No shared approval flag exists (INV-02, INV-03).

The coordination summary has deterministic precedence: STALE if dependencies were invalidated; otherwise DONE if a completion exists for that task revision; otherwise ACKNOWLEDGED if the assigned actor has acknowledged this revision; otherwise ASSIGNED if owner exists; otherwise UNASSIGNED. Another caregiver's acknowledgement is shown separately without overwriting the owner's status. A BLOCKED validity can coexist with historical DONE; it does not uncomplete history. Rehearsal outcome is never used to choose coordination or evidence state.

## Domain transition table

| ID | Trigger and preconditions | Evidence | Coordination | Rehearsal and history |
| --- | --- | --- | --- | --- |
| ST-01 | Import new bounded source at current case version | New source awaits review; no last-upload-wins | Case actionable coordination suspended; current validity BLOCKED, existing events unchanged | Source-dependent current review applicability suspended; never show synced success while offline |
| ST-02 | Owner reviews exact supported source selection | Deterministic field/relationship checks choose SUPPORTED, UNRESOLVED or CONFLICTED | Suspension can clear only when every active source has been accounted for and relevant evidence passes | Review event records source/version; does not create an acknowledgement or rehearsal attempt |
| ST-03 | Two unlinked active appointment lines disagree | CONFLICTED; both exact sources visible | Transport action blocked; neutral PREPARE_CLARIFICATION permitted | Rehearsal cannot settle disagreement; clarification completion leaves conflict |
| ST-04 | Explicit valid replacement link, two existing versions, current case precondition | Prior evidence SUPERSEDED; new source still independently reviewed; unrelated conflicts survive | All tasks depending on replaced document get current STALE validity; initial policy includes unchanged wording | Append INVALIDATED events; all corresponding acknowledgements/attempts lose current validity; no payload edited |
| ST-05 | Replacement correspondence uncertain | No guessed equivalence; new evidence requires review | DOCUMENT_WIDE fallback with visible extra re-review | Original bindings preserved; do not claim selective retention |
| ST-06 | Create eligible nonclinical task | Unchanged supported evidence or actual clarification issue | New task revision UNASSIGNED; description derived, no submitted DONE/actor | New lineage; former task and completion remain historical |
| ST-07 | Actor confirms own ownership at current case and task versions | Unchanged | ASSIGNED or reaffirmed self; cannot take another owner without future reassignment contract | OWNER_CONFIRMED event is not acknowledgement/completion |
| ST-08 | Actor acknowledges eligible exact task revision | Unchanged | Own personal acknowledgement event; summary follows precedence above | Exact dependencies copied; no clinical approval and no source resolution |
| ST-09 | Current assigned actor completes eligible task | Unchanged, including unresolved clarification issues | DONE for this task revision; historical event appended | Rehearsal unchanged; future replacement changes validity only |
| ST-10 | Create supported fixed rehearsal item | Unchanged | Unchanged | NOT_REVIEWED, exact source and item revision, AUTHORED mode |
| ST-11 | Current item attempt matches quoted choice | Unchanged | Unchanged | MATCH attempt; REVIEWED_FOR_VERSION with current validity; textual agreement only |
| ST-12 | Mismatch or unclear attempt | Unchanged | Unchanged | Record MISMATCH/UNCLEAR; NOT_REVIEWED remains until a MATCH; do not invent advice or rewrite a previous attempt |
| ST-13 | New key with stale case/resource revision | No change | 412 case or 409 resource rejection; zero accepted event/receipt | No new attempt/ack; refresh and explicit review required |
| ST-14 | Exact previously accepted retry, actor still authorized | Current state unchanged | Return original receipt plus current validity; no new mutation | Original event count preserved even after later invalidation |
| ST-15 | Same actor/key, changed route/payload | No change | 409 IDEMPOTENCY_KEY_REUSED | No event or accepted receipt for conflicting command |
| ST-16 | Reset/expiry | Remove case evidence and revoke access | Remove case projections, events, receipts; old requests cannot restore it | Historical append-only rule ends with explicit case deletion |

A later MISMATCH/UNCLEAR does not erase an earlier MATCH event. The current rehearsal summary for an actor/item uses that actor's latest accepted attempt: MATCH gives REVIEWED_FOR_VERSION, other outcomes give NOT_REVIEWED. After dependency invalidation, NEEDS_REREVIEW dominates until a new supported item revision is reviewed; the old item never becomes current again. RehearsalProjection must be scoped to actor as well as item, to avoid treating one person's answer as everyone's understanding.

Issue history is immutable; applicability is derived from the active source graph. A conflict specifically between old/new documents can cease to block only after an explicit valid replacement establishes their relationship and the new source is reviewed. A third unlinked contradictory source still blocks. Missing detail in the new source still blocks. No generic issue-resolved flag, acknowledgement, task completion or rehearsal chooses disputed wording. If the service cannot demonstrate these applicability rules, it must retain the block.

## Two transaction orders and failure atomicity

Order A: acknowledgement commits for r1; replacement follows. History contains the r1 event, while current validity becomes stale. Identical retry returns that original event with STALE validity.

Order B: replacement commits first; old acknowledgement follows. The old case ETag fails (412); using a new case ETag while retaining old task revision still fails (409). No obsolete acknowledgement is appended. Both operations lock/compare the same case aggregate, including authorization and idempotency. The Day 3 single-object calls and lexical assertions do not prove these orderings under real concurrency.

A conflict, limit failure or process exception must roll back source/link/events/projections/receipt together. Concurrent imports cannot exceed the document cap, concurrent events cannot exceed the event cap, and retry races cannot allocate duplicate accepted events. A revoked actor cannot replay a stored success. Tests must use real separately authenticated service contexts and independent database connections; those tests are pending.

## Complete FR and INV trace

Each row names an acceptance obligation. `red-test-plan.md` records only the subset demonstrated to fail against Day 3; the remainder must not be implied green.

| Contract ID | Spec obligation | Required implementation evidence |
| --- | --- | --- |
| FR-01 | UTF-8 bounds, immutable source capture and explicit unsupported format | Binary/PDF/Unicode/limit tests, exact text readback |
| FR-02 | Field value equals exact source quote with identity/version/offsets | Mismatch, wrong source, duplicate span and empty field cases |
| FR-03 | Server-derived unresolved/conflicted/superseded states | Two unlinked sources, missing detail, acknowledgement cannot resolve |
| FR-04 | Fixed nonclinical task templates; medication read-only | Direct authoritative-path bypass and disguised-description rejection |
| FR-05 | Valid explicit replacement graph and conservative matching | Missing endpoints, cycle/self-link, competing replacement and third-source tests |
| FR-06 | Immutable lineage, affected validity and historical completion | Changed/unchanged fallback, old events, actor-bound acknowledgements |
| FR-07 | Case/resource preconditions, current auth and scoped idempotency | Actual concurrency, changed payload, revoked actor and duplicate receipts |
| FR-08 | Source/item/actor-bound fixed practice with unclear outcome | Quote choices, mismatch/unclear, stale attempts, separate actor summaries |
| FR-09 | Atomic snapshot export preserving unresolved history | Export/source comparison under concurrent mutation |
| FR-10 | Visible simulation, replay, unavailable and offline state | Two-context evidence for sharing; offline/replay screen tests |
| FR-11 | Isolation, bounded requests, inert text and reset | Foreign IDs, forged actor, markup/network absence, deletion and expiry |
| FR-12 | Keyboard/mobile inspection and honest evaluator counts | Observed keyboard/320px paths and artifact-linked run denominators |
| INV-01 | Source/span/event identity immutable, exact provenance | Duplicate ID, mutation/readback and version-bound joins |
| INV-02 | Three state dimensions and personal ownership/acknowledgement | Independent projection transition assertions |
| INV-03 | No upload/ack/completion/rehearsal authenticates source | Conflict remains despite all coordination actions |
| INV-04 | Explicit relationship, uncertain mapping blocked | Graph validation and no model-driven silent supersession |
| INV-05 | Every acknowledgement/attempt names exact revision | Replacement invalidates current validity without relabeling history |
| INV-06 | Historical DONE survives derived STALE | Before/after immutable event digest comparison |
| INV-07 | Stale events rejected; exact retry one accepted event | Both transaction orders and idempotency scope/fingerprint cases |
| INV-08 | No unresolved action; neutral clarification only | Conflicting-source direct API requests remain blocked |
| INV-09 | Medication quotation-only; citations not clinical truth | Clinical-category and allowed-label bypass tests |
| INV-10 | Textual practice and honest execution/sharing labels | No fabricated model/sync or medical competence outcome |
| INV-11 | Source data never grants action authority; case isolation | Inert content plus real unauthorized access/reset tests |

Human review of these specifications does not yet exist. A separate agent may inspect the contract, but participant understanding, clinical review and release acceptance remain pending. See [red tests](red-test-plan.md), [Day 5 handoff](day05-handoff.md) and [security](security-and-boundaries.md).
