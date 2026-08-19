#!/usr/bin/env python3

import subprocess
import sys

modules = [
    # Duplicate authority and behaviour
    "scripts.possible_duplicate_review_authority_smoke",
    "scripts.possible_duplicate_keep_separate_v2_smoke",
    "scripts.possible_duplicate_reevaluation_auto_merge_v1_smoke",
    "scripts.possible_duplicate_reevaluation_distinct_v1_smoke",
    "scripts.possible_duplicate_title_choice_v1_smoke",

    # Clarification state/creation behaviour
    "scripts.clarification_review_state_transitions_smoke",
    "scripts.supabase_clarification_creation_smoke",
]

for module in modules:
    print(f"\n=== {module} ===")
    result = subprocess.run(
        [sys.executable, "-m", module],
        check=False,
    )
    if result.returncode:
        raise SystemExit(
            f"RESULT: REVIEW PARITY SMOKE FAILED: {module}"
        )

print()
print("RESULT: REVIEW PARITY SMOKE PASSED")
