"""
VisionNOC — vision/detector.py

The real OpenCV visual-incident-detection pipeline.

Pipeline (see docs/OPENCV.md for full write-up):

  dashboard screenshot (PNG)
        |
        v
  load_image (cv2.imread)
        |
        v
  denoise (cv2.GaussianBlur)
        |
        v
  for each configured status-chip ROI:
        crop_normalized -> to_hsv -> color_mask_fraction (cv2.inRange +
        cv2.countNonZero) against healthy/down/warning HSV ranges
        + find_status_contours (cv2.threshold/OTSU + cv2.findContours)
          as corroborating structural evidence
        |
        v
  per-chip ChipReading (state, confidence)
        |
        v
  overall_state = worst-case aggregation across chips
        |
        v
  VisionResult (validated, structured) -> consumed by agent/agent.py

This module performs REAL pixel processing — it does not read filenames
or metadata to decide the answer. Swap in a real Grafana screenshot with
the same layout and it will be analyzed the same way.
"""
from __future__ import annotations

import cv2

from vision import preprocessing as pre
from vision.config import STATUS_CHIPS, HSV_RANGES, MIN_MATCH_FRACTION, CHANGE_DIFF_THRESHOLD
from vision.models import ChipReading, VisionResult


def classify_chip(name: str, roi_bgr) -> ChipReading:
    hsv_roi = pre.to_hsv(roi_bgr)

    fractions = {
        "healthy": pre.color_mask_fraction(hsv_roi, *HSV_RANGES["healthy"]),
        "down": max(
            pre.color_mask_fraction(hsv_roi, *HSV_RANGES["down"]),
            pre.color_mask_fraction(hsv_roi, *HSV_RANGES["down_hi"]),
        ),
        "warning": pre.color_mask_fraction(hsv_roi, *HSV_RANGES["warning"]),
    }

    # Corroborating structural evidence: a real status chip should contain
    # at least one solid contour (a filled dot/box), not just scattered
    # noise pixels that happen to match a color range.
    contours = pre.find_status_contours(roi_bgr)
    has_solid_shape = len(contours) > 0

    best_state, best_fraction = max(fractions.items(), key=lambda kv: kv[1])

    if best_fraction < MIN_MATCH_FRACTION or not has_solid_shape:
        return ChipReading(
            name=name,
            state="unknown",
            confidence=round(best_fraction, 4),
            match_fractions={k: round(v, 4) for k, v in fractions.items()},
        )

    return ChipReading(
        name=name,
        state=best_state,
        confidence=round(min(0.99, best_fraction + (0.15 if has_solid_shape else 0.0)), 4),
        match_fractions={k: round(v, 4) for k, v in fractions.items()},
    )


def analyze_dashboard(image_path: str) -> VisionResult:
    """Run the full OpenCV pipeline on a dashboard screenshot and return a
    validated VisionResult. This is the single entry point the agent
    layer calls."""
    img = pre.load_image(image_path)
    img = pre.denoise(img)

    chips = []
    for chip_cfg in STATUS_CHIPS:
        roi = pre.crop_normalized(img, chip_cfg.bbox)
        chips.append(classify_chip(chip_cfg.name, roi))

    # Worst-case aggregation: if ANY chip reads down, the dashboard's
    # overall state is down; else worst of warning/unknown/healthy.
    priority = {"down": 3, "warning": 2, "unknown": 1, "healthy": 0}
    worst = max(chips, key=lambda c: priority[c.state])
    overall_state = worst.state
    overall_confidence = worst.confidence

    return VisionResult(
        image_path=image_path,
        chips=[c.to_dict() for c in chips],
        overall_state=overall_state,
        overall_confidence=overall_confidence,
        opencv_version=cv2.__version__,
    )


def visual_recovery_score(before_path: str, after_path: str) -> float:
    """Fraction of the dashboard that visibly changed between two
    screenshots. Used as one signal (not the only signal) during
    post-remediation verification."""
    img_a = pre.load_image(before_path)
    img_b = pre.load_image(after_path)
    return pre.frame_diff_score(img_a, img_b, CHANGE_DIFF_THRESHOLD)
