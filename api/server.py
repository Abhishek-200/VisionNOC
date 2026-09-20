"""VisionNOC stdlib HTTP API.

The MVP intentionally uses Python's standard library HTTP server so the local
incident workflow remains dependency-light. It exposes JSON lifecycle routes,
Prometheus metrics, an optional bearer-token guard, and a small browser UI for
human approval. FastAPI remains an optional future replacement, not a runtime
requirement.
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path
import os
import cv2

from agent import agent as agent_ops
from agent import tools
from agent.models import Incident
from store.db import IncidentStore
from vision.detector import analyze_dashboard

STORE = IncidentStore()
ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_ROOT = (ROOT / "docs" / "evidence").resolve()

ROUTES_STATIC = {
    ("GET", "/health"),
    ("GET", "/api/status"),
    ("GET", "/api/incidents"),
    ("POST", "/api/vision/analyze"),
    ("POST", "/api/demo/trigger"),
}
ID_ROUTE = re.compile(r"^/api/incidents/(?P<id>[A-Za-z0-9\-]+)(?P<sub>/approve|/reject|/verify)?$")


def _json_response(handler: BaseHTTPRequestHandler, status: int, body: dict):
    payload = json.dumps(body, default=str).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _read_body(handler: BaseHTTPRequestHandler) -> tuple[dict | None, str | None]:
    try:
        length = int(handler.headers.get("Content-Length", 0) or 0)
        if length > 1_000_000: return None, "request body too large"
        raw = handler.rfile.read(length)
        if not raw: return {}, None
        value = json.loads(raw)
        if not isinstance(value, dict): return None, "JSON body must be an object"
        return value, None
    except (ValueError, json.JSONDecodeError):
        return None, "invalid JSON body"


def _safe_image_path(value: str) -> str:
    path = Path(value).expanduser().resolve()
    if EVIDENCE_ROOT not in path.parents:
        raise ValueError("image_path must point inside docs/evidence")
    if not path.is_file(): raise ValueError("image_path does not exist")
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}: raise ValueError("unsupported image type")
    return str(path)

def _load_incident(incident_id: str) -> Incident | None:
    raw = STORE.get(incident_id)
    return Incident.from_dict(raw) if raw else None

def _auth_required(handler: BaseHTTPRequestHandler) -> bool:
    token = os.environ.get("VISIONNOC_API_TOKEN")
    if not token: return True
    if handler.headers.get("Authorization", "") == f"Bearer {token}": return True
    _json_response(handler, 401, {"error":"missing or invalid bearer token"}); return False


def _persist(incident: Incident):
    STORE.save(incident)


def _text_response(handler, status: int, body: str, content_type: str):
    payload=body.encode(); handler.send_response(status); handler.send_header("Content-Type", content_type); handler.send_header("Content-Length", str(len(payload))); handler.end_headers(); handler.wfile.write(payload)


UI = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VisionNOC — Agentic Incident Response</title>
<style>
:root{
  --bg:#0b1020;
  --panel:#121a2b;
  --panel2:#182238;
  --text:#e8edf7;
  --muted:#94a3b8;
  --border:#26344f;
  --green:#22c55e;
  --red:#ef4444;
  --yellow:#f59e0b;
  --blue:#38bdf8;
}
*{box-sizing:border-box}
body{
  margin:0;
  background:var(--bg);
  color:var(--text);
  font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
.container{
  max-width:1200px;
  margin:auto;
  padding:28px 20px 50px;
}
header{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:20px;
  margin-bottom:25px;
}
.brand h1{
  margin:0;
  font-size:30px;
}
.brand p{
  margin:6px 0 0;
  color:var(--muted);
}
button{
  border:0;
  border-radius:9px;
  padding:11px 18px;
  font-size:14px;
  font-weight:700;
  cursor:pointer;
}
.primary{background:var(--blue);color:#06111a}
.approve{background:var(--green);color:#041208}
.reject{background:var(--red);color:white}
.verify{background:var(--panel2);color:var(--text);border:1px solid var(--border)}
button:disabled{opacity:.5;cursor:not-allowed}
.status{
  padding:14px 18px;
  border:1px solid var(--border);
  border-radius:12px;
  background:var(--panel);
  margin-bottom:20px;
}
.status strong{font-size:18px}
.status.healthy{border-color:#166534}
.status.incident{border-color:#991b1b}
.status.waiting{border-color:#92400e}
.status.resolved{border-color:#166534}
.grid{
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:16px;
}
.card{
  background:var(--panel);
  border:1px solid var(--border);
  border-radius:14px;
  padding:20px;
}
.card.full{grid-column:1/-1}
.card h2{
  margin:0 0 15px;
  font-size:17px;
}
.step{
  display:flex;
  align-items:center;
  gap:12px;
  margin-bottom:15px;
}
.step:last-child{margin-bottom:0}
.badge{
  width:34px;
  height:34px;
  border-radius:50%;
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight:800;
  background:var(--panel2);
  color:var(--blue);
}
.label{color:var(--muted);font-size:12px;text-transform:uppercase}
.value{font-size:16px;font-weight:700;margin-top:3px}
.metrics{
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:10px;
}
.metric{
  background:var(--panel2);
  padding:13px;
  border-radius:9px;
}
.metric .label{font-size:11px}
.metric .value{font-size:18px}
.good{color:var(--green)}
.bad{color:var(--red)}
.warn{color:var(--yellow)}
.info{color:var(--blue)}
.evidence{
  display:grid;
  gap:9px;
}
.evidence-row{
  display:flex;
  justify-content:space-between;
  gap:15px;
  padding:11px 13px;
  border-radius:8px;
  background:var(--panel2);
}
.actions{
  display:flex;
  gap:10px;
  flex-wrap:wrap;
}
.timeline{
  display:grid;
  gap:10px;
}
.timeline-item{
  padding:13px;
  border-left:3px solid var(--blue);
  background:var(--panel2);
  border-radius:0 8px 8px 0;
}
.small{font-size:12px;color:var(--muted)}
pre{
  white-space:pre-wrap;
  word-break:break-word;
  background:#070b15;
  padding:15px;
  border-radius:9px;
  overflow:auto;
  max-height:400px;
  font-size:12px;
}
.hidden{display:none}
@media(max-width:800px){
  .grid{grid-template-columns:1fr}
  .card.full{grid-column:auto}
  .metrics{grid-template-columns:1fr}
  header{align-items:flex-start;flex-direction:column}
}
</style>
</head>

<body>
<div class="container">

<header>
  <div class="brand">
    <h1>VisionNOC</h1>
    <p>Agentic Visual Incident Response System</p>
  </div>
  <button class="primary" onclick="trigger()">Trigger Backend Incident</button>
</header>

<div id="status" class="status">
  <strong>Ready</strong>
  <div class="small">Waiting for an incident.</div>
</div>

<div id="dashboard" class="hidden">

<div class="grid">

<section class="card full">
  <h2>Agentic Vision Pipeline</h2>

  <div class="step">
    <div class="badge">1</div>
    <div>
      <div class="label">SEE</div>
      <div class="value">OpenCV 5 Visual Analysis</div>
    </div>
  </div>

  <div class="step">
    <div class="badge">2</div>
    <div>
      <div class="label">INVESTIGATE</div>
      <div class="value">Docker + HTTP + Prometheus + Logs</div>
    </div>
  </div>

  <div class="step">
    <div class="badge">3</div>
    <div>
      <div class="label">DECIDE</div>
      <div class="value">Agent Diagnosis & Action</div>
    </div>
  </div>

  <div class="step">
    <div class="badge">4</div>
    <div>
      <div class="label">HUMAN APPROVAL</div>
      <div class="value">Controlled Remediation</div>
    </div>
  </div>

  <div class="step">
    <div class="badge">5</div>
    <div>
      <div class="label">VERIFY</div>
      <div class="value">Independent Recovery Verification</div>
    </div>
  </div>
</section>

<section class="card">
  <h2>SEE — OpenCV 5</h2>
  <div class="metrics">
    <div class="metric">
      <div class="label">OpenCV</div>
      <div id="opencv" class="value info">—</div>
    </div>
    <div class="metric">
      <div class="label">Visual State</div>
      <div id="visualState" class="value">—</div>
    </div>
    <div class="metric">
      <div class="label">Confidence</div>
      <div id="confidence" class="value">—</div>
    </div>
  </div>
</section>

<section class="card">
  <h2>DECIDE — Agent</h2>
  <div class="evidence">
    <div class="evidence-row">
      <span>Incident</span>
      <strong id="incidentType">—</strong>
    </div>
    <div class="evidence-row">
      <span>Severity</span>
      <strong id="severity">—</strong>
    </div>
    <div class="evidence-row">
      <span>Probable Cause</span>
      <strong id="cause">—</strong>
    </div>
    <div class="evidence-row">
      <span>Recommended Action</span>
      <strong id="action">—</strong>
    </div>
  </div>
</section>

<section class="card full">
  <h2>INVESTIGATE — Evidence</h2>
  <div class="metrics">
    <div class="metric">
      <div class="label">Docker</div>
      <div id="docker" class="value">—</div>
    </div>
    <div class="metric">
      <div class="label">HTTP</div>
      <div id="http" class="value">—</div>
    </div>
    <div class="metric">
      <div class="label">Prometheus</div>
      <div id="prometheus" class="value">—</div>
    </div>
  </div>
</section>

<section id="approvalCard" class="card full hidden">
  <h2>HUMAN APPROVAL REQUIRED</h2>
  <p>
    VisionNOC has identified a remediation action.
    No infrastructure-changing action will occur without approval.
  </p>
  <div class="actions">
    <button class="approve" onclick="approve()">Approve Remediation</button>
    <button class="reject" onclick="reject()">Reject</button>
  </div>
</section>

<section class="card full">
  <h2>ACT — Remediation</h2>
  <div id="remediation" class="evidence">
    <div class="evidence-row">
      <span>Status</span>
      <strong>Not executed</strong>
    </div>
  </div>
</section>

<section class="card full">
  <h2>VERIFY — Recovery</h2>
  <div id="verification" class="evidence">
    <div class="evidence-row">
      <span>Verification</span>
      <strong>Waiting</strong>
    </div>
  </div>
</section>

<section class="card full">
  <h2>Incident Timeline</h2>
  <div id="timeline" class="timeline"></div>
</section>

<section class="card full">
  <details>
    <summary>Technical JSON / Audit Evidence</summary>
    <pre id="raw"></pre>
  </details>
</section>

</div>
</div>

<script>
let id = null;

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: {"Content-Type":"application/json"},
    ...options
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || ("HTTP " + response.status));
  }

  return data;
}

function setStatus(text, type) {
  const el = document.getElementById("status");
  el.className = "status " + (type || "");
  el.innerHTML = "<strong>" + text + "</strong>";
}

function stateClass(state) {
  if (state === "healthy" || state === "running" || state === "recovered") return "good";
  if (state === "down" || state === "exited" || state === "unhealthy") return "bad";
  if (state === "warning" || state === "awaiting_approval") return "warn";
  return "info";
}

function addTimeline(title, detail) {
  const item = document.createElement("div");
  item.className = "timeline-item";
  item.innerHTML =
    "<strong>" + title + "</strong>" +
    "<div class='small'>" + detail + "</div>";
  document.getElementById("timeline").appendChild(item);
}

function render(j) {
  id = j.incident_id;

  document.getElementById("dashboard").classList.remove("hidden");

  const v = j.vision_result || {};
  const d = j.decision || {};

  document.getElementById("opencv").textContent =
    v.opencv_version || "—";

  const visual = document.getElementById("visualState");
  visual.textContent = (v.overall_state || "—").toUpperCase();
  visual.className = "value " + stateClass(v.overall_state);

  document.getElementById("confidence").textContent =
    v.overall_confidence != null
      ? (v.overall_confidence * 100).toFixed(2) + "%"
      : "—";

  document.getElementById("incidentType").textContent =
    d.incident || "none";

  document.getElementById("severity").textContent =
    d.severity || "—";

  document.getElementById("cause").textContent =
    d.probable_cause || "—";

  document.getElementById("action").textContent =
    d.recommended_action || "none";

  const calls = j.tool_calls || [];

  const dockerCall = calls.find(x => x.tool === "check_docker_container");
  const httpCall = calls.find(x => x.tool === "check_http_health");
  const promCall = calls.find(x => x.tool === "get_prometheus_metrics");

  document.getElementById("docker").textContent =
    dockerCall?.output?.status || "—";

  document.getElementById("docker").className =
    "value " + stateClass(dockerCall?.output?.status);

  document.getElementById("http").textContent =
    httpCall?.output?.healthy === true
      ? "HEALTHY"
      : httpCall?.output?.healthy === false
      ? "UNHEALTHY"
      : "—";

  document.getElementById("http").className =
    "value " +
    (httpCall?.output?.healthy === true ? "good" : "bad");

  let promUp = null;

  if (promCall?.output?.result?.length) {
    const value = promCall.output.result[0].value;
    promUp = Array.isArray(value)
      ? String(value[1]) === "1"
      : String(value) === "1";
  }

  document.getElementById("prometheus").textContent =
    promUp === true ? "UP" : promUp === false ? "DOWN" : "—";

  document.getElementById("prometheus").className =
    "value " + (promUp === true ? "good" : "bad");

  const approvalCard = document.getElementById("approvalCard");

  if (j.status === "awaiting_approval") {
    approvalCard.classList.remove("hidden");
    setStatus("⚠ HUMAN APPROVAL REQUIRED", "waiting");
  } else if (j.status === "resolved") {
    approvalCard.classList.add("hidden");

    if (j.verification_result?.overall_recovered) {
      setStatus("🟢 INCIDENT RESOLVED — SYSTEM RECOVERED", "resolved");
    } else {
      setStatus("🟢 SYSTEM HEALTHY", "healthy");
    }
  } else if (j.status === "verifying") {
    approvalCard.classList.add("hidden");
    setStatus("🔵 VERIFYING RECOVERY", "");
  } else {
    approvalCard.classList.add("hidden");
    setStatus(j.status || "Processing", "");
  }

  const rem = j.remediation_result;

  if (rem) {
    document.getElementById("remediation").innerHTML =
      "<div class='evidence-row'><span>Backend</span><strong class='" +
      (rem.success ? "good" : "bad") +
      "'>" + (rem.backend || "—") + "</strong></div>" +
      "<div class='evidence-row'><span>Result</span><strong class='" +
      (rem.success ? "good" : "bad") +
      "'>" + (rem.success ? "SUCCESS" : "FAILED") + "</strong></div>";
  }

  const ver = j.verification_result;

  if (ver) {
    document.getElementById("verification").innerHTML =
      "<div class='evidence-row'><span>Docker</span><strong class='" +
      (ver.signals.docker ? "good" : "bad") + "'>" +
      (ver.signals.docker ? "RECOVERED" : "FAILED") +
      "</strong></div>" +

      "<div class='evidence-row'><span>HTTP</span><strong class='" +
      (ver.signals.http ? "good" : "bad") + "'>" +
      (ver.signals.http ? "HEALTHY" : "UNHEALTHY") +
      "</strong></div>" +

      "<div class='evidence-row'><span>Prometheus</span><strong class='" +
      (ver.signals.prometheus ? "good" : "bad") + "'>" +
      (ver.signals.prometheus ? "UP" : "DOWN") +
      "</strong></div>" +

      "<div class='evidence-row'><span>Visual</span><strong class='" +
      (ver.signals.visual ? "good" : "bad") + "'>" +
      (ver.signals.visual ? "RECOVERED" : "FAILED") +
      "</strong></div>" +

      "<div class='evidence-row'><span>Overall</span><strong class='" +
      (ver.overall_recovered ? "good" : "bad") + "'>" +
      (ver.overall_recovered ? "RECOVERED" : "NOT RECOVERED") +
      "</strong></div>";
  }

  document.getElementById("raw").textContent =
    JSON.stringify(j, null, 2);

  document.getElementById("timeline").innerHTML = "";

  addTimeline(
    "SEE",
    "OpenCV " + (v.opencv_version || "—") +
    " detected " + (v.overall_state || "unknown") +
    " with " +
    (v.overall_confidence != null
      ? (v.overall_confidence * 100).toFixed(2) + "%"
      : "—") +
    " confidence."
  );

  addTimeline(
    "INVESTIGATE",
    "Agent queried Docker, HTTP health, Prometheus and container logs."
  );

  addTimeline(
    "DECIDE",
    (d.incident || "No incident") +
    " → " +
    (d.recommended_action || "no action") +
    (d.requires_approval ? " → human approval required." : ".")
  );

  if (rem) {
    addTimeline(
      "ACT",
      rem.backend + " remediation → " +
      (rem.success ? "success" : "failed") + "."
    );
  }

  if (ver) {
    addTimeline(
      "VERIFY",
      ver.overall_recovered
        ? "All required recovery signals confirmed."
        : "Recovery verification did not pass."
    );
  }
}

async function trigger() {
  try {
    setStatus("🔵 Capturing dashboard and investigating...", "");
    document.getElementById("dashboard").classList.remove("hidden");

    const result = await api("/api/demo/trigger", {
      method: "POST",
      body: JSON.stringify({scenario:"backend_down"})
    });

    render(result);
  } catch (e) {
    setStatus("🔴 Error: " + e.message, "incident");
  }
}

async function approve() {
  try {
    setStatus("🟠 Executing approved remediation...", "waiting");

    const result = await api(
      "/api/incidents/" + id + "/approve",
      {
        method:"POST",
        body:JSON.stringify({
          approved_by:"web-operator"
        })
      }
    );

    render(result.incident);

    setTimeout(verify, 1000);
  } catch (e) {
    setStatus("🔴 Remediation error: " + e.message, "incident");
  }
}

async function reject() {
  try {
    const result = await api(
      "/api/incidents/" + id + "/reject",
      {
        method:"POST",
        body:JSON.stringify({
          rejected_by:"web-operator"
        })
      }
    );

    render(result.incident);
  } catch (e) {
    setStatus("🔴 Error: " + e.message, "incident");
  }
}

async function verify() {
  try {
    const result = await api(
      "/api/incidents/" + id + "/verify",
      {
        method:"POST",
        body:"{}"
      }
    );

    render(result.incident);
  } catch (e) {
    setStatus("🔴 Verification error: " + e.message, "incident");
  }
}
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    server_version = "VisionNOC/0.1"

    def log_message(self, fmt, *args):  # quieter default logging
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/ui"):
            return _text_response(self, 200, UI, "text/html; charset=utf-8")
        if path == "/health":
            return _json_response(self, 200, {"status":"ok", "opencv_version":cv2.__version__})
        if path == "/metrics":
            lines = [
                "# HELP visionnoc_incidents_total Total persisted incidents.",
                "# TYPE visionnoc_incidents_total gauge",
                f"visionnoc_incidents_total {len(STORE.list(limit=100000))}",
                "# HELP visionnoc_up VisionNOC API availability.",
                "# TYPE visionnoc_up gauge",
                "visionnoc_up 1",
            ]
            return _text_response(self, 200, "\n".join(lines) + "\n", "text/plain; version=0.0.4; charset=utf-8")
        if not _auth_required(self): return
        try:
            if path == "/health":
                return _json_response(self, 200, {"status": "ok"})
            if path == "/api/status":
                return _json_response(self, 200, {
                    "status": "ok",
                    "opencv_version": __import__("cv2").__version__,
                    "docker_available": tools.DOCKER_CLIENT.ping(),
                    "incident_count": len(STORE.list(limit=10_000)),
                })
            if path == "/api/incidents":
                return _json_response(self, 200, {"incidents": STORE.list(limit=50)})
            m = ID_ROUTE.match(path)
            if m and not m.group("sub"):
                incident = STORE.get(m.group("id"))
                if incident is None:
                    return _json_response(self, 404, {"error": "not found"})
                return _json_response(self, 200, incident)
            return _json_response(self, 404, {"error": "no such route", "path": path})
        except Exception as exc:  # noqa: BLE001
            return _json_response(self, 500, {"error": str(exc)})

    def do_POST(self):
        path = urlparse(self.path).path
        body, body_error = _read_body(self)
        if body_error: return _json_response(self, 400, {"error": body_error})
        if not _auth_required(self): return
        try:
            if path == "/api/vision/analyze":
                image_path = body.get("image_path")
                if not image_path:
                    return _json_response(self, 400, {"error": "image_path is required"})
                result = analyze_dashboard(_safe_image_path(image_path))
                return _json_response(self, 200, result.to_dict())

            if path == "/api/demo/trigger":
                scenario = body.get("scenario", "backend_down")
                if scenario == "backend_down":
                    tools.stop_backend()
                    img = tools.capture_dashboard()["image_path"]
                elif scenario == "healthy":
                    tools.restart_backend()
                    img = tools.capture_dashboard()["image_path"]
                else:
                    return _json_response(self, 400, {"error": f"unknown scenario {scenario!r}"})

                vision = agent_ops.see_and_understand(img)
                incident = Incident.new(vision)
                evidence = agent_ops.investigate(incident)
                agent_ops.decide(incident, evidence)
                _persist(incident)
                return _json_response(self, 201, incident.to_dict())

            m = ID_ROUTE.match(path)
            if m and m.group("sub"):
                incident_id, sub = m.group("id"), m.group("sub")
                incident = _load_incident(incident_id)
                if incident is None:
                    return _json_response(self, 404, {"error": "incident not found"})
                if sub == "/approve":
                    agent_ops.approve(incident, approved_by=body.get("approved_by", "operator"))
                    result = agent_ops.act(incident)
                    _persist(incident)
                    return _json_response(self, 200, {"remediation_result": result, "incident": incident.to_dict()})
                if sub == "/reject":
                    agent_ops.reject(incident, rejected_by=body.get("rejected_by", "operator"))
                    _persist(incident)
                    return _json_response(self, 200, incident.to_dict())
                if sub == "/verify":
                    after_image = _safe_image_path(body["after_image"]) if body.get("after_image") else tools.capture_dashboard()["image_path"]
                    before_image = _safe_image_path(body["before_image"]) if body.get("before_image") else incident.vision_result.get("image_path")
                    result = agent_ops.verify(incident, before_image=before_image, after_image=after_image)
                    _persist(incident)
                    return _json_response(self, 200, {"verification_result": result, "incident": incident.to_dict()})

            return _json_response(self, 404, {"error": "no such route", "path": path})
        except ValueError as exc:
            return _json_response(self, 409, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            return _json_response(self, 500, {"error": str(exc)})


def run(host: str = "127.0.0.1", port: int = 8000):
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"VisionNOC API listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    import os
    run(
        host=os.environ.get("VISIONNOC_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("VISIONNOC_API_PORT", "8000")),
    )
