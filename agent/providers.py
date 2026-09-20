"""
VisionNOC — agent/providers.py

Pluggable decision-making backends, selected via the AI_PROVIDER env var
(see .env.example), matching spec section 9.

  AI_PROVIDER=heuristic  (DEFAULT, and the only one runnable in this
                          sandbox — deterministic rule engine over the
                          investigation evidence, no network required)
  AI_PROVIDER=ollama     (calls a local Ollama server — BLOCKED here:
                          this sandbox has no network/local Ollama
                          install; code path is implemented and will run
                          wherever Ollama is reachable)
  AI_PROVIDER=api        (calls a hosted LLM API via HTTPS — BLOCKED
                          here for the same reason; never hardcode a key,
                          read it from ANTHROPIC_API_KEY / OPENAI_API_KEY
                          etc. per .env.example)

Every provider must return a plain dict matching agent.models.IncidentDecision's
fields; agent/agent.py validates it through that dataclass before using it.
This is the "never trust raw LLM output" gate from spec section 10.
"""
from __future__ import annotations

import json
import os
import urllib.request


class ProviderUnavailable(RuntimeError):
    pass


def decide_heuristic(evidence: dict) -> dict:
    """Deterministic rule-based decision engine. This is what actually
    runs end-to-end in this sandbox (verified — see docs/TESTING.md).
    It looks at the same investigation evidence an LLM-backed provider
    would receive and applies explicit, auditable rules instead of a
    model call."""
    vision_state = evidence["vision"]["overall_state"]
    vision_conf = evidence["vision"]["overall_confidence"]
    docker = evidence.get("docker", {})
    http = evidence.get("http", {})

    docker_status = docker.get("status") if docker.get("found") else None
    http_healthy = http.get("healthy")

    ev_lines = [f"OpenCV detected dashboard state: {vision_state} (confidence {vision_conf})"]
    if docker.get("found"):
        ev_lines.append(f"Docker reports container status: {docker_status}")
    if http_healthy is not None:
        ev_lines.append(f"HTTP health check: {'healthy' if http_healthy else 'unhealthy'}")

    if vision_state == "healthy" and (http_healthy is not False):
        return {
            "incident": "none",
            "confidence": vision_conf,
            "severity": "low",
            "evidence": ev_lines,
            "probable_cause": "n/a",
            "recommended_action": "none",
            "requires_approval": False,
        }

    if vision_state == "unknown":
        return {
            "incident": "visual_uncertainty",
            "confidence": vision_conf,
            "severity": "low",
            "evidence": ev_lines + ["Visual classification confidence too low to act on"],
            "probable_cause": "insufficient_visual_evidence",
            "recommended_action": "none",
            "requires_approval": False,
        }

    # vision_state in ("down", "warning") from here
    conflicting = docker_status is not None and (
        (vision_state == "down") != (docker_status != "running")
    )
    if conflicting:
        return {
            "incident": "conflicting_evidence",
            "confidence": min(vision_conf, 0.5),
            "severity": "medium",
            "evidence": ev_lines + ["Visual state and Docker state disagree — further investigation required before any action"],
            "probable_cause": "unknown_conflicting_signals",
            "recommended_action": "none",
            "requires_approval": False,
        }

    severity = "high" if vision_state == "down" else "medium"
    action = "restart_backend" if docker_status in ("stopped", "exited") else "none"
    return {
        "incident": "backend_down" if vision_state == "down" else "backend_degraded",
        "confidence": vision_conf,
        "severity": severity,
        "evidence": ev_lines,
        "probable_cause": "backend_container_stopped" if docker_status in ("stopped", "exited") else "unknown",
        "recommended_action": action,
        "requires_approval": action != "none",
    }


def decide_ollama(evidence: dict, model: str = "llama3", host: str = "http://localhost:11434") -> dict:
    """BLOCKED — USER ACTION REQUIRED in this sandbox (no local Ollama,
    no network). Implemented for completeness; will work wherever an
    Ollama server is reachable at `host`."""
    prompt = (
        "You are an SRE incident-diagnosis assistant. Given this evidence, "
        "respond with ONLY a JSON object with keys: incident, confidence, "
        "severity, evidence (list of strings), probable_cause, "
        "recommended_action (one of restart_backend/restart_database/none), "
        "requires_approval (bool). Evidence:\n" + json.dumps(evidence)
    )
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(f"{host}/api/generate", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return json.loads(data["response"])
    except Exception as exc:  # noqa: BLE001
        raise ProviderUnavailable(f"Ollama unreachable at {host}: {exc}") from exc


def decide_api(evidence: dict) -> dict:
    """BLOCKED — USER ACTION REQUIRED in this sandbox (no network, no key
    provisioned). Reads the key from an env var only — never hardcoded.
    Implemented for completeness; will work with network + a valid key."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ProviderUnavailable("ANTHROPIC_API_KEY not set")
    body = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 1000,
        "messages": [{
            "role": "user",
            "content": (
                "Respond with ONLY a JSON object with keys: incident, confidence, "
                "severity, evidence, probable_cause, recommended_action "
                "(restart_backend/restart_database/none), requires_approval. "
                f"Evidence: {json.dumps(evidence)}"
            ),
        }],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
        return json.loads(text)
    except Exception as exc:  # noqa: BLE001
        raise ProviderUnavailable(f"API provider unavailable: {exc}") from exc


def get_decision(evidence: dict) -> dict:
    provider = os.environ.get("AI_PROVIDER", "heuristic")
    if provider == "heuristic":
        return decide_heuristic(evidence)
    if provider == "ollama":
        return decide_ollama(evidence)
    if provider == "api":
        return decide_api(evidence)
    raise ValueError(f"Unknown AI_PROVIDER: {provider}")
