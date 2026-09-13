# Day 4 security and product boundaries

Status: proposed service requirements and test obligations, **NOT_IMPLEMENTED** unless a separate execution record explicitly demonstrates the relevant behavior. A local spike or a passing documentation verifier does not establish authorization, persistence, real concurrency, injection resistance or deployment readiness. The [Day 1 contract](../day01/scope-and-acceptance.md) controls the nonclinical boundaries; Day 4 adopts UTF-8 plain text only. Prior Day 3 statements about PDF support and broad robustness do not substitute for missing evidence.

## Trust boundary and session lifecycle

Only original fictional English examples may enter this research prototype. The initial service exposes one active synthetic case per session; its boundary is the authenticated server session plus case membership. A random case ID is not authorization. Source documents, candidate extractions, filenames, browser state and request bodies are untrusted. A server-held capability determines who may access each case and perform each operation. Never accept an acting identity, permission, authoritative evidence state or current-validity field from a request body, source text or model output. Task ownership is self-confirmed from the server actor context; the request accepts no assignee or acting-identity field.

Proposed lifecycle: POST session bootstrap creates an isolated synthetic session and its one case; then import bounded text, inspect and coordinate, and reset/delete or expire. Bootstrap establishes a fresh namespace and is the sole exception without a precondition/idempotency key before identity exists; clients must never automatically retry bootstrap. Existing-case operations resolve all document, revision, span, task, event and rehearsal IDs through the case-scoped JSON resource registry; global lookup followed by an optional case check is prohibited. The registry is a logical contract, not proof of a database implementation. Deleted or expired cases cannot be restored through old receipts, pending requests or copied resource IDs.

For initial local implementation, browser access uses a server-issued opaque session credential held in an HttpOnly, SameSite cookie; transport security and origin checks must be enforced before remote exposure. No credentials in URLs or browser-readable project exports. Session theft, CSRF prevention and remote authentication are pending implementation tests, not solved by this specification. An offline or role-switch demonstration must say so visibly; role switching is not authentication or multi-device synchronization (FR-10, FR-11; INV-10, INV-11).

Proposed roles are capabilities, not verified real-world identities:

| Capability role | Permitted scope | Explicit boundary |
| --- | --- | --- |
| OWNER | Import and classify/review source, assert replacement relationship, create supported nonclinical tasks, self-confirm ownership, reset case | Cannot authenticate clinician/source authority, resolve clinical disagreement or write another actor's acknowledgement |
| CAREGIVER | Read authorized case; create permitted tasks/issues; self-confirm ownership; acknowledge/rehearse for own actor and exact revision; record own permitted coordination actions | Cannot import/classify/link source, expand membership, forge another actor, bypass conflict/task gates or modify source history |
| VIEWER | GET authorized synthetic case, documents, history and export only | Cannot acknowledge for participants, mutate tasks or convert a review into clinical approval |

Membership provisioning is server-controlled; public arbitrary role selection is not an authorization mechanism. If the first prototype only simulates these roles, disable shared-write claims and label the simulation. Session revocation is checked on every request, including an idempotent retry. A role does not establish age, consent, clinical credentials or eligibility.

## Concrete initial limits — design decisions, not measured capacity

The canonical limits are in the [contract registry](../../contracts/day04/contract.json) and must be mirrored in schema/HTTP validation before implementation acceptance. Reject whole requests without partial effects; never truncate an accepted source or quotation.

| Resource | Initial bound | Rejection behavior |
| --- | --- | --- |
| Imported source | Strict UTF-8 plain text; 64 KiB decoded-content UTF-8 byte length per document; no binary/NUL content | Reject invalid encoding/unsupported format/size; offer pasted text; no PDF/OCR inference |
| Source inventory | 8 immutable documents per case (at most 512 KiB at the per-document bound) | Reject excess import before allocation/publication |
| HTTP JSON body | 128 KiB encoded request body | Reject before JSON parsing or persistence |
| Review selections | 32 fields per review; 2,000 source characters per field | Reject excess; preserve exact source text; no truncation |
| Event inventory | 1,000 immutable events per case | Reject commands whose transaction would exceed limit; preserve history rather than evicting evidence |
| Session lifetime | 24-hour absolute expiry; expired credentials lose access | Purge case data through deletion path; do not silently extend via activity |

The 128 KiB HTTP body bound is a supplementary transport-design limit; it does not expand the registry document/field limits. Request bodies accept only the fields listed for their operation. There are no arbitrary completion notes, task descriptions or free-text rehearsal answers: descriptions/questions use fixed server templates and rehearsal submits a choice ID or null. Counts must be checked atomically with writes. Rate/transport limits require implementation configuration and tests before hosting; this local design does not authorize a public endpoint. Limits may change only through a recorded contract change and boundary-test update (FR-01, FR-11; INV-11).

## Authoritative writes, replay and history

Every write against an existing case carries an `If-Match` precondition for the global case `state_version`, plus a case/actor-scoped idempotency key. This deliberately serializes unrelated case edits; it is coarse protection, not fine-grained concurrency. Exact resource revision bindings remain separate from the case ETag. The service must atomically validate authorization, resource membership, preconditions and task/evidence gates, then append immutable events, update projections and increment case state_version once for the committed mutation. Missing/stale preconditions or failed gates cannot produce partial state.

Authenticate and authorize the actor first. Within the case/actor/key scope, compare a canonical payload-and-route fingerprint. A matching accepted retry returns the original receipt before applying stale-write checks, with separately derived **current_validity**; it never reapplies the event or restores current acknowledgement validity. A reused key with changed route/payload is rejected. Unauthorized or deleted-case retries cannot retrieve receipts. Failed attempts must not consume an accepted-event identity or publish a success. A missing precondition yields 428 PRECONDITION_REQUIRED; a mismatched case ETag yields 412 CASE_VERSION_MISMATCH; a mismatched bound resource revision yields 409 STALE_REVISION_ERROR. These semantics are mandatory (FR-06, FR-07; INV-05, INV-06, INV-07).

Source upload suspends affected case coordination pending review; a neutral, fixed-template clarification task remains allowed without selecting disputed details. Unresolved sources remain unresolved. An explicit replacement claim initially invalidates dependent state across the replaced document conservatively. It does not authenticate the source. Document-wide rereview can include literally unchanged content; disclose that limitation. Future selective preservation requires exact, attested provenance mapping. Never rewrite an original acknowledgement or completion with the new revision merely because wording matches. A historical event stays at its original source version even when a current derived view becomes stale (FR-05, FR-06, FR-08; INV-01, INV-04, INV-05, INV-06).

## Inert source data and clinical boundaries

Render all source text, names and any future model candidates as escaped text. Markdown-looking content is text in this initial format. Never execute embedded HTML, scripts, shell text, tool requests, remote images, URL previews or document-driven network calls. An ordinary URL inside a quote is not an instruction to fetch it. Future link navigation must be a separate explicit user action under a reviewed policy. Keyword detection is not a sufficient injection defense: remove tool/action authority from the data path and test both obvious and paraphrased malicious content (FR-01, FR-11; INV-11).

An exact anchor requires the immutable document identity, revision and validated character interval, with the quoted slice unchanged. Anchoring proves textual origin only. Candidate schema validity does not prove that a field means what the source says or that extraction is complete. No PDF parser or live model has been validated by this Day 4 contract (FR-02; INV-01, INV-09).

The initial task allowlist is ARRANGE_TRANSPORT, LOCATE_OFFICE_CONTACT and PREPARE_CLARIFICATION. Office contact location and clarification preparation do not send messages or place calls. A fixed-template clarification task may ask about conflicting appointment details without choosing one of them. Medication is a read-only quotation: no dependent task or rehearsal, administration checkbox, dose arithmetic, treatment advice or inferred schedule. Acknowledgement means source review for a revision; rehearsal assesses agreement with cited text only, can record unclear answers, and never authorizes conflicted evidence. Evidence, coordination and rehearsal states remain separate in storage, UI and export (FR-03, FR-04, FR-08, FR-09; INV-02, INV-03, INV-08, INV-09).

## Logging, export and deletion

Operational logs contain only opaque request/case identifiers, operation class, outcome code and measured timing if available. Do not log credential/cookie/header values, source bodies, full model prompts/responses or personal histories. Case audit events are access-controlled product data, not a public diagnostic log. Avoid interpolating source filenames into filesystem paths; filenames are display metadata.

Export is a read-only GET over one committed snapshot. Exports are user-requested, case-authorized snapshots with source/revision identifiers, exact relevant quotations, current-versus-historical state and unresolved questions. Include snapshot state_version/time and simulation/offline/replay labels where applicable. Escape markup and avoid executable content. If CSV export is later added, spreadsheet-formula injection needs its own neutralization and round-trip fidelity tests. Export is not clinical approval; downloaded copies cannot be revoked by server reset (FR-09, FR-10, FR-11; INV-02, INV-10, INV-11).

Hard reset is DELETE case and requires OWNER capability and the current case precondition. Repeated DELETE returns 404 after revocation rather than replaying a deleted receipt. Atomically make the case inaccessible, revoke case-specific access and remove its documents, derived projections, events, rehearsal records and idempotency receipts. Immutable history means no mutation during a live case, not indefinite retention after deletion. Clear local cached case content and pending writes; old tabs must show deleted/expired state. Initial local prototype should not create backups or exported files automatically. If persistence backups are introduced later, their deletion/retention policy becomes a new explicit acceptance dependency.

## Required security evidence

These are planned tests; a red-test stub or negative control does not prove a real service passed them.

| Threat/control | Required observable evidence | Trace |
| --- | --- | --- |
| Actor forgery and cross-case ID access | Two server identities/cases; tampered actor and foreign IDs yield no read/write or existence leak | FR-07, FR-11; INV-07, INV-11 |
| Stale/duplicate writes | Two independently held case versions; one commit; stale second write rejected; exact retry gives one original event and current stale validity after replacement | FR-06, FR-07; INV-05, INV-06, INV-07 |
| Changed-payload retry | Same actor/key with another route or payload rejected without new event | FR-07; INV-07 |
| Source injection/unsafe rendering | Malicious markup and tool/network instructions remain visible text; instrumented execution/network side-effect count zero | FR-11; INV-11 |
| Conflict and medication escape | Direct API candidate bypass attempts cannot publish a prohibited or disputed action; history/rehearsal cannot change evidence authority | FR-03, FR-04, FR-08; INV-03, INV-08, INV-09 |
| Limit races | Concurrent imports cannot exceed count/byte bound; failed request leaves no partial document | FR-01, FR-07, FR-11; INV-07, INV-11 |
| Reset, expiry and cached retry | Fresh read, old tab, old receipt and queued write all fail after deletion/revocation; storage inspection finds no case payload | FR-10, FR-11; INV-10, INV-11 |
| Export/log leakage | Snapshot retains uncertainty/version; malicious fields inert; log capture contains no bodies or credentials | FR-09, FR-11; INV-02, INV-11 |

Implementation must produce actual command output, fixtures and assertions for these claims. Human consent, identity and eligibility remain pending external facts; authorization to build local synthetic artifacts supplies none of them.
