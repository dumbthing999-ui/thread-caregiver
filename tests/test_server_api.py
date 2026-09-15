"""Integration test for THREAD HTTP API and Viewer Server."""

from __future__ import annotations

import json
import threading
import time
import unittest
import urllib.error
import urllib.request

from app.server import run_server


class TestServerAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 8998
        cls.host = "127.0.0.1"
        cls.server = run_server(cls.host, cls.port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=1.0)

    def _url(self, path: str) -> str:
        return f"http://{self.host}:{self.port}{path}"

    def test_ai_endpoint_revision_consent_origin_and_no_mutation(self):
        from unittest.mock import patch
        from app.server import SERVICE
        case = SERVICE.create_case(fictional_only=True)
        SERVICE.import_document(case.case_id, 'Fictional.txt', 'Follow-up appointment: Monday at 09:00.', 'Morgan')
        snapshot = SERVICE.get_case_snapshot(case.case_id)
        path = '/api/v1/cases/' + case.case_id + '/ai/source-finder'
        def send(body, origin=None):
            headers = {'Content-Type': 'application/json'}
            if origin:
                headers['Origin'] = origin
            req = urllib.request.Request(self._url(path), data=json.dumps(body).encode(), headers=headers)
            try:
                with urllib.request.urlopen(req) as resp:
                    return resp.status, json.load(resp)
            except urllib.error.HTTPError as exc:
                with exc:
                    return exc.code, json.load(exc)
        body = {'fictional_only': True, 'etag': snapshot['etag']}
        with patch('app.server.find_sources', return_value={'citations': []}) as provider:
            self.assertEqual(send({})[0], 400)
            self.assertEqual(send({**body, 'etag': 'old'})[0], 409)
            self.assertEqual(send(body, 'https://unrelated.example')[0], 403)
            provider.assert_not_called()
            status, result = send(body)
            self.assertEqual(status, 200)
            self.assertEqual(result['etag'], snapshot['etag'])
            self.assertEqual(SERVICE.get_case_snapshot(case.case_id), snapshot)
            self.assertEqual(provider.call_args.args[0], snapshot['documents'])
        def change_during_request(documents):
            SERVICE.import_document(case.case_id, 'Update.txt', 'Follow-up appointment: Tuesday at 10:00.', 'Morgan')
            return {'citations': []}
        with patch('app.server.find_sources', side_effect=change_during_request):
            self.assertEqual(send(body)[0], 409)

    def test_ui_serves_html(self):
        req = urllib.request.Request(self._url("/"))
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/html", resp.headers.get("Content-Type", ""))
            content = resp.read().decode("utf-8")
            self.assertIn("Know what changed.", content)
            self.assertIn("Create a local handoff", content)
            self.assertIn("Judge demo · scripted example", content)
            self.assertIn("Export case JSON", content)
            self.assertIn('aria-label="Handoff progress"', content)
            self.assertIn('src="/assets/ui.js"', content)
            self.assertIn('href="/assets/ui.css"', content)

    def test_unknown_page_gets_a_human_404_page(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self._url("/missing-page"))
        with caught.exception as response:
            self.assertEqual(response.code, 404)
            self.assertIn("text/html", response.headers.get("Content-Type", ""))
            page = response.read().decode("utf-8")
            self.assertIn("That thread leads nowhere.", page)
            self.assertIn('href="/"', page)

    def test_fixture_route_restricts_file_access(self):
        with urllib.request.urlopen(self._url('/api/v1/fixtures/s01_v1.txt')) as resp:
            self.assertIn('Follow-up appointment:', json.load(resp)['content'])
        for name in ('../../../README.md', '/etc/hostname',
                     '%2e%2e/%2e%2e/%2e%2e/README.md', 'unsupported_format.bin'):
            with self.subTest(name=name):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(self._url('/api/v1/fixtures/' + name))
                with caught.exception as response:
                    self.assertEqual(response.code, 404)

    def test_ui_assets_and_isolated_conflict_examples(self):
        for asset, mime in (("ui.js", "text/javascript"), ("ui.css", "text/css")):
            with urllib.request.urlopen(self._url("/assets/" + asset)) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn(mime, resp.headers["Content-Type"])
                self.assertGreater(len(resp.read()), 100)
        examples = []
        for _ in range(2):
            req = urllib.request.Request(self._url("/api/v1/demo/init-conflicting-path"),
                data=b'{"isolated":true}', headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req) as resp:
                examples.append(json.load(resp))
        self.assertNotEqual(examples[0]["case_id"], examples[1]["case_id"])
        self.assertNotEqual(examples[0]["doc_a"]["document_id"], examples[1]["doc_a"]["document_id"])
        for example in examples:
            with urllib.request.urlopen(self._url("/api/v1/cases/" + example["case_id"])) as resp:
                snapshot = json.load(resp)
                self.assertEqual(len(snapshot["documents"]), 2)
                self.assertEqual(len(snapshot["issues"]), 1)

    def test_e2e_http_working_path(self):
        # 1. Initialize working path demo
        req = urllib.request.Request(
            self._url("/api/v1/demo/init-working-path"),
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)
            init_data = json.loads(resp.read().decode("utf-8"))
            cid = init_data["case_id"]
            etag = init_data["etag"]

        # 2. Review exact quote
        review_body = json.dumps({
            "document_id": init_data["doc1"]["document_id"],
            "expected_source_version": "v1",
            "category": "APPOINTMENT_QUOTE",
            "field_name": "appointment_wording",
            "exact_quote": "Follow-up appointment: Thursday at 10:00.",
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/source-reviews"),
            data=review_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)
            rev_data = json.loads(resp.read().decode("utf-8"))
            instr_id = rev_data["instruction"]["instruction_id"]
            etag = rev_data["etag"]

        # 3. Create transport task
        task_body = json.dumps({
            "task_type": "ARRANGE_TRANSPORT",
            "instruction_id": instr_id,
            "description": "Arrange wheelchair transport for Thursday 10:00.",
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/tasks"),
            data=task_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)
            task_data = json.loads(resp.read().decode("utf-8"))
            task_id = task_data["task"]["task_id"]
            trev = task_data["task"]["task_revision"]
            etag = task_data["etag"]

        # 4. Acknowledge task
        ack_body = json.dumps({
            "task_id": task_id,
            "expected_task_revision": trev,
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/acknowledgements"),
            data=ack_body,
            headers={
                "Content-Type": "application/json",
                "If-Match": etag,
                "Idempotency-Key": "http-ack-001",
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)
            ack_data = json.loads(resp.read().decode("utf-8"))
            etag = ack_data["etag"]
            self.assertEqual(ack_data["projection"]["status"], "ACKNOWLEDGED")

        # 5. Link replacement document
        link_body = json.dumps({
            "prior_document_id": init_data["doc1"]["document_id"],
            "new_document_id": init_data["doc2"]["document_id"],
            "expected_prior_source_version": "v1",
            "expected_new_source_version": "v2",
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/replacement-links"),
            data=link_body,
            headers={"Content-Type": "application/json", "If-Match": etag},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)
            link_data = json.loads(resp.read().decode("utf-8"))
            etag = link_data["etag"]

        # 6. Verify service rejects stale acknowledgement with 409
        stale_body = json.dumps({
            "task_id": task_id,
            "expected_task_revision": trev,
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/acknowledgements"),
            data=stale_body,
            headers={
                "Content-Type": "application/json",
                "If-Match": etag,
                "Idempotency-Key": "stale-http-key-002",
            },
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        with ctx.exception as exc:
            self.assertEqual(exc.code, 409)
            err_body = json.loads(exc.read().decode("utf-8"))
            self.assertEqual(err_body["error"]["code"], "STALE_REVISION_ERROR")

        # 7. Verify conflicting retry under existing key returns 409 IDEMPOTENCY_KEY_REUSED
        conflict_body = json.dumps({
            "task_id": task_id,
            "expected_task_revision": "different-revision",
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/acknowledgements"),
            data=conflict_body,
            headers={
                "Content-Type": "application/json",
                "If-Match": etag,
                "Idempotency-Key": "http-ack-001",
            },
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        with ctx.exception as exc:
            self.assertEqual(exc.code, 409)
            err_body = json.loads(exc.read().decode("utf-8"))
            self.assertEqual(err_body["error"]["code"], "IDEMPOTENCY_KEY_REUSED")

        # 8. Check history endpoint
        req = urllib.request.Request(self._url(f"/api/v1/cases/{cid}/history"))
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            hist_data = json.loads(resp.read().decode("utf-8"))
            events = hist_data["events"]
            self.assertTrue(len(events) >= 6)

    def test_http_rehearsal_and_medication_rejection(self):
        # 1. Initialize working path demo
        req = urllib.request.Request(
            self._url("/api/v1/demo/init-working-path"),
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            init_data = json.loads(resp.read().decode("utf-8"))
            cid = init_data["case_id"]

        # 2. Source review appointment quote
        review_body = json.dumps({
            "document_id": init_data["doc1"]["document_id"],
            "expected_source_version": "v1",
            "category": "APPOINTMENT_QUOTE",
            "field_name": "appointment_wording",
            "exact_quote": "Follow-up appointment: Thursday at 10:00.",
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/source-reviews"),
            data=review_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            rev_data = json.loads(resp.read().decode("utf-8"))
            instr_id = rev_data["instruction"]["instruction_id"]
            irev = rev_data["instruction"]["instruction_revision"]

        # 3. Create rehearsal item via HTTP
        rehearsal_body = json.dumps({
            "instruction_id": instr_id,
            "expected_instruction_revision": irev,
            "question": "When is the appointment?",
            "choices": [
                {"choice_id": "c1", "text": "Thursday at 10:00", "is_match": True},
                {"choice_id": "c2", "text": "Saturday at 09:00", "is_match": False},
            ],
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/rehearsals"),
            data=rehearsal_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)
            ritem_data = json.loads(resp.read().decode("utf-8"))
            item_id = ritem_data["rehearsal_item"]["item_id"]
            item_rev = ritem_data["rehearsal_item"]["item_revision"]
            self.assertEqual(ritem_data["projection"]["state"], "NOT_REVIEWED")

        # 4. Attempt rehearsal choice via HTTP
        attempt_body = json.dumps({
            "expected_item_revision": item_rev,
            "actor_id": "Pat",
            "choice_id": "c1",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/rehearsals/{item_id}/attempts"),
            data=attempt_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)
            att_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(att_data["attempt"]["outcome"], "MATCH")
            self.assertEqual(att_data["projection"]["state"], "REVIEWED_FOR_VERSION")

        # 5. Ingest medication quote and attempt clinical rehearsal (must reject 422)
        med_rev_body = json.dumps({
            "document_id": init_data["doc1"]["document_id"],
            "expected_source_version": "v1",
            "category": "MEDICATION_QUOTE",
            "field_name": "medication_text",
            "exact_quote": "Lisinopril 10mg oral daily in morning.",
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/source-reviews"),
            data=med_rev_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            med_data = json.loads(resp.read().decode("utf-8"))
            med_instr_id = med_data["instruction"]["instruction_id"]
            med_irev = med_data["instruction"]["instruction_revision"]

        bad_rehearsal_body = json.dumps({
            "instruction_id": med_instr_id,
            "expected_instruction_revision": med_irev,
            "question": "What is the dose?",
            "choices": [{"choice_id": "m1", "text": "10 mg", "is_match": True}],
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/rehearsals"),
            data=bad_rehearsal_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        with ctx.exception as exc:
            self.assertEqual(exc.code, 422)
            err = json.loads(exc.read().decode("utf-8"))
            self.assertEqual(err["error"]["code"], "TASK_NOT_ALLOWED")

    def test_http_diff_export_and_reset(self):
        # 1. Init demo
        req = urllib.request.Request(
            self._url("/api/v1/demo/init-working-path"),
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            init_data = json.loads(resp.read().decode("utf-8"))
            cid = init_data["case_id"]
            d1_id = init_data["doc1"]["document_id"]
            d2_id = init_data["doc2"]["document_id"]

        # 2. Diff endpoint
        req = urllib.request.Request(self._url(f"/api/v1/cases/{cid}/diff?doc1={d1_id}&doc2={d2_id}"))
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            diff_data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("diff", diff_data)
            diff_types = {row["type"] for row in diff_data["diff"]}
            self.assertIn("add", diff_types)
            self.assertIn("del", diff_types)

        # 3. Export endpoint
        req = urllib.request.Request(self._url(f"/api/v1/cases/{cid}/export"))
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            export_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(export_data["case"]["case_id"], cid)
            self.assertEqual(len(export_data["documents"]), 2)
            self.assertIn("events", export_data)

        # 4. Reset endpoint
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/reset"),
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)

        # Verify case is not found after reset
        req = urllib.request.Request(self._url(f"/api/v1/cases/{cid}"))
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        with ctx.exception as exc:
            self.assertEqual(exc.code, 404)

    def test_task_completion_endpoint(self):
        # 1. Initialize demo case
        req = urllib.request.Request(self._url("/api/v1/demo/init-working-path"), data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as resp:
            init_data = json.loads(resp.read().decode("utf-8"))
            cid = init_data["case_id"]

        # 2. Source review
        rev_body = json.dumps({
            "document_id": init_data["doc1"]["document_id"],
            "expected_source_version": "v1",
            "category": "APPOINTMENT_QUOTE",
            "field_name": "appointment_wording",
            "exact_quote": "Follow-up appointment: Thursday at 10:00.",
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(self._url(f"/api/v1/cases/{cid}/source-reviews"), data=rev_body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as resp:
            rev_data = json.loads(resp.read().decode("utf-8"))
            instr_id = rev_data["instruction"]["instruction_id"]

        # 3. Create task
        task_body = json.dumps({
            "task_type": "ARRANGE_TRANSPORT",
            "instruction_id": instr_id,
            "description": "Arrange transport for appointment.",
            "actor_id": "Morgan",
        }).encode("utf-8")
        req = urllib.request.Request(self._url(f"/api/v1/cases/{cid}/tasks"), data=task_body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as resp:
            task_data = json.loads(resp.read().decode("utf-8"))
            tid = task_data["task"]["task_id"]
            trev = task_data["task"]["task_revision"]
            etag = task_data["etag"]

        # 4. Complete task
        comp_body = json.dumps({
            "expected_task_revision": trev,
            "actor_id": "Morgan",
            "completion_note": "Ride confirmed with driver.",
        }).encode("utf-8")
        req = urllib.request.Request(
            self._url(f"/api/v1/cases/{cid}/tasks/{tid}/complete"),
            data=comp_body,
            headers={"Content-Type": "application/json", "If-Match": etag, "Idempotency-Key": "comp-key-1"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            comp_res = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(comp_res["projection"]["status"], "DONE")


if __name__ == "__main__":
    unittest.main()
