from pathlib import Path

web = Path("aios/web_capture/app.py").read_text()

checks = [
    ("version marker", 'WEB_PENDING_FRAGMENT_POLL_VERSION = "pending-fragment-poll-v2b"' in web),
    ("shared fragment poll helper", "def _fragment_poll_script(" in web),
    ("shared fragment poll client", "__AIOS_FRAGMENT_POLL__" in web),
    ("breakdown panel helper", "def _breakdown_panel_view(" in web),
    ("breakdown panel endpoint", '@app.get("/api/tasks/{task_id}/breakdown-panel")' in web),
    ("breakdown no reload loop", "Building proposed breakdown" in web and "setTimeout(function(){ window.location.reload(); }, 2500)" not in web),
    ("breakdown init hook", "aiosInitBreakdownPanel" in web),
    ("project work results helper", "def _project_work_results_view(" in web),
    ("project work results endpoint", '@app.get("/api/projects/{project_id}/work-results")' in web),
    ("project no reload loop", "aios-project-proposal-refresh-count" not in web or "setTimeout(() => window.location.reload(), 2000)" not in web.split("def _project_detail_page")[1].split("def _possible_duplicate_new_task_page")[0]),
    ("reviews cards helper", "def _build_review_cards(" in web),
    ("reviews enrich helper", "def _enrich_duplicate_reviews(" in web),
    ("reviews list endpoint", '@app.get("/api/reviews/list")' in web),
    ("reviews no reload loop", "setTimeout(() => window.location.reload(), 2000)" not in web.split("def _reviews_page")[1].split("def _fetch_reviews")[0]),
    ("fragment timeout retry UI", "data-fragment-poll-retry" in web),
    ("exponential backoff", "Math.min(Math.round(delay * 1.6), maxDelay)" in web and "_FRAGMENT_POLL_CLIENT_JS" in web),
]

failed = False
for label, ok in checks:
    print(f'{"PASS" if ok else "FAIL"}: {label}')
    failed |= not ok

if failed:
    raise SystemExit("RESULT: PENDING FRAGMENT POLL V2B VALIDATION FAILED")
print("RESULT: PENDING FRAGMENT POLL V2B VALIDATION PASSED")
