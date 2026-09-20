"""Structured, validated data models for the vision layer.

We don't have network access to pip-install pydantic in this environment
(documented in docs/PROJECT_STATUS.md), so these use Python's stdlib
`dataclasses` with manual validation in __post_init__. The shapes match
1:1 what you'd write as pydantic BaseModels, so swapping in pydantic
later (see requirements.txt) is a drop-in change, not a redesign.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal

ChipState = Literal["healthy", "down", "warning", "unknown"]


@dataclass
class ChipReading:
    name: str
    state: ChipState
    confidence: float
    match_fractions: dict

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence out of range: {self.confidence}")
        if self.state not in ("healthy", "down", "warning", "unknown"):
            raise ValueError(f"invalid state: {self.state}")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VisionResult:
    """The structured output of a single dashboard-image analysis pass.
    This is the object that the agent layer consumes — the agent never
    looks at raw pixels, only at this validated structure."""
    image_path: str
    chips: list  # list[ChipReading]
    overall_state: ChipState
    overall_confidence: float
    opencv_version: str

    def to_dict(self) -> dict:
        d = asdict(self)
        return d
