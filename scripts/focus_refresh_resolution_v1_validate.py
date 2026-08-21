from pathlib import Path

api = Path('aios/api/app.py').read_text()
web = Path('aios/web_capture/app.py').read_text()

checks = [
    ('activation history no longer implies pending', 'task["activation_pending"] = False\n            task["activation_history_exists"] = bool(activation_history)' in api),
    ('activation history exposed separately', 'task["activation_history_exists"] = True' in api),
    ('refresh state is bounded', 'maxAttempts' in web and 'aios-focus-activation-refresh-count' in web and 'url.searchParams.delete("refresh_focus")' in web),
    ('refresh resolves to focus card', '+ "#focus-card"' in web),
    ('start-here pending has spinner', '<span class="mini-spinner"></span> Finding your next step…' in web),
    ('stale starter suppressed after activation history', 'elif activation_pending or activation_history_exists:' in web),
    ('ordinary snooze stores exact scroll', 'document.querySelectorAll(".task-snooze-menu form")' in web and 'saveScroll();' in web),
    ('focus actions do not restore stale pixel position', 'if (form.closest(".focus-card"))' in web and 'sessionStorage.removeItem(scrollKey);' in web),
]

failed = False
for label, ok in checks:
    print(f'{"PASS" if ok else "FAIL"}: {label}')
    failed |= not ok

if failed:
    raise SystemExit('RESULT: FOCUS REFRESH RESOLUTION V1 STRUCTURE FAILED')
print('RESULT: FOCUS REFRESH RESOLUTION V1 STRUCTURE VALID')
