# ADR-003 — narrow the system contract before implementation

Status: accepted as a local Day 4 engineering specification, subject to the recorded contract review. Product implementation and human acceptance remain pending. This follows [ADR-002](ADR-002-differentiation-gate.md) and the [Day 3 audit](../day04/day03-audit.md).

The 13 Day 3 tests pass, but additional assertions expose failures in quote/value agreement, clinical task gating, revision identity, replacement validation, idempotency and event immutability. The store is in memory and lacks authorization/transaction guarantees. These findings qualify prior readiness language without deleting historical tests or rewriting their outcomes.

Decisions:

1. Initial input is original fictional UTF-8 plain text only. PDF support and live model schema reliability are unverified. Render Markdown literally and reject unsupported formats; do not treat UTF-8-decoded PDF bytes as extracted text.
2. Published values initially equal their source quotations. Strict schema and source verification must run at the authoritative publication path. Fixed supported appointment/contact patterns and server-owned nonclinical task templates replace trusted candidate category/status/description fields. Uncertain data stays read-only/unresolved.
3. Separate immutable sources, fields, dependencies and events from evidence, task and actor-specific rehearsal projections. Reset can delete a whole case; ordinary changes cannot rewrite history.
4. Use case-level state_version plus exact resource revisions for writes. Authenticate current server context; scope idempotency by case/actor/key and bind method/path/body. Store receipt/event/projection atomically. Day 3 object methods are not a production persistence layer.
5. Use disclosed document-wide invalidation initially. Selective unchanged mapping is a later measured extension, not an existing success. The tradeoff is extra review and potential loss of the proposed selective benefit; compare against manual whole-document review before claiming value.
6. Define 16 operations and 19 records in the [registry](../../contracts/day04/contract.json), with [API semantics](../day04/api-contract.md). This compact project format is dependency-free; translating it into framework-specific schemas is future work and requires validation. Do not call it OpenAPI or claim runtime schema enforcement.
7. Ship no model, multi-device, clinical or usability claims without corresponding evidence. Initial source-choice rehearsal is AUTHORED and role switching is ROLE_SIMULATION. Medication remains quotation-only.

Alternatives considered: immediately adopt the spike classes (rejected because demonstrated gaps violate the base contract); implement a full database/API during specification (deferred so the contract and failing tests precede implementation); preserve fine-grained invalidation claims (rejected without dependency evidence); build a general clinical chatbot (outside scope). Relational transactional persistence remains the architectural target; exact driver/framework locks require a later real compatibility check.

Day 4 acceptance means reviewed specification plus reproducible red assertions, not repaired production behavior. The raw red suite must remain nonzero while the known gaps persist; a separate baseline-integrity check may succeed only if the explicit expected failures and positive controls match exactly with zero errors/skips. No failing test may be removed to manufacture acceptance.

Reopen if whole-document review removes any advantage over a manual checklist, if case serialization creates unacceptable friction, if quoted fields are mistaken for authority, if real transaction/authentication tests cannot pass, or if source/rehearsal complexity cannot be explained at the entrant comprehension checkpoint. That checkpoint, eligibility, user demand and independent label review remain pending. Planned Day 4 effort is five agent-hours; actual productive runtime is unmeasured.
