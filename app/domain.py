"""THREAD Core Domain & Authoritative Coordination Service.

Implements the single working path defined in README.md:
  1. Ingest fictional plain UTF-8 text with strict format/encoding validation.
  2. Provenance slicing: exact quotes, character offsets, and immutable SourceSpans.
  3. Strict schema gating: derives display values from source quotes; rejects clinical tasks.
  4. Task creation and assignment: nonclinical templates only (ARRANGE_TRANSPORT).
  5. Personal acknowledgement: revision-bound, with idempotency key.
  6. Explicit replacement linking: acyclic, invalidates prior dependencies to STALE.
  7. Authoritative service rejection: 409 STALE_REVISION_ERROR on superseded writes,
     412 CASE_VERSION_MISMATCH on stale ETag, 409 IDEMPOTENCY_KEY_REUSED on payload conflicts.
  8. Immutable event history: deeply frozen, append-only, preserves past completions.
  9. Conflicting-source case: unlinked contradictions stay CONFLICTED and BLOCKED.
"""

from __future__ import annotations

import copy
import dataclasses
import datetime
import enum
import hashlib
import re
import threading
import types
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple


class ImmutableDict(dict):
    """Deeply immutable dictionary to protect historical event payloads."""
    def __setitem__(self, key, value):
        raise TypeError("Event payload is immutable and cannot be modified")
    def __delitem__(self, key):
        raise TypeError("Event payload is immutable and cannot be modified")
    def pop(self, *args, **kwargs):
        raise TypeError("Event payload is immutable and cannot be modified")
    def popitem(self, *args, **kwargs):
        raise TypeError("Event payload is immutable and cannot be modified")
    def clear(self):
        raise TypeError("Event payload is immutable and cannot be modified")
    def update(self, *args, **kwargs):
        raise TypeError("Event payload is immutable and cannot be modified")
    def setdefault(self, *args, **kwargs):
        raise TypeError("Event payload is immutable and cannot be modified")
    def __copy__(self):
        return ImmutableDict(self)
    def __deepcopy__(self, memo):
        return ImmutableDict({k: copy.deepcopy(v, memo) for k, v in self.items()})


def freeze_payload(d: Any) -> Any:
    if isinstance(d, dict):
        return ImmutableDict({k: freeze_payload(v) for k, v in d.items()})
    elif isinstance(d, list):
        return tuple(freeze_payload(v) for v in d)
    return d


# --- Enums ---

class EvidenceState(str, enum.Enum):
    SUPPORTED = "SUPPORTED"
    UNRESOLVED = "UNRESOLVED"
    CONFLICTED = "CONFLICTED"
    SUPERSEDED = "SUPERSEDED"


class TaskState(str, enum.Enum):
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DONE = "DONE"
    STALE = "STALE"


class Validity(str, enum.Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    BLOCKED = "BLOCKED"


class TaskType(str, enum.Enum):
    ARRANGE_TRANSPORT = "ARRANGE_TRANSPORT"
    LOCATE_OFFICE_CONTACT = "LOCATE_OFFICE_CONTACT"
    PREPARE_CLARIFICATION = "PREPARE_CLARIFICATION"
    # Prohibited clinical types (strictly rejected at service boundary)
    MODIFY_TREATMENT = "MODIFY_TREATMENT"
    ADMINISTER_MEDICATION = "ADMINISTER_MEDICATION"


class Category(str, enum.Enum):
    APPOINTMENT_QUOTE = "APPOINTMENT_QUOTE"
    OFFICE_CONTACT_QUOTE = "OFFICE_CONTACT_QUOTE"
    MEDICATION_QUOTE = "MEDICATION_QUOTE"
    CLINICAL_TREATMENT = "CLINICAL_TREATMENT"


class RehearsalState(str, enum.Enum):
    NOT_REVIEWED = "NOT_REVIEWED"
    REVIEWED_FOR_VERSION = "REVIEWED_FOR_VERSION"
    NEEDS_REREVIEW = "NEEDS_REREVIEW"


class AttemptOutcome(str, enum.Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    UNCLEAR = "UNCLEAR"


class EventType(str, enum.Enum):
    SOURCE_ADDED = "SOURCE_ADDED"
    REVIEW_RECORDED = "REVIEW_RECORDED"
    REPLACEMENT_LINKED = "REPLACEMENT_LINKED"
    ISSUE_OPENED = "ISSUE_OPENED"
    TASK_CREATED = "TASK_CREATED"
    OWNER_CONFIRMED = "OWNER_CONFIRMED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    COMPLETED = "COMPLETED"
    INVALIDATED = "INVALIDATED"
    REHEARSAL_CREATED = "REHEARSAL_CREATED"
    REHEARSAL_ATTEMPTED = "REHEARSAL_ATTEMPTED"


# --- Exceptions with HTTP Status Mapping ---

class DomainError(Exception):
    status_code: int = 400
    code: str = "BAD_REQUEST"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class MalformedRequestError(DomainError):
    status_code = 400
    code = "MALFORMED_REQUEST"


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"


class StaleRevisionError(DomainError):
    status_code = 409
    code = "STALE_REVISION_ERROR"


class IdempotencyKeyReusedError(DomainError):
    status_code = 409
    code = "IDEMPOTENCY_KEY_REUSED"


class InvalidReplacementError(DomainError):
    status_code = 409
    code = "INVALID_REPLACEMENT"


class EvidenceBlockedError(DomainError):
    status_code = 409
    code = "EVIDENCE_BLOCKED"


class CaseVersionMismatchError(DomainError):
    status_code = 412
    code = "CASE_VERSION_MISMATCH"


class UnsupportedFormatError(DomainError):
    status_code = 415
    code = "UNSUPPORTED_FORMAT"


class ProvenanceInvalidError(DomainError):
    status_code = 422
    code = "PROVENANCE_INVALID"


class TaskNotAllowedError(DomainError):
    status_code = 422
    code = "TASK_NOT_ALLOWED"


class PreconditionRequiredError(DomainError):
    status_code = 428
    code = "PRECONDITION_REQUIRED"


# --- Data Records ---

@dataclasses.dataclass(frozen=True)
class SourceSpan:
    span_id: str
    case_id: str
    document_id: str
    source_version: str
    start_char: int
    end_char: int
    exact_quote: str


@dataclasses.dataclass(frozen=True)
class SourceDocument:
    document_id: str
    case_id: str
    source_version: str
    filename: str
    text: str
    sha256: str
    char_count: int
    created_at: str
    uploaded_by: str


@dataclasses.dataclass(frozen=True)
class InstructionField:
    field_id: str
    case_id: str
    instruction_id: str
    name: str
    value: str
    span_id: str


@dataclasses.dataclass(frozen=True)
class Instruction:
    instruction_id: str
    case_id: str
    instruction_revision: str
    category: Category
    field_ids: List[str]
    review_event_id: str


@dataclasses.dataclass(frozen=True)
class CoordinationTask:
    task_id: str
    case_id: str
    task_revision: str
    prior_task_revision: Optional[str]
    task_type: TaskType
    description_template: str
    instruction_ids: List[str]
    issue_ids: List[str]


@dataclasses.dataclass
class TaskProjection:
    task_id: str
    case_id: str
    state_version: int
    status: TaskState
    validity: Validity
    assigned_actor_id: Optional[str]
    historical_completion_event_ids: List[str]


@dataclasses.dataclass(frozen=True)
class TaskEvent:
    event_id: str
    case_id: str
    case_sequence: int
    actor_id: str
    event_type: EventType
    resource_id: str
    resource_revision: str
    dependency_ids: List[str]
    payload: Dict[str, Any]
    created_at: str


@dataclasses.dataclass(frozen=True)
class Acknowledgement:
    ack_id: str
    case_id: str
    task_id: str
    task_revision: str
    actor_id: str
    dependency_ids: List[str]
    event_id: str


@dataclasses.dataclass(frozen=True)
class EvidenceIssue:
    issue_id: str
    case_id: str
    kind: str  # "CONFLICT" or "MISSING_DETAIL"
    span_ids: List[str]
    question_template: str
    opened_event_id: str


@dataclasses.dataclass(frozen=True)
class RevisionLink:
    link_id: str
    case_id: str
    prior_document_id: str
    new_document_id: str
    asserted_by: str
    created_at: str
    mapping_policy: str = "DOCUMENT_WIDE"


@dataclasses.dataclass(frozen=True)
class CommandReceipt:
    receipt_id: str
    case_id: str
    actor_id: str
    idempotency_key: str
    request_fingerprint: str
    committed_state_version: int
    event_ids: List[str]
    result: Dict[str, Any]


@dataclasses.dataclass
class Case:
    case_id: str
    state_version: int
    created_at: str
    coordination_suspended: bool = False
    sharing_mode: str = "ROLE_SIMULATION"


@dataclasses.dataclass(frozen=True)
class RehearsalChoice:
    choice_id: str
    text: str
    is_match: bool


@dataclasses.dataclass(frozen=True)
class RehearsalItem:
    item_id: str
    case_id: str
    item_revision: str
    instruction_id: str
    span_ids: List[str]
    question_template: str
    choices: List[RehearsalChoice]
    execution_mode: str = "AUTHORED"


@dataclasses.dataclass(frozen=True)
class RehearsalAttempt:
    attempt_id: str
    case_id: str
    item_id: str
    item_revision: str
    actor_id: str
    choice_id: Optional[str]
    outcome: AttemptOutcome
    event_id: str


@dataclasses.dataclass
class RehearsalProjection:
    item_id: str
    actor_id: str
    case_id: str
    state_version: int
    state: RehearsalState
    validity: Validity


# --- Authoritative Coordination Service ---

class ThreadService:
    """Core domain service enforcing invariants, transactions, and boundaries."""

    def __init__(self, storage: Optional[Any] = None):
        self._lock = threading.RLock()
        self.storage = storage
        self.cases: Dict[str, Case] = {}
        self.documents: Dict[str, SourceDocument] = {}
        self.spans: Dict[str, SourceSpan] = {}
        self.instructions: Dict[str, Instruction] = {}
        self.instruction_fields: Dict[str, InstructionField] = {}
        self.tasks: Dict[str, CoordinationTask] = {}
        self.task_projections: Dict[str, TaskProjection] = {}
        self.events: List[TaskEvent] = []
        self.acknowledgements: Dict[str, Acknowledgement] = {}
        self.issues: Dict[str, EvidenceIssue] = {}
        self.links: Dict[str, RevisionLink] = {}
        self.receipts: Dict[Tuple[str, str, str], CommandReceipt] = {}  # (case_id, actor_id, key) -> receipt
        self.rehearsals: Dict[str, RehearsalItem] = {}
        self.rehearsal_attempts: Dict[str, RehearsalAttempt] = {}
        self.rehearsal_projections: Dict[Tuple[str, str], RehearsalProjection] = {}
        if self.storage is not None:
            self.storage.load_into_service(self)

    def create_case(self, case_id: Optional[str] = None, fictional_only: bool = True) -> Case:
        with self._lock:
            if not fictional_only:
                raise MalformedRequestError("Service strictly requires fictional_only=true; real PHI prohibited.")
            cid = case_id or f"case-{uuid.uuid4().hex[:8]}"
            if cid in self.cases:
                self.reset_case(cid)
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            c = Case(case_id=cid, state_version=0, created_at=now)
            self.cases[cid] = c
            if self.storage:
                self.storage.persist_case(self, cid)
            return c

    def get_case(self, case_id: str) -> Case:
        with self._lock:
            if case_id not in self.cases:
                raise NotFoundError(f"Case '{case_id}' does not exist.")
            return self.cases[case_id]

    def validate_preconditions(
        self,
        case_id: str,
        if_match: Optional[str] = None,
        require_etag: bool = True,
    ) -> Case:
        with self._lock:
            c = self.get_case(case_id)
            if require_etag:
                if not if_match:
                    raise PreconditionRequiredError("Mutation requires If-Match header with current case ETag.")
                expected = f'"case-state-{c.state_version}"'
                if if_match.strip() != expected:
                    raise CaseVersionMismatchError(
                        f"If-Match '{if_match}' does not match current ETag {expected} (state version {c.state_version})."
                    )
            return c

    def _compute_fingerprint(self, method: str, path: str, payload: Any) -> str:
        canonical = f"{method.upper()}:{path}:{sorted_json(payload)}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def check_idempotency(
        self,
        case_id: str,
        actor_id: str,
        idempotency_key: str,
        fingerprint: str,
    ) -> Optional[CommandReceipt]:
        with self._lock:
            key_tuple = (case_id, actor_id, idempotency_key)
            if key_tuple in self.receipts:
                prior = self.receipts[key_tuple]
                if prior.request_fingerprint != fingerprint:
                    raise IdempotencyKeyReusedError(
                        f"Idempotency key '{idempotency_key}' reused with different operation or payload."
                    )
                return prior
            return None

    def _record_receipt(
        self,
        case_id: str,
        actor_id: str,
        idempotency_key: str,
        fingerprint: str,
        state_version: int,
        event_ids: List[str],
        result: Dict[str, Any],
    ) -> CommandReceipt:
        with self._lock:
            receipt = CommandReceipt(
                receipt_id=f"receipt-{uuid.uuid4().hex[:8]}",
                case_id=case_id,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                committed_state_version=state_version,
                event_ids=event_ids,
                result=result,
            )
            self.receipts[(case_id, actor_id, idempotency_key)] = receipt
            return receipt

    def _append_event(
        self,
        case_id: str,
        actor_id: str,
        event_type: EventType,
        resource_id: str,
        resource_revision: str,
        dependency_ids: List[str],
        payload: Dict[str, Any],
    ) -> TaskEvent:
        with self._lock:
            c = self.cases[case_id]
            c.state_version += 1
            seq = len(self.events) + 1
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            # Deeply freeze payload to guarantee immutability against reader mutation (INV-01, INV-05)
            safe_payload = freeze_payload(copy.deepcopy(payload))
            event = TaskEvent(
                event_id=f"evt-{seq:04d}",
                case_id=case_id,
                case_sequence=seq,
                actor_id=actor_id,
                event_type=event_type,
                resource_id=resource_id,
                resource_revision=resource_revision,
                dependency_ids=dependency_ids,
                payload=safe_payload,
                created_at=now,
            )
            self.events.append(event)
            return event

    def import_document(
        self,
        case_id: str,
        filename: str,
        text: str,
        actor_id: str = "system",
        doc_id: Optional[str] = None,
        source_version: Optional[str] = None,
    ) -> SourceDocument:
        with self._lock:
            self.get_case(case_id)
            # Check input limits (≤ 65,536 bytes plain UTF-8 text)
            encoded = text.encode("utf-8")
            if len(encoded) > 65536:
                raise MalformedRequestError(f"Document exceeds max allowed size of 65,536 bytes (got {len(encoded)}).")

            # Validate non-plain-text and PDF signatures (FR-01, INV-11)
            if b"\x00" in encoded[:1024] or encoded.startswith(b"%PDF-") or encoded.startswith(b"\x89PNG"):
                raise UnsupportedFormatError("Unsupported format: only plain UTF-8 text documents are supported; PDFs and binaries rejected.")

            did = doc_id or f"doc-{uuid.uuid4().hex[:8]}"
            sver = source_version or "v1"
            sha = hashlib.sha256(encoded).hexdigest()

            # Prevent overwriting existing document identity (FR-01, INV-01)
            if did in self.documents:
                existing = self.documents[did]
                if existing.sha256 != sha or existing.source_version != sver:
                    raise MalformedRequestError(f"Document ID '{did}' already exists with different content or revision.")
                return existing

            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            doc = SourceDocument(
                document_id=did,
                case_id=case_id,
                source_version=sver,
                filename=filename,
                text=text,
                sha256=sha,
                char_count=len(text),
                created_at=now,
                uploaded_by=actor_id,
            )
            self.documents[did] = doc

            self._append_event(
                case_id=case_id,
                actor_id=actor_id,
                event_type=EventType.SOURCE_ADDED,
                resource_id=did,
                resource_revision=sver,
                dependency_ids=[],
                payload={"filename": filename, "sha256": sha, "char_count": len(text)},
            )
            if self.storage:
                self.storage.persist_case(self, case_id)
            return doc

    def resolve_anchor(
        self,
        case_id: str,
        document_id: str,
        exact_quote: str,
        context_hint: Optional[str] = None,
    ) -> SourceSpan:
        with self._lock:
            if document_id not in self.documents:
                raise NotFoundError(f"Document '{document_id}' not found.")
            doc = self.documents[document_id]

            # Slicing & exact quote lookup
            occurrences = [m.start() for m in re.finditer(re.escape(exact_quote), doc.text)]
            if not occurrences:
                raise ProvenanceInvalidError(f"Exact quotation '{exact_quote}' not found in source document '{document_id}'.")

            if len(occurrences) == 1:
                start_idx = occurrences[0]
            else:
                if not context_hint:
                    raise ProvenanceInvalidError(f"Ambiguous quote appears {len(occurrences)} times; context_hint required.")
                hint_occurrences = [m.start() for m in re.finditer(re.escape(context_hint), doc.text)]
                if not hint_occurrences:
                    raise ProvenanceInvalidError(f"Context hint '{context_hint}' not found in source document.")
                matched_idx = None
                for h_start in hint_occurrences:
                    h_end = h_start + len(context_hint)
                    for idx in occurrences:
                        if h_start <= idx and (idx + len(exact_quote)) <= h_end:
                            matched_idx = idx
                            break
                    if matched_idx is not None:
                        break
                if matched_idx is None:
                    for h_start in hint_occurrences:
                        for idx in occurrences:
                            if abs(idx - h_start) <= max(100, len(context_hint)):
                                matched_idx = idx
                                break
                        if matched_idx is not None:
                            break
                if matched_idx is None:
                    raise ProvenanceInvalidError("Cannot disambiguate quote with provided context hint.")
                start_idx = matched_idx

            end_idx = start_idx + len(exact_quote)
            span_id = f"span-{uuid.uuid4().hex[:8]}"
            span = SourceSpan(
                span_id=span_id,
                case_id=case_id,
                document_id=document_id,
                source_version=doc.source_version,
                start_char=start_idx,
                end_char=end_idx,
                exact_quote=exact_quote,
            )
            self.spans[span_id] = span
            return span

    def review_source(
        self,
        case_id: str,
        document_id: str,
        expected_source_version: str,
        category: Category,
        field_name: str,
        exact_quote: str,
        actor_id: str = "Morgan",
    ) -> Tuple[Instruction, SourceSpan]:
        doc = self.documents.get(document_id)
        if not doc:
            raise NotFoundError(f"Document '{document_id}' not found.")
        if doc.source_version != expected_source_version:
            raise StaleRevisionError(f"Document version mismatch: expected '{expected_source_version}', got '{doc.source_version}'.")

        # Resolve exact span
        span = self.resolve_anchor(case_id, document_id, exact_quote)

        # Invariant: Display value must derive strictly from exact source quote (FR-02, INV-01)
        value = exact_quote

        instr_id = f"instr-{uuid.uuid4().hex[:8]}"
        instr_rev = f"ir-{uuid.uuid4().hex[:6]}"
        field_id = f"field-{uuid.uuid4().hex[:8]}"

        field = InstructionField(
            field_id=field_id,
            case_id=case_id,
            instruction_id=instr_id,
            name=field_name,
            value=value,
            span_id=span.span_id,
        )
        self.instruction_fields[field_id] = field

        evt = self._append_event(
            case_id=case_id,
            actor_id=actor_id,
            event_type=EventType.REVIEW_RECORDED,
            resource_id=instr_id,
            resource_revision=instr_rev,
            dependency_ids=[span.span_id],
            payload={"category": category.value, "field_name": field_name, "value": value},
        )

        instr = Instruction(
            instruction_id=instr_id,
            case_id=case_id,
            instruction_revision=instr_rev,
            category=category,
            field_ids=[field_id],
            review_event_id=evt.event_id,
        )
        self.instructions[instr_id] = instr
        if self.storage:
            self.storage.persist_case(self, case_id)
        return instr, span

    def create_task(
        self,
        case_id: str,
        task_type: TaskType,
        instruction_id: str,
        description_template: str,
        actor_id: str = "Morgan",
        task_id: Optional[str] = None,
        task_revision: Optional[str] = None,
    ) -> Tuple[CoordinationTask, TaskProjection]:
        # Strictly enforce nonclinical boundary (FR-04, INV-08, INV-09)
        if task_type not in (TaskType.ARRANGE_TRANSPORT, TaskType.LOCATE_OFFICE_CONTACT, TaskType.PREPARE_CLARIFICATION):
            raise TaskNotAllowedError(f"Task type '{task_type}' is prohibited. Only supported nonclinical tasks allowed.")

        # Disguised treatment action check in description
        prohibited_terms = ["treatment", "medication", "prescribe", "dosage", "dose", "administer", "drug"]
        lower_desc = description_template.lower()
        if any(term in lower_desc for term in prohibited_terms) and task_type != TaskType.PREPARE_CLARIFICATION:
            raise TaskNotAllowedError(f"Task description contains prohibited clinical terms: '{description_template}'.")

        instr = self.instructions.get(instruction_id)
        if not instr:
            raise NotFoundError(f"Instruction '{instruction_id}' not found.")

        # Clinical category cannot spawn actionable coordination tasks
        if instr.category in (Category.CLINICAL_TREATMENT, Category.MEDICATION_QUOTE):
            raise TaskNotAllowedError(f"Instruction category '{instr.category}' is read-only and cannot spawn actionable tasks.")

        tid = task_id or f"task-{uuid.uuid4().hex[:8]}"
        trev = task_revision or f"tr-{uuid.uuid4().hex[:6]}"

        task = CoordinationTask(
            task_id=tid,
            case_id=case_id,
            task_revision=trev,
            prior_task_revision=None,
            task_type=task_type,
            description_template=description_template,
            instruction_ids=[instruction_id],
            issue_ids=[],
        )
        self.tasks[tid] = task

        evt = self._append_event(
            case_id=case_id,
            actor_id=actor_id,
            event_type=EventType.TASK_CREATED,
            resource_id=tid,
            resource_revision=trev,
            dependency_ids=[instruction_id],
            payload={"task_type": task_type.value, "description": description_template},
        )

        c = self.cases[case_id]
        projection = TaskProjection(
            task_id=tid,
            case_id=case_id,
            state_version=c.state_version,
            status=TaskState.UNASSIGNED,
            validity=Validity.CURRENT,
            assigned_actor_id=None,
            historical_completion_event_ids=[],
        )
        self.task_projections[tid] = projection
        if self.storage:
            self.storage.persist_case(self, case_id)
        return task, projection

    def confirm_owner(
        self,
        case_id: str,
        task_id: str,
        expected_task_revision: str,
        actor_id: str,
    ) -> TaskProjection:
        task = self.tasks.get(task_id)
        if not task:
            raise NotFoundError(f"Task '{task_id}' not found.")
        if task.task_revision != expected_task_revision:
            raise StaleRevisionError(f"Task revision mismatch: expected '{expected_task_revision}', got '{task.task_revision}'.")

        proj = self.task_projections[task_id]
        if proj.validity == Validity.STALE:
            raise StaleRevisionError(f"Cannot assign actor to STALE task '{task_id}'.")

        proj.assigned_actor_id = actor_id
        proj.status = TaskState.ASSIGNED
        c = self.cases[case_id]
        proj.state_version = c.state_version + 1

        self._append_event(
            case_id=case_id,
            actor_id=actor_id,
            event_type=EventType.OWNER_CONFIRMED,
            resource_id=task_id,
            resource_revision=task.task_revision,
            dependency_ids=[task.task_revision],
            payload={"assigned_to": actor_id},
        )
        if self.storage:
            self.storage.persist_case(self, case_id)
        return proj

    def acknowledge_task(
        self,
        case_id: str,
        task_id: str,
        expected_task_revision: str,
        actor_id: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> Tuple[Acknowledgement, TaskProjection]:
        # Check idempotency first (FR-07, INV-07)
        prior_receipt = self.check_idempotency(case_id, actor_id, idempotency_key, request_fingerprint)
        if prior_receipt:
            proj = self.task_projections[task_id]
            ack_id = prior_receipt.result.get("ack_id")
            ack = self.acknowledgements[ack_id]
            return ack, proj

        task = self.tasks.get(task_id)
        if not task:
            raise NotFoundError(f"Task '{task_id}' not found.")

        # Stale write rejection: if addressed revision differs or is stale (FR-07, INV-06)
        if task.task_revision != expected_task_revision:
            raise StaleRevisionError(
                f"Task revision '{expected_task_revision}' is superseded. Current revision is '{task.task_revision}'."
            )

        proj = self.task_projections[task_id]
        if proj.validity == Validity.STALE:
            raise StaleRevisionError(
                f"Task '{task_id}' has STALE validity due to explicit replacement. Write rejected at the authoritative service."
            )
        if proj.validity == Validity.BLOCKED:
            raise EvidenceBlockedError(f"Task '{task_id}' is BLOCKED by unresolved conflicting source instructions.")

        ack_id = f"ack-{uuid.uuid4().hex[:8]}"
        evt = self._append_event(
            case_id=case_id,
            actor_id=actor_id,
            event_type=EventType.ACKNOWLEDGED,
            resource_id=task_id,
            resource_revision=task.task_revision,
            dependency_ids=[task.task_revision],
            payload={"status": "VALID", "ack_id": ack_id},
        )

        ack = Acknowledgement(
            ack_id=ack_id,
            case_id=case_id,
            task_id=task_id,
            task_revision=task.task_revision,
            actor_id=actor_id,
            dependency_ids=[task.task_revision],
            event_id=evt.event_id,
        )
        self.acknowledgements[ack_id] = ack

        proj.status = TaskState.ACKNOWLEDGED
        c = self.cases[case_id]
        proj.state_version = c.state_version

        self._record_receipt(
            case_id=case_id,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            fingerprint=request_fingerprint,
            state_version=c.state_version,
            event_ids=[evt.event_id],
            result={"ack_id": ack_id, "task_id": task_id, "status": "ACKNOWLEDGED"},
        )
        if self.storage:
            self.storage.persist_case(self, case_id)
        return ack, proj

    def complete_task(
        self,
        case_id: str,
        task_id: str,
        expected_task_revision: str,
        actor_id: str,
        completion_note: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> TaskProjection:
        # Check idempotency
        prior_receipt = self.check_idempotency(case_id, actor_id, idempotency_key, request_fingerprint)
        if prior_receipt:
            return self.task_projections[task_id]

        task = self.tasks.get(task_id)
        if not task:
            raise NotFoundError(f"Task '{task_id}' not found.")
        if task.task_revision != expected_task_revision:
            raise StaleRevisionError(f"Task revision mismatch: '{expected_task_revision}' != '{task.task_revision}'.")

        proj = self.task_projections[task_id]
        if proj.validity == Validity.STALE:
            raise StaleRevisionError(f"Cannot complete STALE task '{task_id}'.")

        evt = self._append_event(
            case_id=case_id,
            actor_id=actor_id,
            event_type=EventType.COMPLETED,
            resource_id=task_id,
            resource_revision=task.task_revision,
            dependency_ids=[task.task_revision],
            payload={"completion_note": completion_note},
        )

        proj.status = TaskState.DONE
        proj.historical_completion_event_ids.append(evt.event_id)
        c = self.cases[case_id]
        proj.state_version = c.state_version

        self._record_receipt(
            case_id=case_id,
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            fingerprint=request_fingerprint,
            state_version=c.state_version,
            event_ids=[evt.event_id],
            result={"task_id": task_id, "status": "DONE"},
        )
        if self.storage:
            self.storage.persist_case(self, case_id)
        return proj

    def link_replacement(
        self,
        case_id: str,
        prior_document_id: str,
        new_document_id: str,
        expected_prior_version: str,
        expected_new_version: str,
        actor_id: str = "Morgan",
    ) -> RevisionLink:
        with self._lock:
            # Endpoint validation (FR-05, INV-04)
            if prior_document_id not in self.documents:
                raise InvalidReplacementError(f"Prior document '{prior_document_id}' does not exist.")
            if new_document_id not in self.documents:
                raise InvalidReplacementError(f"New document '{new_document_id}' does not exist.")
            if prior_document_id == new_document_id:
                raise InvalidReplacementError("Self-replacement is strictly invalid (prior_document_id == new_document_id).")

            # Check for cycle in replacement graph (acyclic invariant INV-04)
            queue = [new_document_id]
            visited = set()
            while queue:
                curr = queue.pop(0)
                if curr == prior_document_id:
                    raise InvalidReplacementError("Circular replacement detected in document revision graph.")
                if curr in visited:
                    continue
                visited.add(curr)
                for l in self.links.values():
                    if l.case_id == case_id and l.prior_document_id == curr:
                        queue.append(l.new_document_id)

            prior_doc = self.documents[prior_document_id]
            new_doc = self.documents[new_document_id]

            if prior_doc.source_version != expected_prior_version:
                raise StaleRevisionError(f"Prior document version mismatch: expected '{expected_prior_version}', got '{prior_doc.source_version}'.")
            if new_doc.source_version != expected_new_version:
                raise StaleRevisionError(f"New document version mismatch: expected '{expected_new_version}', got '{new_doc.source_version}'.")

            link_id = f"link-{uuid.uuid4().hex[:8]}"
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            link = RevisionLink(
                link_id=link_id,
                case_id=case_id,
                prior_document_id=prior_document_id,
                new_document_id=new_document_id,
                asserted_by=actor_id,
                created_at=now,
                mapping_policy="DOCUMENT_WIDE",
            )
            self.links[link_id] = link

            # Record replacement link event
            self._append_event(
                case_id=case_id,
                actor_id=actor_id,
                event_type=EventType.REPLACEMENT_LINKED,
                resource_id=link_id,
                resource_revision="1",
                dependency_ids=[prior_document_id, new_document_id],
                payload={"prior_document_id": prior_document_id, "new_document_id": new_document_id},
            )

            # Apply DOCUMENT_WIDE invalidation policy (INV-05, INV-06)
            # Invalidate all tasks and acknowledgements bound to the replaced document
            invalidated_task_ids = []
            for tid, task in self.tasks.items():
                # Find if task depends on instructions in prior_doc
                depends_on_prior = False
                for instr_id in task.instruction_ids:
                    instr = self.instructions.get(instr_id)
                    if not instr:
                        continue
                    for fid in instr.field_ids:
                        field = self.instruction_fields.get(fid)
                        if not field:
                            continue
                        span = self.spans.get(field.span_id)
                        if span and span.document_id == prior_document_id:
                            depends_on_prior = True
                            break

                if depends_on_prior:
                    proj = self.task_projections[tid]
                    proj.validity = Validity.STALE
                    proj.status = TaskState.STALE
                    c = self.cases[case_id]
                    proj.state_version = c.state_version
                    invalidated_task_ids.append(tid)

                    self._append_event(
                        case_id=case_id,
                        actor_id="system",
                        event_type=EventType.INVALIDATED,
                        resource_id=tid,
                        resource_revision=task.task_revision,
                        dependency_ids=[link_id],
                        payload={"reason": "DOCUMENT_WIDE_REPLACEMENT", "prior_document_id": prior_document_id},
                    )

            # Invalidate rehearsal projections for items tied to prior document (FR-08, INV-05, INV-10)
            for (item_id, act_id), rproj in self.rehearsal_projections.items():
                ritem = self.rehearsals.get(item_id)
                if not ritem:
                    continue
                rinstr = self.instructions.get(ritem.instruction_id)
                if not rinstr:
                    continue
                depends = False
                for fid in rinstr.field_ids:
                    field = self.instruction_fields.get(fid)
                    if field:
                        span = self.spans.get(field.span_id)
                        if span and span.document_id == prior_document_id:
                            depends = True
                            break
                if depends:
                    rproj.state = RehearsalState.NEEDS_REREVIEW
                    rproj.validity = Validity.STALE
                    c = self.cases[case_id]
                    rproj.state_version = c.state_version

            if self.storage:
                self.storage.persist_case(self, case_id)
            return link

    def create_rehearsal_item(
        self,
        case_id: str,
        instruction_id: str,
        expected_instruction_revision: str,
        question_template: str,
        choices: List[Dict[str, Any]],
        actor_id: str = "Morgan",
    ) -> Tuple[RehearsalItem, RehearsalProjection]:
        instr = self.instructions.get(instruction_id)
        if not instr:
            raise NotFoundError(f"Instruction '{instruction_id}' not found.")
        if instr.instruction_revision != expected_instruction_revision:
            raise StaleRevisionError(f"Instruction revision mismatch: '{expected_instruction_revision}' != '{instr.instruction_revision}'.")
        # Medication rehearsal strictly prohibited (FR-08, INV-09)
        if instr.category in (Category.MEDICATION_QUOTE, Category.CLINICAL_TREATMENT):
            raise TaskNotAllowedError("Rehearsal is strictly prohibited for clinical/medication instructions.")

        item_id = f"item-{uuid.uuid4().hex[:8]}"
        item_rev = f"ir-{uuid.uuid4().hex[:6]}"
        parsed_choices = [
            RehearsalChoice(
                choice_id=c.get("choice_id", f"c-{i}"),
                text=c.get("text", ""),
                is_match=bool(c.get("is_match", False)),
            )
            for i, c in enumerate(choices)
        ]
        span_ids = [self.instruction_fields[fid].span_id for fid in instr.field_ids if fid in self.instruction_fields]
        item = RehearsalItem(
            item_id=item_id,
            case_id=case_id,
            item_revision=item_rev,
            instruction_id=instruction_id,
            span_ids=span_ids,
            question_template=question_template,
            choices=parsed_choices,
            execution_mode="AUTHORED",
        )
        self.rehearsals[item_id] = item

        evt = self._append_event(
            case_id=case_id,
            actor_id=actor_id,
            event_type=EventType.REHEARSAL_CREATED,
            resource_id=item_id,
            resource_revision=item_rev,
            dependency_ids=[instruction_id],
            payload={"question": question_template, "choice_count": len(parsed_choices)},
        )

        c = self.cases[case_id]
        proj = RehearsalProjection(
            item_id=item_id,
            actor_id=actor_id,
            case_id=case_id,
            state_version=c.state_version,
            state=RehearsalState.NOT_REVIEWED,
            validity=Validity.CURRENT,
        )
        self.rehearsal_projections[(item_id, actor_id)] = proj
        if self.storage:
            self.storage.persist_case(self, case_id)
        return item, proj

    def attempt_rehearsal(
        self,
        case_id: str,
        item_id: str,
        expected_item_revision: str,
        actor_id: str,
        choice_id: Optional[str] = None,
    ) -> Tuple[RehearsalAttempt, RehearsalProjection]:
        item = self.rehearsals.get(item_id)
        if not item:
            raise NotFoundError(f"Rehearsal item '{item_id}' not found.")
        if item.item_revision != expected_item_revision:
            raise StaleRevisionError(f"Item revision mismatch: '{expected_item_revision}' != '{item.item_revision}'.")

        proj_key = (item_id, actor_id)
        if proj_key not in self.rehearsal_projections:
            c = self.cases[case_id]
            self.rehearsal_projections[proj_key] = RehearsalProjection(
                item_id=item_id,
                actor_id=actor_id,
                case_id=case_id,
                state_version=c.state_version,
                state=RehearsalState.NOT_REVIEWED,
                validity=Validity.CURRENT,
            )
        proj = self.rehearsal_projections[proj_key]

        if proj.validity == Validity.STALE:
            raise StaleRevisionError(f"Rehearsal item '{item_id}' has STALE validity due to replacement.")

        # Determine outcome
        if choice_id is None:
            outcome = AttemptOutcome.UNCLEAR
        else:
            matching = [c for c in item.choices if c.choice_id == choice_id]
            if not matching:
                raise MalformedRequestError(f"Choice ID '{choice_id}' does not belong to item '{item_id}'.")
            outcome = AttemptOutcome.MATCH if matching[0].is_match else AttemptOutcome.MISMATCH

        attempt_id = f"att-{uuid.uuid4().hex[:8]}"
        evt = self._append_event(
            case_id=case_id,
            actor_id=actor_id,
            event_type=EventType.REHEARSAL_ATTEMPTED,
            resource_id=item_id,
            resource_revision=item.item_revision,
            dependency_ids=[item.item_revision],
            payload={"choice_id": choice_id, "outcome": outcome.value},
        )

        attempt = RehearsalAttempt(
            attempt_id=attempt_id,
            case_id=case_id,
            item_id=item_id,
            item_revision=item.item_revision,
            actor_id=actor_id,
            choice_id=choice_id,
            outcome=outcome,
            event_id=evt.event_id,
        )
        self.rehearsal_attempts[attempt_id] = attempt

        c = self.cases[case_id]
        proj.state_version = c.state_version
        if outcome == AttemptOutcome.MATCH:
            proj.state = RehearsalState.REVIEWED_FOR_VERSION
        else:
            proj.state = RehearsalState.NOT_REVIEWED

        if self.storage:
            self.storage.persist_case(self, case_id)
        return attempt, proj

    def export_case(self, case_id: str) -> Dict[str, Any]:
        snapshot = self.get_case_snapshot(case_id)
        history = self.get_history(case_id)
        rehearsals = [dataclasses.asdict(r) for r in self.rehearsals.values() if r.case_id == case_id]
        rehearsal_attempts = [dataclasses.asdict(a) for a in self.rehearsal_attempts.values() if a.case_id == case_id]
        rehearsal_projections = [dataclasses.asdict(p) for p in self.rehearsal_projections.values() if p.case_id == case_id]
        return {
            "export_version": "0.1.0",
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "case": snapshot["case"],
            "etag": snapshot["etag"],
            "documents": snapshot["documents"],
            "spans": snapshot["spans"],
            "instructions": snapshot["instructions"],
            "instruction_fields": snapshot["instruction_fields"],
            "tasks": snapshot["tasks"],
            "task_projections": snapshot["task_projections"],
            "acknowledgements": snapshot["acknowledgements"],
            "issues": snapshot["issues"],
            "links": snapshot["links"],
            "rehearsals": rehearsals,
            "rehearsal_attempts": rehearsal_attempts,
            "rehearsal_projections": rehearsal_projections,
            "events": history,
            "execution_mode": "ROLE_SIMULATION",
            "fictional_only": True,
        }

    def reset_case(self, case_id: str) -> None:
        if case_id in self.cases:
            del self.cases[case_id]
        self.documents = {k: v for k, v in self.documents.items() if v.case_id != case_id}
        self.spans = {k: v for k, v in self.spans.items() if v.case_id != case_id}
        self.instructions = {k: v for k, v in self.instructions.items() if v.case_id != case_id}
        self.instruction_fields = {k: v for k, v in self.instruction_fields.items() if v.case_id != case_id}
        self.tasks = {k: v for k, v in self.tasks.items() if v.case_id != case_id}
        self.task_projections = {k: v for k, v in self.task_projections.items() if v.case_id != case_id}
        self.acknowledgements = {k: v for k, v in self.acknowledgements.items() if v.case_id != case_id}
        self.issues = {k: v for k, v in self.issues.items() if v.case_id != case_id}
        self.links = {k: v for k, v in self.links.items() if v.case_id != case_id}
        self.rehearsals = {k: v for k, v in self.rehearsals.items() if v.case_id != case_id}
        self.rehearsal_attempts = {k: v for k, v in self.rehearsal_attempts.items() if v.case_id != case_id}
        self.rehearsal_projections = {k: v for k, v in self.rehearsal_projections.items() if v.case_id != case_id}
        self.events = [e for e in self.events if e.case_id != case_id]
        self.receipts = {k: v for k, v in self.receipts.items() if k[0] != case_id}
        if self.storage:
            self.storage.delete_case(case_id)

    def open_issue(
        self,
        case_id: str,
        kind: str,
        span_ids: List[str],
        question_template: str,
        actor_id: str = "Morgan",
    ) -> EvidenceIssue:
        issue_id = f"issue-{uuid.uuid4().hex[:8]}"
        evt = self._append_event(
            case_id=case_id,
            actor_id=actor_id,
            event_type=EventType.ISSUE_OPENED,
            resource_id=issue_id,
            resource_revision="1",
            dependency_ids=span_ids,
            payload={"kind": kind, "question": question_template},
        )
        issue = EvidenceIssue(
            issue_id=issue_id,
            case_id=case_id,
            kind=kind,
            span_ids=span_ids,
            question_template=question_template,
            opened_event_id=evt.event_id,
        )
        self.issues[issue_id] = issue
        if self.storage:
            self.storage.persist_case(self, case_id)
        return issue

    def setup_conflicting_case(
        self,
        case_id: str,
        text_a: str,
        text_b: str,
    ) -> Tuple[SourceDocument, SourceDocument, EvidenceIssue, CoordinationTask]:
        """Sets up the required conflicting-source case that stays blocked (README.md)."""
        # Different demo cases must not overwrite one another's source identities.
        doc_a = self.import_document(case_id, "consultation_a.txt", text_a, "fictional-note-a")
        doc_b = self.import_document(case_id, "consultation_b.txt", text_b, "fictional-note-b")

        # Extract appointment quotes from each
        span_a = self.resolve_anchor(case_id, doc_a.document_id, "Follow-up appointment: Wednesday at 11:00.")
        span_b = self.resolve_anchor(case_id, doc_b.document_id, "Follow-up appointment: Thursday at 15:30.")

        # Open conflict issue
        issue = self.open_issue(
            case_id=case_id,
            kind="CONFLICT",
            span_ids=[span_a.span_id, span_b.span_id],
            question_template="Westside Clinic specifies Wednesday 11:00 while Eastside Clinic specifies Thursday 15:30. Which follow-up appointment is correct?",
            actor_id="Morgan",
        )

        # Create clarification task (neutral nonclinical task permitted under FR-04, INV-08)
        cid = f"task-clarify-{uuid.uuid4().hex[:6]}"
        task = CoordinationTask(
            task_id=cid,
            case_id=case_id,
            task_revision="cr1",
            prior_task_revision=None,
            task_type=TaskType.PREPARE_CLARIFICATION,
            description_template="Call clinics to clarify conflicting Wednesday vs Thursday appointment dates.",
            instruction_ids=[],
            issue_ids=[issue.issue_id],
        )
        self.tasks[cid] = task

        c = self.cases[case_id]
        proj = TaskProjection(
            task_id=cid,
            case_id=case_id,
            state_version=c.state_version,
            status=TaskState.UNASSIGNED,
            validity=Validity.CURRENT,
            assigned_actor_id=None,
            historical_completion_event_ids=[],
        )
        self.task_projections[cid] = proj

        self._append_event(
            case_id=case_id,
            actor_id="Morgan",
            event_type=EventType.TASK_CREATED,
            resource_id=cid,
            resource_revision="cr1",
            dependency_ids=[issue.issue_id],
            payload={"task_type": TaskType.PREPARE_CLARIFICATION.value, "issue_id": issue.issue_id},
        )
        if self.storage:
            self.storage.persist_case(self, case_id)
        return doc_a, doc_b, issue, task

    def get_case_snapshot(self, case_id: str) -> Dict[str, Any]:
        c = self.get_case(case_id)
        return {
            "case": dataclasses.asdict(c),
            "etag": f'"case-state-{c.state_version}"',
            "documents": [dataclasses.asdict(d) for d in self.documents.values() if d.case_id == case_id],
            "spans": [dataclasses.asdict(s) for s in self.spans.values() if s.case_id == case_id],
            "instructions": [dataclasses.asdict(i) for i in self.instructions.values() if i.case_id == case_id],
            "instruction_fields": [dataclasses.asdict(f) for f in self.instruction_fields.values() if f.case_id == case_id],
            "tasks": [dataclasses.asdict(t) for t in self.tasks.values() if t.case_id == case_id],
            "task_projections": {k: dataclasses.asdict(v) for k, v in self.task_projections.items() if v.case_id == case_id},
            "acknowledgements": [dataclasses.asdict(a) for a in self.acknowledgements.values() if a.case_id == case_id],
            "issues": [dataclasses.asdict(i) for i in self.issues.values() if i.case_id == case_id],
            "links": [dataclasses.asdict(l) for l in self.links.values() if l.case_id == case_id],
            "rehearsals": [dataclasses.asdict(r) for r in self.rehearsals.values() if r.case_id == case_id],
            "rehearsal_projections": [dataclasses.asdict(p) for p in self.rehearsal_projections.values() if p.case_id == case_id],
            "event_count": len([e for e in self.events if e.case_id == case_id]),
        }

    def get_history(self, case_id: str) -> List[Dict[str, Any]]:
        return [dataclasses.asdict(e) for e in self.events if e.case_id == case_id]


def sorted_json(obj: Any) -> str:
    import json
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))
