"""
Structured, validated models for agent decisions and incidents.

Same note as vision/models.py: stdlib dataclasses with __post_init__
validation, standing in for pydantic (no network to install it in this
sandbox — see docs/PROJECT_STATUS.md). The agent never trusts raw model
text; every decision passes through IncidentDecision.__post_init__
before anything downstream acts on it.
"""
from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional

Severity = Literal["low", "medium", "high", "critical"]

VALID_ACTIONS = {"restart_backend", "restart_database", "none"}


@dataclass
class ToolCallRecord:
    tool: str
    input: dict
    output: dict
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IncidentDecision:
    """The agent's structured diagnosis. Mirrors section 10 of the spec
    exactly. Validated on construction — never trust raw LLM/heuristic
    output without this gate."""
    incident: str
    confidence: float
    severity: Severity
    evidence: list
    probable_cause: str
    recommended_action: str
    requires_approval: bool

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence out of range: {self.confidence}")
        if self.severity not in ("low", "medium", "high", "critical"):
            raise ValueError(f"invalid severity: {self.severity}")
        if self.recommended_action not in VALID_ACTIONS:
            raise ValueError(
                f"recommended_action {self.recommended_action!r} is not in the "
                f"allowlist {VALID_ACTIONS} — refusing to construct an "
                f"unvalidated decision"
            )
        if not isinstance(self.evidence, list) or not self.evidence:
            raise ValueError("evidence must be a non-empty list")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Incident:
    incident_id: str
    created_at: float
    status: str  # detected | investigating | awaiting_approval | remediating | verifying | resolved | rejected | failed
    vision_result: dict
    decision: Optional[dict] = None
    tool_calls: list = field(default_factory=list)
    approval: Optional[dict] = None
    remediation_result: Optional[dict] = None
    verification_result: Optional[dict] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Incident":
        required = {"incident_id", "created_at", "status", "vision_result"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"invalid persisted incident; missing {sorted(missing)}")
        return cls(
            incident_id=str(data["incident_id"]), created_at=float(data["created_at"]),
            status=str(data["status"]), vision_result=dict(data["vision_result"]),
            decision=data.get("decision"), tool_calls=list(data.get("tool_calls") or []),
            approval=data.get("approval"), remediation_result=data.get("remediation_result"),
            verification_result=data.get("verification_result"),
        )

    @staticmethod
    def new(vision_result: dict) -> "Incident":
        return Incident(
            incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
            created_at=time.time(),
            status="detected",
            vision_result=vision_result,
        )

    def to_dict(self) -> dict:
        return asdict(self)
