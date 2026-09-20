"""
VisionNOC — demo/generate_dashboard.py

Generates synthetic "Grafana-style" dashboard PNGs used by the offline
demo and test suite.

WHY SYNTHETIC IMAGES: this sandbox has no network access and cannot run
Docker/Prometheus/Grafana (see docs/PROJECT_STATUS.md). Rather than fake
the vision result, we generate real PNG images with real pixels in the
exact layout vision/config.py's STATUS_CHIPS expects, and detector.py
processes those pixels with real OpenCV calls (color thresholding +
contour detection). This is documented, not hidden: docs/OPENCV.md
explains exactly what would need to change (the ROI bboxes in
vision/config.py) to point the same pipeline at a real Grafana
screenshot instead.

Layout (1200x700 canvas):
  - Top banner (overall status)         -> chip "overall_banner"
  - Left panel: "Backend Service"       -> chip "backend_service"
  - Right panel: "Database Service"     -> chip "database_service"
"""
from __future__ import annotations

import os
import cv2
import numpy as np

WIDTH, HEIGHT = 1200, 700

COLORS_BGR = {
    "healthy": (60, 180, 75),   # green
    "down": (40, 40, 220),      # red
    "warning": (0, 200, 240),   # amber
    "bg": (35, 30, 25),
    "panel": (55, 48, 40),
    "text": (230, 230, 230),
}


def _panel(img, x1, y1, x2, y2, color_bgr, label):
    cv2.rectangle(img, (x1, y1), (x2, y2), COLORS_BGR["panel"], thickness=-1)
    # status chip: a filled circle, sized/positioned to sit inside the
    # normalized bbox that vision/config.py's STATUS_CHIPS references
    cx, cy = x1 + 60, y1 + 45
    cv2.circle(img, (cx, cy), 28, color_bgr, thickness=-1)
    cv2.putText(img, label, (x1 + 15, y2 - 20), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, COLORS_BGR["text"], 1, cv2.LINE_AA)


def render_dashboard(backend_state: str, database_state: str, out_path: str) -> str:
    """Render a dashboard PNG with the given per-service states
    ('healthy' | 'down' | 'warning') and write it to out_path."""
    img = np.full((HEIGHT, WIDTH, 3), COLORS_BGR["bg"], dtype=np.uint8)

    overall = "down" if "down" in (backend_state, database_state) else (
        "warning" if "warning" in (backend_state, database_state) else "healthy"
    )

    # Top banner (spans ~4%-16% height, 4%-96% width — matches
    # vision.config.STATUS_CHIPS "overall_banner" bbox)
    bx1, by1 = int(0.04 * WIDTH), int(0.04 * HEIGHT)
    bx2, by2 = int(0.96 * WIDTH), int(0.16 * HEIGHT)
    cv2.rectangle(img, (bx1, by1), (bx2, by2), COLORS_BGR[overall], thickness=-1)
    cv2.putText(img, f"VisionNOC Demo Cluster - {overall.upper()}",
                (bx1 + 20, by2 - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (10, 10, 10), 2, cv2.LINE_AA)

    # Backend panel (matches "backend_service" bbox 0.06-0.32 x, 0.20-0.34 y)
    px1, py1 = int(0.06 * WIDTH), int(0.20 * HEIGHT)
    px2, py2 = int(0.32 * WIDTH), int(0.34 * HEIGHT)
    _panel(img, px1, py1, px2, py2, COLORS_BGR[backend_state], "backend")

    # Database panel (matches "database_service" bbox 0.68-0.94 x, 0.20-0.34 y)
    qx1, qy1 = int(0.68 * WIDTH), int(0.20 * HEIGHT)
    qx2, qy2 = int(0.94 * WIDTH), int(0.34 * HEIGHT)
    _panel(img, qx1, qy1, qx2, qy2, COLORS_BGR[database_state], "database")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    ok = cv2.imwrite(out_path, img)
    if not ok:
        raise IOError(f"cv2.imwrite failed for {out_path}")
    return out_path


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "evidence")
    render_dashboard("healthy", "healthy", os.path.join(out_dir, "01_healthy_dashboard.png"))
    render_dashboard("down", "healthy", os.path.join(out_dir, "02_incident_dashboard.png"))
    render_dashboard("healthy", "healthy", os.path.join(out_dir, "07_recovered_dashboard.png"))
    print("Synthetic dashboards written to", os.path.abspath(out_dir))
