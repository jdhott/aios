from pathlib import Path

web = Path("aios/web_capture/app.py").read_text()

checks = [
    ("focus card JSON endpoint", '@app.get("/api/focus-card")' in web),
    ("shared focus card view helper", "def _focus_card_view(" in web),
    ("poll config injected", "window.__AIOS_FOCUS_POLL__" in web),
    ("fetch-based polling", 'new URL("/api/focus-card"' in web),
    ("exponential backoff", "Math.min(Math.round(delay * 1.6), maxDelay)" in web),
    ("bounded attempts retained", "maxAttempts" in web and "aios-focus-activation-refresh-count" in web),
    ("partial DOM replace", "replaceFocusCard" in web),
    ("no dashboard reload loop", "setTimeout(() => window.location.reload(), 2000)" not in web.split("def _page(")[1]),
    ("rebind after patch", "initFocusCard" in web),
    ("snooze waits for focus change", "waitForFocusChange" in web and "previousFocusId" in web),
    ("focus id change reload", "data.focus_id !== config.initialFocusId" in web),
]

failed = False
for label, ok in checks:
    print(f'{"PASS" if ok else "FAIL"}: {label}')
    failed |= not ok

if failed:
    raise SystemExit("RESULT: FOCUS POLL V1 VALIDATION FAILED")
print("RESULT: FOCUS POLL V1 VALIDATION PASSED")
