#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import re
import shutil
import sys

project = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "LocalProjects/aios"
run_path = project / "run_aios.py"
recon_path = project / "core" / "metadata" / "reconciliation.py"

if not run_path.exists():
    raise SystemExit(f"Missing run_aios.py: {run_path}")
if not recon_path.exists():
    raise SystemExit(f"Missing reconciliation.py: {recon_path}")

backup_dir = project / "backups" / f"metadata_reconciliation_phase2_5_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
backup_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(run_path, backup_dir / "run_aios.py.bak")
shutil.copy2(recon_path, backup_dir / "reconciliation.py.bak")

# -----------------------
# Patch run_aios.py
# -----------------------
run_text = run_path.read_text()

# Normalize the glued dashboard/bootstrap line if present.
run_text = run_text.replace(
    "if not TEST_MODE:\n    update_aios_dashboard()# === AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP ===",
    "if not TEST_MODE:\n    update_aios_dashboard()\n\n# === AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP ===",
)

bootstrap_re = re.compile(
    r"\n?# === AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP ===\n"
    r".*?"
    r"# === END AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP ===\n?",
    re.DOTALL,
)

bootstrap_replacement = (
    "\n# === AIOS METADATA RECONCILIATION PHASE 2.5 BOOTSTRAP ===\n"
    "# Reconciliation no longer runs via atexit.\n"
    "# It is invoked inline before run summary / notification / dashboard update.\n"
    "print(\"[Metadata Reconciliation] Inline reconciliation active; atexit hook disabled\")\n"
    "# === END AIOS METADATA RECONCILIATION PHASE 2.5 BOOTSTRAP ===\n"
)

if bootstrap_re.search(run_text):
    run_text = bootstrap_re.sub(bootstrap_replacement, run_text, count=1)
else:
    print("[Installer] No Phase 1 atexit bootstrap found. Continuing.")

inline_block = (
    "\n# === AIOS METADATA RECONCILIATION PHASE 2.5 INLINE RUN ===\n"
    "# Run reconciliation before summary/notification/dashboard so Notion never sees\n"
    "# a late post-notification clear/rewrite cycle.\n"
    "if TEST_MODE:\n"
    "    print(\"TEST_MODE is enabled → skipping metadata reconciliation inline pass.\")\n"
    "else:\n"
    "    try:\n"
    "        from core.metadata.reconciliation import emit_metadata_reconciliation_diagnostics\n"
    "        print(\"=== METADATA RECONCILIATION — PHASE 2.5: INLINE PRE-SUMMARY PASS ===\")\n"
    "        emit_metadata_reconciliation_diagnostics(globals())\n"
    "    except Exception as exc:\n"
    "        print(f\"[Metadata Reconciliation] Inline pass skipped: {exc}\")\n"
    "# === END AIOS METADATA RECONCILIATION PHASE 2.5 INLINE RUN ===\n\n"
)

if "PHASE 2.5: INLINE PRE-SUMMARY PASS" not in run_text:
    anchor = "print_run_summary()\nnotify_run_summary()"
    if anchor not in run_text:
        raise SystemExit("Could not find print_run_summary()/notify_run_summary() anchor")
    run_text = run_text.replace(anchor, inline_block + anchor, 1)
else:
    print("[Installer] Inline block already present.")

run_path.write_text(run_text)

# -----------------------
# Patch reconciliation.py
# -----------------------
recon_lines = recon_path.read_text().splitlines()

if any("Execution rank rewrite skipped: canonical ranks already current" in line for line in recon_lines):
    print("[Installer] No-op rank rewrite guard already present.")
else:
    clear_idx = None
    for i, line in enumerate(recon_lines):
        if "Clearing existing Execution Rank values before canonical rewrite" in line:
            clear_idx = i
            break

    if clear_idx is None:
        raise SystemExit("Could not find rank clearing line in reconciliation.py")

    # Find the end of the rank_actions branch: the next 4-space indented else after clear_idx.
    end_idx = None
    for j in range(clear_idx + 1, len(recon_lines)):
        if recon_lines[j] == "    else:":
            # Verify this is the else paired with if rank_actions by looking ahead.
            if j + 1 < len(recon_lines) and "True execution rank rewrite: 0" in recon_lines[j + 1]:
                end_idx = j
                break

    if end_idx is None:
        raise SystemExit("Could not find end of rank_actions branch in reconciliation.py")

    old_mutation_block = recon_lines[clear_idx:end_idx]
    indented_old = ["        else:"] + ["    " + line for line in old_mutation_block]

    new_guard_block = [
        "        if changed_count == 0:",
        "            print(\"[Metadata Reconciliation] Execution rank rewrite skipped: canonical ranks already current\")",
    ] + indented_old

    recon_lines = recon_lines[:clear_idx] + new_guard_block + recon_lines[end_idx:]
    recon_path.write_text("\n".join(recon_lines) + "\n")

marker = project / ".metadata_reconciliation_phase2_5_fixed_last_backup"
marker.write_text(str(backup_dir))

print("Phase 2.5 fixed install complete.")
print(f"Backup directory: {backup_dir}")
