from pathlib import Path

web = Path("aios/web_capture/app.py").read_text()
dashboard_js = web.split("def _page(")[1].split("</html>")[0]

checks = [
    ("version marker", 'WEB_DASHBOARD_ASYNC_V2A_VERSION = "dashboard-async-v2a"' in web),
    ("shared dashboard sync helper", "syncDashboardFragments" in web),
    ("undo uses fragment sync", "syncDashboardFragments({" in web and "undo-complete-optimistic" in web),
    ("undo no success reload", dashboard_js.count("window.location.reload()") == 1),
    ("undo retry toast", "showOptimisticErrorToast" in web and "Undo could not be saved." in web),
    ("focus poll timeout UI", "showFocusPollTimeout" in web and "focus-poll-timeout" in web),
    ("timeout retry button", "data-focus-poll-retry" in web),
    ("timeout no auto reload", "if (config.waitForFocusChange) {\n              window.location.reload();" not in web),
    ("restore re-inits focus card", "initFocusCard(state.focusCard)" in web),
    ("manual refresh escape hatch", "data-focus-poll-reload" in web),
]

failed = False
for label, ok in checks:
    print(f'{"PASS" if ok else "FAIL"}: {label}')
    failed |= not ok

if failed:
    raise SystemExit("RESULT: DASHBOARD ASYNC V2A VALIDATION FAILED")
print("RESULT: DASHBOARD ASYNC V2A VALIDATION PASSED")
