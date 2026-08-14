#!/usr/bin/env python3
from __future__ import annotations
import runpy
from pathlib import Path
from aios.job.config import validate_job_environment

def main():
    settings = validate_job_environment()
    print("=== AIOS CLOUD RUN JOB V1 ===")
    print("Environment:", settings.environment)
    print("Datastore:", settings.datastore)
    print("Inbox source:", settings.inbox_source)

    root = Path(__file__).resolve().parents[1]
    runpy.run_path(str(root / "run_aios.py"), run_name="__main__")

if __name__ == "__main__":
    main()
