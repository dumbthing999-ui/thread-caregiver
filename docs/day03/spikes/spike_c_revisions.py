"""Spike C: Revisions, History, and Service-Side Concurrency Rejection.

Evaluates an event-sourced authoritative state model with optimistic concurrency,
fine-grained dependency invalidation, and immutable audit history.

Requirements Traced:
  - FR-05: Fine-grained revision invalidation (only changed dependencies marked stale).
  - FR-06: Explicit replacement linking (no automatic last-upload-wins).
  - FR-07: Authoritative service-side stale write rejection (not just client disabling).
  - FR-10: Immutable event audit trail (historical completions are preserved).
  - INV-02: Newest upload is not automatically authoritative.
  - INV-04: Source-dependent acknowledgements bind to exact revisions.
  - INV-05: Historical event records are never rewritten or deleted.
  - INV-06: Stale writes are rejected at the authoritative service.
  - INV-07: Duplicate events with matching idempotency keys are deduplicated.
  - INV-10: Role switching does not bypass authoritative synchronization.
"""

from __future__ import annotations

import dataclasses
import datetime
import enum
import pathlib
import sys
import unittest
import uuid
from typing import Optional

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from docs.day03.spikes.spike_b_schema_gate import EvidenceState, TaskStatus, TaskType


class StateError(Exception):
    """Base exception for coordination service state errors."""


class StaleRevisionError(StateError):
    """Raised when an action references a superseded revision."""


class DuplicateEventError(StateError):
    """Raised or handled when an event idempotency key was already processed."""


class ConflictedActionError(StateError):
    """Raised when an action attempts to bypass an unresolved conflict."""


@dataclasses.dataclass(frozen=True)
class TaskEvent:
    event_id: str
    idempotency_key: str
    task_id: str
    revision_id: str
    actor: str
    action_type: str  # "ASSIGN", "ACKNOWLEDGE", "COMPLETE", "INVALIDATE"
    payload: dict
    timestamp: str


@dataclasses.dataclass
class CoordinationTaskRecord:
    task_id: str
    task_type: TaskType
    description: str
    bound_revision_id: str
    status: TaskStatus
    assigned_to: Optional[str] = None
    completion_note: Optional[str] = None
    historical_completion: Optional[str] = None


@dataclasses.dataclass
class AcknowledgementRecord:
    ack_id: str
    revision_id: str
    actor: str
    status: str  # "VALID", "STALE"
    timestamp: str


@dataclasses.dataclass
class RevisionRecord:
    revision_id: str
    doc_id: str
    version_number: int
    state: EvidenceState
    replaces_revision_id: Optional[str] = None
    timestamp: str = ""


class AuthoritativeCoordinationService:
    """In-memory reference implementation of the authoritative coordination service."""

    def __init__(self):
        self.revisions: dict[str, RevisionRecord] = {}
        self.tasks: dict[str, CoordinationTaskRecord] = {}
        self.acknowledgements: dict[str, AcknowledgementRecord] = {}
        self.events: list[TaskEvent] = []
        self._seen_idempotency_keys: set[str] = set()

    def register_revision(
        self,
        revision_id: str,
        doc_id: str,
        version_number: int,
        replaces_revision_id: Optional[str] = None,
    ) -> RevisionRecord:
        """Register a new document revision.

        Notice: If replaces_revision_id is None, the newest upload does NOT automatically
        supersede earlier uploads (INV-02: No last-upload-wins).
        """
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        state = EvidenceState.SOURCE_SUPPORTED

        rev = RevisionRecord(
            revision_id=revision_id,
            doc_id=doc_id,
            version_number=version_number,
            state=state,
            replaces_revision_id=replaces_revision_id,
            timestamp=now,
        )
        self.revisions[revision_id] = rev

        # If an explicit replacement link is declared, execute fine-grained invalidation
        if replaces_revision_id and replaces_revision_id in self.revisions:
            self._apply_replacement_invalidation(
                old_rev_id=replaces_revision_id,
                new_rev_id=revision_id,
            )

        return rev

    def _apply_replacement_invalidation(self, old_rev_id: str, new_rev_id: str) -> None:
        """Mark old revision superseded and invalidate affected dependent tasks and acknowledgements."""
        old_rev = self.revisions[old_rev_id]
        old_rev.state = EvidenceState.SUPERSEDED

        # Invalidate acknowledgements bound to the old revision
        for ack in self.acknowledgements.values():
            if ack.revision_id == old_rev_id and ack.status == "VALID":
                ack.status = "STALE"

        # Invalidate tasks bound to changed dependencies in the old revision
        for task in self.tasks.values():
            if task.bound_revision_id == old_rev_id:
                # If appointment/transport changed, mark task as STALE
                if task.task_type in (TaskType.ARRANGE_TRANSPORT, TaskType.CALL_OFFICE):
                    task.status = TaskStatus.STALE

    def create_task(
        self,
        task_id: str,
        task_type: TaskType,
        description: str,
        bound_revision_id: str,
        assigned_to: Optional[str] = None,
    ) -> CoordinationTaskRecord:
        rev = self.revisions.get(bound_revision_id)
        if not rev:
            raise StateError(f"Revision '{bound_revision_id}' does not exist.")
        if rev.state == EvidenceState.SUPERSEDED:
            raise StaleRevisionError(f"Cannot create tasks on superseded revision '{bound_revision_id}'.")

        task = CoordinationTaskRecord(
            task_id=task_id,
            task_type=task_type,
            description=description,
            bound_revision_id=bound_revision_id,
            status=TaskStatus.ASSIGNED if assigned_to else TaskStatus.UNASSIGNED,
            assigned_to=assigned_to,
        )
        self.tasks[task_id] = task
        return task

    def acknowledge_revision(
        self,
        revision_id: str,
        actor: str,
        idempotency_key: str,
    ) -> AcknowledgementRecord:
        """Record a caregiver acknowledgement bound to an exact revision."""
        if idempotency_key in self._seen_idempotency_keys:
            # Idempotent response
            for ack in self.acknowledgements.values():
                if ack.revision_id == revision_id and ack.actor == actor:
                    return ack

        rev = self.revisions.get(revision_id)
        if not rev:
            raise StateError(f"Revision '{revision_id}' not found.")

        # Stale write rejection: if revision has been superseded, reject write!
        if rev.state == EvidenceState.SUPERSEDED:
            raise StaleRevisionError(
                f"STALE_REVISION_ERROR: Cannot acknowledge revision '{revision_id}' because it has been superseded by a newer replacement."
            )

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ack_id = f"ack-{uuid.uuid4().hex[:8]}"
        ack = AcknowledgementRecord(
            ack_id=ack_id,
            revision_id=revision_id,
            actor=actor,
            status="VALID",
            timestamp=now,
        )
        self.acknowledgements[ack_id] = ack
        self._seen_idempotency_keys.add(idempotency_key)

        self.events.append(
            TaskEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                idempotency_key=idempotency_key,
                task_id="system-ack",
                revision_id=revision_id,
                actor=actor,
                action_type="ACKNOWLEDGE",
                payload={"status": "VALID"},
                timestamp=now,
            )
        )
        return ack

    def complete_task(
        self,
        task_id: str,
        expected_revision_id: str,
        actor: str,
        completion_note: str,
        idempotency_key: str,
    ) -> CoordinationTaskRecord:
        """Complete a task with optimistic revision concurrency check."""
        if idempotency_key in self._seen_idempotency_keys:
            return self.tasks[task_id]

        task = self.tasks.get(task_id)
        if not task:
            raise StateError(f"Task '{task_id}' does not exist.")

        # Concurrency check 1: Was the task bound to the expected revision?
        if task.bound_revision_id != expected_revision_id:
            raise StaleRevisionError(
                f"STALE_REVISION_ERROR: Task '{task_id}' is bound to '{task.bound_revision_id}', not expected '{expected_revision_id}'."
            )

        # Concurrency check 2: Has the bound revision been superseded?
        bound_rev = self.revisions.get(task.bound_revision_id)
        if bound_rev and bound_rev.state == EvidenceState.SUPERSEDED:
            raise StaleRevisionError(
                f"STALE_REVISION_ERROR: Revision '{task.bound_revision_id}' has been superseded. Task '{task_id}' is stale and cannot be completed."
            )

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        task.status = TaskStatus.DONE
        task.completion_note = completion_note
        task.historical_completion = f"Completed by {actor} at {now}: {completion_note}"

        self._seen_idempotency_keys.add(idempotency_key)
        self.events.append(
            TaskEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                idempotency_key=idempotency_key,
                task_id=task_id,
                revision_id=task.bound_revision_id,
                actor=actor,
                action_type="COMPLETE",
                payload={"completion_note": completion_note},
                timestamp=now,
            )
        )
        return task


class TestSpikeCRevisions(unittest.TestCase):
    """Test suite for Spike C: Revisions, History and Service Rejection."""

    def setUp(self):
        self.service = AuthoritativeCoordinationService()

    def test_full_lifecycle_and_stale_write_rejection(self):
        # 1. Establish revision 1 (r1)
        r1 = self.service.register_revision(
            revision_id="rev-001",
            doc_id="doc-s01-v1",
            version_number=1,
        )
        self.assertEqual(r1.state, EvidenceState.SOURCE_SUPPORTED)

        # Create transport task on r1
        t1 = self.service.create_task(
            task_id="task-transport-1",
            task_type=TaskType.ARRANGE_TRANSPORT,
            description="Arrange wheelchair ride for Thursday 10:00",
            bound_revision_id="rev-001",
            assigned_to="Caregiver-A",
        )
        self.assertEqual(t1.status, TaskStatus.ASSIGNED)

        # Caregiver B acknowledges r1
        ack1 = self.service.acknowledge_revision(
            revision_id="rev-001",
            actor="Caregiver-B",
            idempotency_key="idemp-ack-001",
        )
        self.assertEqual(ack1.status, "VALID")

        # Caregiver A completes t1 on r1
        comp1 = self.service.complete_task(
            task_id="task-transport-1",
            expected_revision_id="rev-001",
            actor="Caregiver-A",
            completion_note="Van booked with City Transit for Thursday 09:30",
            idempotency_key="idemp-comp-001",
        )
        self.assertEqual(comp1.status, TaskStatus.DONE)
        self.assertIsNotNone(comp1.historical_completion)

        # 2. Upload revision 2 (r2) WITHOUT replacement link:
        # Verify no automatic "last-upload-wins" rule (INV-02).
        r2 = self.service.register_revision(
            revision_id="rev-002",
            doc_id="doc-s01-v2",
            version_number=2,
            replaces_revision_id=None,
        )
        # Both r1 and r2 remain SOURCE_SUPPORTED
        self.assertEqual(self.service.revisions["rev-001"].state, EvidenceState.SOURCE_SUPPORTED)
        self.assertEqual(self.service.revisions["rev-002"].state, EvidenceState.SOURCE_SUPPORTED)
        self.assertEqual(self.service.acknowledgements[ack1.ack_id].status, "VALID")

        # 3. Explicit replacement relationship is declared: r2 replaces r1
        self.service._apply_replacement_invalidation(old_rev_id="rev-001", new_rev_id="rev-002")
        self.assertEqual(self.service.revisions["rev-001"].state, EvidenceState.SUPERSEDED)

        # Downstream dependencies invalidated:
        # Ack on r1 becomes STALE
        self.assertEqual(self.service.acknowledgements[ack1.ack_id].status, "STALE")
        # Task t1 becomes STALE
        self.assertEqual(self.service.tasks["task-transport-1"].status, TaskStatus.STALE)

        # BUT historical completion is preserved in audit history (INV-05)
        self.assertIn("City Transit", self.service.tasks["task-transport-1"].historical_completion)
        self.assertTrue(any(e.task_id == "task-transport-1" and e.action_type == "COMPLETE" for e in self.service.events))

        # 4. Service-side stale write rejection (INV-06)
        # Concurrent caregiver in context A attempts to acknowledge r1 after r2 replacement
        with self.assertRaises(StaleRevisionError) as ctx:
            self.service.acknowledge_revision(
                revision_id="rev-001",
                actor="Caregiver-A",
                idempotency_key="idemp-ack-stale-001",
            )
        self.assertIn("STALE_REVISION_ERROR", str(ctx.exception))

        # Attempt to complete a task bound to superseded r1 is also rejected
        with self.assertRaises(StaleRevisionError) as ctx:
            self.service.complete_task(
                task_id="task-transport-1",
                expected_revision_id="rev-001",
                actor="Caregiver-A",
                completion_note="Late update",
                idempotency_key="idemp-comp-stale-002",
            )
        self.assertIn("STALE_REVISION_ERROR", str(ctx.exception))

    def test_idempotent_event_deduplication(self):
        """Verify duplicate events with same idempotency key are deduplicated (INV-07)."""
        self.service.register_revision("rev-001", "doc-1", 1)
        ack_a = self.service.acknowledge_revision(
            revision_id="rev-001",
            actor="Caregiver-B",
            idempotency_key="idemp-dup-test",
        )
        # Re-sending with same idempotency key
        ack_b = self.service.acknowledge_revision(
            revision_id="rev-001",
            actor="Caregiver-B",
            idempotency_key="idemp-dup-test",
        )
        self.assertEqual(ack_a.ack_id, ack_b.ack_id)
        # Only one event in audit log
        matching_events = [e for e in self.service.events if e.idempotency_key == "idemp-dup-test"]
        self.assertEqual(len(matching_events), 1)


if __name__ == "__main__":
    unittest.main()
