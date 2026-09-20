"""
VisionNOC — docker/demo_app.py

A deliberately tiny stdlib HTTP service standing in for "the backend
application" in the Docker Compose demo stack. Its only job is to expose
/health and a Prometheus-format /metrics endpoint so `docker stop
visionnoc-backend` produces a real, visible outage that Prometheus and
Grafana (once wired up per docker-compose.yml) can show.

STATUS: written but NOT VERIFIED running — this sandbox has no Docker
daemon (see docs/PROJECT_STATUS.md). It has no dependencies beyond the
stdlib, so it should run correctly under `python3 docker/demo_app.py`
directly if you want to sanity-check it before building the image.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import time

START = time.time()
REQUEST_COUNT = 0


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        global REQUEST_COUNT
        REQUEST_COUNT += 1
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        elif self.path == "/metrics":
            uptime = time.time() - START
            body = (
                f"application_up 1\n"
                f"application_requests_total {REQUEST_COUNT}\n"
                f"application_uptime_seconds {uptime:.1f}\n"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"VisionNOC demo backend\n")


if __name__ == "__main__":
    print("demo backend listening on :9000")
    ThreadingHTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
