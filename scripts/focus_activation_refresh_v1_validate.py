from pathlib import Path

api = Path("aios/api/app.py").read_text()
refresh = Path("aios/focus_activation_refresh.py").read_text()
requirements = Path("requirements-api.txt").read_text()
deploy = Path("scripts/deploy_cloud_run_api.sh").read_text()

checks = [
    ("refresh module version", 'FOCUS_ACTIVATION_REFRESH_VERSION = "focus-activation-refresh-v1"' in refresh),
    ("api version marker", "AIOS_FOCUS_ACTIVATION_REFRESH_VERSION" in api),
    ("fast refresh helper", "def _refresh_focus_activation_after_action(" in api),
    ("complete schedules fast refresh", "focus_activation_refresh_scheduled" in api),
    ("not now uses fast refresh", '"/tasks/{task_id}/not-now"' in api and "_refresh_focus_activation_after_action" in api),
    ("context save uses fast refresh", 'regenerating_start_here": True' in api),
    ("openai in api requirements", "openai==" in requirements),
    ("openai secret on deploy", "OPENAI_API_KEY=aios-openai-api-key:latest" in deploy),
    ("undo-safe verify gate", "verify_completed_at" in api),
    ("processor fallback", "falling back to processor" in api),
]

for label, ok in checks:
    assert ok, f"FAIL: {label}"
    print(f"PASS: {label}")

print("RESULT: FOCUS ACTIVATION REFRESH V1 STRUCTURE VALID")
