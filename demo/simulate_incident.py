"""
VisionNOC — demo/simulate_incident.py

Runs the full demo sequence from docs/DEMO_GUIDE.md end to end in the
terminal, narrating each step. This is the "./scripts/simulate_incident.sh"
mechanism from spec section 5 — actually implemented in Python for
portability, wrapped by scripts/simulate_incident.sh.

Usage:
    python3 -m demo.simulate_incident            # interactive (asks for approval)
    python3 -m demo.simulate_incident --auto     # non-interactive (auto-approves)
"""
from __future__ import annotations

import argparse
import json
import sys

from agent import agent as agent_ops
from agent import tools


def line(char="-", n=60):
    print(char * n)


def step(n: int, title: str):
    print()
    line("=")
    print(f"STEP {n}: {title}")
    line("=")


def main():
    parser = argparse.ArgumentParser(description="VisionNOC incident demo")
    parser.add_argument("--auto", action="store_true", help="auto-approve remediation (non-interactive)")
    args = parser.parse_args()

    step(1, "HEALTHY STATE — capture baseline dashboard")
    healthy_img = tools.capture_dashboard("healthy", "healthy")["image_path"]
    print(f"Baseline dashboard: {healthy_img}")

    step(2, "TRIGGER INCIDENT — stop the backend container")
    tools.CLUSTER.stop("visionnoc-backend")
    print("visionnoc-backend -> STOPPED (simulated cluster)")

    step(3, "SEE — capture the incident dashboard (real PNG, real pixels)")
    incident_img = tools.capture_dashboard("down", "healthy")["image_path"]
    print(f"Incident dashboard: {incident_img}")

    step(4, "UNDERSTAND — OpenCV analyzes the dashboard")
    vision = agent_ops.see_and_understand(incident_img)
    print(json.dumps(vision, indent=2))

    from agent.models import Incident
    incident = Incident.new(vision)
    print(f"\nIncident opened: {incident.incident_id}")

    step(5, "INVESTIGATE — read-only tool calls")
    evidence = agent_ops.investigate(incident)
    for call in incident.tool_calls:
        print(f"  [{call['tool']}] -> {json.dumps(call['output'])}")

    step(6, "DECIDE — structured, validated diagnosis")
    decision = agent_ops.decide(incident, evidence)
    print(json.dumps(decision.to_dict(), indent=2))

    if decision.recommended_action == "none":
        print("\nNo remediation recommended. Demo ends here (nothing to approve).")
        return

    step(7, "HUMAN APPROVAL REQUIRED")
    print(f"Incident {incident.incident_id}: {decision.incident}")
    print(f"Evidence: {decision.evidence}")
    print(f"Recommended action: {decision.recommended_action}")

    if args.auto:
        approved = True
        print("[--auto] auto-approving remediation")
    else:
        resp = input("Approve remediation? [y/N]: ").strip().lower()
        approved = resp == "y"

    if not approved:
        agent_ops.reject(incident)
        print(f"\nRejected. Incident status: {incident.status}")
        return

    agent_ops.approve(incident)

    step(8, "ACT — run the ALLOWLISTED remediation")
    result = agent_ops.act(incident)
    print(json.dumps(result, indent=2))

    step(9, "VERIFY — independent multi-signal recovery check")
    after_img = tools.capture_dashboard("healthy", "healthy")["image_path"]
    verification = agent_ops.verify(incident, before_image=incident_img, after_image=after_img)
    print(json.dumps(verification, indent=2))

    step(10, f"FINAL STATUS: {incident.status.upper()}")
    print(f"Incident {incident.incident_id} tool-call audit trail ({len(incident.tool_calls)} calls):")
    for call in incident.tool_calls:
        print(f"  - {call['tool']}")


if __name__ == "__main__":
    sys.exit(main())
