# Video Script (≤ 5 minutes, per competition rules)

**Status: script only — no video has been recorded.** BLOCKED — USER
ACTION REQUIRED: record screen + voiceover following this script.

---

### 0:00–0:20 — Introduction
"Hi, I'm [name], and this is VisionNOC — an agentic visual
incident-response system built for the OpenCV AI Competition 2026's
Agentic Vision path. VisionNOC watches a monitoring dashboard, and when
OpenCV detects a visual incident, that detection actually changes what
the system does next — it investigates, proposes a fix, waits for human
approval, and verifies recovery."

### 0:20–0:50 — Problem
"On-call engineers stare at dashboards. When something turns red, they
manually correlate it with logs, metrics, and container state before
acting. VisionNOC automates the *investigation and evidence-gathering*
step — using real computer vision on the dashboard itself as the
trigger — while keeping a human in the loop for anything destructive."

### 0:50–1:30 — Architecture
[Show docs/ARCHITECTURE.md diagram on screen]
"The pipeline is SEE, UNDERSTAND, INVESTIGATE, DECIDE, APPROVE, ACT,
VERIFY. Vision and decision-making are cleanly separated: OpenCV only
ever produces a structured, validated result — it doesn't know or care
what happens next. The agent layer holds a strict allowlist of tools;
there is no arbitrary shell execution anywhere in this codebase."

### 1:30–1:50 — OpenCV 5 note (honesty, not spin)
"One honest note: the competition requires OpenCV 5, which was released
in June 2026. My development sandbox for this build had no network
the audit environment could not download OpenCV 5; the repository is now pinned to 5.0.0.93, so final 5.x runtime verification is a to-do before
final submission — documented in docs/COMPETITION_REQUIREMENTS.md. The
vision code itself only uses long-stable OpenCV APIs, so the upgrade
should be a version bump, not a rewrite."

### 1:50–3:30 — Live incident demo
[Run `./scripts/simulate_incident.sh --auto` on screen, or drive it via
the HTTP API per docs/DEMO_GUIDE.md]
"Here's the backend service, healthy. I stop its container. VisionNOC
captures the dashboard — watch the backend panel turn red. That's a real
PNG, real pixels, real OpenCV color-and-contour analysis — not a
canned response. It correctly classifies backend as down and the
database, correctly, as still healthy. Now it investigates: checks
Docker, checks the HTTP health endpoint, checks Prometheus, pulls logs
— every one of these calls is logged for audit. Based on that evidence
it recommends restarting the backend, with 66% confidence, and — because
this is a destructive action — it stops and asks me to approve. I
approve. It restarts the container, then independently re-verifies
across four signals: Docker, HTTP, Prometheus, and a fresh OpenCV read
of the dashboard. All four agree: recovered."

### 3:30–4:10 — Why this is "agentic," not just a vision demo
"The key thing the competition is judging here: does the visual output
change what happens next? It does, in two concrete ways. First, a
healthy read short-circuits the whole pipeline — no tools even get
called beyond the vision check. Second, if OpenCV and Docker disagree —
say OpenCV reads down but Docker reports running — the agent explicitly
refuses to act and flags conflicting evidence instead of guessing.
That's real evidence-driven branching, not a script."

### 4:10–4:40 — Testing and honesty
"45 automated tests pass, covering the vision pipeline, the decision
engine, the tool allowlist, and full incident flows — including failure
paths like conflicting evidence and rejected approvals. Everything
you've seen in this video actually ran; nothing is a mockup. What's
still outstanding — real AWS deployment, a real Grafana dashboard
instead of a synthetic one, and the OpenCV 5 upgrade — is documented
honestly in docs/WHAT_I_ACTUALLY_BUILT.md rather than glossed over."

### 4:40–5:00 — Close
"That's VisionNOC — thanks for watching. Code, docs, and the full test
suite are in the repo linked below."
