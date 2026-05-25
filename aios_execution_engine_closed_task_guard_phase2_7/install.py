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

backup_dir = project / "backups" / f"execution_engine_closed_task_guard_phase2_7_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
backup_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(target, backup_dir / "execution_engine_v2.py.bak")

text = target.read_text()

helper = '\ndef get_checkbox_value(task, property_name):\n    props = task.get("properties", {}) or {}\n    return safe_nested_get(props, property_name, "checkbox") is True\n\n\ndef get_select_name(task, property_name):\n    props = task.get("properties", {}) or {}\n    return safe_nested_get(props, property_name, "select", "name")\n\n\ndef is_closed_or_done_task(task):\n    """Return True when a task is closed/done and must not receive execution ranks."""\n    props = task.get("properties", {}) or {}\n\n    if safe_nested_get(props, "Done", "checkbox") is True:\n        return True\n\n    if safe_nested_get(props, "Closed", "checkbox") is True:\n        return True\n\n    for property_name in ("Status", "Task Status", "State"):\n        status = safe_nested_get(props, property_name, "status", "name")\n        if status and str(status).strip().lower() in {\n            "done", "complete", "completed", "closed", "archived", "cancelled", "canceled"\n        }:\n            return True\n\n        select_value = safe_nested_get(props, property_name, "select", "name")\n        if select_value and str(select_value).strip().lower() in {\n            "done", "complete", "completed", "closed", "archived", "cancelled", "canceled"\n        }:\n            return True\n\n    return False\n\n\n'
old_active = 'def get_execution_active_tasks(open_tasks):\n    return [\n        task for task in open_tasks\n        if is_execution_active(task)\n    ]\n'
new_active = 'def get_execution_active_tasks(open_tasks):\n    active = []\n    excluded_closed = 0\n\n    for task in open_tasks:\n        if is_closed_or_done_task(task):\n            if is_execution_active(task):\n                excluded_closed += 1\n            continue\n\n        if is_execution_active(task):\n            active.append(task)\n\n    print(f"[Execution Engine V2] Closed/done tasks excluded from sparse reset: {excluded_closed}")\n    return active\n'
old_diag = '    diagnostics = {\n        "total_open_tasks": len(open_tasks),\n        "rejected_deferred": 0,\n        "rejected_jdi": 0,\n        "included_quick_win": 0,\n        "rejected_non_actionable": 0,\n        "eligible": 0,\n    }\n'
new_diag = '    diagnostics = {\n        "total_open_tasks": len(open_tasks),\n        "rejected_closed_or_done": 0,\n        "rejected_deferred": 0,\n        "rejected_jdi": 0,\n        "included_quick_win": 0,\n        "rejected_non_actionable": 0,\n        "eligible": 0,\n    }\n'
old_loop = '    for task in open_tasks:\n        if is_deferred_until_future(task):\n            diagnostics["rejected_deferred"] += 1\n            continue\n'
new_loop = '    for task in open_tasks:\n        if is_closed_or_done_task(task):\n            diagnostics["rejected_closed_or_done"] += 1\n            continue\n\n        if is_deferred_until_future(task):\n            diagnostics["rejected_deferred"] += 1\n            continue\n'
old_prints = '    print("\\\\n--- Execution Eligibility Scan ---")\n    print(f"Total open tasks: {diagnostics[\'total_open_tasks\']}")\n    print(f"Rejected deferred: {diagnostics[\'rejected_deferred\']}")\n'
new_prints = '    print("\\\\n--- Execution Eligibility Scan ---")\n    print(f"Total open tasks: {diagnostics[\'total_open_tasks\']}")\n    print(f"Rejected closed/done: {diagnostics[\'rejected_closed_or_done\']}")\n    print(f"[Execution Engine V2] Closed/done tasks excluded before ranking: {diagnostics[\'rejected_closed_or_done\']}")\n    print(f"Rejected deferred: {diagnostics[\'rejected_deferred\']}")\n'
old_append = '            ranked.append({\n                "task": task,\n                "title": title,\n                "score": score,\n'
new_append = '            if is_closed_or_done_task(task):\n                print(\n                    "[Execution Engine V2] Skipping closed/done task before ranking append: "\n                    f"{title}"\n                )\n                continue\n\n            ranked.append({\n                "task": task,\n                "title": title,\n                "score": score,\n'
old_persist_loop = '    for rank_position, item in enumerate(persisted_ranked, start=1):\n        try:\n            task = item["task"]\n            task_id = task["id"]\n'
new_persist_loop = '    for rank_position, item in enumerate(persisted_ranked, start=1):\n        try:\n            task = item["task"]\n\n            if is_closed_or_done_task(task):\n                print(\n                    "[Execution Engine V2] ERROR: closed/done task reached persistence; skipped: "\n                    f"rank={rank_position} title={item.get(\'title\')}"\n                )\n                continue\n\n            task_id = task["id"]\n'

if "def is_closed_or_done_task(task):" not in text:
    marker = "def is_deferred_until_future(task, today=None):"
    if marker not in text:
        raise SystemExit("Could not find insertion point before is_deferred_until_future")
    text = text.replace(marker, helper + marker, 1)
else:
    print("[Installer] Closed/done helper already present.")

if "Closed/done tasks excluded from sparse reset" not in text:
    if old_active not in text:
        raise SystemExit("Could not patch get_execution_active_tasks")
    text = text.replace(old_active, new_active, 1)
else:
    print("[Installer] Sparse reset guard already present.")

if '"rejected_closed_or_done"' not in text:
    if old_diag not in text:
        raise SystemExit("Could not patch eligibility diagnostics")
    text = text.replace(old_diag, new_diag, 1)

if 'diagnostics["rejected_closed_or_done"] += 1' not in text:
    if old_loop not in text:
        raise SystemExit("Could not patch eligibility loop")
    text = text.replace(old_loop, new_loop, 1)

if "Closed/done tasks excluded before ranking" not in text:
    if old_prints not in text:
        raise SystemExit("Could not patch eligibility logging")
    text = text.replace(old_prints, new_prints, 1)

if "Skipping closed/done task before ranking append" not in text:
    if old_append not in text:
        raise SystemExit("Could not patch ranked.append defensive guard")
    text = text.replace(old_append, new_append, 1)

if "closed/done task reached persistence" not in text:
    if old_persist_loop not in text:
        raise SystemExit("Could not patch persistence defensive guard")
    text = text.replace(old_persist_loop, new_persist_loop, 1)

target.write_text(text)

marker = project / ".execution_engine_closed_task_guard_phase2_7_last_backup"
marker.write_text(str(backup_dir))

print("Phase 2.7 installed successfully.")
print(f"Backup directory: {backup_dir}")
