#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil
import sys

project = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / "LocalProjects/aios"
target = project / "execution_engine_v2.py"

if not target.exists():
    raise SystemExit(f"Missing execution_engine_v2.py: {target}")

backup_dir = project / "backups" / f"execution_engine_rank_authority_phase2_6_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
backup_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(target, backup_dir / "execution_engine_v2.py.bak")

text = target.read_text()

old_sort = '    ranked.sort(\n        key=lambda x: x["score"],\n        reverse=True,\n    )\n'
new_sort = '    def _canonical_execution_rank_key(item):\n        # Deterministic rank ordering owned by Execution Engine V2.\n        # Execution authority must not depend on API/list iteration order.\n        # Ties are resolved by normalized task title, then stable Notion page id.\n        title_key = str(item.get("title") or "").strip().casefold()\n        page_id = str((item.get("task") or {}).get("id") or "")\n        score = item.get("score") or 0\n        return (-score, title_key, page_id)\n\n    ranked.sort(key=_canonical_execution_rank_key)\n\n    print(\n        "[Execution Engine V2] Canonical rank ordering active: "\n        "score desc, title asc, page_id asc"\n    )\n'
old_persisted = '    persisted_ranked = ranked[:PERSISTED_EXECUTION_RANK_LIMIT]\n\n    for rank_position, item in enumerate(persisted_ranked, start=1):\n'
new_persisted = '    persisted_ranked = ranked[:PERSISTED_EXECUTION_RANK_LIMIT]\n\n    print("\\n--- Execution Engine V2 Canonical Persistence Plan ---")\n    for rank_position, item in enumerate(persisted_ranked[:15], start=1):\n        task = item.get("task") or {}\n        short_id = str(task.get("id") or "")[:8]\n        print(\n            "[Execution Engine V2] Canonical persistence row: "\n            f"rank={rank_position} score={item.get(\'score\')} "\n            f"id={short_id} title={item.get(\'title\')}"\n        )\n\n    for rank_position, item in enumerate(persisted_ranked, start=1):\n'
old_update = '            success = safe_update_task(\n                update_fn=update_fn,\n                task_id=task_id,\n                properties=properties,\n            )\n'
new_update = '            print(\n                "[Execution Engine V2] Write payload: "\n                f"rank={rank_position} score={item[\'score\']} "\n                f"id={str(task_id)[:8]} title={item[\'title\']}"\n            )\n\n            success = safe_update_task(\n                update_fn=update_fn,\n                task_id=task_id,\n                properties=properties,\n            )\n'

if "Canonical rank ordering active: score desc, title asc, page_id asc" in text:
    print("[Installer] Deterministic sort already installed.")
elif old_sort in text:
    text = text.replace(old_sort, new_sort, 1)
else:
    raise SystemExit("Could not find score-only ranked.sort block in execution_engine_v2.py")

if "Canonical persistence row:" in text:
    print("[Installer] Canonical persistence preview already installed.")
elif old_persisted in text:
    text = text.replace(old_persisted, new_persisted, 1)
else:
    raise SystemExit("Could not find persisted_ranked block in execution_engine_v2.py")

if "[Execution Engine V2] Write payload:" in text:
    print("[Installer] Write payload logging already installed.")
elif old_update in text:
    text = text.replace(old_update, new_update, 1)
else:
    raise SystemExit("Could not find execution rank update call in execution_engine_v2.py")

target.write_text(text)

marker = project / ".execution_engine_rank_authority_phase2_6_last_backup"
marker.write_text(str(backup_dir))

print("Phase 2.6 installed successfully.")
print(f"Backup directory: {backup_dir}")
