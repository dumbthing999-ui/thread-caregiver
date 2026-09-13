# Day 3 Architecture & State Contracts

## 1. System Architecture Overview

THREAD is an evidence-grounded, version-aware nonclinical caregiver coordination and rehearsal platform. The architecture separates untrusted model extraction from authoritative deterministic state management:

```
┌─────────────────┐       ┌──────────────────────┐       ┌────────────────────────┐
│  Source Input   │ ───>  │  Immutable Snapshot  │ ───>  │ Candidate Model Extract│
│ (Plain/PDF text)│       │  (SHA-256 Verified)  │       │ (Untrusted Proposals)  │
└─────────────────┘       └──────────────────────┘       └────────────────────────┘
                                                                     │
                                                                     ▼
┌─────────────────┐       ┌──────────────────────┐       ┌────────────────────────┐
│ UI Presentation │ <───  │ Authoritative State  │ <───  │   Deterministic Task   │
│   and Export    │       │ (Event-Sourced Store)│       │          Gate          │
└─────────────────┘       └──────────────────────┘       └────────────────────────┘
```

---

## 2. Core Record Types

### 2.1 Evidence Records

#### `SourceDocument`
Represents an ingested, immutable source document.
```python
@dataclasses.dataclass(frozen=True)
class SourceDocument:
    doc_id: str             # Unique identifier (e.g. "doc-001")
    filename: str           # Source filename
    raw_content: str        # Exact UTF-8 text representation
    sha256_hash: str        # Cryptographic digest of source bytes
    total_chars: int        # Character length
    total_lines: int        # Line count
    created_at: str         # ISO 8601 UTC timestamp
```

#### `SourceSpan`
Exact character-level anchor resolving directly into `SourceDocument.raw_content`.
```python
@dataclasses.dataclass(frozen=True)
class SourceSpan:
    span_id: str            # Unique span identifier
    doc_id: str             # Parent document identifier
    start_char: int         # 0-indexed inclusive start offset
    end_char: int           # 0-indexed exclusive end offset
    line_start: int         # 1-indexed line start
    col_start: int          # 1-indexed column start
    line_end: int           # 1-indexed line end
    col_end: int            # 1-indexed column end
    exact_quote: str        # Identical substring at raw_content[start_char:end_char]
    page_index: int = 0     # 0-indexed page number
```

#### `Instruction`
A clinical instruction card extracted from source text.
```python
@dataclasses.dataclass(frozen=True)
class Instruction:
    instruction_id: str
    revision_id: str
    category: InstructionCategory  # FOLLOW_UP_APPOINTMENT, OFFICE_CONTACT, MEDICATION_SUMMARY
    fields: list[InstructionField]
    state: EvidenceState          # SOURCE_SUPPORTED, UNRESOLVED, CONFLICTED, SUPERSEDED
```

#### `InstructionField`
A single typed attribute within an instruction, bound to an exact provenance span.
```python
@dataclasses.dataclass(frozen=True)
class InstructionField:
    name: str               # e.g., "appointment_time", "clinic_location", "contact_phone"
    value: str              # Normalized display value
    span: SourceSpan        # Verifiable source anchor
```

---

### 2.2 Coordination & Concurrency Records

#### `CoordinationTask`
A supported nonclinical task assigned to a caregiver.
```python
@dataclasses.dataclass
class CoordinationTask:
    task_id: str
    task_type: TaskType     # ARRANGE_TRANSPORT, CALL_OFFICE, CLARIFY_CONFLICT
    description: str
    bound_revision_id: str  # Revision this task is currently bound to
    status: TaskStatus      # UNASSIGNED, ASSIGNED, ACKNOWLEDGED, DONE, STALE
    assigned_to: Optional[str] = None
    completion_note: Optional[str] = None
    historical_completion: Optional[str] = None
```

#### `TaskEvent`
Append-only immutable event record powering the audit history.
```python
@dataclasses.dataclass(frozen=True)
class TaskEvent:
    event_id: str
    idempotency_key: str    # Unique client-provided idempotency token
    task_id: str
    revision_id: str
    actor: str              # Caregiver or Coordinator identifier
    action_type: str        # ASSIGN, ACKNOWLEDGE, COMPLETE, INVALIDATE
    payload: dict
    timestamp: str          # ISO 8601 UTC timestamp
```

#### `Acknowledgement`
Caregiver confirmation bound to an exact document revision.
```python
@dataclasses.dataclass
class Acknowledgement:
    ack_id: str
    revision_id: str        # Exact revision acknowledged
    actor: str              # Caregiver identifier
    status: str             # "VALID", "STALE"
    timestamp: str
```

#### `RevisionLink`
Explicitly declared relationship between two document versions.
```python
@dataclasses.dataclass(frozen=True)
class RevisionLink:
    link_id: str
    prior_revision_id: str  # Superseded revision
    new_revision_id: str    # Replacement revision
    asserted_by: str        # User or Coordinator who verified replacement
    timestamp: str
```

---

## 3. State Models & Transitions

THREAD enforces strict separation across three distinct state domains:

### 3.1 Evidence State
Tracks whether extracted facts are supported, ambiguous, or superseded by document updates:
- **`SOURCE_SUPPORTED`**: Supported by an exact verifiable quotation in an active document.
- **`UNRESOLVED`**: Mentioned in source but lacks complete required fields (e.g. appointment date without a time).
- **`CONFLICTED`**: Two unlinked documents assert contradictory instructions (e.g., Wednesday 11:00 vs Thursday 15:30).
- **`SUPERSEDED`**: Replaced by an explicit newer revision via `RevisionLink`.

### 3.2 Coordination State
Tracks caregiver task ownership and execution:
- **`UNASSIGNED`**: Task identified, awaiting caregiver owner.
- **`ASSIGNED`**: Caregiver accepted responsibility.
- **`DONE`**: Task completed and recorded in audit log.
- **`STALE`**: Underlying source wording changed; task requires re-review.

### 3.3 Rehearsal State
Tracks teach-back comprehension of source instructions:
- **`NOT_REVIEWED`**: No rehearsal attempt recorded.
- **`REVIEWED_FOR_VERSION`**: Successfully rehearsed against exact revision `rX`.
- **`NEEDS_REREVIEW`**: Revision changed to `rY`; prior rehearsal comprehension invalidated.

---

## 4. Concurrency & Rejection Contract

To prevent silent race conditions between caregivers operating on stale documents:

1. **Optimistic Revision Check**:
   Every state-modifying request MUST submit `expected_revision_id` and `idempotency_key`.
2. **Atomic Service-Side Rejection**:
   If `expected_revision_id != current_active_revision_id`:
   - Service returns `409 Conflict` with error code `STALE_REVISION_ERROR`.
   - No event is appended; database state remains unchanged.
3. **Idempotent Deduplication**:
   If an event with an identical `idempotency_key` is received:
   - Service returns the existing entity state with `200 OK`.
   - No duplicate event is appended to `TaskEvent`.
4. **Historical Completion Preservation**:
   When an explicit replacement marks a task `STALE`, any prior `TaskEvent` (such as completed transport booking for revision 1) remains permanent in the event store.

---

## 5. API Shapes (Target for Day 4)

| Endpoint | Method | Input Payload | Concurrency Header | Success Response | Conflict Response |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/api/v1/documents` | `POST` | `{ "filename": str, "content": str }` | None | `201 Created` (`SourceDocument`) | `400 Bad Request` |
| `/api/v1/revisions/{id}/replacement` | `POST` | `{ "replaces_revision_id": str }` | `Idempotency-Key` | `200 OK` (`RevisionLink`) | `404 Not Found` |
| `/api/v1/tasks/{id}/assign` | `POST` | `{ "actor": str }` | `If-Match: rev_id`, `Idempotency-Key` | `200 OK` (`CoordinationTask`) | `409 Conflict` (`STALE_REVISION_ERROR`) |
| `/api/v1/revisions/{id}/acknowledge` | `POST` | `{ "actor": str }` | `If-Match: rev_id`, `Idempotency-Key` | `200 OK` (`Acknowledgement`) | `409 Conflict` (`STALE_REVISION_ERROR`) |
| `/api/v1/tasks/{id}/complete` | `POST` | `{ "actor": str, "note": str }` | `If-Match: rev_id`, `Idempotency-Key` | `200 OK` (`CoordinationTask`) | `409 Conflict` (`STALE_REVISION_ERROR`) |
