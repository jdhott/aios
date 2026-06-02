#!/bin/bash
set -e
cd "$HOME/LocalProjects/aios"
exec ./venv/bin/python tools/aios_runtime_lock.py /bin/bash run_aios_inner.sh
