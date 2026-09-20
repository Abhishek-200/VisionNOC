#!/usr/bin/env python3
"""Fail-fast environment check for a competition-ready VisionNOC checkout."""
import shutil
import subprocess
import sys

import cv2

print(f"Python: {sys.version.split()[0]}")
print(f"OpenCV: {cv2.__version__}")
if not cv2.__version__.startswith("5."):
    raise SystemExit("FAIL: VisionNOC requires OpenCV 5.x. Install requirements.txt in a networked environment.")
print("OpenCV 5: PASS")
print(f"Docker: {shutil.which('docker') or 'NOT FOUND'}")
print(f"AWS CLI: {shutil.which('aws') or 'NOT FOUND'}")
if shutil.which("docker"):
    subprocess.run(["docker", "compose", "version"], check=False)
