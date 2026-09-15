"""Fictional-only public adapter: per-visitor state and atomic Supabase commits."""
import dataclasses
import enum
import hashlib
import json
import os
import re
import secrets
import time
import urllib.request
from http.cookies import SimpleCookie
from urllib.parse import urlparse

from app import domain
from app.server import ThreadRequestHandler, FIXTURES_DIR, REPO_ROOT

# Only these domain types can be restored. No pickle or executable payloads.
TYPES = {name: value for name, value in vars(domain).items()
         if isinstance(value, type) and (dataclasses.is_dataclass(value) or issubclass(value, enum.Enum))}


def encode(value):
    if isinstance(value, enum.Enum):
        return {'type': type(value).__name__, 'value': value.value}
    if dataclasses.is_dataclass(value):
        return {'type': type(value).__name__, 'fields': {f.name: encode(getattr(value, f.name)) for f in dataclasses.fields(value)}}
    if isinstance(value, dict):
        return {'pairs': [[encode(k), encode(v)] for k, v in value.items()]}
    if isinstance(value, tuple):
        return {'tuple': [encode(v) for v in value]}
    if isinstance(value, list):
        return [encode(v) for v in value]
    return value


def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if not isinstance(value, dict):
        return value
    if 'pairs' in value:
        return {decode(k): decode(v) for k, v in value['pairs']}
    if 'tuple' in value:
        return tuple(decode(v) for v in value['tuple'])
    cls = TYPES[value['type']]
    if 'value' in value:
        return cls(value['value'])
    fields = {k: decode(v) for k, v in value['fields'].items()}
    if cls is domain.TaskEvent:
        fields['payload'] = domain.freeze_payload(fields['payload'])
    return cls(**fields)


def dump(service):
    return {k: encode(v) for k, v in vars(service).items() if k not in ('storage', '_lock')}


def restore(state):
    service = domain.ThreadService()
    for key in vars(service):
        if key not in ('storage', '_lock') and key in state:
            setattr(service, key, decode(state[key]))
    return service


class SupabaseStore:
    def rpc(self, operation, payload):
        base = os.environ['SUPABASE_URL'].rstrip('/')
        key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
        req = urllib.request.Request(base + '/rest/v1/rpc/thread_demo_' + operation,
            data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json',
            'apikey': key, 'Authorization': 'Bearer ' + key})
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=20) as response:
                    return json.load(response)
            except (urllib.error.URLError, TimeoutError):
                if attempt == 1:
                    raise
                time.sleep(0.5)

    def load(self, token_hash):
        return self.rpc('load', {'p_token': token_hash})

    def save(self, token_hash, version, state):
        return self.rpc('save', {'p_token': token_hash, 'p_version': version, 'p_state': state})


class HostedHandler(ThreadRequestHandler):
    store = SupabaseStore()

    @property
    def service(self):
        return self._service

    def log_message(self, *args):
        pass  # Source/request bodies are never logged by this adapter.

    def _send_cors_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        if getattr(self, '_new_cookie', None):
            self.send_header('Set-Cookie', '__Host-thread=' + self._new_cookie + '; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=86400')

    def _send_json(self, status, data, extra_headers=None):
        # Capture first; a response is successful only after a durable CAS commit.
        self._response = (status, data, extra_headers)

    def _parse_body(self):
        return self._body

    def _serve_ui(self):
        html = (REPO_ROOT / 'app/ui.html').read_text()
        html = html.replace('<script defer src="/assets/ui.js"></script>', '<script defer src="/assets/hosted-config.js"></script><script defer src="/assets/ui.js"></script>')
        html = html.replace('</head>', '<link rel="stylesheet" href="/assets/hosted.css"></head>')
        html = html.replace('YOUR LOCAL WORKSPACE', 'YOUR FICTIONAL DEMO')
        html = html.replace('Bring a source note.<br>Keep the handoff connected.', 'Try a changed appointment.<br>See what needs review.')
        html = html.replace('Use fictional text in this prototype.', 'Fixed fictional notes only. Session access expires after 24 hours.')
        html = html.replace('local service', 'hosted service').replace('local demo', 'hosted demo')
        html = html.replace('What works locally', 'What you can try')
        html = html.replace('AI source navigation requires a configured NVIDIA key.', 'AI source navigation is live with NVIDIA NIM.')
        self._send_html(html)

    def _allowed_body(self, path, body):
        if not isinstance(body, dict):
            return False
        if path.endswith('/ai/source-finder'):
            case_id = path.split('/')[4]
            return (
                body.get('fictional_only') is True
                and 'etag' in body
                and case_id in self.service.cases
                and body['etag'] == f'"case-state-{self.service.cases[case_id].state_version}"'
            )
        # Values are fixed fictional content or IDs already owned by this session.
        fixed = {
            'actor_id': {'Morgan'}, 'fictional_only': {True}, 'isolated': {True},
            'category': {'APPOINTMENT_QUOTE'}, 'field_name': {'appointment_wording'},
            'task_type': {'ARRANGE_TRANSPORT'},
            'description': {'Arrange transport for the quoted appointment.'},
            'filename': {'Original note.txt', 'Updated note.txt'},
            'text': {(FIXTURES_DIR / n).read_text() for n in ('s01_v1.txt', 's01_v2.txt')},
            'exact_quote': {line for d in self.service.documents.values() for line in d.text.splitlines() if line.startswith('Follow-up appointment:')},
        }
        id_fields = {
            'document_id': self.service.documents, 'prior_document_id': self.service.documents,
            'new_document_id': self.service.documents, 'instruction_id': self.service.instructions,
            'task_id': self.service.tasks,
            'expected_source_version': {d.source_version for d in self.service.documents.values()},
            'expected_prior_source_version': {d.source_version for d in self.service.documents.values()},
            'expected_new_source_version': {d.source_version for d in self.service.documents.values()},
            'expected_task_revision': {t.task_revision for t in self.service.tasks.values()},
        }
        for key, value in body.items():
            if not isinstance(value, (str, bool, int)):
                return False
            if key in fixed and value in fixed[key]:
                continue
            if key in id_fields and value in id_fields[key]:
                continue
            if key == 'completion_note' and isinstance(value, str) and len(value) <= 200:
                continue
            return False
        return True

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        self._handle(False)

    def do_POST(self):
        self._handle(True)

    def _handle(self, write):
        self._new_cookie = None
        self._response = (404, {'error': 'Not found'}, None)
        path = urlparse(self.path).path.rstrip('/') or '/'
        try:
            if not write and (path == '/' or path.startswith('/assets/') or path.startswith('/api/v1/fixtures/')):
                if path in ('/assets/hosted-config.js', '/assets/hosted.css'):
                    filename = path.rsplit('/', 1)[1]
                    data = (REPO_ROOT / 'app' / filename).read_bytes()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/javascript' if filename.endswith('.js') else 'text/css')
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(data)
                    return
                super().do_GET()
                if path.startswith('/api/') or path not in ('/', '/assets/ui.js', '/assets/ui.css'):
                    ThreadRequestHandler._send_json(self, *self._response)
                return
            if not write and not path.startswith('/api/'):
                return self._serve_not_found()
            if write:
                origin = self.headers.get('Origin')
                if (origin and origin not in ('https://' + self.headers.get('Host', ''), 'http://' + self.headers.get('Host', ''))) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                    return ThreadRequestHandler._send_json(self, 403, {'error': 'Use the demo on its own page.'})
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return ThreadRequestHandler._send_json(self, 415, {'error': 'JSON required'})
                length = int(self.headers.get('Content-Length', 0))
                if not 0 <= length <= 8192:
                    return ThreadRequestHandler._send_json(self, 413, {'error': 'Request too large'})
                self._body = json.loads(self.rfile.read(length))
            create = write and path in ('/api/v1/sessions', '/api/v1/demo/init-conflicting-path')
            cookies = SimpleCookie()
            cookies.load(self.headers.get('Cookie', ''))
            token = cookies.get('__Host-thread')
            token = token.value if token else ''
            if not re.fullmatch(r'[a-f0-9]{64}', token):
                if not create:
                    return ThreadRequestHandler._send_json(self, 401, {'error': 'Open a new fictional example to begin.'})
                token = secrets.token_hex(32)
                self._new_cookie = token
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            row = self.store.load(token_hash)
            if not row and not create:
                return ThreadRequestHandler._send_json(self, 401, {'error': 'This demo session expired. Reload to begin again.'})
            version = row['version'] if row else 0
            self._service = restore(row['state']) if row else domain.ThreadService()
            if write:
                allowed = re.fullmatch(r'/api/v1/cases/[^/]+/(documents|source-reviews|tasks|tasks/[^/]+/owner|tasks/[^/]+/complete|acknowledgements|replacement-links|reset|ai/source-finder)', path)
                if not create and not allowed:
                    return ThreadRequestHandler._send_json(self, 404, {'error': 'This action is not part of the public demo.'})
                if not self._allowed_body(path, self._body):
                    return ThreadRequestHandler._send_json(self, 400, {'error': 'This demo accepts only its fixed fictional examples.'})
                if create and len(self.service.cases) >= 2:
                    return ThreadRequestHandler._send_json(self, 409, {'error': 'Reset an existing example before opening another.'})
                if len(self.service.events) >= 100 and not path.endswith('/reset'):
                    return ThreadRequestHandler._send_json(self, 409, {'error': 'Demo limit reached. Reset this example.'})
                if path.endswith('/acknowledgements') and self.headers.get('Idempotency-Key') not in ('original-ack-01', 'updated-ack-01', 'stale-check-01'):
                    return ThreadRequestHandler._send_json(self, 400, {'error': 'Unsupported demo action key'})
                super().do_POST()
            else:
                if not re.fullmatch(r'/api/v1/cases/[^/]+(?:/(history|export|diff))?', path):
                    return ThreadRequestHandler._send_json(self, 404, {'error': 'Not found'})
                super().do_GET()
            status, data, headers = self._response
            if status >= 500 and not path.endswith('/ai/source-finder'):
                data = {'error': 'The demo could not complete this action.'}
            if write and status < 300:
                if not self.store.save(token_hash, version, dump(self.service)):
                    self._new_cookie = None
                    status, data = 409, {'error': 'The session changed in another request. Reconnect and retry.'}
            ThreadRequestHandler._send_json(self, status, data, headers)
        except (ValueError, TypeError, KeyError):
            self._new_cookie = None
            ThreadRequestHandler._send_json(self, 400, {'error': 'Invalid demo request or configuration.'})
        except Exception:
            self._new_cookie = None
            ThreadRequestHandler._send_json(self, 503, {'error': 'Demo storage is temporarily unavailable. Please retry shortly.'})
