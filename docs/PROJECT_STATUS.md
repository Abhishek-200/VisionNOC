# Project Status — Deep Audit & Fix (2026-09-19)

## Verified in this audit environment

- Python 3.x available
- `python3 -m compileall -q .` — PASS
- `python3 -m unittest discover -s tests -v` — **47/47 PASS** using the currently installed OpenCV 4.13.0.92
- Docker CLI — NOT INSTALLED in this environment
- AWS CLI — NOT INSTALLED in this environment
- Current imported `cv2.__version__` — 4.13.0

## Important competition status

The competition requires OpenCV 5 for substantive image/video analysis and a meaningful AWS component. The repository is now pinned to `opencv-python-headless==5.0.0.93`, and the Dockerfile/CI workflow use that same pin. The current audit environment cannot install or execute that wheel because outbound package downloads are unavailable. Therefore **OpenCV 5 is required by the repository but NOT locally verified in this audit environment**.

Official sources confirm OpenCV 5.0.0 exists and `opencv-python` 5.0.0.93 provides Linux x86-64 wheels. Re-run the environment verification on a networked machine before submission.

## Fixes made

1. Pinned the project and Docker image to OpenCV 5.0.0.93; removed conflicting multiple OpenCV packages.
2. Fixed persisted incident lifecycle: approve/reject/verify now rehydrate incidents from SQLite instead of depending on an in-memory cache.
3. Fixed real Docker mapping: logical `visionnoc-backend` maps to the Compose container `visionnoc-demo-app`.
4. Fixed incident trigger so Docker-enabled runs actually stop/restart the real demo container rather than only mutating the simulator.
5. Fixed HTTP health default from port 8080 to the demo app's port 9000 and made it configurable for host/container execution.
6. Added real Prometheus HTTP querying with an explicitly labeled simulator fallback.
7. Fixed Prometheus verification to handle real Prometheus's `[timestamp, value]` response format and empty results safely.
8. Fixed Grafana dashboard query to use the Prometheus `up` metric for target health.
9. Added `/metrics` to the VisionNOC API for proper Prometheus scraping.
10. Added malformed-JSON validation and a 1 MB request-body limit.
11. Restricted API image analysis to images under `docs/evidence` to avoid arbitrary local-file reads.
12. Added optional bearer-token protection using `VISIONNOC_API_TOKEN`.
13. Added a small browser UI for the human approval step at `/` or `/ui`.
14. Removed silent fallback from configured LLM providers to the heuristic provider; a configured provider now fails explicitly if unavailable.
15. Added a remediation confidence gate below 0.55.
16. Added regression tests for malformed JSON and persisted incident loading.

## Still required before competition submission

- Install and run OpenCV 5.0.0.93 and re-run the complete test suite.
- Run Docker Compose end-to-end on a machine with Docker.
- Verify a real Grafana/Prometheus incident path.
- Deploy a meaningful component to AWS.
- Configure secure authentication/TLS for any public endpoint.
- Run the complete judge-facing demo and collect evidence.
- Record the <=5-minute judge-accessible video.
- Re-check the live Devpost page immediately before submission.
