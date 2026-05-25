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

backup_dir = project / "backups" / f"metadata_reconciliation_phase2_5_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
backup_dir.mkdir(parents=True, exist_ok=True)

shutil.copy2(run_path, backup_dir / "run_aios.py.bak")
shutil.copy2(recon_path, backup_dir / "reconciliation.py.bak")

run_text = run_path.read_text()

# Remove existing late atexit reconciliation block.
atexit_block_pattern = re.compile(
    r"if not TEST_MODE:\n"
    r"    update_aios_dashboard\(\)# === AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP ===\n"
    r".*?"
    r"# === END AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP ===",
    re.DOTALL,
)

replacement_dashboard_block = """if not TEST_MODE:
    update_aios_dashboard()

# === AIOS METADATA RECONCILIATION PHASE 2.5 BOOTSTRAP ===
# Reconciliation no longer runs via atexit.
# It is invoked inline before run summary / notification / dashboard update.
print("[Metadata Reconciliation] Inline reconciliation active; atexit hook disabled")
# === END AIOS METADATA RECONCILIATION PHASE 2.5 BOOTSTRAP ==="""

if atexit_block_pattern.search(run_text):
    run_text = atexit_block_pattern.sub(replacement_dashboard_block, run_text)
else:
    standalone_pattern = re.compile(
        r"# === AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP ===\n"
        r".*?"
        r"# === END AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP ===",
        re.DOTALL,
    )
    if standalone_pattern.search(run_text):
        run_text = standalone_pattern.sub(
            "# === AIOS METADATA RECONCILIATION PHASE 2.5 BOOTSTRAP ===\n"
            "# Reconciliation no longer runs via atexit.\n"
            "# It is invoked inline before run summary / notification / dashboard update.\n"
            "print(\"[Metadata Reconciliation] Inline reconciliation active; atexit hook disabled\")\n"
            "# === END AIOS METADATA RECONCILIATION PHASE 2.5 BOOTSTRAP ===",
            run_text,
        )
    else:
        print("[Installer] No Phase 1 atexit bootstrap block found; continuing.")

inline_block = """
# === AIOS METADATA RECONCILIATION PHASE 2.5 INLINE RUN ===
# Run reconciliation before summary/notification/dashboard so Notion never sees
# a late post-notification clear/rewrite cycle.
if TEST_MODE:
    print("TEST_MODE is enabled → skipping metadata reconciliation inline pass.")
else:
    try:
        from core.metadata.reconciliation import emit_metadata_reconciliation_diagnostics
        print("=== METADATA RECONCILIATION — PHASE 2.5: INLINE PRE-SUMMARY PASS ===")
        emit_metadata_reconciliation_diagnostics(globals())
    except Exception as exc:
        print(f"[Metadata Reconciliation] Inline pass skipped: {exc}")
# === END AIOS METADATA RECONCILIATION PHASE 2.5 INLINE RUN ===

"""

if "PHASE 2.5: INLINE PRE-SUMMARY PASS" not in run_text:
    anchor = "print_run_summary()\nnotify_run_summary()"
    if anchor not in run_text:
        raise SystemExit("Could not find print_run_summary()/notify_run_summary() anchor in run_aios.py")
    run_text = run_text.replace(anchor, inline_block + anchor, 1)
else:
    print("[Installer] Inline reconciliation block already present.")

run_path.write_text(run_text)

# Patch reconciliation rank rewrite behavior.
recon_text = recon_path.read_text()

rank_block_pattern = re.compile(
    r"    if rank_actions:\n"
    r"        changed_count = sum\(1 for action in rank_actions if action.get\(\"changed\"\)\)\n"
    r"        print\(f\"\[Metadata Reconciliation\] Applying true execution rank rewrite: \{len\(rank_actions\)\} active rows; changed=\{changed_count\}\"\)\n"
    r"        print\(f\"\[Metadata Reconciliation\] Clearing existing Execution Rank values before canonical rewrite: \{len\(rank_actions\)\}\"\)\n"
    r"        for action in rank_actions\[:_MAX_EXAMPLES\]:\n"
    r"            print\(\n"
    r"                \"\[Metadata Reconciliation\] Canonical rank assignment preview: \"\n"
    r"                f\"new_rank=\{action.get\('new_rank'\)\} current_rank=\{action.get\('current_rank'\)\} \"\n"
    r"                f\"score=\{action.get\('score'\):g\} id=\{action.get\('short_id'\)\} title=\{action.get\('title'\)\}\"\n"
    r"            \)\n"
    r"        updated, errors = apply_execution_rank_canonicalization\(rank_actions\)\n"
    r"        print\(f\"\[Metadata Reconciliation\] Execution ranks rewritten canonically: \{updated\}\"\)\n"
    r"        if errors:\n"
    r"            print\(f\"\[Metadata Reconciliation\] True rank rewrite mutation errors: \{len\(errors\)\}\"\)\n"
    r"            for err in errors\[:_MAX_EXAMPLES\]:\n"
    r"                print\(f\"\[Metadata Reconciliation\] True rank rewrite mutation error detail: \{err\}\"\)\n"
    r"    else:\n"
    r"        print\(\"\\[Metadata Reconciliation\\] True execution rank rewrite: 0\"\)",
    re.DOTALL,
)

new_rank_block = """    if rank_actions:
        changed_count = sum(1 for action in rank_actions if action.get("changed"))
        print(f"[Metadata Reconciliation] Applying true execution rank rewrite: {len(rank_actions)} active rows; changed={changed_count}")
        for action in rank_actions[:_MAX_EXAMPLES]:
            print(
                "[Metadata Reconciliation] Canonical rank assignment preview: "
                f"new_rank={action.get('new_rank')} current_rank={action.get('current_rank')} "
                f"score={action.get('score'):g} id={action.get('short_id')} title={action.get('title')}"
            )
        if changed_count == 0:
            print("[Metadata Reconciliation] Execution rank rewrite skipped: canonical ranks already current")
        else:
            print(f"[Metadata Reconciliation] Clearing existing Execution Rank values before canonical rewrite: {len(rank_actions)}")
            updated, errors = apply_execution_rank_canonicalization(rank_actions)
            print(f"[Metadata Reconciliation] Execution ranks rewritten canonically: {updated}")
            if errors:
                print(f"[Metadata Reconciliation] True rank rewrite mutation errors: {len(errors)}")
                for err in errors[:_MAX_EXAMPLES]:
                    print(f"[Metadata Reconciliation] True rank rewrite mutation error detail: {err}")
    else:
        print("[Metadata Reconciliation] True execution rank rewrite: 0")"""

if "Execution rank rewrite skipped: canonical ranks already current" in recon_text:
    print("[Installer] No-op rank rewrite guard already present.")
else:
    new_recon_text, count = rank_block_pattern.subn(new_rank_block, recon_text, count=1)
    if count != 1:
        raise SystemExit("Could not patch rank rewrite block in reconciliation.py")
    recon_path.write_text(new_recon_text)

marker = project / ".metadata_reconciliation_phase2_5_last_backup"
marker.write_text(str(backup_dir))

print("Phase 2.5 installed successfully.")
print(f"Backup directory: {backup_dir}")
