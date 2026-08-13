#!/bin/bash
set -e

echo "Running AIOS at $(date)"

cd "$HOME/LocalProjects/aios"

exec ./.venv/bin/python run_aios.py
