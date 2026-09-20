# Architecture

## System diagram

```
                         ┌────────────────────────┐
                         │   Grafana Dashboard      │  (synthetic PNG in this
                         │   (or synthetic image)   │   sandbox; real Grafana
                         └───────────┬──────────────┘   once Docker/AWS are up)
                                     │ screenshot
                                     v
                         ┌────────────────────────┐
                         │  vision/detector.py      │  SEE + UNDERSTAND
                         │  (real OpenCV pipeline)  │
                         └───────────┬──────────────┘
                                     │ VisionResult (structured, validated)
                                     v
                         ┌────────────────────────┐
                         │  agent/agent.py          │  INVESTIGATE
                         │  investigate()           │──────┐
                         └───────────┬──────────────┘      │
                                     │ evidence dict        v
                                     │              ┌───────────────────┐
                                     │              │ agent/tools.py     │
                                     │              │ (allowlisted,      │
                                     │              │  read-only tools:  │
                                     │              │  docker/http/prom/ │
                                     │              │  logs)             │
                                     │              └───────────────────┘
                                     v
                         ┌────────────────────────┐
                         │  agent/providers.py      │  DECIDE
                         │  get_decision()           │  (heuristic default;
                         │  -> agent/models.py       │   pluggable ollama/api)
                         │     IncidentDecision      │
                         │     (validated dataclass) │
                         └───────────┬──────────────┘
                                     │ requires_approval?
                                     v
                         ┌────────────────────────┐
                         │  Human operator          │  APPROVE / REJECT
                         │  (API call or CLI prompt) │
                         └───────────┬──────────────┘
                                     │ approved
                                     v
                         ┌────────────────────────┐
                         │  agent/tools.py           │  ACT
                         │  ALLOWED_ACTIONS[...]     │  (restart_backend /
                         │  (real docker CLI if      │   restart_database
                         │   present, else simulated)│   — nothing else)
                         └───────────┬──────────────┘
                                     v
                         ┌────────────────────────┐
                         │  agent/tools.py           │  VERIFY
                         │  verify_incident()        │  (docker + http +
                         │  (independent, multi-     │   prometheus + visual
                         │   signal, no fabrication) │   — never fabricated)
                         └───────────┬──────────────┘
                                     v
                         ┌────────────────────────┐
                         │  store/db.py (SQLite)    │  audit trail
                         │  api/server.py (stdlib   │  (spec §15)
                         │  HTTP JSON API)           │
                         └────────────────────────┘
```

## Why each piece is shaped the way it is

- **vision/** never talks to `agent/` directly about actions — it only
  ever returns a validated `VisionResult`. This keeps "what did the
  pixels say" cleanly separated from "what should we do about it."
- **agent/tools.py** is the only place allowed to touch the outside
  world (Docker/HTTP/Prometheus), and its remediation actions
  (`ALLOWED_ACTIONS`) are a strict subset of its read-only tools
  (`TOOLS`) — there is no code path from a decision straight into a
  container restart without passing through `agent/policies.py`'s
  approval gate first (enforced in `agent/agent.py::act()`, which
  raises if `incident.status != "remediating"`).
- **agent/providers.py** isolates "how do we decide" behind one
  function (`get_decision`) so the heuristic engine that actually runs
  in this sandbox and a future Ollama/hosted-LLM engine are
  interchangeable — both must return the same shape, validated by
  `IncidentDecision`.
- **api/server.py** is stdlib-only (see docs/PROJECT_STATUS.md for why)
  and exposes the documented HTTP route table directly. FastAPI is optional, not required, so the
  additive, not a rewrite.

## AWS target architecture (planned, not yet deployed)

See `docs/AWS_DEPLOYMENT.md` for the full picture — summary:

```
   Internet
      │
      v
  ALB / API Gateway
      │
      v
  ECS Fargate (or EC2) — vision-api container (this repo's api/ + agent/ + vision/)
      │                                    │
      v                                    v
  S3 (dashboard screenshots,          CloudWatch Logs/Metrics
      incident evidence)              (audit trail)
```
