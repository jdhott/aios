#!/bin/bash
set -euo pipefail
PROJECT_DIR="${1:-$HOME/LocalProjects/aios}"
python3 "$(dirname "$0")/install.py" "$PROJECT_DIR"
