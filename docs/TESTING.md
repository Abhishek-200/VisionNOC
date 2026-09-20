# Testing

## How to run

```bash
cd visionnoc
python3 -m unittest discover -s tests -v
# or, if you `pip install pytest`:
pytest tests/ -v
```

## Actual last-run result (this exact command, in the authoring sandbox)

```
Ran 45 tests in 0.701s

OK
```

All 45 tests pass. Zero skipped, zero failed, zero errored. This is the
literal output of the command above, not a transcription of expected
behavior.

## Test files and what each actually covers

| File | Tests | What it verifies |
|---|---|---|
| `tests/test_vision.py` | 8 | Real OpenCV pipeline: healthy/down/warning classification per-panel, both-services-down, missing-file error handling, frame-diff change detection (nonzero for real change, exactly 0.0 for identical images), `opencv_version` always populated |
| `tests/test_agent.py` | 11 | `IncidentDecision` construction/validation (rejects out-of-range confidence, non-allowlisted actions, empty evidence); heuristic provider's four branches (healthy/down+stopped/conflicting/unknown); policy functions |
| `tests/test_tools.py` | 9 | Allowlist shape (exactly 2 remediation actions, no overlap with read-only tools); `SimulatedCluster` state transitions are real (stop/restart actually mutate state); Prometheus metrics reflect real container state; `verify_incident` never fabricates a missing signal (returns `None`, not `True`/`False`, when no before/after image given) |
| `tests/test_incident_flow.py` | 7 | Full SEE→VERIFY cycle end to end; approval gate genuinely blocks `act()` before approval; rejection genuinely prevents remediation; incident IDs are unique; every tool call is recorded |
| `tests/test_api.py` | 9 | Real HTTP requests against a real `ThreadingHTTPServer` instance (not mocked) — health check, 404s, 409 conflict on double-approve, full lifecycle via HTTP, vision-analyze endpoint |

## What is deliberately tested as a FAILURE path (spec section 14)

- `test_act_before_approval_raises` — remediation attempted without
  approval must raise, not silently proceed
- `test_reject_prevents_remediation` — a rejected incident cannot later
  be acted on
- `test_conflicting_evidence_does_not_recommend_action` — OpenCV says
  DOWN, Docker says RUNNING → agent must not auto-remediate
- `test_unknown_visual_state_does_not_act` — low-confidence vision read
  → no action
- `test_verify_incident_never_fabricates_missing_signal` — a signal the
  system genuinely couldn't check must come back as `None`, never a
  guessed boolean
- `test_missing_file_raises` — a bad image path is a hard error, not a
  silently-empty result
- `test_approve_twice_returns_conflict` — the state machine rejects an
  invalid transition via a proper HTTP 409, not a crash or silent no-op

## What is NOT tested / measured (spec section 33 — do not fabricate numbers)

- **Detection accuracy on real Grafana screenshots** — NOT YET MEASURED.
  All vision tests run against the synthetic generator
  (`demo/generate_dashboard.py`); there is no labeled dataset of real
  dashboard screenshots in this repo.
- **False positive / false negative rates** — NOT YET MEASURED (would
  require a labeled dataset per above).
- **Latency under load / concurrency** — NOT YET MEASURED. `api/server.py`
  uses `ThreadingHTTPServer` so concurrent requests are handled, but no
  load test has been run.
- **Real Docker / Prometheus / Grafana integration** — NOT TESTED. Every
  test above exercises the `SimulatedCluster` backend in
  `agent/tools.py` (documented explicitly in every simulated tool's
  return value via `"backend": "simulated"`), because this sandbox has
  no Docker daemon. `agent/tools.py`'s real-Docker code path
  (`_run_docker`, used automatically when `shutil.which("docker")`
  finds a binary) has not been exercised.
- **Ollama / hosted-API decision providers** — NOT TESTED against a live
  server (see docs/AGENT_DESIGN.md). Only the automatic fallback-to-heuristic
  path is implicitly exercised (since `AI_PROVIDER` defaults to
  `heuristic` and was never set to `ollama`/`api` in any test run).

## CI

`.github/workflows/ci.yml` runs the same `unittest discover` command on
every push. **NOT VERIFIED** — this sandbox cannot reach github.com, so
the workflow has never actually executed on GitHub's infrastructure.
BLOCKED — USER ACTION REQUIRED: push to a GitHub repo and confirm the
Actions run goes green.
