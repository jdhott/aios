#!/usr/bin/env python3
from pathlib import Path
import re

path = Path("execution_engine_v2.py")
if not path.exists():
    raise SystemExit("execution_engine_v2.py not found. Run from AIOS project root.")

text = path.read_text(encoding="utf-8")

# Remove prior runtime analytics hooks so the summary is emitted exactly once.
for version in ("A1.0", "A1.1", "A1.2"):
    text = re.sub(
        rf"\n\s*# === AIOS Runtime Analytics {re.escape(version)} ===\n.*?\n\s*# === END AIOS Runtime Analytics {re.escape(version)} ===\n",
        "\n",
        text,
        flags=re.S,
    )

hook = '''

    # === AIOS Runtime Analytics A1.2 ===
    # Hardened read-only analytics ledger. Writes local CSV/JSON/NDJSON snapshots only.
    # No Notion mutations, no ranking changes, no authority impact.
    try:
        from core.runtime_analytics import write_runtime_analytics

        write_runtime_analytics(ranked, winners, run_label="execution_engine_v2")
    except Exception as e:
        print(f"[Runtime Analytics] write failed nonfatally: {e}")
    # === END AIOS Runtime Analytics A1.2 ===
'''

# Prefer placing analytics after D1.3 provenance output so the human-readable summary reads like a summary.
needle = "    emit_bna_metadata_provenance_audit(winners)\n"
if needle in text:
    text = text.replace(needle, needle + hook, 1)
else:
    fallback = "\n    updated = 0\n"
    if fallback not in text:
        raise SystemExit("Could not find insertion anchor for runtime analytics hook")
    text = text.replace(fallback, hook + fallback, 1)

path.write_text(text, encoding="utf-8")
print("Patched execution_engine_v2.py with AIOS Runtime Analytics A1.2 hook.")
