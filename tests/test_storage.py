"""Tests for THREAD SQLite persistence adapter (app/storage.py).

Verifies:
  - Database table initialization with WAL mode and foreign key support
  - Atomic persistence of cases, documents, spans, instructions, tasks,
    projections, acknowledgements, issues, links, and events
  - Rehearsal items, attempts, and projections roundtrip persistence
  - Idempotency receipt caching across database reloads
  - Foreign key cascading deletion on reset_case
  - Full case recovery from disk into a fresh ThreadService instance
"""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.domain import (
    Category,
    InvalidReplacementError,
    StaleRevisionError,
    TaskNotAllowedError,
    TaskType,
    ThreadService,
    Validity,
)
from app.storage import ThreadStorage


class TestThreadStorage(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_thread.db"
        self.storage = ThreadStorage(str(self.db_path))
        self.service = ThreadService(storage=self.storage)

    def tearDown(self):
        self.storage.close()
        self.temp_dir.cleanup()

    def test_database_initialization_and_wal_mode(self):
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode;")
        mode = cur.fetchone()[0]
        self.assertEqual(mode.upper(), "WAL")
        conn.close()

    def test_case_and_document_persistence(self):
        case = self.service.create_case("case-persist-01", fictional_only=True)
        doc = self.service.import_document(
            case.case_id,
            "discharge_notes.txt",
            "Patient Pat Taylor follow-up on Friday 14:00.",
            "Morgan",
            "doc-01",
            "v1",
        )

        # Inspect raw SQLite database
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("SELECT case_id, state_version FROM cases WHERE case_id = ?", (case.case_id,))
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "case-persist-01")
        self.assertEqual(row[1], 1)  # state_version incremented by document event

        cur.execute("SELECT filename, uploaded_by FROM documents WHERE document_id = ?", (doc.document_id,))
        drow = cur.fetchone()
        self.assertIsNotNone(drow)
        self.assertEqual(drow[0], "discharge_notes.txt")
        self.assertEqual(drow[1], "Morgan")
        conn.close()

    def test_full_working_path_roundtrip_reload(self):
        # 1. Setup case and working path in service 1
        case_id = "case-roundtrip"
        self.service.create_case(case_id, fictional_only=True)
        v1_text = "Follow-up appointment: Friday at 14:00. Call transport at 555-0199."
        doc1 = self.service.import_document(case_id, "v1.txt", v1_text, "Morgan", "doc-rt-1", "v1")
        instr, span = self.service.review_source(
            case_id, doc1.document_id, "v1", Category.APPOINTMENT_QUOTE,
            "appointment_wording", "Follow-up appointment: Friday at 14:00.", "Morgan"
        )
        task, proj = self.service.create_task(
            case_id, TaskType.ARRANGE_TRANSPORT, instr.instruction_id,
            "Arrange non-emergency transport for Friday at 14:00.", "Morgan"
        )
        self.service.confirm_owner(case_id, task.task_id, task.task_revision, "Pat")
        ack, ack_proj = self.service.acknowledge_task(
            case_id, task.task_id, task.task_revision, "Pat",
            "idem-key-rt-1", "fingerprint-rt-1"
        )

        # 2. Add rehearsal item and attempt
        item, rproj = self.service.create_rehearsal_item(
            case_id, instr.instruction_id, instr.instruction_revision,
            "When is your follow-up appointment?",
            [
                {"choice_id": "opt-1", "text": "Friday at 14:00", "is_match": True},
                {"choice_id": "opt-2", "text": "Saturday at 09:00", "is_match": False},
            ],
            "Pat"
        )
        attempt, att_proj = self.service.attempt_rehearsal(
            case_id, item.item_id, item.item_revision, "Pat", "opt-1"
        )

        # 3. Create second independent service instance pointing to the same SQLite db
        fresh_storage = ThreadStorage(str(self.db_path))
        fresh_service = ThreadService(storage=fresh_storage)

        # 4. Verify all entities exist in fresh service with matching state
        loaded_case = fresh_service.get_case(case_id)
        self.assertEqual(loaded_case.case_id, case_id)
        self.assertEqual(loaded_case.state_version, self.service.cases[case_id].state_version)

        self.assertIn(doc1.document_id, fresh_service.documents)
        self.assertIn(span.span_id, fresh_service.spans)
        self.assertIn(instr.instruction_id, fresh_service.instructions)
        self.assertIn(task.task_id, fresh_service.tasks)
        self.assertEqual(fresh_service.task_projections[task.task_id].assigned_actor_id, "Pat")
        self.assertIn(ack.ack_id, fresh_service.acknowledgements)

        # Verify idempotency key is remembered in fresh service
        receipt = fresh_service.check_idempotency(case_id, "Pat", "idem-key-rt-1", "fingerprint-rt-1")
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.result["ack_id"], ack.ack_id)

        # Verify rehearsal state in fresh service
        self.assertIn(item.item_id, fresh_service.rehearsals)
        self.assertIn(attempt.attempt_id, fresh_service.rehearsal_attempts)
        self.assertIn((item.item_id, "Pat"), fresh_service.rehearsal_projections)
        self.assertEqual(fresh_service.rehearsal_projections[(item.item_id, "Pat")].state.value, "REVIEWED_FOR_VERSION")

        # Verify event history count matches
        self.assertEqual(len(fresh_service.events), len(self.service.events))
        fresh_storage.close()

    def test_cascade_deletion_on_case_reset(self):
        case_id = "case-cascade"
        self.service.create_case(case_id, fictional_only=True)
        doc = self.service.import_document(case_id, "note.txt", "Follow-up Monday at 10:00.", "Morgan", "doc-c1", "v1")
        instr, span = self.service.review_source(
            case_id, doc.document_id, "v1", Category.APPOINTMENT_QUOTE,
            "appointment_wording", "Follow-up Monday at 10:00.", "Morgan"
        )
        task, proj = self.service.create_task(
            case_id, TaskType.ARRANGE_TRANSPORT, instr.instruction_id, "Transport", "Morgan"
        )

        # Verify records exist in SQLite
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tasks WHERE case_id = ?", (case_id,))
        self.assertEqual(cur.fetchone()[0], 1)
        conn.close()

        # Reset case
        self.service.reset_case(case_id)

        # Verify in-memory state cleared
        self.assertNotIn(case_id, self.service.cases)
        self.assertNotIn(task.task_id, self.service.tasks)

        # Verify database records cascaded and deleted
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cases WHERE case_id = ?", (case_id,))
        self.assertEqual(cur.fetchone()[0], 0)
        cur.execute("SELECT COUNT(*) FROM documents WHERE case_id = ?", (case_id,))
        self.assertEqual(cur.fetchone()[0], 0)
        cur.execute("SELECT COUNT(*) FROM tasks WHERE case_id = ?", (case_id,))
        self.assertEqual(cur.fetchone()[0], 0)
        cur.execute("SELECT COUNT(*) FROM events WHERE case_id = ?", (case_id,))
        self.assertEqual(cur.fetchone()[0], 0)
        conn.close()

    def test_replacement_link_invalidation_persisted(self):
        case_id = "case-invalidation"
        self.service.create_case(case_id, fictional_only=True)
        doc1 = self.service.import_document(case_id, "v1.txt", "Appointment Friday 14:00.", "Morgan", "doc-inv-1", "v1")
        doc2 = self.service.import_document(case_id, "v2.txt", "Appointment Monday 09:00.", "Morgan", "doc-inv-2", "v2")
        instr, _ = self.service.review_source(
            case_id, doc1.document_id, "v1", Category.APPOINTMENT_QUOTE,
            "appointment_wording", "Appointment Friday 14:00.", "Morgan"
        )
        task, _ = self.service.create_task(case_id, TaskType.ARRANGE_TRANSPORT, instr.instruction_id, "Transport", "Morgan")

        # Link replacement
        self.service.link_replacement(case_id, doc1.document_id, doc2.document_id, "v1", "v2", "Morgan")

        # Verify task is STALE in memory
        self.assertEqual(self.service.task_projections[task.task_id].validity, Validity.STALE)

        # Reload from storage into fresh service
        fresh_storage = ThreadStorage(str(self.db_path))
        fresh_service = ThreadService(storage=fresh_storage)
        self.assertEqual(fresh_service.task_projections[task.task_id].validity, Validity.STALE)
        fresh_storage.close()


if __name__ == "__main__":
    unittest.main()
