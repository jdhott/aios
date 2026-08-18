from pathlib import Path

root = Path(__file__).resolve().parents[1]
run = (root / "run_aios.py").read_text()
api = (root / "aios/api/app.py").read_text()
web = (root / "aios/web_capture/app.py").read_text()
writer = (root / "aios/storage/task_creation_writer.py").read_text()
migration = (root / "migrations/20260818_manual_breakdown_proposal_v1.sql").read_text()

checks = [
    ("automatic broad verbs are uncertain, not automatic yes", 'if is_process_task(task_text) and word_count >= 2:\n        return "uncertain"' in run),
    ("automatic AI requires domain confidence", "reasonable confidence in the task domain" in run),
    ("automatic AI is conservative", "When uncertain, return no" in run),
    ("subtask generator prefers smallest useful set", "smallest useful set of 2–5" in run),
    ("manual guidance reaches generator", 'manual_context=""' in run and "Optional user guidance" in run),
    ("processor handles pending manual breakdown requests", "process_manual_breakdown_requests" in run),
    ("manual proposal never creates children in processor", '"breakdown_state": state' in run),
    ("API exposes request endpoint", '/breakdown/request' in api),
    ("API exposes accept endpoint", '/breakdown/accept' in api),
    ("API exposes cancel endpoint", '/breakdown/cancel' in api),
    ("existing parent child creator exists", "create_children_for_existing_parent" in writer),
    ("accept requires at least two tasks", "Keep at least two breakdown tasks" in api),
    ("Task Detail asks for optional guidance", "Anything AIOS should know?" in web),
    ("proposal is editable before acceptance", "breakdown-editor" in web and "Accept Breakdown" in web),
    ("proposal supports cancel", "Cancel" in web and '/breakdown/cancel' in web),
    ("migration stores proposal workflow", "breakdown_proposal jsonb" in migration and "breakdown_request_context text" in migration),
]

failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    failed |= not ok

if failed:
    print("RESULT: MANUAL BREAKDOWN PROPOSAL V1 STRUCTURE VALIDATION FAILED")
    raise SystemExit(1)
print("RESULT: MANUAL BREAKDOWN PROPOSAL V1 STRUCTURE VALID")
