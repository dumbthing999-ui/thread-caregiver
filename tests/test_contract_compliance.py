"""Contract compliance suite validating that app.domain resolves all 12 contract gaps.

Each test verifies that app.domain satisfies the requirements where Day 3 spikes failed:
  1. FR-02/INV-01/INV-09: Displayed value must be supported by its exact quote.
  2. FR-02/FR-03: Empty instruction cannot publish supported.
  3. FR-04/INV-08/INV-09: Clinical category cannot spawn transport task.
  4. FR-04/INV-08/INV-09: Allowed task label cannot disguise clinical treatment actions.
  5. FR-01/FR-06/INV-01: Document and revision identity cannot be overwritten.
  6. FR-05/INV-04: Replacement requires existing prior endpoint.
  7. FR-05/INV-04: Replacement cannot point to itself.
  8. FR-07/INV-07: Idempotency key cannot mask different operation.
  9. FR-07/INV-07: Idempotency key cannot mask different payload.
 10. FR-06/INV-01/INV-05: Historical event payload cannot be mutated by reader.
 11. FR-01/INV-01/INV-11: UTF-8-decodable PDF envelope is actively rejected.
 12. FR-04/INV-08/INV-09: Direct service creation of clinical tasks is prohibited.
 Plus all 5 positive controls.
"""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from app.domain import (
    Category,
    IdempotencyKeyReusedError,
    InvalidReplacementError,
    MalformedRequestError,
    ProvenanceInvalidError,
    StaleRevisionError,
    TaskNotAllowedError,
    TaskState,
    TaskType,
    ThreadService,
    UnsupportedFormatError,
    Validity,
)

QUOTE = "Follow-up appointment: Thursday at 10:00."


class ContractCompliance(unittest.TestCase):
    def setUp(self):
        self.service = ThreadService()
        self.case = self.service.create_case("test-compliance-case", fictional_only=True)
        self.cid = self.case.case_id
        self.doc = self.service.import_document(
            self.cid, "synthetic.txt", QUOTE, "Morgan", "synthetic-doc", "r1"
        )

    def test_value_must_be_supported_by_its_quote(self):
        """FR-02/INV-01: Cannot review an anchor with mismatched or hallucinated quote."""
        with self.assertRaises(ProvenanceInvalidError, msg="Mismatched quote must be rejected"):
            self.service.resolve_anchor(self.cid, self.doc.document_id, "Follow-up appointment: Friday at 14:00")

    def test_empty_instruction_cannot_publish_supported(self):
        """FR-02/FR-03: Empty quote string must be rejected."""
        with self.assertRaises(ProvenanceInvalidError, msg="Empty quote must be rejected"):
            self.service.review_source(
                self.cid, self.doc.document_id, "r1", Category.APPOINTMENT_QUOTE, "appointment_wording", ""
            )

    def test_clinical_category_cannot_spawn_transport(self):
        """FR-04/INV-08: A clinical category is not an eligible nonclinical dependency."""
        instr, _ = self.service.review_source(
            self.cid, self.doc.document_id, "r1", Category.CLINICAL_TREATMENT, "treatment_wording", QUOTE
        )
        with self.assertRaises(TaskNotAllowedError, msg="Clinical category cannot spawn transport task"):
            self.service.create_task(self.cid, TaskType.ARRANGE_TRANSPORT, instr.instruction_id, "Arrange transport")

    def test_allowed_task_label_cannot_hide_treatment_action(self):
        """FR-04/INV-08: An allowed enum does not make clinical text permissible."""
        instr, _ = self.service.review_source(
            self.cid, self.doc.document_id, "r1", Category.APPOINTMENT_QUOTE, "appointment_wording", QUOTE
        )
        with self.assertRaises(TaskNotAllowedError, msg="Disguised treatment action must be rejected"):
            self.service.create_task(
                self.cid, TaskType.ARRANGE_TRANSPORT, instr.instruction_id, "Change the treatment dosage now."
            )

    def test_duplicate_revision_cannot_overwrite_source_identity(self):
        """FR-01/INV-01: Duplicate document ID cannot overwrite existing document."""
        doc_original = self.service.documents[self.doc.document_id]
        orig_sha = doc_original.sha256
        # Attempting to re-register doc with changed text must fail
        with self.assertRaises(MalformedRequestError, msg="Duplicate doc ID with different content must be rejected"):
            self.service.import_document(
                self.cid, "changed.txt", "Different content.", "Morgan", self.doc.document_id, "r1"
            )
        self.assertEqual(self.service.documents[self.doc.document_id].sha256, orig_sha)

    def test_replacement_requires_existing_old_endpoint(self):
        """FR-05/INV-04: Reject a dangling claimed replacement."""
        doc2 = self.service.import_document(self.cid, "doc2.txt", "Some new text.", "Morgan", "doc-2", "r2")
        with self.assertRaises(InvalidReplacementError, msg="FR-05: reject dangling predecessor"):
            self.service.link_replacement(self.cid, "missing-r0", doc2.document_id, "r0", "r2")

    def test_replacement_cannot_point_to_itself(self):
        """INV-04: Self-replacement is not a valid revision link."""
        with self.assertRaises(InvalidReplacementError, msg="INV-04: self-replacement must be rejected"):
            self.service.link_replacement(self.cid, self.doc.document_id, self.doc.document_id, "r1", "r1")

    def test_replacement_cycle_is_rejected(self):
        """INV-04: Circular replacement chains must be rejected."""
        doc2 = self.service.import_document(self.cid, "doc2.txt", "Update text.", "Morgan", "doc-2", "r2")
        doc3 = self.service.import_document(self.cid, "doc3.txt", "Third text.", "Morgan", "doc-3", "r3")
        # Link doc1 -> doc2, doc2 -> doc3
        self.service.link_replacement(self.cid, self.doc.document_id, doc2.document_id, "r1", "r2")
        self.service.link_replacement(self.cid, doc2.document_id, doc3.document_id, "r2", "r3")
        # Attempting to link doc3 -> doc1 creates a cycle and must be rejected
        with self.assertRaises(InvalidReplacementError, msg="INV-04: circular replacement cycle must be rejected"):
            self.service.link_replacement(self.cid, doc3.document_id, self.doc.document_id, "r3", "r1")

    def test_idempotency_key_cannot_mask_different_operation(self):
        """FR-07/INV-07: Same key with different operation must conflict."""
        instr, _ = self.service.review_source(
            self.cid, self.doc.document_id, "r1", Category.APPOINTMENT_QUOTE, "appointment_wording", QUOTE
        )
        task, _ = self.service.create_task(self.cid, TaskType.ARRANGE_TRANSPORT, instr.instruction_id, "Transport", task_revision="tr1")
        
        fp1 = self.service._compute_fingerprint("POST", "/api/v1/cases/ack", {"op": "ack"})
        self.service.acknowledge_task(self.cid, task.task_id, "tr1", "Morgan", "same-key", fp1)

        fp2 = self.service._compute_fingerprint("POST", "/api/v1/cases/comp", {"op": "complete"})
        with self.assertRaises(IdempotencyKeyReusedError, msg="FR-07: same key with different op must conflict"):
            self.service.complete_task(self.cid, task.task_id, "tr1", "Morgan", "Done.", "same-key", fp2)

    def test_idempotency_key_cannot_mask_different_payload(self):
        """FR-07/INV-07: Conflicting retry payload must be rejected."""
        instr, _ = self.service.review_source(
            self.cid, self.doc.document_id, "r1", Category.APPOINTMENT_QUOTE, "appointment_wording", QUOTE
        )
        task, _ = self.service.create_task(self.cid, TaskType.ARRANGE_TRANSPORT, instr.instruction_id, "Transport", task_revision="tr1")

        fp1 = self.service._compute_fingerprint("POST", "/api/v1/cases/comp", {"note": "original"})
        self.service.complete_task(self.cid, task.task_id, "tr1", "Morgan", "original", "comp-key", fp1)

        fp2 = self.service._compute_fingerprint("POST", "/api/v1/cases/comp", {"note": "changed"})
        with self.assertRaises(IdempotencyKeyReusedError, msg="FR-07: conflicting retry payload must be rejected"):
            self.service.complete_task(self.cid, task.task_id, "tr1", "Morgan", "changed", "comp-key", fp2)

    def test_history_payload_cannot_be_mutated_by_reader(self):
        """INV-01/INV-05: Frozen outer event must protect nested historical payload."""
        instr, _ = self.service.review_source(
            self.cid, self.doc.document_id, "r1", Category.APPOINTMENT_QUOTE, "appointment_wording", QUOTE
        )
        task, _ = self.service.create_task(self.cid, TaskType.ARRANGE_TRANSPORT, instr.instruction_id, "Transport", task_revision="tr1")
        fp = self.service._compute_fingerprint("POST", "/api/v1/cases/ack", {})
        self.service.acknowledge_task(self.cid, task.task_id, "tr1", "Morgan", "ack-key", fp)

        event = self.service.events[-1]
        with self.assertRaises(TypeError, msg="INV-01/INV-05: modifying payload must raise TypeError"):
            event.payload["status"] = "REWRITTEN"
        self.assertEqual(event.payload["status"], "VALID")

    def test_plain_ascii_pdf_is_rejected_by_text_only_importer(self):
        """FR-01: Decoding PDF bytes is not supported extraction."""
        pdf_bytes = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
        with self.assertRaises(UnsupportedFormatError, msg="FR-01: decoding PDF bytes must be rejected"):
            self.service.import_document(self.cid, "fictional.pdf", pdf_bytes)

    def test_service_cannot_create_prohibited_clinical_task(self):
        """FR-04: Direct service creation must enforce task boundary."""
        instr, _ = self.service.review_source(
            self.cid, self.doc.document_id, "r1", Category.APPOINTMENT_QUOTE, "appointment_wording", QUOTE
        )
        with self.assertRaises(TaskNotAllowedError, msg="Prohibited task type must be rejected"):
            self.service.create_task(self.cid, TaskType.MODIFY_TREATMENT, instr.instruction_id, "Modify treatment")


class PositiveControlsCompliance(unittest.TestCase):
    def setUp(self):
        self.service = ThreadService()
        self.case = self.service.create_case("test-controls-case", fictional_only=True)
        self.cid = self.case.case_id
        self.doc = self.service.import_document(self.cid, "doc.txt", QUOTE, "Morgan", "doc-1", "r1")

    def test_exact_source_anchor_resolves(self):
        span = self.service.resolve_anchor(self.cid, self.doc.document_id, QUOTE)
        self.assertEqual(self.doc.text[span.start_char:span.end_char], QUOTE)

    def test_supported_nonclinical_candidate_publishes(self):
        instr, _ = self.service.review_source(
            self.cid, self.doc.document_id, "r1", Category.APPOINTMENT_QUOTE, "appointment_wording", QUOTE
        )
        task, proj = self.service.create_task(self.cid, TaskType.ARRANGE_TRANSPORT, instr.instruction_id, "Arrange transport")
        self.assertEqual(task.task_type, TaskType.ARRANGE_TRANSPORT)
        self.assertEqual(proj.validity, Validity.CURRENT)

    def test_missing_quote_blocks_publication(self):
        with self.assertRaises(ProvenanceInvalidError):
            self.service.resolve_anchor(self.cid, self.doc.document_id, "Not in doc")

    def test_identical_retry_records_one_event(self):
        instr, _ = self.service.review_source(self.cid, self.doc.document_id, "r1", Category.APPOINTMENT_QUOTE, "appointment_wording", QUOTE)
        task, _ = self.service.create_task(self.cid, TaskType.ARRANGE_TRANSPORT, instr.instruction_id, "Transport", task_revision="tr1")
        fp = self.service._compute_fingerprint("POST", "/api/v1/cases/ack", {})
        first, _ = self.service.acknowledge_task(self.cid, task.task_id, "tr1", "Morgan", "same-req", fp)
        second, _ = self.service.acknowledge_task(self.cid, task.task_id, "tr1", "Morgan", "same-req", fp)
        self.assertEqual(first.ack_id, second.ack_id)

    def test_new_stale_acknowledgement_is_rejected(self):
        instr, _ = self.service.review_source(self.cid, self.doc.document_id, "r1", Category.APPOINTMENT_QUOTE, "appointment_wording", QUOTE)
        task, _ = self.service.create_task(self.cid, TaskType.ARRANGE_TRANSPORT, instr.instruction_id, "Transport", task_revision="tr1")
        doc2 = self.service.import_document(self.cid, "doc2.txt", "Friday 14:00", "Morgan", "doc-2", "r2")
        self.service.link_replacement(self.cid, self.doc.document_id, doc2.document_id, "r1", "r2")

        fp = self.service._compute_fingerprint("POST", "/api/v1/cases/ack", {})
        with self.assertRaises(StaleRevisionError):
            self.service.acknowledge_task(self.cid, task.task_id, "tr1", "Morgan", "new-stale", fp)


if __name__ == "__main__":
    unittest.main()
