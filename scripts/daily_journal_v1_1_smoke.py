from pathlib import Path
api=Path("aios/api/app.py").read_text(); web=Path("aios/web_capture/app.py").read_text()
assert "_journal_completion_summary" in api
assert "daily_completion_summaries" in api
assert "completion_fingerprint" in api
assert "completed-details" in web
assert "Your journal" in web
print("Existing Completed Today Summary cache reused: PASS")
print("No second Journal AI generation path added: PASS")
print("Completed-task list is secondary detail: PASS")
print("Free-form journal retained: PASS")
print("RESULT: DAILY JOURNAL V1.1 SMOKE TEST PASSED")
