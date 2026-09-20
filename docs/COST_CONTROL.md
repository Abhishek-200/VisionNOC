# Cost Control

## Free / local components (this repo, as built)

- `vision/`, `agent/`, `store/`, `api/`, `demo/` — pure Python, no paid
  services, run entirely on your machine at zero cost.
- `AI_PROVIDER=heuristic` (the default) — zero API cost, no network
  needed at all.
- SQLite (`store/db.py`) — local file, no hosted database cost.

## Potentially paid components

| Component | When it costs money | Typical cost |
|---|---|---|
| `AI_PROVIDER=api` (hosted LLM) | Every decision call, if you switch away from `heuristic` | Depends on provider/model; a few decisions per demo is negligible, but don't leave a high-frequency polling loop running against a paid API |
| AWS ECS Fargate (docs/AWS_DEPLOYMENT.md) | While the task is running | ~$0.01–0.02/hour for a 0.5 vCPU/1GB task — remember to delete the service when not demoing |
| AWS S3 | Storage + requests | Negligible at hackathon-demo scale; the lifecycle rule in docs/AWS_DEPLOYMENT.md expires objects after 30 days to prevent silent accumulation |
| AWS CloudWatch Logs | Log ingestion/storage | Negligible at this scale, but set a log-group retention period (not done automatically — BLOCKED, USER ACTION REQUIRED) |
| AWS ALB (if used instead of API Gateway) | Hourly + per-request | ~$16-20/month if left running continuously — an API Gateway HTTP API is cheaper for low, bursty traffic and is the better default here |
| Compute grant ($150, if awarded per competition rules) | Offsets the above | Apply per the competition's grant process — outside this repo's scope |

## What should NOT be left running

- Do not leave an ECS service running 24/7 for a hackathon demo —
  `aws ecs update-service --desired-count 0` between demo sessions, or
  delete it entirely per docs/AWS_DEPLOYMENT.md's cleanup commands.
- Do not set `AI_PROVIDER=api` with a tight polling loop — this repo's
  demo/API only calls the decision provider once per incident, which is
  fine, but a custom monitoring loop built on top of this should debounce.
- Do not leave an ALB provisioned if you switch to API Gateway — ALBs
  bill hourly whether or not they're receiving traffic.

## AWS Free Tier note (per the competition's own page)

The competition page states new AWS customers can get up to $100 in
Free Tier credits (plus up to $100 more through eligible activities),
and that teams may use these for eligible services subject to AWS Free
Tier terms. This has not been independently verified beyond what the
Devpost page states — check current AWS Free Tier terms directly before
relying on it: https://aws.amazon.com/free/terms/
