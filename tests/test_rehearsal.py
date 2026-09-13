"""Tests for Rehearsal & Practice Mode (FR-08, INV-05, INV-09, INV-10)."""

from __future__ import annotations

import unittest
from pathlib import Path

from app.domain import (
    AttemptOutcome,
    Category,
    RehearsalState,
    StaleRevisionError,
    TaskNotAllowedError,
    ThreadService,
    Validity,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "docs" / "day03" / "fixtures"


class TestRehearsalMode(unittest.TestCase):
    def setUp(self):
        self.service = ThreadService()
        self.case = self.service.create_case("test-rehearsal-case", fictional_only=True)
        self.cid = self.case.case_id

        self.v1_text = (FIXTURES_DIR / "s01_v1.txt").read_text(encoding="utf-8")
        self.v2_text = (FIXTURES_DIR / "s01_v2.txt").read_text(encoding="utf-8")

        self.doc1 = self.service.import_document(self.cid, "s01_v1.txt", self.v1_text, "Morgan", "doc-1", "v1")

    def test_rehearsal_full_lifecycle(self):
        # 1. Review appointment quote
        quote = "Follow-up appointment: Thursday at 10:00."
        instr, span = self.service.review_source(
            self.cid, self.doc1.document_id, "v1", Category.APPOINTMENT_QUOTE, "appointment_wording", quote, "Morgan"
        )

        # 2. Create Rehearsal Item with quoted choices
        choices = [
            {"choice_id": "c1", "text": "Thursday at 10:00", "is_match": True},
            {"choice_id": "c2", "text": "Friday at 14:00", "is_match": False},
        ]
        item, proj = self.service.create_rehearsal_item(
            self.cid,
            instr.instruction_id,
            instr.instruction_revision,
            "When is Pat's scheduled follow-up appointment?",
            choices,
            "Morgan",
        )
        self.assertEqual(proj.state, RehearsalState.NOT_REVIEWED)
        self.assertEqual(proj.validity, Validity.CURRENT)

        # 3. Attempt rehearsal: Mismatch choice
        att_mismatch, proj = self.service.attempt_rehearsal(
            self.cid, item.item_id, item.item_revision, "Morgan", "c2"
        )
        self.assertEqual(att_mismatch.outcome, AttemptOutcome.MISMATCH)
        self.assertEqual(proj.state, RehearsalState.NOT_REVIEWED)

        # 4. Attempt rehearsal: Match choice
        att_match, proj = self.service.attempt_rehearsal(
            self.cid, item.item_id, item.item_revision, "Morgan", "c1"
        )
        self.assertEqual(att_match.outcome, AttemptOutcome.MATCH)
        self.assertEqual(proj.state, RehearsalState.REVIEWED_FOR_VERSION)

        # 5. Link replacement document
        doc2 = self.service.import_document(self.cid, "s01_v2.txt", self.v2_text, "Morgan", "doc-2", "v2")
        self.service.link_replacement(self.cid, self.doc1.document_id, doc2.document_id, "v1", "v2", "Morgan")

        # 6. Verify Rehearsal Projection is invalidated to NEEDS_REREVIEW and STALE (FR-08, INV-05)
        rproj = self.service.rehearsal_projections[(item.item_id, "Morgan")]
        self.assertEqual(rproj.state, RehearsalState.NEEDS_REREVIEW)
        self.assertEqual(rproj.validity, Validity.STALE)

        # 7. Attempting rehearsal on STALE item revision is rejected
        with self.assertRaises(StaleRevisionError):
            self.service.attempt_rehearsal(self.cid, item.item_id, item.item_revision, "Morgan", "c1")

    def test_medication_rehearsal_strictly_prohibited(self):
        """Clinical/medication instructions cannot be used for rehearsal (INV-09)."""
        med_quote = "Lisinopril 10mg oral daily in morning. (Read-only quotation. Do not alter dose.)"
        instr_med, _ = self.service.review_source(
            self.cid, self.doc1.document_id, "v1", Category.MEDICATION_QUOTE, "medication_summary", med_quote
        )
        with self.assertRaises(TaskNotAllowedError, msg="Medication rehearsal must be rejected"):
            self.service.create_rehearsal_item(
                self.cid,
                instr_med.instruction_id,
                instr_med.instruction_revision,
                "What is the dose?",
                [{"choice_id": "c1", "text": "10mg", "is_match": True}],
            )


if __name__ == "__main__":
    unittest.main()
