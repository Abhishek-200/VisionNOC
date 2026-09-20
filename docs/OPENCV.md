# How VisionNOC uses OpenCV

**Installed version in the authoring sandbox: `opencv-python 4.13.0.92`
(confirmed via `cv2.__version__`).** The competition requires OpenCV 5. The repository is pinned to the 5.0.0.93 Python package, but this audit environment could not install it because outbound package downloads are disabled.,
which was confirmed (via web search) to have actually been released
(June 6, 2026) — see docs/COMPETITION_REQUIREMENTS.md row 1 for the full,
honest status of this gap. Nothing in this document or in
`vision/detector.py` claims OpenCV 5 is running; every version string
shown in this project's output (`VisionResult.opencv_version`,
`/api/status`'s `opencv_version` field) is read live from `cv2.__version__`,
never hardcoded.

## Why synthetic dashboard images

This sandbox has no outbound network and no Docker daemon (see
docs/PROJECT_STATUS.md), so it cannot run Grafana. Rather than fake a
vision result by branching on a filename or a hardcoded flag,
`demo/generate_dashboard.py` renders real 1200x700 BGR images with
`cv2.rectangle`/`cv2.circle`/`cv2.putText`, and `vision/detector.py`
processes those images' actual pixel data — it has no knowledge of how
they were produced. Pointing the same pipeline at a real Grafana
screenshot requires re-measuring four numbers (the normalized ROI boxes
in `vision/config.py::STATUS_CHIPS`) against that dashboard's actual
layout — no other code changes.

## The pipeline, step by step (`vision/detector.py::analyze_dashboard`)

1. `preprocessing.py::load_image` — `cv2.imread`, raises
   `FileNotFoundError` if OpenCV can't decode the file (never silently
   returns a placeholder).
2. `preprocessing.py::denoise` — `cv2.GaussianBlur(img, (5,5), 0)` to
   reduce screenshot compression artifacts before color thresholding.
3. For each configured status chip (`vision/config.py::STATUS_CHIPS`):
   - `preprocessing.py::crop_normalized` — pixel-space crop from a
     normalized bounding box (resolution-independent).
   - `preprocessing.py::to_hsv` — `cv2.cvtColor(..., COLOR_BGR2HSV)`,
     because HSV is far more robust to lighting/anti-aliasing than raw
     BGR thresholds for "is this pixel green/red/amber."
   - `preprocessing.py::color_mask_fraction` — `cv2.inRange` + 
     `cv2.countNonZero` per configured HSV range (healthy/down/warning),
     with red split into two ranges (`down` and `down_hi`) to handle
     hue wraparound at 0°/360°.
   - `preprocessing.py::find_status_contours` — `cv2.threshold` with
     Otsu's method + `cv2.findContours` as **corroborating structural
     evidence**: a chip must contain an actual solid shape (a real
     contour), not just scattered pixels that happen to match a color
     range. `vision/detector.py::classify_chip` requires both a
     sufficient color-match fraction (`MIN_MATCH_FRACTION`, default
     0.25) *and* at least one contour before committing to a
     non-`unknown` classification.
4. Per-chip results aggregate to an overall dashboard state by
   worst-case priority (`down` > `warning` > `unknown` > `healthy`).
5. `preprocessing.py::frame_diff_score` — `cv2.absdiff` + `cv2.threshold`
   between a before/after screenshot, used during verification
   (`agent/tools.py::verify_incident`) as one independent recovery
   signal alongside Docker/HTTP/Prometheus.

## What this pipeline is NOT

It is not a machine-learned classifier and does not do OCR — spec
section 6 lists OCR as one *possible* technique, not a requirement, and
color+contour classification is more deterministic and reliable for a
timed hackathon demo (spec section 7 explicitly asks for
"deterministic enough for a hackathon demo"). If a future iteration
needs to read actual text (e.g. an error message in a log panel),
OCR (e.g. via `pytesseract`) would be added as an additional pipeline
stage, not a replacement.

## Verified test coverage

`tests/test_vision.py` — 8 tests, all passing against the real pipeline
(see docs/TESTING.md), covering: healthy detection, backend-down
detection, warning-state detection, both-services-down, missing-file
error handling, frame-diff change detection (nonzero for a real change,
exactly zero for identical images), and that `opencv_version` is always
populated from the live `cv2` import.
