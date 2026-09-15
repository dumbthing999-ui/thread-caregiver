"""Run locally, or THREAD_TEST_URL=https://... python -m unittest tests.test_hosted."""
import copy
import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from app.hosted import HostedHandler
from app.server import FIXTURES_DIR


class MemoryStore:
    def __init__(self):
        self.rows = {}
        self.lock = threading.Lock()
        self.reject = False

    def load(self, token):
        with self.lock:
            return copy.deepcopy(self.rows.get(token))

    def save(self, token, version, state):
        with self.lock:
            if self.reject or self.rows.get(token, {}).get('version', 0) != version:
                return False
            self.rows[token] = {'version': version + 1, 'state': copy.deepcopy(state)}
            return True


class TestHosted(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.origin = os.getenv('THREAD_TEST_URL')
        if not cls.origin:
            class Handler(HostedHandler):
                store = MemoryStore()
            cls.handler = Handler
            cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            cls.origin = 'http://127.0.0.1:' + str(cls.server.server_port)
            cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
            cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'server'):
            cls.server.shutdown()
            cls.server.server_close()
            cls.thread.join()

    def setUp(self):
        self.cookie = ''

    def request(self, path, body=None, headers=None, cookie=None):
        h = {'Content-Type': 'application/json', 'Cookie': self.cookie if cookie is None else cookie}
        h.update(headers or {})
        req = urllib.request.Request(self.origin + path, data=None if body is None else json.dumps(body).encode(), headers=h)
        try:
            response = urllib.request.urlopen(req, timeout=40)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            if response.headers.get('Set-Cookie'):
                self.cookie = response.headers['Set-Cookie'].split(';')[0]
                self.assertIn('HttpOnly', response.headers['Set-Cookie'])
                self.assertIn('Secure', response.headers['Set-Cookie'])
            return response.status, json.load(response)

    def start(self):
        status, case = self.request('/api/v1/sessions', {'fictional_only': True})
        self.assertEqual(status, 201, case)
        return '/api/v1/cases/' + case['case_id']

    def test_full_path_isolation_stale_retry_reset(self):
        path = self.start()
        first_cookie = self.cookie
        def post(suffix, body, headers=None):
            status, data = self.request(path + suffix, body, headers)
            self.assertLess(status, 300, data)
            return data
        def import_doc(name, fixture):
            return post('/documents', {'filename': name, 'text': (FIXTURES_DIR / fixture).read_text(), 'actor_id': 'Morgan'})['document']
        doc = import_doc('Original note.txt', 's01_v1.txt')
        quote = next(line for line in doc['text'].splitlines() if line.startswith('Follow-up appointment:'))
        review = post('/source-reviews', {'document_id': doc['document_id'], 'expected_source_version': doc['source_version'], 'category': 'APPOINTMENT_QUOTE', 'field_name': 'appointment_wording', 'exact_quote': quote, 'actor_id': 'Morgan'})
        task = post('/tasks', {'instruction_id': review['instruction']['instruction_id'], 'task_type': 'ARRANGE_TRANSPORT', 'description': 'Arrange transport for the quoted appointment.', 'actor_id': 'Morgan'})['task']
        owned = post('/tasks/' + task['task_id'] + '/owner', {'expected_task_revision': task['task_revision'], 'actor_id': 'Morgan'})
        body = {'task_id': task['task_id'], 'expected_task_revision': task['task_revision'], 'actor_id': 'Morgan'}
        ack = post('/acknowledgements', body, {'If-Match': owned['etag'], 'Idempotency-Key': 'original-ack-01'})
        updated = import_doc('Updated note.txt', 's01_v2.txt')
        _, snapshot = self.request(path)
        linked = post('/replacement-links', {'prior_document_id': doc['document_id'], 'new_document_id': updated['document_id'], 'expected_prior_source_version': doc['source_version'], 'expected_new_source_version': updated['source_version'], 'actor_id': 'Morgan'}, {'If-Match': snapshot['etag']})
        _, before = self.request(path + '/history')
        code, stale = self.request(path + '/acknowledgements', body, {'If-Match': linked['etag'], 'Idempotency-Key': 'stale-check-01'})
        self.assertEqual(code, 409, stale)
        self.assertEqual(stale['error']['code'], 'STALE_REVISION_ERROR')
        retried = post('/acknowledgements', body, {'If-Match': linked['etag'], 'Idempotency-Key': 'original-ack-01'})
        self.assertEqual(retried['acknowledgement']['ack_id'], ack['acknowledgement']['ack_id'])
        self.assertEqual(self.request(path + '/history')[1], before)
        self.assertEqual(self.request(path, cookie='')[0], 401)
        self.cookie = ''
        other = self.start()
        self.assertEqual(self.request(path)[0], 404)
        self.request(other + '/reset', {})
        self.cookie = first_cookie
        post('/reset', {})
        self.assertEqual(self.request(path)[0], 404)

    def test_public_input_and_origin_restrictions(self):
        path = self.start()
        for suffix, payload in [('/documents', {'filename': 'Original note.txt', 'text': 'Arbitrary fictional upload'}), ('/ai/source-finder', {'fictional_only': True})]:
            self.assertIn(self.request(path + suffix, payload)[0], (400, 404))
        self.assertEqual(self.request(path + '/reset', {}, {'Origin': 'https://unrelated.example'})[0], 403)
        self.assertEqual(self.request('/api/v1/sessions', {'case_id': 'injected'})[0], 400)
        self.assertEqual(self.request(path + '/reset', {})[0], 200)

    def test_conflict_survives_state_roundtrip(self):
        code, case = self.request('/api/v1/demo/init-conflicting-path', {'isolated': True})
        self.assertEqual(code, 201, case)
        path = '/api/v1/cases/' + case['case_id']
        code, snapshot = self.request(path)
        self.assertEqual(code, 200, snapshot)
        self.assertEqual(len(snapshot['issues']), 1)
        self.assertEqual(len(snapshot['documents']), 2)
        self.assertEqual(self.request(path + '/export')[0], 200)
        self.assertEqual(self.request(path + '/reset', {})[0], 200)

    def test_ai_source_finder_endpoint(self):
        path = self.start()
        status, data = self.request(path + '/documents', {
            'filename': 'Original note.txt',
            'text': (FIXTURES_DIR / 's01_v1.txt').read_text(),
            'actor_id': 'Morgan'
        })
        self.assertEqual(status, 201)
        status, snapshot = self.request(path)
        self.assertEqual(status, 200)
        # Stale/mismatched etag rejected
        status, _ = self.request(path + '/ai/source-finder', {'fictional_only': True, 'etag': 'invalid-etag'})
        self.assertIn(status, (400, 409))
        # Valid request with etag
        status, res = self.request(path + '/ai/source-finder', {'fictional_only': True, 'etag': snapshot['etag']})
        if os.getenv('THREAD_TEST_URL'):
            self.assertIn(status, (200, 503), res)
        elif os.getenv('NVIDIA_API_KEY'):
            self.assertEqual(status, 200, res)
            self.assertIn('citations', res)
        else:
            self.assertIn(status, (200, 503), res)
        self.request(path + '/reset', {})

    def test_rejected_commit_is_not_success_or_mutation(self):
        if os.getenv('THREAD_TEST_URL'):
            self.skipTest('Fault injection is local only')
        path = self.start()
        before = self.request(path)[1]
        self.handler.store.reject = True
        try:
            self.assertEqual(self.request(path + '/reset', {})[0], 409)
        finally:
            self.handler.store.reject = False
        self.assertEqual(self.request(path)[1], before)
        self.request(path + '/reset', {})


class TestVercelRoute(unittest.TestCase):
    def test_rewrite_restores_original_route_and_query(self):
        from unittest.mock import patch
        from api.index import handler
        request = object.__new__(handler)
        request.path = '/api/index?__thread_path=api/v1/cases/example/diff&doc1=a&doc2=b'
        with patch.object(HostedHandler, '_handle') as dispatch:
            request._handle(False)
        self.assertEqual(request.path, '/api/v1/cases/example/diff?doc1=a&doc2=b')
        dispatch.assert_called_once_with(False)
