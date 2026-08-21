from pathlib import Path

api = Path("aios/api/app.py").read_text()
refresh = Path("aios/focus_activation_refresh.py").read_text()
context = Path("aios/focus_context_refresh.py").read_text()
dashboard = Path("aios/dashboard_focus.py").read_text()
requirements = Path("requirements-api.txt").read_text()
deploy = Path("scripts/deploy_cloud_run_api.sh").read_text()

checks = [
    ("refresh module version", 'FOCUS_ACTIVATION_REFRESH_VERSION = "focus-activation-refresh-v2"' in refresh),
    ("context refresh module", 'FOCUS_CONTEXT_REFRESH_VERSION = "focus-context-refresh-v1"' in context),
    ("dashboard focus resolver", "def resolve_dashboard_focus_task(" in dashboard),
    ("dashboard focus fast path", "def _refresh_dashboard_focus_after_action(" in api),
    ("context fast path", "def _refresh_focus_context_after_action(" in api),
    ("api version marker", "AIOS_FOCUS_ACTIVATION_REFRESH_VERSION" in api),
    ("context version marker", "AIOS_FOCUS_CONTEXT_REFRESH_VERSION" in api),
    ("fast refresh helper", "def _refresh_focus_activation_after_action(" in api),
    ("complete schedules fast refresh", "focus_activation_refresh_scheduled" in api),
    ("BNA complete skips processor", "was_dashboard_focus" in api),
    ("activation complete skips processor", "activation_parent_id" in api),
    ("not now uses fast refresh", "_refresh_focus_activation_after_action" in api),
    ("not useful uses context refresh", "_refresh_focus_context_after_action" in api),
    ("context help uses fast refresh", 'focus_context_help_state": "pending"' in api),
    ("context answer uses fast refresh", 'focus_context_help_state": "answer_pending"' in api),
    ("snooze uses dashboard focus refresh", "_refresh_dashboard_focus_after_action" in api),
    ("context save uses fast refresh", 'regenerating_start_here": True' in api),
    ("completion summary on BNA complete", "refresh_summary=True" in api),
    ("openai in api requirements", "openai==" in requirements),
    ("openai secret on deploy", "OPENAI_API_KEY=aios-openai-api-key:latest" in deploy),
    ("undo-safe verify gate", "verify_completed_at" in api),
    ("processor fallback", "falling back to processor" in api),
]

for label, ok in checks:
    assert ok, f"FAIL: {label}"
    print(f"PASS: {label}")

print("RESULT: FOCUS ACTIVATION REFRESH V1 STRUCTURE VALID")
