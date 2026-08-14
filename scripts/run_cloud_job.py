#!/usr/bin/env python3
from __future__ import annotations
import runpy
from pathlib import Path
from aios.job.config import validate_job_environment
from aios.processing.trigger_coordinator import (
    ProcessingTriggerCoordinator,
)
from aios.storage.supabase_store import SupabaseStore

PROCESSOR_TRIGGER_JOB_LOOP_VERSION = "cloud-processor-trigger-v1"

def main():
    settings = validate_job_environment()
    print("=== AIOS CLOUD RUN JOB V1 ===")
    print("Environment:", settings.environment)
    print("Datastore:", settings.datastore)
    print("Inbox source:", settings.inbox_source)

    root = Path(__file__).resolve().parents[1]
    coordinator = ProcessingTriggerCoordinator(
        SupabaseStore()
    )

    if not coordinator.begin_processing():
        print(
            "[Processor Trigger] Another processor execution is active; "
            "this execution exits without running AIOS."
        )
        return

    cycle = 0

    try:
        while True:
            cycle += 1
            print(
                f"[Processor Trigger] Starting AIOS processing cycle {cycle}"
            )

            runpy.run_path(
                str(root / "run_aios.py"),
                run_name="__main__",
            )

            rerun_needed = coordinator.finish_cycle()

            if not rerun_needed:
                print(
                    "[Processor Trigger] Queue settled; processor lease released."
                )
                break

            print(
                "[Processor Trigger] New capture arrived during processing; "
                "running another cycle in the same Cloud Run Job."
            )

    except BaseException:
        coordinator.mark_failed()
        raise

if __name__ == "__main__":
    main()
