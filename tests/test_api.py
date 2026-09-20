import json
import os
import sys
import threading
import time
import unittest
import urllib.request
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from http.server import ThreadingHTTPServer
from api.server import Handler
from agent import tools

HOST, PORT = "127.0.0.1", 8091
BASE = f"http://{HOST}:{PORT}"


def _get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _post(path, body=None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(BASE + path, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer((HOST, PORT), Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        tools.CLUSTER = tools.SimulatedCluster()

    def test_health(self):
        status, body = _get("/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_status_reports_opencv_version(self):
        status, body = _get("/api/status")
        self.assertEqual(status, 200)
        self.assertIn("opencv_version", body)

    def test_unknown_route_404(self):
        status, body = _get("/api/does-not-exist")
        self.assertEqual(status, 404)

    def test_get_nonexistent_incident_404(self):
        status, body = _get("/api/incidents/INC-DOESNOTEXIST")
        self.assertEqual(status, 404)

    def test_full_lifecycle_via_http(self):
        status, r = _post("/api/demo/trigger", {"scenario": "backend_down"})
        self.assertEqual(status, 201)
        inc_id = r["incident_id"]
        self.assertEqual(r["status"], "awaiting_approval")

        status, r2 = _post(f"/api/incidents/{inc_id}/approve")
        self.assertEqual(status, 200)
        self.assertEqual(r2["incident"]["status"], "verifying")

        status, r3 = _post(f"/api/incidents/{inc_id}/verify")
        self.assertEqual(status, 200)
        self.assertEqual(r3["incident"]["status"], "resolved")

        status, r4 = _get(f"/api/incidents/{inc_id}")
        self.assertEqual(status, 200)
        self.assertEqual(r4["status"], "resolved")

    def test_reject_flow_via_http(self):
        status, r = _post("/api/demo/trigger", {"scenario": "backend_down"})
        inc_id = r["incident_id"]
        status, r2 = _post(f"/api/incidents/{inc_id}/reject")
        self.assertEqual(status, 200)
        self.assertEqual(r2["status"], "rejected")

    def test_approve_twice_returns_conflict(self):
        status, r = _post("/api/demo/trigger", {"scenario": "backend_down"})
        inc_id = r["incident_id"]
        _post(f"/api/incidents/{inc_id}/approve")
        status, body = _post(f"/api/incidents/{inc_id}/approve")
        self.assertEqual(status, 409)  # not awaiting_approval anymore

    def test_vision_analyze_endpoint(self):
        from demo.generate_dashboard import render_dashboard
        path = render_dashboard("healthy", "healthy", os.path.join(os.path.dirname(__file__), "..", "docs", "evidence", "_api_test_healthy.png"))
        status, body = _post("/api/vision/analyze", {"image_path": path})
        self.assertEqual(status, 200)
        self.assertEqual(body["overall_state"], "healthy")

    def test_vision_analyze_missing_param(self):
        status, body = _post("/api/vision/analyze", {})
        self.assertEqual(status, 400)

    def test_malformed_json_returns_400(self):
        req = urllib.request.Request(BASE + "/api/demo/trigger", data=b"{bad", method="POST", headers={"Content-Type":"application/json"})
        try:
            urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)
        else:
            self.fail("expected HTTP 400")

    def test_persisted_incident_can_be_loaded_for_lifecycle(self):
        status, r = _post("/api/demo/trigger", {"scenario":"backend_down"})
        self.assertEqual(status, 201)
        inc_id = r["incident_id"]
        # The lifecycle endpoint reloads from SQLite rather than an in-memory cache.
        status, r2 = _post(f"/api/incidents/{inc_id}/approve")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
