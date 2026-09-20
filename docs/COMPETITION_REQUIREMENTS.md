# Competition Requirements Mapping

**Source of truth:** https://opencv26.devpost.com/ and https://opencv26.devpost.com/rules
(fetched live on 2026-09-19; re-check before final submission in case the
page changes — deadline is Oct 26, 2026).

Key facts pulled directly from the live page:
- Deadline: **Oct 26, 2026, 11:45pm PDT** (submission page says 11:59pm Pacific in the details section — treat 11:45pm PDT as the binding number and submit earlier).
- Every entry must use **OpenCV 5** for substantive image/video analysis, and run a **meaningful component on AWS**.
- Two optional $1,000 paths: **Best Use of COOL** and **Agentic Vision**. VisionNOC targets **Agentic Vision**.
- Judging weights: Technical execution 30%, Innovation 20%, Real-world impact 20%, User experience 10%, Documentation/presentation 10%, Cloud delivery/reproducibility/responsible operation 10%.

| # | Requirement | Official source | How VisionNOC satisfies it | Evidence | Status |
|---|---|---|---|---|---|
| 1 | Use **OpenCV 5** for substantive analysis | devpost.com/opencv26 | `vision/detector.py` uses `cv2.inRange`, `cv2.cvtColor`, `cv2.GaussianBlur`, `cv2.findContours`, `cv2.absdiff`, `cv2.threshold` for real per-panel status classification + change detection | `python -c "import cv2; print(cv2.__version__)"` → `4.13.0` | **REPOSITORY PINNED; LOCAL 5.x VERIFICATION PENDING.** `requirements.txt`, Docker, and CI now pin `opencv-python-headless==5.0.0.93`. The current audit sandbox still imports 4.13.0.92 because it cannot download packages. **BLOCKED — USER ACTION REQUIRED**: on a networked machine, install the pinned requirements and run the OpenCV 5 verification command plus the full test suite. |
| 2 | Run a **meaningful component on AWS** | devpost.com/opencv26 | `docs/AWS_DEPLOYMENT.md` documents an EC2/ECS + S3 + CloudWatch architecture | Documentation only | **NOT IMPLEMENTED** — no AWS account/CLI available in this sandbox (`aws --version` → not found, no network). **BLOCKED — USER ACTION REQUIRED**: provision AWS per `docs/AWS_DEPLOYMENT.md` |
| 3 | Agentic Vision: visual evidence must **change a later tool call/action/approval request**, not just be narrated | devpost.com/opencv26 rules | `agent/agent.py`'s `decide()` output (from OpenCV's `overall_state`) directly determines which tools run next and whether `act()` is reachable at all — verified in `tests/test_incident_flow.py::test_incident_flow_without_approval_stops_at_awaiting_approval` etc. | `pytest`/`unittest`: 47/47 pass; live demo trace in `docs/evidence/` | **IMPLEMENTED + VERIFIED** (logic layer only — real Grafana/AWS integration still pending, see rows 1–2) |
| 4 | Technical report | devpost.com/opencv26 rules | `docs/TECHNICAL_REPORT.md` | — | **IMPLEMENTED** (document written; content honest about what's built vs. planned) |
| 5 | Judge-accessible code repository, pinned dependencies, build/deploy/test instructions | devpost.com/opencv26 rules | This repo; `requirements.txt` (pinned); `README.md` Installation/Testing sections | — | **IMPLEMENTED** |
| 6 | Architecture diagram (OpenCV 5 + AWS + agent/COOL components) | devpost.com/opencv26 rules | `docs/ARCHITECTURE.md` (ASCII diagram) | — | **IMPLEMENTED** (ASCII, not a rendered image — acceptable per rules, which don't mandate a format) |
| 7 | A **working web endpoint** OR an arranged live screen-share demo | devpost.com/opencv26 rules | `api/server.py` — verified running locally and answering all documented routes over real HTTP (see `docs/TESTING.md`) | `curl http://127.0.0.1:8000/health` → `{"status":"ok"}` | **IMPLEMENTED + VERIFIED locally** — **NOT hosted publicly**. **BLOCKED — USER ACTION REQUIRED**: deploy to a public/judge-reachable URL (this is what row 2's AWS component should also satisfy) |
| 8 | Judge-accessible video ≤ 5 minutes | devpost.com/opencv26 rules | `docs/VIDEO_SCRIPT.md` | — | **PLANNED** — script written, no video recorded. **BLOCKED — USER ACTION REQUIRED**: record the actual video |
| 9 | Evaluation evidence incl. failure cases/limitations | devpost.com/opencv26 rules | `docs/TESTING.md`, `docs/WHAT_I_ACTUALLY_BUILT.md` limitations section | 45 automated tests incl. explicit failure-path tests (conflicting evidence, rejection, act-before-approval) | **IMPLEMENTED + VERIFIED** for the logic layer |
| 10 | Team eligibility / registration | devpost.com/opencv26 | N/A — organizational, not technical | — | **NEEDS USER ACTION** — register the team on Devpost, submit the required proposal (competition uses a proposal + build-phase structure, not open build-anytime) |
| 11 | (Optional) Best Use of COOL — AWS Graviton-accelerated OpenCV | devpost.com/opencv26 rules | Not attempted | — | **NOT IMPLEMENTED** (optional path; VisionNOC does not claim this award) |

## Honest bottom line

VisionNOC's **agentic control-flow logic** — the actual "OpenCV output changes
what the agent does next" mechanism the Agentic Vision Award is judging — is
real, implemented, and verified end-to-end in this sandbox. What is **not**
done, and requires the user's own environment (network, Docker, AWS
credentials, a camera-ready OpenCV 5 install), is: (a) confirming/upgrading to
an actual OpenCV 5 package, (b) deploying any component to AWS, (c) pointing
the vision pipeline at a real Grafana dashboard instead of the synthetic one,
(d) recording the demo video, (e) registering/submitting on Devpost.
