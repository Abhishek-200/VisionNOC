"""
VisionNOC — agent/policies.py

Approval gating. Section 11/14 of the spec: destructive operations must
require approval, conflicting/uncertain evidence must not auto-remediate.
"""
from __future__ import annotations

from agent.models import IncidentDecision

MIN_CONFIDENCE_FOR_ANY_ACTION = 0.55


def requires_human_approval(decision: IncidentDecision) -> bool:
    """Everything that isn't a no-op requires approval in this MVP — this
    is a deliberately conservative default for a system that can restart
    production-adjacent services. There is no code path that lets the
    agent skip approval for a real remediation action."""
    if decision.recommended_action == "none":
        return False
    return True


def is_confident_enough_to_propose_action(decision: IncidentDecision) -> bool:
    return decision.confidence >= MIN_CONFIDENCE_FOR_ANY_ACTION


def evidence_is_conflicting(vision_state: str, docker_status: str | None) -> bool:
    """Example from spec section 14: OpenCV says DOWN but Docker says
    RUNNING (or vice versa). When true, the agent must investigate
    further rather than blindly remediate."""
    if docker_status is None:
        return False
    vision_says_down = vision_state == "down"
    docker_says_down = docker_status != "running"
    return vision_says_down != docker_says_down
