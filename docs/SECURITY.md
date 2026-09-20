# Security

## What's actually enforced in code (not just policy prose)

| Control | Where | How it's enforced | Verified by |
|---|---|---|---|
| No arbitrary shell execution from the model/agent | `agent/tools.py` | Only two functions (`restart_backend`, `restart_database`) exist in `ALLOWED_ACTIONS`; `agent/agent.py::act()` looks the action name up in that dict — there is no `eval`, `exec`, `os.system`, or `subprocess.run(shell=True)` anywhere in the codebase | `tests/test_tools.py::TestToolAllowlist`, manual code review (`grep -rn "shell=True\|eval(\|exec(" .` returns nothing) |
| Destructive actions require human approval | `agent/agent.py::act()` | Raises `ValueError` unless `incident.status == "remediating"`, which only `approve()` sets | `tests/test_incident_flow.py::test_act_before_approval_raises`, `::test_reject_prevents_remediation` |
| Decisions are structurally validated before use | `agent/models.py::IncidentDecision.__post_init__` | Validates confidence range, severity enum, non-empty evidence, and `recommended_action` against `VALID_ACTIONS` | `tests/test_agent.py::TestStructuredDecision` (4 tests, including an explicit `"rm -rf /"` rejection test) |
| Docker subprocess calls use a fixed argument list, never a shell string | `agent/tools.py::_run_docker` | `subprocess.run([DOCKER_BIN] + args, ...)` — `args` is always built from this file's own constants, never from model/user input; no `shell=True` | Code review |
| No secrets committed | `.gitignore` | `.env` is gitignored; `.env.example` has empty values for `ANTHROPIC_API_KEY` etc. | `git status` after `cp .env.example .env` shows `.env` untracked |
| API keys read from environment only | `agent/providers.py::decide_api` | `os.environ.get("ANTHROPIC_API_KEY")`, never a hardcoded string | Code review |
| Audit logging | `agent/agent.py::_record_tool_call` | Every tool call (investigation, remediation, verification) appended to `incident.tool_calls`, persisted to SQLite | `tests/test_incident_flow.py::test_audit_trail_records_every_tool_call` |
| Input validation on the API | `api/server.py` | `/api/vision/analyze` returns 400 if `image_path` missing; unknown routes return 404; state-machine violations (e.g. double-approve) return 409, not a crash | `tests/test_api.py` (9 tests) |
| Timeouts on external calls | `agent/tools.py` | `_run_docker` (5s), `check_http_health` (2s default) | Code review |

## What is NOT implemented / reviewed

- **No authentication/authorization on the API.** `api/server.py` has no
  auth layer — anyone who can reach the port can trigger demo incidents
  and approve/reject remediations. Acceptable for a local hackathon demo,
  **NOT acceptable for a real production deployment.** BLOCKED — USER
  ACTION REQUIRED before any real-world use: add at minimum an API key
  header check, ideally proper auth (e.g. AWS Cognito / IAM if deployed
  behind API Gateway).
- **No rate limiting.**
- **No TLS** — `api/server.py` serves plain HTTP. Behind an ALB/API
  Gateway in the AWS deployment (docs/AWS_DEPLOYMENT.md), TLS termination
  would happen at the load balancer, but that has not been set up.
- **No formal threat-modeling exercise was performed** — the table above
  is a review of what the code does, not an independent red-team
  assessment.
- **The `/var/run/docker.sock` mount in `docker-compose.yml`** (so the
  containerized API can call the real Docker CLI against the host) is a
  known-sensitive pattern — it effectively gives the API container
  root-equivalent access to the host's Docker daemon. This is documented
  here explicitly rather than hidden; for anything beyond a local demo,
  prefer a scoped Docker API proxy (e.g. `docker-socket-proxy`) instead
  of mounting the raw socket.

## Least privilege

`agent/tools.py`'s `ALLOWED_ACTIONS` allowlist is intentionally tiny —
two named container restarts, nothing else (no `restart_database` is
even reachable from the current heuristic decision engine, since
`decide_heuristic` never recommends it; it exists for future
extension and is exercised directly by `tests/test_tools.py`).
