from pathlib import Path
import ast
api=Path("aios/api/app.py").read_text()
web=Path("aios/web_capture/app.py").read_text()
checks=[
("summary helper","def _journal_completion_summary(" in api),
("uses existing fingerprint","completion_fingerprint(completed_work)" in api),
("reads summary cache",'.table("daily_completion_summaries")' in api),
("excludes focus activation",'generated_source") != "focus_activation"' in api),
("summary API field",'"completion_summary": completion_summary' in api),
("summary state field",'"completion_summary_state": completion_summary_state' in api),
("summary UI","journal-summary-root" in web),
("journal poll api",'/api/journal/{journal_date}/day-panel' in web),
("completed work secondary",'class="completed-details"' in web),
("freeform retained","Anything worth remembering about today?" in web),
("autosave retained","setTimeout(save,700)" in web),
]
failed=False
for label,ok in checks:
    print(("PASS" if ok else "FAIL")+": "+label); failed|=not ok
ast.parse(api); ast.parse(web)
print("api parses: PASS"); print("web parses: PASS")
if failed: raise SystemExit("RESULT: DAILY JOURNAL V1.1 VALIDATION FAILED")
print("RESULT: DAILY JOURNAL V1.1 STRUCTURE VALID")
