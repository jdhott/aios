from pathlib import Path

api_path = Path("aios/api/app.py")
web_path = Path("aios/web_capture/app.py")

api = api_path.read_text()
web = web_path.read_text()

old = '.select("id,title")\n            .in_("id", parent_ids)'
new = '.select("id,title,due_at")\n            .in_("id", parent_ids)'
if old not in api:
    raise SystemExit("FAIL: parent metadata select marker not found")
api = api.replace(old, new, 1)

old = '''        parent_title_by_id = {
            str(parent.get("id")): str(parent.get("title") or "").strip()
            for parent in parent_rows
            if parent.get("id")
        }
    for row in rows:
        parent_id = str(row.get("parent_task_id") or "").strip()
        if parent_id:
            row["parent_title"] = parent_title_by_id.get(parent_id) or None
'''
new = '''        parent_meta_by_id = {
            str(parent.get("id")): {
                "title": str(parent.get("title") or "").strip(),
                "due_at": parent.get("due_at"),
            }
            for parent in parent_rows
            if parent.get("id")
        }
    else:
        parent_meta_by_id = {}

    for row in rows:
        parent_id = str(row.get("parent_task_id") or "").strip()
        if parent_id:
            parent_meta = parent_meta_by_id.get(parent_id) or {}
            row["parent_title"] = parent_meta.get("title") or None
            parent_due_at = parent_meta.get("due_at")
            if not row.get("due_at") and parent_due_at:
                row["effective_due_at"] = parent_due_at
                row["due_inherited_from_parent"] = True
            else:
                row["effective_due_at"] = row.get("due_at")
                row["due_inherited_from_parent"] = False
        else:
            row["effective_due_at"] = row.get("due_at")
            row["due_inherited_from_parent"] = False
'''
if old not in api:
    raise SystemExit("FAIL: parent title enrichment block not found")
api = api.replace(old, new, 1)

old = '''    def due_today(row: dict) -> bool:
        raw = row.get("due_at")
'''
new = '''    def due_today(row: dict) -> bool:
        raw = row.get("effective_due_at") or row.get("due_at")
'''
if old not in api:
    raise SystemExit("FAIL: due_today marker not found")
api = api.replace(old, new, 1)

old = '''        key=lambda row: (str(row.get("due_at") or "")[:10], *score_key(row)),
'''
new = '''        key=lambda row: (str(row.get("effective_due_at") or row.get("due_at") or "")[:10], *score_key(row)),
'''
if old not in api:
    raise SystemExit("FAIL: Today sort marker not found")
api = api.replace(old, new, 1)

old = '''        due_at = str(task.get("due_at") or "").strip()
'''
new = '''        due_at = str(task.get("effective_due_at") or task.get("due_at") or "").strip()
'''
if old not in web:
    raise SystemExit("FAIL: web due metadata marker not found")
web = web.replace(old, new, 1)

api_path.write_text(api)
web_path.write_text(web)
print("PASS: Breakdown Due-Date Inheritance v1 applied")
