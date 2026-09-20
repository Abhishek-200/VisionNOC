"""
Real OpenCV preprocessing utilities used by detector.py.

Nothing in this file is simulated: every function here calls into
cv2/numpy and operates on actual pixel data loaded from disk or memory.
"""
from __future__ import annotations

import cv2
import numpy as np


def load_image(path: str) -> np.ndarray:
    """Load an image from disk as a BGR numpy array (OpenCV convention)."""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"OpenCV could not read image: {path}")
    return img


def to_hsv(img: np.ndarray) -> np.ndarray:
    """Convert a BGR image to HSV for robust color-based classification."""
    return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


def crop_normalized(img: np.ndarray, bbox: tuple) -> np.ndarray:
    """Crop `img` using a normalized (0-1) bounding box (x_min, y_min, x_max, y_max)."""
    h, w = img.shape[:2]
    x_min, y_min, x_max, y_max = bbox
    x1, y1 = int(x_min * w), int(y_min * h)
    x2, y2 = int(x_max * w), int(y_max * h)
    x1, x2 = max(0, x1), min(w, x2)
    y1, y2 = max(0, y1), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"Degenerate crop for bbox {bbox} on image of size {(w, h)}")
    return img[y1:y2, x1:x2]


def denoise(img: np.ndarray) -> np.ndarray:
    """Light Gaussian blur to reduce screenshot compression / render noise
    before color thresholding."""
    return cv2.GaussianBlur(img, (5, 5), 0)


def color_mask_fraction(hsv_roi: np.ndarray, lower: tuple, upper: tuple) -> float:
    """Return the fraction of pixels in `hsv_roi` that fall inside the
    given HSV range."""
    lower_arr = np.array(lower, dtype=np.uint8)
    upper_arr = np.array(upper, dtype=np.uint8)
    mask = cv2.inRange(hsv_roi, lower_arr, upper_arr)
    total = mask.shape[0] * mask.shape[1]
    if total == 0:
        return 0.0
    return float(cv2.countNonZero(mask)) / float(total)


def find_status_contours(roi_bgr: np.ndarray) -> list:
    """Run contour detection on a status-chip ROI. Used as corroborating
    structural evidence alongside color classification (e.g. to check a
    chip actually contains a solid filled shape rather than noise)."""
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return list(contours)


def frame_diff_score(img_a: np.ndarray, img_b: np.ndarray, threshold: int) -> float:
    """Compute the fraction of pixels that changed materially between two
    same-sized images. Used for before/after visual-recovery verification."""
    if img_a.shape != img_b.shape:
        img_b = cv2.resize(img_b, (img_a.shape[1], img_a.shape[0]))
    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(gray_a, gray_b)
    _, changed = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    total = changed.shape[0] * changed.shape[1]
    return float(cv2.countNonZero(changed)) / float(total) if total else 0.0
