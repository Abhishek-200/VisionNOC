# AWS Deployment (planned — NOT deployed)

**Status: NOT IMPLEMENTED.** This sandbox has no `aws` CLI and no
outbound network (verified: `aws --version` → not found; general network
egress is blocked except an allowlist that does not include AWS
endpoints). Nothing described below has been provisioned, and no AWS
resources exist for this project. This document is the plan a user (or
a later Claude session with network + credentials) should execute.

## Why this matters for the competition

The rules require every entry to run "a meaningful component on AWS."
The architecture below puts VisionNOC's actual compute (the API +
agent + vision pipeline) on AWS, not just a static asset — satisfying
that in substance, not just checkbox form.

## Target architecture

```
Internet
   │
   v
Application Load Balancer  (or API Gateway, if going fully serverless)
   │
   v
ECS Fargate service (1 task, 0.5 vCPU / 1GB is plenty for this workload)
   - runs docker/Dockerfile.api (this repo's api/ + agent/ + vision/)
   - task role: least-privilege IAM (see below)
   │
   ├──> S3 bucket (dashboard screenshots / incident evidence)
   │       - lifecycle rule: expire objects after 30 days (cost control)
   │
   └──> CloudWatch Logs (container stdout -> log group /visionnoc/api)
        CloudWatch Metrics/Alarms (optional: alarm on incident rate)
```

## Prerequisites (user must do)

1. AWS account with billing set up.
2. `aws configure` with a non-root IAM user that has permissions to
   create ECR/ECS/S3/CloudWatch/IAM resources (or a scoped deployment
   role).
3. Docker installed locally (to build and push the image — see
   docs/PROJECT_STATUS.md for why this sandbox couldn't do it).

## Commands (untested here — BLOCKED, USER ACTION REQUIRED to run and verify)

```bash
# 1. Create an ECR repo and push the API image
aws ecr create-repository --repository-name visionnoc-api
aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker build -f docker/Dockerfile.api -t visionnoc-api .
docker tag visionnoc-api:latest <account-id>.dkr.ecr.<region>.amazonaws.com/visionnoc-api:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/visionnoc-api:latest

# 2. Create the S3 evidence bucket
aws s3 mb s3://visionnoc-evidence-<your-suffix>

# 3. Create an ECS cluster + Fargate service pointing at the pushed image
#    (recommend doing this step via the AWS Console or a small Terraform
#    config the first time, rather than raw CLI — there are ~6
#    interdependent resources: cluster, task definition, service,
#    security group, target group, listener rule)

# 4. Point AI_PROVIDER at api or ollama if desired, or leave as heuristic
#    (works with zero external dependencies either way)
```

## IAM requirements (least privilege)

The ECS task role needs, at minimum:
- `s3:PutObject`, `s3:GetObject` scoped to the evidence bucket only
- `logs:CreateLogStream`, `logs:PutLogEvents` scoped to `/visionnoc/*`
- If wiring `agent/tools.py`'s Docker path to a real EC2-hosted Docker
  daemon rather than ECS-managed containers: none of the above — that
  path talks to the local Docker socket, not AWS APIs.

Do NOT attach `AdministratorAccess` or broad `s3:*`/`logs:*` to the task
role.

## Cost considerations

See docs/COST_CONTROL.md.

## Cleanup commands (once deployed)

```bash
aws ecs delete-service --cluster visionnoc --service visionnoc-api --force
aws ecs delete-cluster --cluster visionnoc
aws ecr delete-repository --repository-name visionnoc-api --force
aws s3 rb s3://visionnoc-evidence-<your-suffix> --force
aws logs delete-log-group --log-group-name /visionnoc/api
```
