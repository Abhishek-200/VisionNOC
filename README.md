# VisionNOC

**See the incident. Investigate the cause. Take action. Verify recovery.**

Built for the [OpenCV AI Competition 2026, powered by AWS](https://opencv26.devpost.com/) — Agentic Vision path.

> **Honesty note up front:** this repo was built in a sandboxed
> environment with no Docker, no AWS access, and no outbound network
> (so no `pip install fastapi`, no OpenCV 5 upgrade, no live LLM calls).
> Everything under "What actually works" below was run and verified in
> that sandbox. Everything else is written and ready to go but genuinely
> untested — see **[docs/WHAT_I_ACTUALLY_BUILT.md](docs/WHAT_I_ACTUALLY_BUILT.md)**
> for the full, unvarnished accounting, and
> **[docs/COMPETITION_REQUIREMENTS.md](docs/COMPETITION_REQUIREMENTS.md)**
> for exactly where this stands against the competition's real rules
> (fetched live from Devpost, not guessed).

## 1. Overview

VisionNOC watches a monitoring dashboard, uses real OpenCV to detect
when something's visually wrong, investigates using real (or simulated)
infrastructure tools, proposes a fix, waits for human approval, and then
independently verifies recovery. It's built around one idea: the
competition's Agentic Vision path requires that *"the visual evidence
must change what the system does next"* — not just be narrated by a
chatbot — and this repo makes that a structural property of the code,
not a suggestion.

## 2. Problem

On-call engineers manually correlate a red dashboard panel with
container state, logs, and metrics before deciding what to restart.
That correlation step is exactly what VisionNOC automates — while
keeping a human in the loop for anything destructive.

## 3. Solution

A strict pipeline: **SEE → UNDERSTAND → INVESTIGATE → DECIDE → APPROVE
→ ACT → VERIFY**. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for
the full diagram and [docs/AGENT_DESIGN.md](docs/AGENT_DESIGN.md) for
exactly how each safety property (no arbitrary shell access,
structurally-required approval, validated decisions, full audit trail)
is enforced in code, not just described in prose.

## 4. Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 5. How OpenCV is used

Real HSV color-range thresholding + Otsu-threshold contour detection per
dashboard region, plus frame-differencing for recovery verification.
Full pipeline walkthrough: [docs/OPENCV.md](docs/OPENCV.md).
**Repository pin: OpenCV 5.0.0.93. The audit sandbox still imports 4.13.0.92 because it has no package-network access; OpenCV 5 must be verified on a networked machine before submission.**
(genuinely released June 2026; this sandbox had no network to upgrade).
See docs/COMPETITION_REQUIREMENTS.md.

## 6. How agentic behavior works

See [docs/AGENT_DESIGN.md](docs/AGENT_DESIGN.md). In short: OpenCV's
output determines whether any other tool is even reachable, and a
low-confidence or conflicting read explicitly blocks remediation instead
of guessing.

## 7. AWS integration

Planned, documented, **not deployed** — see
[docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md).

## 8. Installation

```bash
git clone <this-repo> visionnoc
cd visionnoc
python3 -m pip install -r requirements.txt   # opencv-python/numpy/pillow are the only ones actually required to run
cp .env.example .env
```

## 9. Local setup

No database setup needed — `store/db.py` creates `data/visionnoc.db`
(SQLite) automatically on first use. No Docker required for the
verified demo paths below.

## 10. Running the demo

```bash
./scripts/simulate_incident.sh --auto
```

See [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) for this and two other
verified ways to run it (interactive CLI, live HTTP API), plus the
Docker Compose path (**not yet verified**, no Docker in the build
sandbox).

## 11. Triggering an incident

The demo does this for you (`tools.CLUSTER.stop("visionnoc-backend")`),
or via the API: `POST /api/demo/trigger {"scenario": "backend_down"}`.

## 12. Approving remediation

CLI: interactive `y/N` prompt. API: `POST /api/incidents/{id}/approve`.
Both were run and verified — see docs/TESTING.md.

## 13. Verification

`POST /api/incidents/{id}/verify` (or automatic, in the CLI's `--auto`
mode) checks Docker + HTTP + Prometheus + a fresh OpenCV read, and never
reports a signal it couldn't actually check.

## 14. Screenshots

Generated synthetic dashboards live in `docs/evidence/` (healthy,
incident, recovered). Real Grafana screenshots are not included — no
Grafana instance was running in this sandbox. See
`docs/evidence/` and docs/OPENCV.md.

## 15. API

Full route table and request/response shapes: see the docstring at the
top of `api/server.py`, or run the server and hit `GET /api/status`.
Nine endpoints, all verified over real HTTP (docs/TESTING.md).

## 16. Testing

```bash
python3 -m unittest discover -s tests -v
```
47/47 passing in the audit sandbox (with its existing OpenCV 4.13 runtime). Full breakdown: [docs/TESTING.md](docs/TESTING.md).

## 17. Security

[docs/SECURITY.md](docs/SECURITY.md) — control-by-control breakdown of
what's actually enforced (no arbitrary shell execution, structural
approval gate, validated decisions, audit logging) and what's known-gap
(no API auth, no TLS at the stdlib server, `docker.sock` mount is a
documented sharp edge).

## 18. Limitations

Synthetic dashboard only; OpenCV 4.x not 5.x; no AWS deployed; no API
auth; rule-based decision engine by default. Full list:
[docs/WHAT_I_ACTUALLY_BUILT.md](docs/WHAT_I_ACTUALLY_BUILT.md).

## 19. Future improvements

Point the vision ROIs at a real Grafana dashboard; upgrade to OpenCV 5;
deploy to AWS; add API auth + TLS; exercise the Ollama/hosted-API
decision providers live; add retry/backoff for failed remediations. See
docs/TECHNICAL_REPORT.md's Future Work section.

## 20. Competition requirements mapping

[docs/COMPETITION_REQUIREMENTS.md](docs/COMPETITION_REQUIREMENTS.md) —
row-by-row against the live Devpost rules page, with honest
IMPLEMENTED/NOT IMPLEMENTED/BLOCKED statuses.

---

## Project layout

```
visionnoc/
├── vision/        real OpenCV detection pipeline
├── agent/         orchestration, tools, policies, decision providers
├── store/         SQLite incident persistence
├── api/           stdlib HTTP JSON API
├── demo/          synthetic dashboard generator + narrated CLI demo
├── tests/         45 unittest tests (vision, agent, tools, flow, API)
├── docker/        Dockerfiles + Prometheus/Grafana config (unverified)
├── docs/          every document listed above
├── scripts/       shell wrapper for the demo
└── docker-compose.yml, requirements.txt, .env.example, Makefile, LICENSE
```

## Quick sanity check

```bash
make test        # 47/47 tests in the audit sandbox
make demo-auto    # full narrated incident lifecycle
make api          # start the HTTP API on :8000
```
