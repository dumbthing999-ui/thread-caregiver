"""THREAD HTTP Service and Interactive Viewer.

Serves:
  1. REST API enforcing RFC 9110/6585 concurrency headers, scoped idempotency,
     stale write rejection, and strict nonclinical boundaries.
  2. Single-Page Interactive Web Application at /:
     - Inspect original vs replacement source documents side-by-side.
     - Interactive step-by-step runner of the single working path.
     - Live demonstration of authoritative service rejection (409 STALE_REVISION_ERROR).
     - Live demonstration of idempotency conflict rejection (409 IDEMPOTENCY_KEY_REUSED).
     - Live inspection of the immutable event audit trail.
     - Live inspection of the blocked conflicting-source case.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import pathlib
import sys
import traceback
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from app.domain import (
    Category,
    DomainError,
    MalformedRequestError,
    NotFoundError,
    PreconditionRequiredError,
    TaskType,
    ThreadService,
    Validity,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "docs" / "day03" / "fixtures"

# Global service instance for the running server process
SERVICE = ThreadService()


import dataclasses


def to_serializable(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, dict):
        return {k: to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_serializable(v) for v in obj]
    return obj


class ThreadRequestHandler(BaseHTTPRequestHandler):
    server_version = "THREAD-HTTP/0.1.0"

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, If-Match, Idempotency-Key")

    def _send_json(self, status: int, data: Any, extra_headers: Optional[Dict[str, str]] = None):
        body = json.dumps(to_serializable(data), indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._send_cors_headers()
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_content: str):
        body = html_content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _parse_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MalformedRequestError(f"Malformed JSON body: {exc}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        try:
            if path == "/":
                return self._serve_ui()

            # Serve only these bundled assets; never turn request paths into file paths.
            assets = {"/assets/ui.css": ("ui.css", "text/css"), "/assets/ui.js": ("ui.js", "text/javascript")}
            if path in assets:
                filename, content_type = assets[path]
                body = (REPO_ROOT / "app" / filename).read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type + "; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return

            # API: GET /api/v1/cases/{case_id}
            if path.startswith("/api/v1/cases/"):
                parts = path.split("/")
                if len(parts) == 5:
                    case_id = parts[4]
                    snapshot = SERVICE.get_case_snapshot(case_id)
                    etag = snapshot["etag"]
                    return self._send_json(HTTPStatus.OK, snapshot, {"ETag": etag})
                elif len(parts) == 6 and parts[5] == "history":
                    case_id = parts[4]
                    history = SERVICE.get_history(case_id)
                    return self._send_json(HTTPStatus.OK, {"case_id": case_id, "events": history})
                elif len(parts) == 6 and parts[5] == "export":
                    case_id = parts[4]
                    exported = SERVICE.export_case(case_id)
                    return self._send_json(HTTPStatus.OK, exported)
                elif len(parts) == 6 and parts[5] == "diff":
                    case_id = parts[4]
                    qs = parse_qs(parsed.query)
                    doc1_id = qs.get("doc1", [None])[0]
                    doc2_id = qs.get("doc2", [None])[0]
                    if not doc1_id or not doc2_id:
                        raise MalformedRequestError("Diff requires 'doc1' and 'doc2' query parameters.")
                    if doc1_id not in SERVICE.documents or doc2_id not in SERVICE.documents:
                        raise NotFoundError("One or both documents not found in service.")
                    t1 = SERVICE.documents[doc1_id].text
                    t2 = SERVICE.documents[doc2_id].text
                    raw_diff = list(difflib.ndiff(t1.splitlines(), t2.splitlines()))
                    lines = []
                    for line in raw_diff:
                        code = line[:2]
                        content = line[2:]
                        if code == "+ ":
                            lines.append({"type": "add", "text": content})
                        elif code == "- ":
                            lines.append({"type": "del", "text": content})
                        elif code == "  ":
                            lines.append({"type": "same", "text": content})
                        elif code == "? ":
                            lines.append({"type": "hint", "text": content})
                    return self._send_json(HTTPStatus.OK, {
                        "case_id": case_id,
                        "doc1_id": doc1_id,
                        "doc2_id": doc2_id,
                        "diff": lines,
                    })
                elif len(parts) == 6 and parts[5] == "rehearsals":
                    case_id = parts[4]
                    rehearsals = [dataclasses.asdict(r) for r in SERVICE.rehearsals.values() if r.case_id == case_id]
                    projections = [dataclasses.asdict(p) for p in SERVICE.rehearsal_projections.values() if p.case_id == case_id]
                    return self._send_json(HTTPStatus.OK, {
                        "case_id": case_id,
                        "rehearsals": rehearsals,
                        "rehearsal_projections": projections,
                    })

            # API: GET /api/v1/fixtures/{name}
            if path.startswith("/api/v1/fixtures/"):
                name = path.replace("/api/v1/fixtures/", "")
                fix_file = FIXTURES_DIR / name
                if fix_file.exists() and fix_file.is_file():
                    content = fix_file.read_text(encoding="utf-8")
                    return self._send_json(HTTPStatus.OK, {"name": name, "content": content})
                return self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Fixture '{name}' not found"})

            return self._send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found", "path": path})

        except DomainError as de:
            return self._send_json(de.status_code, {"error": {"code": de.code, "message": de.message}})
        except Exception as exc:
            return self._send_json(500, {"error": {"code": "INTERNAL_SERVER_ERROR", "message": str(exc)}})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            # 1. POST /api/v1/sessions
            if path == "/api/v1/sessions":
                body = self._parse_body()
                fictional_only = body.get("fictional_only", True)
                case_id = body.get("case_id")
                case = SERVICE.create_case(case_id=case_id, fictional_only=fictional_only)
                return self._send_json(HTTPStatus.CREATED, {
                    "case_id": case.case_id,
                    "state_version": case.state_version,
                    "etag": f'"case-state-{case.state_version}"',
                    "message": "Fictional case initialized.",
                })

            # 2. POST /api/v1/cases/{case_id}/documents
            if path.endswith("/documents") and "/cases/" in path:
                case_id = path.split("/")[4]
                body = self._parse_body()
                filename = body.get("filename", "unnamed.txt")
                text = body.get("text", "")
                actor = body.get("actor_id", "Morgan")
                doc = SERVICE.import_document(case_id, filename, text, actor)
                c = SERVICE.get_case(case_id)
                return self._send_json(HTTPStatus.CREATED, {
                    "document": doc,
                    "state_version": c.state_version,
                    "etag": f'"case-state-{c.state_version}"',
                })

            # 3. POST /api/v1/cases/{case_id}/source-reviews
            if path.endswith("/source-reviews") and "/cases/" in path:
                case_id = path.split("/")[4]
                body = self._parse_body()
                doc_id = body.get("document_id")
                expected_sver = body.get("expected_source_version")
                category_str = body.get("category", "APPOINTMENT_QUOTE")
                category = Category[category_str]
                field_name = body.get("field_name", "appointment_wording")
                exact_quote = body.get("exact_quote", "")
                actor = body.get("actor_id", "Morgan")
                instr, span = SERVICE.review_source(case_id, doc_id, expected_sver, category, field_name, exact_quote, actor)
                c = SERVICE.get_case(case_id)
                return self._send_json(HTTPStatus.CREATED, {
                    "instruction": instr,
                    "span": span,
                    "state_version": c.state_version,
                    "etag": f'"case-state-{c.state_version}"',
                })

            # 4. POST /api/v1/cases/{case_id}/tasks
            if path.endswith("/tasks") and "/cases/" in path:
                case_id = path.split("/")[4]
                body = self._parse_body()
                task_type_str = body.get("task_type", "ARRANGE_TRANSPORT")
                task_type = TaskType[task_type_str]
                instr_id = body.get("instruction_id")
                desc = body.get("description", "Arrange non-emergency transport.")
                actor = body.get("actor_id", "Morgan")
                task, proj = SERVICE.create_task(case_id, task_type, instr_id, desc, actor)
                c = SERVICE.get_case(case_id)
                return self._send_json(HTTPStatus.CREATED, {
                    "task": task,
                    "projection": proj,
                    "state_version": c.state_version,
                    "etag": f'"case-state-{c.state_version}"',
                })

            # 5. POST /api/v1/cases/{case_id}/tasks/{task_id}/owner
            if "/tasks/" in path and path.endswith("/owner"):
                parts = path.split("/")
                case_id = parts[4]
                task_id = parts[6]
                body = self._parse_body()
                expected_trev = body.get("expected_task_revision")
                actor = body.get("actor_id", "Morgan")
                proj = SERVICE.confirm_owner(case_id, task_id, expected_trev, actor)
                c = SERVICE.get_case(case_id)
                return self._send_json(HTTPStatus.OK, {
                    "projection": proj,
                    "state_version": c.state_version,
                    "etag": f'"case-state-{c.state_version}"',
                })

            # 6. POST /api/v1/cases/{case_id}/acknowledgements
            if path.endswith("/acknowledgements") and "/cases/" in path:
                case_id = path.split("/")[4]
                if_match = self.headers.get("If-Match")
                idempotency_key = self.headers.get("Idempotency-Key")
                if not idempotency_key:
                    raise MalformedRequestError("Missing Idempotency-Key header.")

                # Validate If-Match case ETag
                SERVICE.validate_preconditions(case_id, if_match, require_etag=True)

                body = self._parse_body()
                task_id = body.get("task_id")
                expected_trev = body.get("expected_task_revision")
                actor = body.get("actor_id", "Morgan")

                fingerprint = SERVICE._compute_fingerprint("POST", path, body)
                ack, proj = SERVICE.acknowledge_task(case_id, task_id, expected_trev, actor, idempotency_key, fingerprint)
                c = SERVICE.get_case(case_id)
                return self._send_json(HTTPStatus.CREATED, {
                    "acknowledgement": ack,
                    "projection": proj,
                    "state_version": c.state_version,
                    "etag": f'"case-state-{c.state_version}"',
                })

            # 7. POST /api/v1/cases/{case_id}/replacement-links
            if path.endswith("/replacement-links") and "/cases/" in path:
                case_id = path.split("/")[4]
                if_match = self.headers.get("If-Match")
                SERVICE.validate_preconditions(case_id, if_match, require_etag=True)

                body = self._parse_body()
                prior_doc_id = body.get("prior_document_id")
                new_doc_id = body.get("new_document_id")
                exp_prior = body.get("expected_prior_source_version")
                exp_new = body.get("expected_new_source_version")
                actor = body.get("actor_id", "Morgan")

                link = SERVICE.link_replacement(case_id, prior_doc_id, new_doc_id, exp_prior, exp_new, actor)
                c = SERVICE.get_case(case_id)
                return self._send_json(HTTPStatus.CREATED, {
                    "link": link,
                    "state_version": c.state_version,
                    "etag": f'"case-state-{c.state_version}"',
                })

            # 8. POST /api/v1/cases/{case_id}/rehearsals
            if path.endswith("/rehearsals") and "/cases/" in path:
                case_id = path.split("/")[4]
                body = self._parse_body()
                instr_id = body.get("instruction_id")
                exp_irev = body.get("expected_instruction_revision")
                question = body.get("question", "")
                choices = body.get("choices", [])
                actor = body.get("actor_id", "Morgan")
                item, proj = SERVICE.create_rehearsal_item(case_id, instr_id, exp_irev, question, choices, actor)
                c = SERVICE.get_case(case_id)
                return self._send_json(HTTPStatus.CREATED, {
                    "rehearsal_item": item,
                    "projection": proj,
                    "state_version": c.state_version,
                    "etag": f'"case-state-{c.state_version}"',
                })

            # 9. POST /api/v1/cases/{case_id}/rehearsals/{item_id}/attempts
            if "/rehearsals/" in path and path.endswith("/attempts"):
                parts = path.split("/")
                case_id = parts[4]
                item_id = parts[6]
                body = self._parse_body()
                exp_irev = body.get("expected_item_revision")
                actor = body.get("actor_id", "Pat")
                choice_id = body.get("choice_id")
                attempt, proj = SERVICE.attempt_rehearsal(case_id, item_id, exp_irev, actor, choice_id)
                c = SERVICE.get_case(case_id)
                return self._send_json(HTTPStatus.CREATED, {
                    "attempt": attempt,
                    "projection": proj,
                    "state_version": c.state_version,
                    "etag": f'"case-state-{c.state_version}"',
                })

            # 10. POST /api/v1/cases/{case_id}/reset
            if path.endswith("/reset") and "/cases/" in path:
                case_id = path.split("/")[4]
                SERVICE.reset_case(case_id)
                return self._send_json(HTTPStatus.OK, {
                    "case_id": case_id,
                    "message": f"Case '{case_id}' reset successfully.",
                })

            # 11. POST /api/v1/demo/init-working-path
            if path == "/api/v1/demo/init-working-path":
                case = SERVICE.create_case("demo-case-01", fictional_only=True)
                # Ingest v1 fixture
                v1_path = FIXTURES_DIR / "s01_v1.txt"
                v1_text = v1_path.read_text(encoding="utf-8")
                doc1 = SERVICE.import_document(case.case_id, "s01_v1.txt", v1_text, "Morgan", "doc-v1", "v1")

                # Ingest v2 fixture
                v2_path = FIXTURES_DIR / "s01_v2.txt"
                v2_text = v2_path.read_text(encoding="utf-8")
                doc2 = SERVICE.import_document(case.case_id, "s01_v2.txt", v2_text, "Morgan", "doc-v2", "v2")

                return self._send_json(HTTPStatus.CREATED, {
                    "case_id": case.case_id,
                    "doc1": doc1,
                    "doc2": doc2,
                    "etag": f'"case-state-{case.state_version}"',
                })

            # 12. POST /api/v1/demo/init-conflicting-path
            if path == "/api/v1/demo/init-conflicting-path":
                # The UI requests a fresh example so it cannot reset another visitor's case.
                body = self._parse_body()
                case = SERVICE.create_case(None if body.get("isolated") is True else "demo-conflict-01", fictional_only=True)
                ca_path = FIXTURES_DIR / "s02_conflicting_a.txt"
                cb_path = FIXTURES_DIR / "s02_conflicting_b.txt"
                text_a = ca_path.read_text(encoding="utf-8")
                text_b = cb_path.read_text(encoding="utf-8")

                doc_a, doc_b, issue, task = SERVICE.setup_conflicting_case(case.case_id, text_a, text_b)
                return self._send_json(HTTPStatus.CREATED, {
                    "case_id": case.case_id,
                    "doc_a": doc_a,
                    "doc_b": doc_b,
                    "issue": issue,
                    "clarification_task": task,
                    "etag": f'"case-state-{case.state_version}"',
                })

            return self._send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found", "path": path})

        except DomainError as de:
            return self._send_json(de.status_code, {"error": {"code": de.code, "message": de.message}})
        except Exception as exc:
            traceback.print_exc()
            return self._send_json(500, {"error": {"code": "INTERNAL_SERVER_ERROR", "message": str(exc)}})

    def _serve_ui(self):
        self._send_html((REPO_ROOT / "app" / "ui.html").read_text(encoding="utf-8"))

class ThreadingServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_server(host: str = "127.0.0.1", port: int = 8000, db_path: Optional[str] = None) -> ThreadingServer:
    global SERVICE
    if db_path:
        from app.storage import ThreadStorage
        storage = ThreadStorage(db_path)
        SERVICE = ThreadService(storage=storage)
    server_address = (host, port)
    server = ThreadingServer(server_address, ThreadRequestHandler)
    print(f"THREAD Server running at http://{host}:{port}/")
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="THREAD Authoritative Coordination Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    parser.add_argument("--db", default=None, help="SQLite database path for persistence (e.g. thread.db)")
    args = parser.parse_args()

    server = run_server(args.host, args.port, db_path=args.db)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.shutdown()
