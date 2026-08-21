from pathlib import Path

s = Path("aios/web_capture/app.py").read_text()

checks = [
    ("BNA uses shared surface card", 'class="focus-card surface-card"' in s),
    ("BNA parent uses shared title row", 'class="task-title-row focus-parent-title-row"' in s),
    ("BNA parent completion tagged", 'class="complete-form focus-parent-complete"' in s),
    ("BNA subcontent uses shared task-sub alignment", 'class="task-sub focus-parent-sub"' in s),
    ("BNA action bar grouped below metadata", 'class="focus-action-bar"' in s),
    ("BNA compact action controls", '.focus-card .trash-button,' in s and 'width:32px;' in s),
    ("Start Here heading retained", '<div class="focus-start-heading">Start here</div>' in s),
    ("Start Here uses shared task row", '<div class="task-title-row">' in s),
    ("shared task sub indentation", 'padding-left:calc(var(--task-check) + var(--task-check-gap));' in s),
]

failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    failed = failed or not ok
if failed:
    raise SystemExit(1)
print("RESULT: MOBILE BNA ALIGNMENT V1 STRUCTURE VALID")
