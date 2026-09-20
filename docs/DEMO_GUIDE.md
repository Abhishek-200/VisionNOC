# Demo Guide

This exact sequence was run in the authoring sandbox and produces the
transcript referenced in docs/WHAT_I_ACTUALLY_BUILT.md. It is fully
repeatable — every step below is a real command, not pseudocode.

## Prerequisites

```bash
cd visionnoc
python3 -m pip install -r requirements.txt   # or just ensure opencv-python/numpy/pillow are installed
```

## Option A — one-shot narrated CLI demo (recommended for a live judge demo)

```bash
./scripts/simulate_incident.sh --auto
```

This runs, in order, with full narration to stdout:

1. **HEALTHY STATE** — capture a baseline dashboard screenshot
2. **TRIGGER INCIDENT** — stop the simulated `visionnoc-backend` container
3. **SEE** — capture the incident dashboard (a real PNG with real pixels)
4. **UNDERSTAND** — OpenCV analyzes it (`vision/detector.py`), prints the
   structured `VisionResult` JSON
5. **INVESTIGATE** — read-only tool calls (Docker, HTTP, Prometheus, logs),
   each printed as it happens
6. **DECIDE** — the heuristic decision engine prints its structured,
   validated `IncidentDecision`
7. **HUMAN APPROVAL REQUIRED** — with `--auto`, auto-approves; without
   it, prompts `Approve remediation? [y/N]:` interactively
8. **ACT** — runs the allowlisted `restart_backend` tool, prints its result
9. **VERIFY** — independent multi-signal check (Docker + HTTP +
   Prometheus + visual), prints the result
10. **FINAL STATUS** — prints `RESOLVED` and the full 6-call tool audit trail

Run it without `--auto` to see the interactive approval prompt instead.

## Option B — drive it through the live HTTP API

```bash
# Terminal 1
python3 -m api.server

# Terminal 2
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/demo/trigger -H "Content-Type: application/json" -d '{"scenario":"backend_down"}'
# copy the "incident_id" from the response, e.g. INC-XXXXXXXX
curl -X POST http://127.0.0.1:8000/api/incidents/INC-XXXXXXXX/approve
curl -X POST http://127.0.0.1:8000/api/incidents/INC-XXXXXXXX/verify
curl http://127.0.0.1:8000/api/incidents/INC-XXXXXXXX
```

This exact sequence was run against a live server in this sandbox — see
docs/TESTING.md and docs/WHAT_I_ACTUALLY_BUILT.md for the captured
output.

## Option C — Docker Compose with a real Grafana dashboard (NOT VERIFIED)

```bash
docker compose up --build
# Grafana: http://localhost:3000 (admin / visionnoc)
# Prometheus: http://localhost:9090
# VisionNOC API: http://localhost:8000

# trigger the failure
docker stop visionnoc-demo-app
# recover it
docker start visionnoc-demo-app
```

**BLOCKED — USER ACTION REQUIRED**: this sandbox has no Docker daemon, so
Option C has never actually been run. Options A and B are the verified
paths.

## What "repeatable" means here

Each run of `./scripts/simulate_incident.sh --auto` creates a brand-new
`SimulatedCluster` state only if you also restart the Python process —
within one process, `agent/tools.CLUSTER` is a module-level singleton, so
running the demo twice in a row in the same process/import will restart
an already-running container (harmless, `restart_count` just increments).
For a clean re-run, start a fresh `python3` process (the CLI script does
this naturally, since it's a new process each time).
