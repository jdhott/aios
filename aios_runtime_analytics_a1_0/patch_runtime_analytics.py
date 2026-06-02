#!/usr/bin/env python3
from pathlib import Path

path = Path("execution_engine_v2.py")
if not path.exists():
    raise SystemExit("execution_engine_v2.py not found. Run from AIOS project root.")

text = path.read_text(encoding="utf-8")

if "AIOS Runtime Analytics A1.0" in text or "write_runtime_analytics(" in text:
    print("Runtime analytics hook already present; no patch needed.")
    raise SystemExit(0)

needle = "    emit_evaluator_tuning_telemetry(ranked, winners)\n"
insert = """    emit_evaluator_tuning_telemetry(ranked, winners)

    # === AIOS Runtime Analytics A1.0 ===
    # Read-only analytics ledger. Writes local CSV/JSON snapshots only.
    # No Notion mutations, no ranking changes, no authority impact.
    try:
        from core.runtime_analytics import write_runtime_analytics

        write_runtime_analytics(ranked, winners, run_label="execution_engine_v2")
    except Exception as e:
        print(f"[Runtime Analytics] write failed nonfatally: {e}")
    # === END AIOS Runtime Analytics A1.0 ===
"""

if needle not in text:
    raise SystemExit("Could not find evaluator telemetry hook in execution_engine_v2.py")

text = text.replace(needle, insert, 1)
path.write_text(text, encoding="utf-8")
print("Patched execution_engine_v2.py with AIOS Runtime Analytics A1.0 hook.")
