"""THREAD SQLite Persistence Engine.

Provides durable, atomic, thread-safe persistence using Python's standard-library sqlite3.
Enforces:
  - WAL mode (Write-Ahead Logging) for concurrent reads and writes
  - Foreign key constraints with ON DELETE CASCADE
  - Atomic transactions for case state and append-only event logs
  - Zero external dependencies (Python 3 standard library only)
"""

from __future__ import annotations

import dataclasses
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.domain import (
    Acknowledgement,
    AttemptOutcome,
    Case,
    Category,
    CommandReceipt,
    CoordinationTask,
    EvidenceIssue,
    EventType,
    Instruction,
    InstructionField,
    RehearsalAttempt,
    RehearsalChoice,
    RehearsalItem,
    RehearsalProjection,
    RehearsalState,
    RevisionLink,
    SourceDocument,
    SourceSpan,
    TaskEvent,
    TaskProjection,
    TaskState,
    TaskType,
    ThreadService,
    Validity,
    freeze_payload,
)


CREATE_TABLES_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    state_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    coordination_suspended INTEGER NOT NULL DEFAULT 0,
    sharing_mode TEXT NOT NULL DEFAULT 'ROLE_SIMULATION'
);

CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    source_version TEXT NOT NULL,
    filename TEXT NOT NULL,
    text TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    uploaded_by TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS spans (
    span_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    source_version TEXT NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    exact_quote TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS instructions (
    instruction_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    instruction_revision TEXT NOT NULL,
    category TEXT NOT NULL,
    field_ids_json TEXT NOT NULL,
    review_event_id TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS instruction_fields (
    field_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    instruction_id TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    span_id TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    task_revision TEXT NOT NULL,
    prior_task_revision TEXT,
    task_type TEXT NOT NULL,
    description_template TEXT NOT NULL,
    instruction_ids_json TEXT NOT NULL,
    issue_ids_json TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS task_projections (
    task_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    state_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    validity TEXT NOT NULL,
    assigned_actor_id TEXT,
    historical_completion_event_ids_json TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS acknowledgements (
    ack_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    task_revision TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    dependency_ids_json TEXT NOT NULL,
    event_id TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS issues (
    issue_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    span_ids_json TEXT NOT NULL,
    question_template TEXT NOT NULL,
    opened_event_id TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS revision_links (
    link_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    prior_document_id TEXT NOT NULL,
    new_document_id TEXT NOT NULL,
    asserted_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    mapping_policy TEXT NOT NULL DEFAULT 'DOCUMENT_WIDE',
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rehearsals (
    item_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    item_revision TEXT NOT NULL,
    instruction_id TEXT NOT NULL,
    span_ids_json TEXT NOT NULL,
    question_template TEXT NOT NULL,
    choices_json TEXT NOT NULL,
    execution_mode TEXT NOT NULL DEFAULT 'AUTHORED',
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rehearsal_attempts (
    attempt_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    item_revision TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    choice_id TEXT,
    outcome TEXT NOT NULL,
    event_id TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rehearsal_projections (
    item_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    state_version INTEGER NOT NULL,
    state TEXT NOT NULL,
    validity TEXT NOT NULL,
    PRIMARY KEY (item_id, actor_id),
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    case_sequence INTEGER NOT NULL,
    actor_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    resource_revision TEXT NOT NULL,
    dependency_ids_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS receipts (
    case_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    receipt_id TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    committed_state_version INTEGER NOT NULL,
    event_ids_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    PRIMARY KEY (case_id, actor_id, idempotency_key),
    FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
);
"""


class ThreadStorage:
    """Thread-safe SQLite storage adapter for the THREAD application."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        if self.db_path != ":memory:":
            Path(self.db_path).resolve().parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")
            if self.db_path != ":memory:":
                cur.execute("PRAGMA journal_mode = WAL;")
                cur.execute("PRAGMA synchronous = NORMAL;")
            cur.executescript(CREATE_TABLES_SQL)
            self._conn.commit()

    def close(self):
        with self._lock:
            self._conn.close()

    def persist_case(self, service: ThreadService, case_id: str):
        """Atomically persists all records for a given case."""
        c = service.cases.get(case_id)
        if not c:
            return

        with self._lock, self._conn:
            cur = self._conn.cursor()

            # 1. Case
            cur.execute(
                """
                INSERT OR REPLACE INTO cases (case_id, state_version, created_at, coordination_suspended, sharing_mode)
                VALUES (?, ?, ?, ?, ?)
                """,
                (c.case_id, c.state_version, c.created_at, int(c.coordination_suspended), c.sharing_mode),
            )

            # 2. Documents
            for doc in service.documents.values():
                if doc.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO documents (document_id, case_id, source_version, filename, text, sha256, char_count, created_at, uploaded_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (doc.document_id, doc.case_id, doc.source_version, doc.filename, doc.text, doc.sha256, doc.char_count, doc.created_at, doc.uploaded_by),
                    )

            # 3. Spans
            for span in service.spans.values():
                if span.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO spans (span_id, case_id, document_id, source_version, start_char, end_char, exact_quote)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (span.span_id, span.case_id, span.document_id, span.source_version, span.start_char, span.end_char, span.exact_quote),
                    )

            # 4. Instructions
            for instr in service.instructions.values():
                if instr.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO instructions (instruction_id, case_id, instruction_revision, category, field_ids_json, review_event_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (instr.instruction_id, instr.case_id, instr.instruction_revision, instr.category.value, json.dumps(instr.field_ids), instr.review_event_id),
                    )

            # 5. Instruction Fields
            for field in service.instruction_fields.values():
                if field.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO instruction_fields (field_id, case_id, instruction_id, name, value, span_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (field.field_id, field.case_id, field.instruction_id, field.name, field.value, field.span_id),
                    )

            # 6. Tasks
            for task in service.tasks.values():
                if task.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO tasks (task_id, case_id, task_revision, prior_task_revision, task_type, description_template, instruction_ids_json, issue_ids_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (task.task_id, task.case_id, task.task_revision, task.prior_task_revision, task.task_type.value, task.description_template, json.dumps(task.instruction_ids), json.dumps(task.issue_ids)),
                    )

            # 7. Task Projections
            for proj in service.task_projections.values():
                if proj.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO task_projections (task_id, case_id, state_version, status, validity, assigned_actor_id, historical_completion_event_ids_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (proj.task_id, proj.case_id, proj.state_version, proj.status.value, proj.validity.value, proj.assigned_actor_id, json.dumps(proj.historical_completion_event_ids)),
                    )

            # 8. Acknowledgements
            for ack in service.acknowledgements.values():
                if ack.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO acknowledgements (ack_id, case_id, task_id, task_revision, actor_id, dependency_ids_json, event_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (ack.ack_id, ack.case_id, ack.task_id, ack.task_revision, ack.actor_id, json.dumps(ack.dependency_ids), ack.event_id),
                    )

            # 9. Issues
            for issue in service.issues.values():
                if issue.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO issues (issue_id, case_id, kind, span_ids_json, question_template, opened_event_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (issue.issue_id, issue.case_id, issue.kind, json.dumps(issue.span_ids), issue.question_template, issue.opened_event_id),
                    )

            # 10. Links
            for link in service.links.values():
                if link.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO revision_links (link_id, case_id, prior_document_id, new_document_id, asserted_by, created_at, mapping_policy)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (link.link_id, link.case_id, link.prior_document_id, link.new_document_id, link.asserted_by, link.created_at, link.mapping_policy),
                    )

            # 11. Rehearsals
            for item in service.rehearsals.values():
                if item.case_id == case_id:
                    choices_data = [dataclasses.asdict(c) for c in item.choices]
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO rehearsals (item_id, case_id, item_revision, instruction_id, span_ids_json, question_template, choices_json, execution_mode)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (item.item_id, item.case_id, item.item_revision, item.instruction_id, json.dumps(item.span_ids), item.question_template, json.dumps(choices_data), item.execution_mode),
                    )

            # 12. Rehearsal Attempts
            for attempt in service.rehearsal_attempts.values():
                if attempt.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO rehearsal_attempts (attempt_id, case_id, item_id, item_revision, actor_id, choice_id, outcome, event_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (attempt.attempt_id, attempt.case_id, attempt.item_id, attempt.item_revision, attempt.actor_id, attempt.choice_id, attempt.outcome.value, attempt.event_id),
                    )

            # 13. Rehearsal Projections
            for (i_id, a_id), rproj in service.rehearsal_projections.items():
                if rproj.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO rehearsal_projections (item_id, actor_id, case_id, state_version, state, validity)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (rproj.item_id, rproj.actor_id, rproj.case_id, rproj.state_version, rproj.state.value, rproj.validity.value),
                    )

            # 14. Events
            for event in service.events:
                if event.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO events (event_id, case_id, case_sequence, actor_id, event_type, resource_id, resource_revision, dependency_ids_json, payload_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (event.event_id, event.case_id, event.case_sequence, event.actor_id, event.event_type.value, event.resource_id, event.resource_revision, json.dumps(event.dependency_ids), json.dumps(event.payload), event.created_at),
                    )

            # 15. Receipts
            for key_tuple, receipt in service.receipts.items():
                if receipt.case_id == case_id:
                    cur.execute(
                        """
                        INSERT OR REPLACE INTO receipts (case_id, actor_id, idempotency_key, receipt_id, request_fingerprint, committed_state_version, event_ids_json, result_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (receipt.case_id, receipt.actor_id, receipt.idempotency_key, receipt.receipt_id, receipt.request_fingerprint, receipt.committed_state_version, json.dumps(receipt.event_ids), json.dumps(receipt.result)),
                    )

    def delete_case(self, case_id: str):
        """Atomically deletes a case and all cascading foreign-key records."""
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))

    def load_into_service(self, service: ThreadService, case_id: Optional[str] = None):
        """Populates in-memory ThreadService structures from SQLite."""
        with self._lock:
            cur = self._conn.cursor()

            # 1. Cases
            if case_id:
                cur.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
            else:
                cur.execute("SELECT * FROM cases")
            for r in cur.fetchall():
                service.cases[r["case_id"]] = Case(
                    case_id=r["case_id"],
                    state_version=r["state_version"],
                    created_at=r["created_at"],
                    coordination_suspended=bool(r["coordination_suspended"]),
                    sharing_mode=r["sharing_mode"],
                )

            # 2. Documents
            query = "SELECT * FROM documents WHERE case_id = ?" if case_id else "SELECT * FROM documents"
            params = (case_id,) if case_id else ()
            cur.execute(query, params)
            for r in cur.fetchall():
                service.documents[r["document_id"]] = SourceDocument(
                    document_id=r["document_id"],
                    case_id=r["case_id"],
                    source_version=r["source_version"],
                    filename=r["filename"],
                    text=r["text"],
                    sha256=r["sha256"],
                    char_count=r["char_count"],
                    created_at=r["created_at"],
                    uploaded_by=r["uploaded_by"],
                )

            # 3. Spans
            query = "SELECT * FROM spans WHERE case_id = ?" if case_id else "SELECT * FROM spans"
            cur.execute(query, params)
            for r in cur.fetchall():
                service.spans[r["span_id"]] = SourceSpan(
                    span_id=r["span_id"],
                    case_id=r["case_id"],
                    document_id=r["document_id"],
                    source_version=r["source_version"],
                    start_char=r["start_char"],
                    end_char=r["end_char"],
                    exact_quote=r["exact_quote"],
                )

            # 4. Instructions
            query = "SELECT * FROM instructions WHERE case_id = ?" if case_id else "SELECT * FROM instructions"
            cur.execute(query, params)
            for r in cur.fetchall():
                service.instructions[r["instruction_id"]] = Instruction(
                    instruction_id=r["instruction_id"],
                    case_id=r["case_id"],
                    instruction_revision=r["instruction_revision"],
                    category=Category[r["category"]],
                    field_ids=json.loads(r["field_ids_json"]),
                    review_event_id=r["review_event_id"],
                )

            # 5. Instruction Fields
            query = "SELECT * FROM instruction_fields WHERE case_id = ?" if case_id else "SELECT * FROM instruction_fields"
            cur.execute(query, params)
            for r in cur.fetchall():
                service.instruction_fields[r["field_id"]] = InstructionField(
                    field_id=r["field_id"],
                    case_id=r["case_id"],
                    instruction_id=r["instruction_id"],
                    name=r["name"],
                    value=r["value"],
                    span_id=r["span_id"],
                )

            # 6. Tasks
            query = "SELECT * FROM tasks WHERE case_id = ?" if case_id else "SELECT * FROM tasks"
            cur.execute(query, params)
            for r in cur.fetchall():
                service.tasks[r["task_id"]] = CoordinationTask(
                    task_id=r["task_id"],
                    case_id=r["case_id"],
                    task_revision=r["task_revision"],
                    prior_task_revision=r["prior_task_revision"],
                    task_type=TaskType[r["task_type"]],
                    description_template=r["description_template"],
                    instruction_ids=json.loads(r["instruction_ids_json"]),
                    issue_ids=json.loads(r["issue_ids_json"]),
                )

            # 7. Task Projections
            query = "SELECT * FROM task_projections WHERE case_id = ?" if case_id else "SELECT * FROM task_projections"
            cur.execute(query, params)
            for r in cur.fetchall():
                service.task_projections[r["task_id"]] = TaskProjection(
                    task_id=r["task_id"],
                    case_id=r["case_id"],
                    state_version=r["state_version"],
                    status=TaskState[r["status"]],
                    validity=Validity[r["validity"]],
                    assigned_actor_id=r["assigned_actor_id"],
                    historical_completion_event_ids=json.loads(r["historical_completion_event_ids_json"]),
                )

            # 8. Acknowledgements
            query = "SELECT * FROM acknowledgements WHERE case_id = ?" if case_id else "SELECT * FROM acknowledgements"
            cur.execute(query, params)
            for r in cur.fetchall():
                service.acknowledgements[r["ack_id"]] = Acknowledgement(
                    ack_id=r["ack_id"],
                    case_id=r["case_id"],
                    task_id=r["task_id"],
                    task_revision=r["task_revision"],
                    actor_id=r["actor_id"],
                    dependency_ids=json.loads(r["dependency_ids_json"]),
                    event_id=r["event_id"],
                )

            # 9. Issues
            query = "SELECT * FROM issues WHERE case_id = ?" if case_id else "SELECT * FROM issues"
            cur.execute(query, params)
            for r in cur.fetchall():
                service.issues[r["issue_id"]] = EvidenceIssue(
                    issue_id=r["issue_id"],
                    case_id=r["case_id"],
                    kind=r["kind"],
                    span_ids=json.loads(r["span_ids_json"]),
                    question_template=r["question_template"],
                    opened_event_id=r["opened_event_id"],
                )

            # 10. Links
            query = "SELECT * FROM revision_links WHERE case_id = ?" if case_id else "SELECT * FROM revision_links"
            cur.execute(query, params)
            for r in cur.fetchall():
                service.links[r["link_id"]] = RevisionLink(
                    link_id=r["link_id"],
                    case_id=r["case_id"],
                    prior_document_id=r["prior_document_id"],
                    new_document_id=r["new_document_id"],
                    asserted_by=r["asserted_by"],
                    created_at=r["created_at"],
                    mapping_policy=r["mapping_policy"],
                )

            # 11. Rehearsals
            query = "SELECT * FROM rehearsals WHERE case_id = ?" if case_id else "SELECT * FROM rehearsals"
            cur.execute(query, params)
            for r in cur.fetchall():
                raw_choices = json.loads(r["choices_json"])
                choices = [RehearsalChoice(**c) for c in raw_choices]
                service.rehearsals[r["item_id"]] = RehearsalItem(
                    item_id=r["item_id"],
                    case_id=r["case_id"],
                    item_revision=r["item_revision"],
                    instruction_id=r["instruction_id"],
                    span_ids=json.loads(r["span_ids_json"]),
                    question_template=r["question_template"],
                    choices=choices,
                    execution_mode=r["execution_mode"],
                )

            # 12. Rehearsal Attempts
            query = "SELECT * FROM rehearsal_attempts WHERE case_id = ?" if case_id else "SELECT * FROM rehearsal_attempts"
            cur.execute(query, params)
            for r in cur.fetchall():
                service.rehearsal_attempts[r["attempt_id"]] = RehearsalAttempt(
                    attempt_id=r["attempt_id"],
                    case_id=r["case_id"],
                    item_id=r["item_id"],
                    item_revision=r["item_revision"],
                    actor_id=r["actor_id"],
                    choice_id=r["choice_id"],
                    outcome=AttemptOutcome[r["outcome"]],
                    event_id=r["event_id"],
                )

            # 13. Rehearsal Projections
            query = "SELECT * FROM rehearsal_projections WHERE case_id = ?" if case_id else "SELECT * FROM rehearsal_projections"
            cur.execute(query, params)
            for r in cur.fetchall():
                service.rehearsal_projections[(r["item_id"], r["actor_id"])] = RehearsalProjection(
                    item_id=r["item_id"],
                    actor_id=r["actor_id"],
                    case_id=r["case_id"],
                    state_version=r["state_version"],
                    state=RehearsalState[r["state"]],
                    validity=Validity[r["validity"]],
                )

            # 14. Events
            query = "SELECT * FROM events WHERE case_id = ? ORDER BY case_sequence ASC" if case_id else "SELECT * FROM events ORDER BY case_id, case_sequence ASC"
            cur.execute(query, params)
            for r in cur.fetchall():
                # Avoid duplicates if service already has events
                if not any(e.event_id == r["event_id"] for e in service.events):
                    payload = freeze_payload(json.loads(r["payload_json"]))
                    service.events.append(TaskEvent(
                        event_id=r["event_id"],
                        case_id=r["case_id"],
                        case_sequence=r["case_sequence"],
                        actor_id=r["actor_id"],
                        event_type=EventType[r["event_type"]],
                        resource_id=r["resource_id"],
                        resource_revision=r["resource_revision"],
                        dependency_ids=json.loads(r["dependency_ids_json"]),
                        payload=payload,
                        created_at=r["created_at"],
                    ))

            # 15. Receipts
            query = "SELECT * FROM receipts WHERE case_id = ?" if case_id else "SELECT * FROM receipts"
            cur.execute(query, params)
            for r in cur.fetchall():
                key_tuple = (r["case_id"], r["actor_id"], r["idempotency_key"])
                service.receipts[key_tuple] = CommandReceipt(
                    receipt_id=r["receipt_id"],
                    case_id=r["case_id"],
                    actor_id=r["actor_id"],
                    idempotency_key=r["idempotency_key"],
                    request_fingerprint=r["request_fingerprint"],
                    committed_state_version=r["committed_state_version"],
                    event_ids=json.loads(r["event_ids_json"]),
                    result=json.loads(r["result_json"]),
                )
