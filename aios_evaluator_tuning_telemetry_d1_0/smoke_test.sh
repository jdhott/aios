#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
cd "$ROOT"
python3 -m py_compile execution_engine_v2.py
python3 smoke_test_evaluator_tuning_telemetry.py
