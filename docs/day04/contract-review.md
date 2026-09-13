# Independent contract review — version 0.1.0 specification

This review independently examines the Day 4 contract suite: [`contracts/day04/contract.json`](../../contracts/day04/contract.json), [system specification](system-specification.md), [API contract](api-contract.md), [state and invariants](state-and-invariants.md), [security boundaries](security-and-boundaries.md), and [ADR-003](../decisions/ADR-003-system-contract.md). It evaluates structural rigor, semantic consistency, and boundary enforcement against the authoritative [Day 1 requirements](../day01/scope-and-acceptance.md).

This review is a local engineering audit. It does not constitute human clinical validation, patient comprehension testing, or production security certification.

---

## 1. Scope, data model, and immutability boundaries

The contract registry defines 19 record types and 16 operations. A central finding of the [Day 3 audit](day03-audit.md) was that in-memory Python classes allowed inadvertent post-hoc mutation of historical events (exposed by `test_history_payload_cannot_be_mutated_by_reader`).

The Day 4 contract cleanly bisects the domain into two distinct categories:

1. **Immutable Historical Records (`mutable: false`)**:
   - `SourceDocument`, `SourceSpan`, `Instruction`, `InstructionField`, `EvidenceIssue`, `RevisionLink`, `Dependency`, `CoordinationTask`, `TaskEvent`, `Acknowledgement`, `RehearsalItem`, `RehearsalAttempt`, `CommandReceipt`, `EvaluationRun`.
   - Invariants: Once committed, payloads, timestamps, actor IDs, and cryptographic hashes are read-only. Service implementations must enforce deep immutability (frozen structures or detached defensive copies) to ensure no reader can alter past events (INV-01, INV-05).

2. **Mutable Aggregate Projections (`mutable: true`)**:
   - `Case`, `Actor`, `EvidenceProjection`, `TaskProjection`, `RehearsalProjection`.
   - Invariants: Projections represent the derived current perspective at an explicit `state_version`. Updating a projection never mutates the underlying immutable events; instead, projections are recomputed or transitioned upon new event append.

**Review verdict**: Resolved in specification. The structural separation between immutable event log and derived projections satisfies INV-01, INV-02, and INV-05. Implementation must enforce deep immutability at the persistence boundary.

---

## 2. Concurrency, precondition, and idempotency protocol

The API contract replaces provisional Day 3 object calls with an RFC 9110 / RFC 6585 compliant transactional protocol:

- **Case Snapshot Concurrency**:
  - GET endpoints return a strong `ETag: "case-state-N"`.
  - Mutation endpoints require `If-Match: "case-state-N"`. Missing header yields `428 PRECONDITION_REQUIRED`; stale ETag yields `412 CASE_VERSION_MISMATCH`.
  - This guards against blind overwrites and concurrent conflicting transactions.

- **Resource Revision Integrity**:
  - Even if the case ETag matches, operations addressing an underlying resource (e.g. acknowledging a task) must provide the expected immutable resource revision (e.g. `task_revision`). If an intervening replacement has invalidated that revision to `STALE`, the service atomically rejects the write with `409 STALE_REVISION_ERROR` (INV-07).

- **Scoped Idempotency**:
  - Idempotency is uniquely scoped by `(case_id, actor_id, idempotency_key)`.
  - A SHA-256 fingerprint is computed over `(method, canonical_path, canonical_body)`.
  - Replaying an exact match returns the original `CommandReceipt` with current validity projections without appending duplicate events (`test_idempotent_event_deduplication`).
  - Submitting the same key with an altered operation or modified payload returns `409 IDEMPOTENCY_KEY_REUSED` (resolving the gaps in `test_idempotency_key_cannot_mask_different_operation` and `test_idempotency_key_cannot_mask_different_payload`).

- **Global Case Serialization Trade-off**:
  - ADR-003 explicitly chooses whole-case write serialization over fine-grained row-level locking.
  - *Risk assessment*: Under multi-caregiver concurrent use, unrelated actions (e.g. caregiver B accepting transport while caregiver A confirms contact details) may experience avoidable `412` retries.
  - *Trade-off justification*: For a single-family prototype, whole-case serialization eliminates distributed concurrency hazards, phantom reads, and partially applied split-brain states. The review accepts this constraint for Day 4, with the explicit reopen trigger recorded in ADR-003.

**Review verdict**: Resolved in specification. The concurrency and idempotency semantics address all gaps identified in Spike C.

---

## 3. Clinical boundaries and quotation fidelity

The contract establishes strict nonclinical boundaries and evidence rules:

- **Strict Source Agreement (INV-01, INV-09)**:
  - `test_value_must_be_supported_by_its_quote` demonstrated that Day 3 accepted mismatched wording (`Friday at 14:00` supported by a `Thursday at 10:00` quote).
  - The specification mandates that `InstructionField.value` must be derived directly from the exact anchored source quote or match it identically. Extrapolated, normalized, or hallucinated values return `422 PROVENANCE_INVALID`.

- **Actionable Task Boundary (FR-04, INV-08, INV-09)**:
  - Direct service creation of clinical tasks (e.g. `MODIFY_TREATMENT`, dosage calculations, medication scheduling) is strictly prohibited (`test_service_cannot_create_prohibited_clinical_task`).
  - Allowed task templates are strictly limited to `ARRANGE_TRANSPORT`, `LOCATE_OFFICE_CONTACT`, and `PREPARE_CLARIFICATION`.
  - Disguised tasks attempting to embed clinical instructions under permitted labels (e.g. `ARRANGE_TRANSPORT` with payload "Change treatment now") are rejected (`test_allowed_task_label_cannot_hide_treatment_action`).
  - Medication text is restricted to read-only quotation (`Category.MEDICATION_QUOTE`). No actionable task can bind to medication categories (`test_clinical_category_cannot_spawn_transport`).

- **Unsupported Formats (FR-01, INV-11)**:
  - Input scope is strictly original fictional plain UTF-8 text (≤65,536 bytes).
  - Binary files and UTF-8-decodable plain-text PDF envelopes (`%PDF-...`) must be actively rejected with `415 UNSUPPORTED_FORMAT` (`test_plain_ascii_pdf_is_rejected_by_text_only_importer`).

**Review verdict**: Resolved in specification. Gaps identified by Day 4 red tests are closed by contract invariants and error codes.

---

## 4. Replacement graph and invalidation policy

The replacement mechanics resolve key safety ambiguities from Spike C:

- **Graph Validation (FR-05, INV-04)**:
  - A replacement link must reference two existing distinct documents in the same case (`test_replacement_requires_existing_old_endpoint`).
  - Self-replacement (`prior_document_id == new_document_id`) is strictly rejected (`test_replacement_cannot_point_to_itself`).
  - Replacement asserts a claimed document lineage; it does not authenticate clinical correctness or make the new upload automatically authoritative.

- **Document-Wide Invalidation Policy (INV-05, INV-06)**:
  - ADR-003 selects `DOCUMENT_WIDE` invalidation as the baseline policy. When a replacement link is established, all tasks and rehearsal items depending on the prior document are invalidated to `STALE`.
  - *Evaluation*: This conservative choice prevents dangerous assumptions where unchanged text might have altered clinical meaning due to omitted context. The cost is that users must re-review unchanged items.
  - Historical completion events remain immutable; historical `DONE` is preserved alongside derived `STALE` current validity (INV-06).

**Review verdict**: Resolved in specification. The fallback policy is transparently documented and defended.

---

## 5. Review findings and resolution matrix

| Item | Area | Finding / Gap | Specification Resolution | Status |
| --- | --- | --- | --- | --- |
| CRF-01 | Data Model | Nested event payload mutable in Spike C | Deep immutability & detached defensive read views mandated | Resolved in Spec (FR-06, INV-01) |
| CRF-02 | Ingestion | PDF envelope decoded as plain UTF-8 text | Pre-ingestion magic header check; reject non-plain text with 415 | Resolved in Spec (FR-01, INV-11) |
| CRF-03 | Provenance | Instruction value diverged from source quote | Derive value strictly from exact anchored quote; 422 if mismatched | Resolved in Spec (FR-02, INV-01) |
| CRF-04 | Clinical Gate | Clinical category spawned transport task | Category-to-task compatibility matrix enforced at gate | Resolved in Spec (FR-04, INV-08) |
| CRF-05 | Clinical Gate | Actionable task created directly via service bypass | Direct service mutation enforces identical task boundaries | Resolved in Spec (FR-04, INV-09) |
| CRF-06 | Replacement | Dangling and self-replacement links permitted | Atomic graph validation; reject invalid endpoints with 409 | Resolved in Spec (FR-05, INV-04) |
| CRF-07 | Concurrency | Stale write accepted without case-level check | Strong ETag + If-Match precondition check (412 / 409) | Resolved in Spec (FR-07, INV-07) |
| CRF-08 | Idempotency | Reused key masked altered operation/payload | Canonical SHA-256 request fingerprinting; 409 on mismatch | Resolved in Spec (FR-07, INV-07) |
| CRF-09 | Persistence | In-memory store lacks atomic ACID rollback | Transactional SQL backing required; deferred to implementation | **Implementation Blocker** |
| CRF-10 | Concurrency | Global case lock may cause high contention | Acceptable for prototype; evaluate with multi-user telemetry | **Monitoring Obligation** |
| CRF-11 | Evaluation | Entrant comprehension checkpoint unexecuted | Walkthrough pending; recorded as unresolved dependency | **Evaluation Blocker** |

---

## 6. Review disposition

**Disposition**: **SPECIFICATION ACCEPTED FOR LOCAL DAY 4 MILESTONE.**

The data model, API contract, and state machine specifications in `contracts/day04/contract.json` and `docs/day04/` provide a coherent, mathematically sound specification that resolves the design gaps revealed by the Day 4 red tests.

**Crucial Qualification**: This approval covers the *system specification* only. All 12 assertion failures in `tests/day04/test_contract_gaps.py` remain active, deliberate evidence that the underlying product implementation is not yet built. A passing documentation verifier must never be represented as product completion.
