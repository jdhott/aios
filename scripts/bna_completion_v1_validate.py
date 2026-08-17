from pathlib import Path

web = Path("aios/web_capture/app.py").read_text()
api = Path("aios/api/app.py").read_text()
activation = Path("aios/focus_activation.py").read_text()

checks = [
    ("BNA parent completion control", 'focus-parent-complete' in web and 'Complete Best Next Action' in web),
    ("normal completion endpoint reused", 'action="/tasks/{safe_id}/complete"' in web),
    ("activation cleanup helper", 'def complete_open_focus_activation_children(' in activation),
    ("cleanup limited to generated activation children", '.eq("generated_source", FOCUS_ACTIVATION_SOURCE)' in activation),
    ("children preserved as completed history", '"is_done": True' in activation and '"is_open": False' in activation),
    ("parent completion invokes cleanup", 'complete_open_focus_activation_children(' in api),
    ("completion timestamp persisted", '"completed_at": completed_at' in api),
]

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)

if not all(ok for _, ok in checks):
    raise SystemExit(1)

print("RESULT: BNA COMPLETION V1 STRUCTURE VALID")
