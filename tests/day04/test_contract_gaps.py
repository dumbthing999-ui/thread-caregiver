"""Day 1 contract assertions against unchanged Day 3 development spikes.

All inputs are original synthetic local data. These are actual failing product
assertions, not expectedFailure markers, deliberate false assertions or mocks.
"""
import dataclasses
import hashlib
from pathlib import Path
import tempfile
import unittest

from docs.day03.spikes.spike_a_anchors import (
    AnchorResolver, SourceDocument, UnsupportedDocumentFormatError,
)
from docs.day03.spikes.spike_b_schema_gate import DeterministicTaskGate, TaskType, TaskStatus
from docs.day03.spikes.spike_c_revisions import (
    AuthoritativeCoordinationService, StateError, StaleRevisionError,
)

QUOTE = 'Follow-up appointment: Thursday at 10:00.'


def document(text=QUOTE):
    return SourceDocument('synthetic-doc', 'synthetic.txt', text,
                          hashlib.sha256(text.encode()).hexdigest(), len(text), 1)


def candidate(value=QUOTE, category='FOLLOW_UP_APPOINTMENT'):
    return {'id': 'instruction-1', 'category': category,
            'fields': [{'name': 'appointment_wording', 'value': value, 'exact_quote': QUOTE}]}


def task(description='Arrange transport for the quoted appointment.'):
    return {'task_id': 'transport-1', 'task_type': 'ARRANGE_TRANSPORT',
            'description': description, 'linked_instruction_id': 'instruction-1'}


def gate(instruction, proposed_task=None):
    return DeterministicTaskGate.validate_and_filter(
        document(), 'r1', [instruction], [] if proposed_task is None else [proposed_task])


def service_with_task():
    service = AuthoritativeCoordinationService()
    service.register_revision('r1', 'doc-1', 1)
    service.create_task('task-1', TaskType.ARRANGE_TRANSPORT,
                        'Arrange transport for the fictional appointment.', 'r1', 'Morgan')
    return service


class ContractGaps(unittest.TestCase):
    def test_value_must_be_supported_by_its_quote(self):
        result = gate(candidate('Follow-up appointment: Friday at 14:00'))
        self.assertEqual(result.accepted_instructions, [],
                         'FR-02: a correct anchor cannot support contradictory displayed wording')

    def test_empty_instruction_cannot_publish_supported(self):
        result = gate({'id': 'empty', 'category': 'FOLLOW_UP_APPOINTMENT', 'fields': []})
        self.assertEqual(result.accepted_instructions, [],
                         'FR-02/FR-03: an empty instruction has no supporting source fields')

    def test_clinical_category_cannot_spawn_transport(self):
        result = gate(candidate(category='CLINICAL_TREATMENT'), task())
        self.assertEqual(result.accepted_tasks, [],
                         'FR-04: a clinical category is not an eligible nonclinical dependency')

    def test_allowed_task_label_cannot_hide_treatment_action(self):
        result = gate(candidate(), task('Change the treatment now.'))
        self.assertEqual(result.accepted_tasks, [],
                         'FR-04: an allowed enum does not make its free text nonclinical')

    def test_duplicate_revision_cannot_overwrite_source_identity(self):
        service = service_with_task()
        original = dataclasses.asdict(service.revisions['r1'])
        try:
            service.register_revision('r1', 'different-document', 99)
        except StateError:
            pass
        self.assertEqual(dataclasses.asdict(service.revisions['r1']), original,
                         'INV-01: revision ID reuse must not overwrite original source identity')

    def test_replacement_requires_existing_old_endpoint(self):
        service = service_with_task()
        with self.assertRaises(StateError, msg='FR-05: reject a dangling claimed replacement'):
            service.register_revision('r2', 'doc-2', 2, replaces_revision_id='missing-r0')

    def test_replacement_cannot_point_to_itself(self):
        service = service_with_task()
        with self.assertRaises(StateError, msg='INV-04: self-replacement is not a valid revision link'):
            service.register_revision('r2', 'doc-2', 2, replaces_revision_id='r2')

    def test_idempotency_key_cannot_mask_different_operation(self):
        service = service_with_task()
        service.acknowledge_revision('r1', 'Morgan', 'same-key')
        with self.assertRaises(StateError, msg='FR-07: same key with different operation must conflict'):
            service.complete_task('task-1', 'r1', 'Morgan', 'Fictional arrangement prepared.', 'same-key')

    def test_idempotency_key_cannot_mask_different_payload(self):
        service = service_with_task()
        service.complete_task('task-1', 'r1', 'Morgan', 'Original fictional note.', 'completion-key')
        with self.assertRaises(StateError, msg='FR-07: conflicting retry payload must be rejected'):
            service.complete_task('task-1', 'r1', 'Morgan', 'Changed fictional note.', 'completion-key')

    def test_history_payload_cannot_be_mutated_by_reader(self):
        service = service_with_task()
        service.acknowledge_revision('r1', 'Morgan', 'ack-key')
        event = service.events[0]
        try:
            event.payload['status'] = 'REWRITTEN'
        except TypeError:
            pass
        self.assertEqual(service.events[0].payload['status'], 'VALID',
                         'INV-01/INV-05: frozen outer event must protect nested historical payload')

    def test_plain_ascii_pdf_is_rejected_by_text_only_importer(self):
        # An entirely UTF-8-decodable PDF envelope: not a supported text document.
        # Create transient input within owned test directory, not elsewhere.
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temp:
            path = Path(temp) / 'fictional.pdf'
            path.write_bytes(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n')
            with self.assertRaises(UnsupportedDocumentFormatError,
                                   msg='FR-01: decoding PDF bytes is not supported extraction'):
                SourceDocument.from_file('unsupported-pdf', path)

    def test_service_cannot_create_prohibited_clinical_task(self):
        service = service_with_task()
        with self.assertRaises(StateError, msg='FR-04: authoritative path must enforce task boundary'):
            service.create_task('clinical-1', TaskType.MODIFY_TREATMENT,
                                'Change treatment.', 'r1', 'Morgan')


class PositiveControls(unittest.TestCase):
    def test_exact_source_anchor_resolves(self):
        doc = document()
        span = AnchorResolver.resolve_anchor(doc, QUOTE, 'span-1')
        self.assertTrue(span.verify_against(doc))
        self.assertEqual(doc.raw_content[span.start_char:span.end_char], QUOTE)

    def test_supported_nonclinical_candidate_publishes(self):
        result = gate(candidate(), task())
        self.assertFalse(result.is_blocked)
        self.assertEqual(len(result.accepted_tasks), 1)
        self.assertEqual(result.accepted_tasks[0].task_type, TaskType.ARRANGE_TRANSPORT)

    def test_missing_quote_blocks_publication(self):
        instruction = candidate()
        instruction['fields'][0]['exact_quote'] = 'Not present in this fictional document.'
        result = gate(instruction, task())
        self.assertTrue(result.is_blocked)
        self.assertEqual(result.accepted_instructions, [])
        self.assertEqual(result.accepted_tasks, [])

    def test_identical_retry_records_one_event(self):
        service = service_with_task()
        first = service.acknowledge_revision('r1', 'Morgan', 'same-request')
        second = service.acknowledge_revision('r1', 'Morgan', 'same-request')
        self.assertEqual(first.ack_id, second.ack_id)
        self.assertEqual(len(service.events), 1)

    def test_new_stale_acknowledgement_is_rejected(self):
        service = service_with_task()
        service.register_revision('r2', 'doc-2', 2, replaces_revision_id='r1')
        with self.assertRaises(StaleRevisionError):
            service.acknowledge_revision('r1', 'Morgan', 'new-stale-request')
        self.assertEqual(service.events, [])
        self.assertEqual(service.tasks['task-1'].status, TaskStatus.STALE)
