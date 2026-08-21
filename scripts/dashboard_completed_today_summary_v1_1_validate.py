from pathlib import Path

run = Path("run_aios.py").read_text()
api = Path("aios/api/app.py").read_text()
web = Path("aios/web_capture/app.py").read_text()
helper = Path("aios/daily_completion_summary.py").read_text()

checks = [
    ("summary helper exists", "refresh_daily_completion_summary" in helper),
    ("processor refresh wired", "[Completed Today Summary]" in run),
    ("API exposes cached summary", '"completed_today_summary"' in api),
    ("web renders journal summary", "_journal_summary_html" in web and "completion_summary" in web),
    ("Notion archive runtime not reintroduced", "from aios.notion import archive as archive_helpers" not in run),
    ("legacy clarification runtime not reintroduced", "from aios import clarification as clarification_helpers" not in run),
    ("legacy duplicate UI not reintroduced", "from aios.notion import duplicate_review as duplicate_review_ui" not in run),
    ("hierarchy-aware subtask guidance retained", "Parent metadata supplies hierarchy context" in run),
]
failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + f": {label}")
    failed |= not ok
print("RESULT: " + ("COMPLETED TODAY SUMMARY V1.1 STRUCTURE VALID" if not failed else "COMPLETED TODAY SUMMARY V1.1 VALIDATION FAILED"))
raise SystemExit(1 if failed else 0)
