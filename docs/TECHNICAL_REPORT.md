# VisionNOC — Technical Report

## Abstract

VisionNOC is an agentic visual incident-response system built for the
OpenCV AI Competition 2026's Agentic Vision path. It demonstrates a
closed loop in which computer-vision output from a monitoring dashboard
directly determines an agent's subsequent investigation, decision, and
(after human approval) remediation actions, followed by independent
multi-signal verification. This report describes what was built and
verified in the authoring environment, and states plainly what remains
for a network-connected environment with AWS access to complete.

## Problem

On-call engineers spend significant time correlating a dashboard's
visual state with underlying system signals (container status, health
endpoints, metrics, logs) before deciding on a remediation. VisionNOC
automates the perception-to-investigation step using real computer
vision on the dashboard image itself, while keeping a human in the loop
for any action with real-world consequences.

## Motivation

The competition's Agentic Vision path specifically requires that visual
evidence *change* a subsequent tool call, plan, or approval request —
not merely be narrated by a chatbot. VisionNOC's architecture makes this
a structural property rather than a suggestion: the vision layer's
output is the input that decides whether any other tool is even called
(see docs/AGENT_DESIGN.md).

## Architecture

See docs/ARCHITECTURE.md for the full diagram. Summary: a strict
pipeline of SEE (OpenCV) → UNDERSTAND (validated structured result) →
INVESTIGATE (allowlisted read-only tools) → DECIDE (pluggable decision
engine, validated output) → APPROVE (human gate, structurally enforced)
→ ACT (allowlisted remediation only) → VERIFY (independent, multi-signal,
never-fabricated).

## OpenCV implementation

See docs/OPENCV.md for the full pipeline walkthrough. In summary: HSV
color-range thresholding (`cv2.inRange`) plus Otsu-threshold contour
detection (`cv2.findContours`) per configured region of interest, with
worst-case aggregation across regions, plus `cv2.absdiff`-based
frame-differencing for before/after recovery verification. Installed
repository pin: OpenCV 5.0.0.93; the audit sandbox still imports OpenCV 4.13.0.92, so the required 5.x runtime remains pending final environment verification — the competition
requires OpenCV 5 (confirmed released June 6, 2026), which this sandbox
had no network access to install. See docs/COMPETITION_REQUIREMENTS.md
for the honest status of this gap.

## Agent architecture

See docs/AGENT_DESIGN.md. The decision engine defaults to a
deterministic, auditable rule set (`agent/providers.py::decide_heuristic`)
rather than an LLM call, because the authoring sandbox had no network
access to reach Ollama or a hosted API. Pluggable Ollama and hosted-API
providers are implemented but unverified (fall back to the heuristic
engine automatically if unreachable).

## Tool orchestration

`agent/tools.py` exposes a small, explicit set of read-only investigation
tools and a strictly smaller set of allowlisted remediation actions.
There is no code path granting the decision layer arbitrary command
execution. A real-Docker backend is implemented and used automatically
when a `docker` binary is present; a stateful, honest simulated cluster
backend is used otherwise (as in this sandbox) — every simulated call
mutates or reads real in-memory state, never a hardcoded canned response.

## AWS architecture

Planned, not deployed. See docs/AWS_DEPLOYMENT.md for the ECS
Fargate + S3 + CloudWatch design and the exact (untested) commands to
provision it.

## Security

See docs/SECURITY.md for the full control-by-control breakdown. Key
properties: no arbitrary shell execution, structurally-enforced human
approval before any remediation, validated decision objects, audit
logging of every tool call, no hardcoded secrets. Known gaps: no
API authentication, no TLS termination at the stdlib server (would sit
behind AWS's ALB/API Gateway TLS in a real deployment), no formal
threat-modeling exercise.

## Evaluation

45 automated tests, all passing (docs/TESTING.md), covering the vision
pipeline, decision engine, tool allowlist enforcement, and full incident
lifecycles including explicit failure paths (conflicting evidence,
rejected approval, act-before-approval). No accuracy/precision/recall
numbers are reported against real-world dashboard screenshots because no
labeled real-world dataset exists in this repo — reported as NOT YET
MEASURED rather than fabricated.

## Failure handling

Implemented and tested: visual uncertainty (low-confidence OpenCV read
→ no action), conflicting evidence (OpenCV and Docker disagree → no
action, flagged explicitly), rejected approval (blocks remediation),
missing tool signals during verification (recorded as `None`, never
guessed). Not implemented: repeated-restart-failure backoff logic (spec
section 14 mentions "do not repeatedly retry forever" — the current
single-shot `act()` never retries at all, which trivially satisfies "do
not retry forever" but has not been extended to a real retry-with-backoff
policy).

## Limitations

- Vision pipeline tuned against a synthetic dashboard generator, not a
  real Grafana instance.
- The audit sandbox imports OpenCV 4.13, but the repository is now pinned to OpenCV 5.0.0.93. Final verification on a networked build environment is still required.
- No AWS component actually deployed.
- No authentication on the API.
- Decision engine is rule-based by default, not LLM-backed (LLM paths
  implemented but unverified).
- No load/concurrency testing performed.

## Future work

- Point `vision/config.py`'s ROIs at a real Grafana dashboard screenshot.
- Upgrade to OpenCV 5.x and re-run the full test suite.
- Deploy the ECS/S3/CloudWatch stack from docs/AWS_DEPLOYMENT.md.
- Add API authentication and TLS.
- Exercise the Ollama/hosted-API decision providers against a live
  server.
- Add retry-with-backoff and a "give up and escalate to human" path for
  repeated remediation failures.

## Competition requirement mapping

See docs/COMPETITION_REQUIREMENTS.md for the full, row-by-row mapping
against the live Devpost rules page.
