# Agent Design

## Principles (spec section 8-11, actually enforced in code)

1. **No arbitrary shell access for the model.** `agent/tools.py` exposes
   a fixed Python dict (`TOOLS` for read-only, `ALLOWED_ACTIONS` for
   remediation). The decision layer (`agent/providers.py`) only ever
   produces a `recommended_action` string, which
   `agent/models.py::IncidentDecision.__post_init__` validates against
   `VALID_ACTIONS = {"restart_backend", "restart_database", "none"}` —
   construction raises `ValueError` on anything else, so an
   unvalidated/malicious action string can never reach `agent/agent.py::act()`.
   Verified by `tests/test_agent.py::test_invalid_action_rejected`.

2. **Approval is structurally required, not just checked.**
   `agent/agent.py::act()` raises `ValueError` unless
   `incident.status == "remediating"`, which is only ever set by
   `approve()`. There is no function that goes straight from `decide()`
   to `act()`. Verified by
   `tests/test_incident_flow.py::test_act_before_approval_raises`.

3. **Decisions are structurally validated, never trusted raw.**
   Every provider in `agent/providers.py` (heuristic, ollama, api)
   returns a plain dict; `agent/agent.py::decide()` immediately wraps it
   in `IncidentDecision(**raw)`, which validates confidence range,
   severity enum, non-empty evidence, and the action allowlist before
   anything downstream can use it.

4. **Every tool call is logged for audit (spec section 15).**
   `agent/agent.py::_record_tool_call()` appends a `ToolCallRecord` to
   `incident.tool_calls` on every single tool invocation — investigation,
   remediation, and verification alike. Verified by
   `tests/test_incident_flow.py::test_audit_trail_records_every_tool_call`.

## Decision engine

Default: `agent/providers.py::decide_heuristic()` — a deterministic rule
engine, not an LLM call, because this sandbox has no network to reach
Ollama or a hosted API (see docs/PROJECT_STATUS.md). It is genuinely
rule-based and auditable:

- healthy vision + not-explicitly-unhealthy HTTP → `recommended_action: none`
- `unknown` vision state (low OpenCV confidence) → `none` (spec section
  14: "visual uncertainty... do not automatically remediate")
- vision says `down` but Docker says `running` (or vice versa) → `none`,
  `incident: conflicting_evidence` (spec section 14's exact example)
- vision says `down`/`warning` AND Docker corroborates `stopped` →
  `restart_backend`, `requires_approval: true`

`agent/providers.py::decide_ollama()` and `::decide_api()` are fully
implemented against the real Ollama HTTP API and Anthropic Messages API
respectively, but **BLOCKED — USER ACTION REQUIRED**: neither has been
exercised against a live server in this sandbox (no network, no local
Ollama binary). Both fall back to the heuristic engine automatically on
`ProviderUnavailable` so a misconfigured `.env` never silently disables
the agent — but that fallback path itself is the only path actually
tested here.

## Why this counts as "agentic" for the competition's Agentic Vision path

The competition's own language: *"the visual evidence must change what
the system does next"* and *"culminates in a running image or video
workload."* Concretely, in this codebase:

- `overall_state == "down"` vs `"healthy"` from `vision/detector.py`
  determines whether `agent/agent.py::investigate()` even matters —
  a healthy read short-circuits to `recommended_action: none` before
  any remediation tool is reachable.
- The **confidence value** from OpenCV (not just a boolean) feeds
  `agent/policies.py::is_confident_enough_to_propose_action` and the
  `unknown`-state branch in `decide_heuristic`, so a low-confidence
  visual read changes the decision even when other signals look bad.
- Verification (`agent/tools.py::verify_incident`) re-runs the vision
  pipeline on an *after* screenshot and folds that into the multi-signal
  recovery check — so vision output gates both the start and the end of
  the loop, not just a middle narration step.
