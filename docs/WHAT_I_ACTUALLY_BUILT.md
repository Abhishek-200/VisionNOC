# Deep Audit Update — 2026-09-19

## Audit result
The original archive was reviewed at source level and the following issues were fixed: SQLite lifecycle persistence, Docker/container naming, real Prometheus querying, Prometheus metric format, request validation, image-path traversal, optional bearer authentication, browser approval UI, provider fallback honesty, confidence-gated remediation, OpenCV 5 dependency pinning, CI OpenCV 5 verification, and related regression tests.

### Verification after fixes
- Python compileall: PASS
- Unit/integration suite: **47/47 PASS**
- OpenCV 5 runtime: **NOT VERIFIED here**; current sandbox imports 4.13.0.92 and has no package network access.
- Docker Compose: **NOT VERIFIED here**; Docker is not installed.
- AWS deployment: **NOT VERIFIED here**; AWS CLI is not installed.

### Current truth
- **Implemented + verified:** local logic, SQLite lifecycle persistence, simulated incident workflow, API workflow, security guards, regression tests.
- **Implemented + pending environment verification:** OpenCV 5 dependency, Docker/Prometheus/Grafana integration, CI on GitHub.
- **Not implemented/deployed:** AWS runtime deployment, public judge endpoint, final demo video.

# What I Actually Built

Status legend: **IMPLEMENTED + VERIFIED**, **IMPLEMENTED + NOT VERIFIED**,
**PLANNED**, **BLOCKED**, **NOT IMPLEMENTED**.

## Software

### Files created (all under `visionnoc/`)
- `vision/` — `config.py`, `preprocessing.py`, `models.py`, `detector.py`, `__init__.py`
- `agent/` — `models.py`, `tools.py`, `policies.py`, `providers.py`, `agent.py`, `__init__.py`
- `store/` — `db.py`, `__init__.py`
- `api/` — `server.py`, `__init__.py`
- `demo/` — `generate_dashboard.py`, `simulate_incident.py`
- `tests/` — `test_vision.py`, `test_agent.py`, `test_tools.py`, `test_incident_flow.py`, `test_api.py`, `__init__.py`
- `docker/` — `Dockerfile.api`, `Dockerfile.demo-app`, `demo_app.py`, `prometheus/prometheus.yml`, `grafana/provisioning/{datasources,dashboards}/*`
- `docker-compose.yml`, `.github/workflows/ci.yml`
- `docs/` — this file plus COMPETITION_REQUIREMENTS.md, ARCHITECTURE.md, AGENT_DESIGN.md, OPENCV.md, AWS_DEPLOYMENT.md, SECURITY.md, TESTING.md, DEMO_GUIDE.md, VIDEO_SCRIPT.md, TECHNICAL_REPORT.md, COST_CONTROL.md, PROJECT_STATUS.md
- `requirements.txt`, `.env.example`, `.gitignore`, `Makefile`, `LICENSE`, `README.md`
- `scripts/simulate_incident.sh`

### Services created
- None deployed. A local-only stdlib HTTP API (`api/server.py`) that
  was run and verified in this sandbox but is not publicly hosted.

### APIs created
- `GET /health`, `GET /api/status`, `GET /api/incidents`,
  `GET /api/incidents/{id}`, `POST /api/vision/analyze`,
  `POST /api/incidents/{id}/approve`, `POST /api/incidents/{id}/reject`,
  `POST /api/incidents/{id}/verify`, `POST /api/demo/trigger` — all
  **IMPLEMENTED + VERIFIED** (real HTTP requests against a real running
  server, `tests/test_api.py`, 9/9 passing).

### Features implemented
- Real OpenCV per-panel visual incident detection — **IMPLEMENTED + VERIFIED**
- Full agentic SEE→UNDERSTAND→INVESTIGATE→DECIDE→APPROVE→ACT→VERIFY loop — **IMPLEMENTED + VERIFIED**
- Structural approval gate (remediation impossible without prior approval) — **IMPLEMENTED + VERIFIED**
- Allowlisted tools, no arbitrary shell execution — **IMPLEMENTED + VERIFIED**
- Validated, structured decision objects (rejects bad actions/confidence/evidence) — **IMPLEMENTED + VERIFIED**
- SQLite incident persistence — **IMPLEMENTED + VERIFIED**
- Audit trail of every tool call — **IMPLEMENTED + VERIFIED**
- CLI demo with narration — **IMPLEMENTED + VERIFIED**
- Multi-signal, non-fabricating verification — **IMPLEMENTED + VERIFIED**
- Real-Docker code path (used automatically if `docker` binary present) — **IMPLEMENTED + NOT VERIFIED** (no Docker daemon here)
- Ollama decision provider — **IMPLEMENTED + NOT VERIFIED** (no local Ollama)
- Hosted-API decision provider — **IMPLEMENTED + NOT VERIFIED** (no network/key)
- Docker Compose full stack (Prometheus + Grafana + demo app + API) — **IMPLEMENTED + NOT VERIFIED** (no Docker daemon)
- GitHub Actions CI — **IMPLEMENTED + NOT VERIFIED** (no network to GitHub)
- AWS deployment — **PLANNED** (documented architecture + commands, nothing provisioned)
- Video — **PLANNED** (script written, not recorded)
- Real Grafana dashboard integration — **NOT IMPLEMENTED** (synthetic dashboard generator used instead, by design — see docs/OPENCV.md)
- API authentication — **NOT IMPLEMENTED**
- Devpost team registration/proposal submission — **NOT IMPLEMENTED** (organizational action, outside this repo)

## OpenCV

- **Exact version:** `4.13.0.92` (from `cv2.__version__`, verified live,
  never hardcoded in output)
- **Competition requires OpenCV 5** — confirmed via web search that
  OpenCV 5.0.0 was genuinely released June 6, 2026. This sandbox has no
  network to upgrade to it. **BLOCKED — USER ACTION REQUIRED**
- **Exact functions used:** `cv2.imread`, `cv2.GaussianBlur`,
  `cv2.cvtColor`, `cv2.inRange`, `cv2.countNonZero`, `cv2.threshold`
  (Otsu), `cv2.findContours`, `cv2.absdiff`, `cv2.rectangle`,
  `cv2.circle`, `cv2.putText`, `cv2.imwrite`
- **Visual pipeline:** documented in full in docs/OPENCV.md
- **Test results:** 8/8 vision tests passing (docs/TESTING.md)

## AI

- **Model/provider:** `AI_PROVIDER=heuristic` (default, deterministic
  rule engine) — this is what actually ran. `ollama` and `api`
  providers implemented but unverified.
- **Agent architecture:** documented in docs/AGENT_DESIGN.md
- **Tools:** 4 read-only investigation tools + 2 allowlisted remediation
  actions, see `agent/tools.py`
- **Decisions:** structured, validated `IncidentDecision` dataclass —
  see `agent/models.py`
- **Approval mechanism:** CLI interactive prompt (`demo/simulate_incident.py`)
  and HTTP `POST /api/incidents/{id}/approve` — both **IMPLEMENTED + VERIFIED**.
  A graphical web approval UI (spec section 11's ASCII mockup) was NOT
  built — only the API endpoint and CLI prompt.

## DevOps

- **Docker:** Dockerfiles + Compose written, **NOT VERIFIED** (no Docker daemon)
- **Prometheus:** config written, **NOT VERIFIED** (never run); its
  *simulated* equivalent (`agent/tools.py::get_prometheus_metrics`) was
  run and tested
- **Grafana:** provisioning config + one dashboard JSON written, **NOT VERIFIED**
- **CI/CD:** workflow written, **NOT VERIFIED** on GitHub's infrastructure
- **Monitoring:** the simulated Prometheus-equivalent and the SQLite
  audit trail are the only monitoring actually exercised

## AWS

**No AWS services were configured or verified.** `docs/AWS_DEPLOYMENT.md`
documents a planned ECS Fargate + S3 + CloudWatch architecture with
exact (untested) CLI commands. No AWS account, credentials, or CLI were
available in this sandbox.

## Testing

Only tests that actually ran are listed. Command: `python3 -m unittest
discover -s tests -v`. Result: **45 passed, 0 failed, 0 errored, 0
skipped**, 0.701s wall time. Breakdown: 8 vision, 11 agent/decision, 9
tool/allowlist, 7 incident-flow, 9 API. No load, concurrency, or
real-Docker/AWS integration tests were run.

## Problems encountered and their solutions

1. **No network for `pip install`** → built the API on stdlib
   `http.server` and structured models on stdlib `dataclasses` instead
   of FastAPI/pydantic, with the latter documented as a drop-in upgrade
   path in `requirements.txt`.
2. **First version of `vision/config.py`'s status-chip ROIs were too
   loose** (covered the whole panel, not just the status circle),
   causing per-chip reads to come back `unknown` even on an obviously
   red/green panel (only the wide `overall_banner` region read
   correctly). Fixed by tightening the ROI boxes to match the actual
   circle geometry in `demo/generate_dashboard.py`, re-verified by
   re-running the detector against both test images before moving on.
3. **Background HTTP server processes were being killed between
   separate shell tool calls** (each call appears to run in a fresh
   shell, and simple `nohup ... &` didn't survive). Fixed by using
   `setsid nohup ... < /dev/null &` and polling `/health` with retries
   before proceeding — after which the full HTTP lifecycle test ran
   successfully.
4. **`curl | python3 -c "...json.load..."` intermittently failed on
   embedded newline characters** in a multi-line log string inside the
   JSON payload, purely a shell-quoting artifact of piping through
   `curl` — not a bug in the API's JSON encoding. Switched the API test
   script to pure Python `urllib` requests, which resolved it cleanly.
5. **`tests/test_api.py`'s `_get()` helper didn't handle 404 responses**
   (urllib raises `HTTPError` instead of returning a response object for
   non-2xx statuses), causing two tests to fail with an unhandled
   exception rather than asserting the expected 404. Fixed by wrapping
   `_get()` in the same try/except pattern already used in `_post()`;
   re-ran the suite and confirmed 45/45 passing.

## Limitations (honest, not exhaustive elsewhere)

- Synthetic dashboard only — not validated against a real Grafana screenshot's actual pixel layout/fonts/anti-aliasing.
- OpenCV 4.x, not the required 5.x.
- No AWS component running.
- No authentication on the API.
- Decision engine is rule-based, not LLM-backed, by default.
- No load, concurrency, or chaos testing.
- No retry/backoff policy for repeated remediation failures.
- Docker/Prometheus/Grafana integration entirely unverified.

## User actions required (everything you still need to do manually)

1. Get network access + `pip install --upgrade opencv-python` (or build
   from source) to move to OpenCV 5.x; re-run `pytest`/`unittest`.
2. Install Docker + Docker Compose; run `docker compose up --build`;
   fix whatever breaks (genuinely untested).
3. Provision the AWS resources in `docs/AWS_DEPLOYMENT.md`; deploy
   `docker/Dockerfile.api`; get a public/judge-reachable URL.
4. Point `vision/config.py`'s `STATUS_CHIPS` at a real Grafana
   dashboard's actual layout once one is running (docker-compose brings
   one up, unverified).
5. Record the demo video per `docs/VIDEO_SCRIPT.md`.
6. Register the team and submit the required proposal on Devpost
   (https://opencv26.devpost.com/) — this repo does not do this for you.
7. If pursuing the Agentic Vision Award specifically, prepare the
   additional evidence the rules ask for: an agent workflow diagram
   (docs/ARCHITECTURE.md's ASCII diagram may need a rendered version),
   and a trace/demo showing OpenCV output changing a later
   decision/action (the demo in docs/DEMO_GUIDE.md's Option A/B already
   is that trace — capture it on video).
8. Decide whether to pursue the optional Best Use of COOL award (not
   attempted here) — would require AWS Graviton + the Cloud-Optimized
   OpenCV Library, both out of scope for this build.
9. Add API authentication before any deployment reachable outside a
   private network.
