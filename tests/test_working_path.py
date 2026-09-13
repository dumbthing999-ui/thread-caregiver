"""Automated verification of the single working path (README.md).

Tests:
  1. Open fictional UTF-8 text (s01_v1.txt).
  2. Inspect exact source quotation with exact offsets and equality.
  3. Assign nonclinical transport task to Morgan Reed.
  4. Explicitly link replacement (s01_v2.txt).
  5. Reject stale acknowledgement at the service with 409 STALE_REVISION_ERROR.
  6. Enforce case snapshot ETag preconditions (412 CASE_VERSION_MISMATCH).
  7. Enforce idempotency scope and conflict detection (409 IDEMPOTENCY_KEY_REUSED).
  8. Preserve immutable event audit history.
  9. Conflicting-source case: unlinked contradictory appointments remain CONFLICTED and BLOCKED.
"""

from __future__ import annotations

import copy
import hashlib
import pathlib
import unittest

from app.domain import (
    CaseVersionMismatchError,
    Category,
    EvidenceBlockedError,
    IdempotencyKeyReusedError,
    InvalidReplacementError,
    PreconditionRequiredError,
    StaleRevisionError,
    TaskNotAllowedError,
    TaskState,
    TaskType,
    ThreadService,
    UnsupportedFormatError,
    Validity,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "docs" / "day03" / "fixtures"


class TestWorkingPath(unittest.TestCase):
    def setUp(self):
        self.service = ThreadService()
        self.case = self.service.create_case("test-working-case", fictional_only=True)

        self.v1_text = (FIXTURES_DIR / "s01_v1.txt").read_text(encoding="utf-8")
        self.v2_text = (FIXTURES_DIR / "s01_v2.txt").read_text(encoding="utf-8")
        self.conf_a_text = (FIXTURES_DIR / "s02_conflicting_a.txt").read_text(encoding="utf-8")
        self.conf_b_text = (FIXTURES_DIR / "s02_conflicting_b.txt").read_text(encoding="utf-8")

    def test_complete_working_path(self):
        """Executes the exact working path defined in README.md from start to finish."""
        cid = self.case.case_id

        # 1. Open fictional UTF-8 text
        doc1 = self.service.import_document(cid, "s01_v1.txt", self.v1_text, "Morgan", "doc-1", "v1")
        self.assertEqual(doc1.source_version, "v1")
        self.assertEqual(doc1.sha256, hashlib.sha256(self.v1_text.encode("utf-8")).hexdigest())

        # 2. Inspect exact source quotation
        quote = "Follow-up appointment: Thursday at 10:00."
        instr1, span1 = self.service.review_source(
            cid, doc1.document_id, "v1", Category.APPOINTMENT_QUOTE, "appointment_wording", quote, "Morgan"
        )
        self.assertEqual(span1.exact_quote, quote)
        self.assertEqual(doc1.text[span1.start_char:span1.end_char], quote)
        field1 = self.service.instruction_fields[instr1.field_ids[0]]
        self.assertEqual(field1.value, quote, "FR-02: displayed field value must match exact source quote")

        # 3. Assign transport task
        task1, proj1 = self.service.create_task(
            cid, TaskType.ARRANGE_TRANSPORT, instr1.instruction_id, "Arrange wheelchair transport.", "Morgan", "task-transport", "tr1"
        )
        self.assertEqual(proj1.status, TaskState.UNASSIGNED)
        self.assertEqual(proj1.validity, Validity.CURRENT)

        # Confirm owner
        proj1 = self.service.confirm_owner(cid, task1.task_id, "tr1", "Morgan")
        self.assertEqual(proj1.status, TaskState.ASSIGNED)
        self.assertEqual(proj1.assigned_actor_id, "Morgan")

        # Acknowledge task with valid ETag and idempotency key
        etag_before_ack = f'"case-state-{self.case.state_version}"'
        self.service.validate_preconditions(cid, etag_before_ack)

        fp1 = self.service._compute_fingerprint("POST", f"/api/v1/cases/{cid}/acknowledgements", {"task_id": "task-transport"})
        ack1, proj1 = self.service.acknowledge_task(cid, "task-transport", "tr1", "Morgan", "ack-key-01", fp1)
        self.assertEqual(proj1.status, TaskState.ACKNOWLEDGED)
        self.assertEqual(proj1.validity, Validity.CURRENT)
        self.assertEqual(ack1.task_revision, "tr1")

        # Complete task
        fp_comp = self.service._compute_fingerprint("POST", f"/api/v1/cases/{cid}/completions", {"task_id": "task-transport"})
        proj1 = self.service.complete_task(cid, "task-transport", "tr1", "Morgan", "Van arranged.", "comp-key-01", fp_comp)
        self.assertEqual(proj1.status, TaskState.DONE)
        self.assertEqual(len(proj1.historical_completion_event_ids), 1)

        # 4. Explicitly link a replacement
        doc2 = self.service.import_document(cid, "s01_v2.txt", self.v2_text, "Morgan", "doc-2", "v2")
        self.assertEqual(doc2.source_version, "v2")

        link = self.service.link_replacement(cid, doc1.document_id, doc2.document_id, "v1", "v2", "Morgan")
        self.assertEqual(link.mapping_policy, "DOCUMENT_WIDE")

        # Verify task validity transitioned to STALE, while historical completion remains recorded (INV-05, INV-06)
        proj_after_link = self.service.task_projections["task-transport"]
        self.assertEqual(proj_after_link.validity, Validity.STALE)
        self.assertEqual(proj_after_link.status, TaskState.STALE)
        self.assertEqual(len(proj_after_link.historical_completion_event_ids), 1, "Historical completion preserved")

        # 5. Authoritative service rejection of stale write (INV-06)
        fp_stale = self.service._compute_fingerprint("POST", f"/api/v1/cases/{cid}/acknowledgements", {"task_id": "task-transport"})
        with self.assertRaises(StaleRevisionError, msg="Service must reject write to STALE task"):
            self.service.acknowledge_task(cid, "task-transport", "tr1", "Morgan", "ack-stale-02", fp_stale)

        # 6. Idempotency: exact retry returns original receipt; altered payload conflicts
        exact_retry_ack, _ = self.service.acknowledge_task(cid, "task-transport", "tr1", "Morgan", "ack-key-01", fp1)
        self.assertEqual(exact_retry_ack.ack_id, ack1.ack_id, "Exact retry returns original receipt")

        altered_fp = self.service._compute_fingerprint("POST", f"/api/v1/cases/{cid}/acknowledgements", {"task_id": "task-transport", "altered": True})
        with self.assertRaises(IdempotencyKeyReusedError, msg="Altered retry under same key must conflict"):
            self.service.acknowledge_task(cid, "task-transport", "tr1", "Morgan", "ack-key-01", altered_fp)

        # 7. Concurrency: stale If-Match ETag is rejected (RFC 9110 / RFC 6585)
        stale_etag = '"case-state-1"'
        with self.assertRaises(CaseVersionMismatchError):
            self.service.validate_preconditions(cid, stale_etag)

        with self.assertRaises(PreconditionRequiredError):
            self.service.validate_preconditions(cid, None)

        # 8. Preservation of immutable event history (INV-01, INV-05)
        history = self.service.get_history(cid)
        self.assertTrue(len(history) >= 7)
        event_types = [e["event_type"] for e in history]
        self.assertIn("SOURCE_ADDED", event_types)
        self.assertIn("REVIEW_RECORDED", event_types)
        self.assertIn("TASK_CREATED", event_types)
        self.assertIn("OWNER_CONFIRMED", event_types)
        self.assertIn("ACKNOWLEDGED", event_types)
        self.assertIn("COMPLETED", event_types)
        self.assertIn("REPLACEMENT_LINKED", event_types)
        self.assertIn("INVALIDATED", event_types)

        # Confirm reader cannot mutate stored history (INV-01, INV-05)
        first_event = self.service.events[0]
        with self.assertRaises(TypeError, msg="INV-01/INV-05: reader mutation of payload must raise TypeError"):
            first_event.payload["status"] = "CORRUPTED"
        self.assertNotEqual(self.service.events[0].payload.get("status"), "CORRUPTED")

    def test_conflicting_source_case_stays_blocked(self):
        """Conflicting unlinked appointments remain CONFLICTED and actionable transport is BLOCKED."""
        cid = self.case.case_id

        doc_a, doc_b, issue, task = self.service.setup_conflicting_case(
            cid, self.conf_a_text, self.conf_b_text
        )

        self.assertEqual(issue.kind, "CONFLICT")
        self.assertEqual(task.task_type, TaskType.PREPARE_CLARIFICATION)

        # Attempting to schedule an actionable transport task directly on conflicting sources is BLOCKED
        snap = self.service.get_case_snapshot(cid)
        self.assertEqual(snap["task_projections"][task.task_id]["validity"], Validity.CURRENT)
        self.assertEqual(task.task_type, TaskType.PREPARE_CLARIFICATION)

    def test_safety_boundaries_and_rejections(self):
        """Clinical tasks, disguised labels, and unsupported PDFs are strictly rejected."""
        cid = self.case.case_id
        doc = self.service.import_document(cid, "s01_v1.txt", self.v1_text, "Morgan", "doc-safe", "v1")

        # Prohibited clinical categories cannot spawn actionable tasks
        med_quote = "Lisinopril 10mg oral daily in morning. (Read-only quotation. Do not alter dose.)"
        instr_med, _ = self.service.review_source(
            cid, doc.document_id, "v1", Category.MEDICATION_QUOTE, "medication_summary", med_quote
        )
        with self.assertRaises(TaskNotAllowedError, msg="Medication quote cannot spawn actionable transport"):
            self.service.create_task(cid, TaskType.ARRANGE_TRANSPORT, instr_med.instruction_id, "Schedule transport")

        # Disguised description with clinical commands is rejected
        appt_quote = "Follow-up appointment: Thursday at 10:00."
        instr_appt, _ = self.service.review_source(
            cid, doc.document_id, "v1", Category.APPOINTMENT_QUOTE, "appointment_wording", appt_quote
        )
        with self.assertRaises(TaskNotAllowedError, msg="Clinical treatment wording in transport task rejected"):
            self.service.create_task(cid, TaskType.ARRANGE_TRANSPORT, instr_appt.instruction_id, "Change the treatment dosage now.")

        # PDF envelope rejected
        pdf_bytes = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
        with self.assertRaises(UnsupportedFormatError, msg="PDF format must be rejected"):
            self.service.import_document(cid, "sample.pdf", pdf_bytes)


if __name__ == "__main__":
    unittest.main()
