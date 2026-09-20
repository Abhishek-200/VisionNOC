#!/usr/bin/env bash
# VisionNOC — scripts/simulate_incident.sh
# Thin wrapper around the Python demo (see demo/simulate_incident.py).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m demo.simulate_incident "$@"
