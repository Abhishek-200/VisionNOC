"""
VisionNOC — agent/agent.py

The orchestration loop that ties vision, tools, policies, and providers
together. This is the "agentic" core the Agentic Vision Award requires:
OpenCV's output changes what happens next (which tools get called, and
whether a remediation is even proposed) rather than just being narrated.

Flow:

  SEE          -> vision.detector.analyze_dashboard(screenshot)
  UNDERSTAND   -> structured VisionResult (already true/false per chip)
  INVESTIGATE  -> agent/tools.py: check_docker_container, check_http_health,
                  get_prometheus_metrics, get_container_logs (read-only)
  DECIDE       -> agent/providers.py: get_decision(evidence) -> IncidentDecision
  APPROVE      -> agent/policies.py: requires_human_approval(); caller must
                  call approve()/reject() before act() will run
  ACT          -> agent/tools.py: ALLOWED_ACTIONS[...] (only after approval)
  VERIFY       -> agent/tools.py: verify_incident() (multi-signal, independent)

Every step is recorded on the Incident object for the audit trail
(spec section 15).
"""
from __future__ import annotations

import time

from agent import tools
from agent.models import Incident, IncidentDecision, ToolCallRecord
from agent.policies import requires_human_approval, is_confident_enough_to_propose_action
from agent.providers import get_decision
from vision.detector import analyze_dashboard


def _record_tool_call(incident: Incident, tool_name: str, tool_input: dict, output: dict):
    incident.tool_calls.append(ToolCallRecord(tool=tool_name, input=tool_input, output=output).to_dict())


def see_and_understand(image_path: str) -> dict:
    """SEE + UNDERSTAND: run the real OpenCV pipeline and return the
    validated VisionResult as a dict."""
    result = analyze_dashboard(image_path)
    return result.to_dict()


def investigate(incident: Incident, container: str = "visionnoc-backend") -> dict:
    """INVESTIGATE: call read-only tools and log every call. Returns the
    combined evidence dict handed to the decision provider."""
    docker_out = tools.check_docker_container(container)
    _record_tool_call(incident, "check_docker_container", {"container": container}, docker_out)

    http_out = tools.check_http_health()
    _record_tool_call(incident, "check_http_health", {}, http_out)

    prom_out = tools.get_prometheus_metrics()
    _record_tool_call(incident, "get_prometheus_metrics", {"query": "up"}, prom_out)

    logs_out = tools.get_container_logs(container)
    _record_tool_call(incident, "get_container_logs", {"container": container, "tail": 20}, logs_out)

    incident.status = "investigating"
    return {
        "vision": incident.vision_result,
        "docker": docker_out,
        "http": http_out,
        "prometheus": prom_out,
        "logs": logs_out,
    }


def decide(incident: Incident, evidence: dict) -> IncidentDecision:
    """DECIDE: get a structured, validated decision (heuristic by
    default; see agent/providers.py for the pluggable LLM path)."""
    raw = get_decision(evidence)
    decision = IncidentDecision(**raw)  # raises on anything malformed — never trusted blindly
    if decision.recommended_action != "none" and not is_confident_enough_to_propose_action(decision):
        decision = IncidentDecision(
            incident=decision.incident,
            confidence=decision.confidence,
            severity=decision.severity,
            evidence=decision.evidence + ["Confidence below remediation threshold; action suppressed"],
            probable_cause=decision.probable_cause,
            recommended_action="none",
            requires_approval=False,
        )
    incident.decision = decision.to_dict()
    incident.status = "awaiting_approval" if requires_human_approval(decision) else "resolved"
    return decision


def approve(incident: Incident, approved_by: str = "operator") -> None:
    if incident.status != "awaiting_approval":
        raise ValueError(f"Incident {incident.incident_id} is not awaiting approval (status={incident.status})")
    incident.approval = {"approved": True, "by": approved_by, "at": time.time()}
    incident.status = "remediating"


def reject(incident: Incident, rejected_by: str = "operator") -> None:
    if incident.status != "awaiting_approval":
        raise ValueError(f"Incident {incident.incident_id} is not awaiting approval (status={incident.status})")
    incident.approval = {"approved": False, "by": rejected_by, "at": time.time()}
    incident.status = "rejected"


def act(incident: Incident) -> dict:
    """ACT: invoke the allowlisted remediation, but ONLY if incident.status
    is 'remediating' (i.e. approve() was already called). There is no
    other code path into tools.ALLOWED_ACTIONS."""
    if incident.status != "remediating":
        raise ValueError(f"Incident {incident.incident_id} is not approved for remediation (status={incident.status})")
    action_name = incident.decision["recommended_action"]
    if action_name not in tools.ALLOWED_ACTIONS:
        raise ValueError(f"Refusing to run non-allowlisted action: {action_name}")
    fn = tools.ALLOWED_ACTIONS[action_name]
    out = fn()
    _record_tool_call(incident, action_name, {}, out)
    incident.remediation_result = out
    incident.status = "verifying"
    return out


def verify(incident: Incident, container: str = "visionnoc-backend", before_image: str = None, after_image: str = None) -> dict:
    """VERIFY: independent multi-signal check. Only marks the incident
    resolved if verify_incident() actually confirms recovery."""
    if incident.status != "verifying":
        raise ValueError(f"Incident {incident.incident_id} is not in verifying state (status={incident.status})")
    out = tools.verify_incident(container=container, before_image=before_image, after_image=after_image)
    _record_tool_call(incident, "verify_incident", {"container": container}, out)
    incident.verification_result = out
    incident.status = "resolved" if out["overall_recovered"] else "failed"
    return out


def run_full_cycle(image_path: str, container: str = "visionnoc-backend", auto_approve: bool = False) -> Incident:
    """Convenience wrapper that runs SEE->UNDERSTAND->INVESTIGATE->DECIDE,
    and — if auto_approve is True (demo/CLI use only; the API layer
    requires an explicit human call) — also APPROVE->ACT->VERIFY.
    Returns the fully-populated Incident."""
    vision = see_and_understand(image_path)
    incident = Incident.new(vision)
    evidence = investigate(incident, container=container)
    decision = decide(incident, evidence)

    if incident.status != "awaiting_approval":
        return incident

    if not auto_approve:
        return incident

    approve(incident)
    act(incident)
    after_image = tools.capture_dashboard("healthy", "healthy")["image_path"]
    verify(incident, container=container, before_image=image_path, after_image=after_image)
    return incident
