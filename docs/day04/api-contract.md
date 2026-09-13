# API contract — version 0.1.0, unimplemented

The [registry](../../contracts/day04/contract.json) lists 16 operations with methods, routes, roles, exact top-level request fields, primary result types and requirement references. This document supplies transport, nested payload and transaction semantics. It supersedes provisional Day 3 endpoint examples for future implementation. No HTTP service is created or tested by this pack.

## Request and response rules

JSON bodies use UTF-8, reject duplicate keys/unknown fields and must match the operation's exact request fields. A nullable `?` field is still required, with null when unused. GET and DELETE accept no body. All IDs in bodies and paths are validated against the authenticated case. Invalid type/shape returns MALFORMED_REQUEST; a present quote with invalid source identity or offsets returns PROVENANCE_INVALID. No endpoint trusts caller `actor`, `state`, `status`, `value`, task description, or precomputed current validity.

`POST /api/v1/sessions` accepts only `{"fictional_only": true}`. It creates one synthetic case at state_version 0, an owner actor and a server session capability in an HttpOnly cookie. False or omitted fictional-only fails. The session credential is never in JSON or logs. Bootstrap has no prior identity/version and is not automatically retried; an interrupted bootstrap can leave only an expiring empty case. Do not promise exactly-once bootstrap.

Protected GET responses carry a strong case snapshot ETag, `"case-state-N"`, and `Cache-Control: no-store`. Existing-case writes require that ETag in `If-Match` plus a 16–128 printable ASCII `Idempotency-Key`. Only one quoted strong tag is accepted; weak tags, lists and wildcard are rejected by this bounded API. All command routes use the case snapshot as their concurrency representation. Missing either required header yields 428 PRECONDITION_REQUIRED. A false If-Match yields 412 CASE_VERSION_MISMATCH; domain revision mismatch yields 409 STALE_REVISION_ERROR. HTTP precondition behavior follows [RFC 9110 section 13.1.1](https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match); 428 is defined by [RFC 6585 section 3](https://www.rfc-editor.org/rfc/rfc6585.html#section-3). The resource-level revision error and key policy are project choices.

Successful write response, except bootstrap and deletion:

```json
{
  "receipt": {
    "receipt_id": "receipt_example",
    "committed_state_version": 8,
    "event_ids": ["event_example"],
    "result": {"resource_ids": ["ack_example"]}
  },
  "resources": [],
  "current_state_version": 8,
  "current_validity": "CURRENT",
  "replayed": false
}
```

This is a shape example, not a runtime receipt. `resources` contains complete authorized records of the operation's primary result type. Source review may create multiple instructions. Ownership/completion return the task projection. A snapshot GET returns `{case, actors, documents, instructions, fields, issues, evidence, tasks, acknowledgements, rehearsal_items, rehearsal_attempts, rehearsal_state, execution_mode}` at one committed version. Document GET returns its source record plus spans. History GET returns `{events, next_cursor}` with at most 100 events, ordered by case sequence; optional opaque `cursor` query only. Source text is inert data, including in JSON exports.

All errors return `{error: {code, message, request_id}}`; after successful authorization, a stale/precondition error may additionally include `current_state_version` and the addressed current resource revision. Do not return other-case resource existence or source excerpts in errors. Codes and HTTP statuses are closed in the registry. No rejected command appends a domain event, receipt or version increment. Minimal operational rejection counters must not contain source text or identity secrets.

## Operation-specific constraints

| Operation | Additional required semantics |
| --- | --- |
| import_document | Owner only; `media_type` exactly `text/plain`; filename is display-only; text ≤65,536 UTF-8 bytes, at most 8 documents/case; no remote URL fetching. Suspends actionable coordination immediately. Duplicate text may create a distinct explicit source; same idempotency key cannot create another. |
| review_source | Owner only; selections array 1–32, each exactly `{category, field_name, start_char, end_char}`. Document and expected source version must match. Derive literal value/quote from source; create spans, instructions, evidence projections and review event in one transaction. Review cannot pick one of conflicting unlinked sources. |
| link_replacement | Owner only; both IDs exist in same case and exact expected source versions match; old≠new, no cycle, no already accepted competing successor. Initial mapping policy is always DOCUMENT_WIDE, assertion_is_authentication always false. Return INVALID_REPLACEMENT for invalid graph; never create a source implicitly. |
| open_issue | Same-case existing spans, at least one; `kind` is CONFLICT or MISSING_DETAIL. Server constructs neutral question template. Any relevant actionable dependent task becomes blocked; historical completion remains. |
| create_task | Task type from allowed enum; instruction revisions listed in the same order as instruction IDs, with no duplicates. Transport/contact need appropriate current supported source; clarification needs actual issue IDs and chooses no disputed wording. New immutable task ID and revision; status UNASSIGNED, owner null. |
| confirm_owner | Self-confirmation from actor context; exact task revision/current eligibility; take an unowned task or reaffirm self. Reassigning another actor's task is unavailable initially. Creates OWNER_CONFIRMED event, not an acknowledgement. |
| acknowledge | Own reviewed-wording event for exact eligible task revision, with copied current dependency IDs. Does not set owner, complete task or settle evidence. No acknowledgement on stale/blocked actionable task. |
| complete_task | Only assigned authenticated actor, current task revision and eligible evidence. A clarification task can complete preparation while conflict stays unresolved. Completion never sends a message or changes source truth. |
| create_rehearsal | Supported appointment/contact only, expected instruction revision; fixed quoted choices and server-owned question. No medication/clinical rehearsal and no external model claim. |
| attempt_rehearsal | Choice ID belongs to the current item revision or null for UNCLEAR. Server calculates MATCH/MISMATCH/UNCLEAR against fixed source choice. Incoming outcome/feedback is rejected. |
| export_case | GET, no mutation; one committed snapshot with all source/version references, owners, historical/current acknowledgement validity, conflicts, questions and mode labels; application/json initially. Future print format must preserve the same content. |
| delete_case | Owner only, both write headers required, atomic removal/revocation, 204 with no body. Retry after revocation gets 404/401 rather than a deleted receipt. Never recreate a case on retry. |

No live extraction endpoint is included: Day 3 has not established model access or schema fidelity. A future adapter needs a versioned command and outage tests before being added. Session sharing and identity grants likewise require a later reviewed extension; the initial UI uses honestly labeled role simulation rather than an unimplemented invitation flow.

## Transaction, authorization and idempotency order

1. Bound request parsing and obtain server session context. Enter the case transaction; verify current session/case access and required role. Unknown/deleted/foreign case is concealed; revoked sessions cannot recover old receipts.
2. Resolve route IDs within that case and validate shape. Compute SHA-256 of method, canonical path and canonical JSON body (sorted keys, no insignificant whitespace, preserved string values). The fingerprint excludes If-Match so a retry with a refreshed view can retrieve its original outcome. No JSON numbers beyond bounded integers are accepted by this contract.
3. Look up `(case_id, actor_id, idempotency_key)`. Same fingerprint returns original receipt with fresh current validity, no event, no version increment; changed fingerprint returns 409 IDEMPOTENCY_KEY_REUSED. Receipt replay is checked before stale preconditions only after current authorization. It never resurrects validity and never impersonates a different actor.
4. For a new key, compare case ETag, expected immutable resource revision(s), references and evidence gate. A stale case token yields 412 even if an old task token also differs; with a fresh case token and obsolete dependency, return 409 STALE_REVISION_ERROR. Current but conflicted evidence yields 409 EVIDENCE_BLOCKED.
5. Append immutable events, receipt and revised projections; increment case state_version once in the same transaction. Commit before responding. Identical simultaneous requests share a unique receipt constraint; exactly one commits. Failure/crash rolls back. Case creation/deletion exceptions are explicit above.

Global case serialization is deliberately conservative: unrelated changes can require a refresh. This is acceptable for a one-case prototype and does not claim fine-grained locking. The future database adapter must prove this algorithm under real separate connections, replacement/write interleavings, duplicate concurrent commands, process failure and revoked access. The Day 3 object methods do not satisfy it.

## Fictional retry example

Morgan reads task `transport_v1` with ETag `"case-state-7"` and submits acknowledgement with expected task revision `tr1` and key `ack-morgan-demo-01`. If replacement commits first, the new acknowledgement gets 412 and no event; a refreshed request still naming tr1 gets 409 STALE_REVISION_ERROR. Morgan must inspect new wording and explicitly acknowledge a newly created task revision under a new key.

If Morgan's original acknowledgement committed first at state 8 but the response was lost, replacement at state 9 makes its current validity stale. Retrying the identical acknowledgement/key returns the original state-8 receipt, current_state_version 9 and current_validity STALE. The historical event exists once, and no current acknowledgement for the new source is manufactured (FR-06, FR-07; INV-05–07).

See [state rules](state-and-invariants.md) for domain guards and [security](security-and-boundaries.md) for session expiry, limits and deletion. All examples remain authored specifications.
