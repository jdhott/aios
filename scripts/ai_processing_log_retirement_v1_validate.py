#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
run = (ROOT / "run_aios.py").read_text()
engine = (ROOT / "execution_engine_v2.py").read_text()
analytics = (ROOT / "core/runtime_analytics.py").read_text()
config = (ROOT / "aios/job/config.py").read_text()
deploy = (ROOT / "scripts/deploy_cloud_run_job.sh").read_text()
audit = (ROOT / "core/storage/supabase_authority_audit.py").read_text()

checks = [
    ("Supabase AI log writes are bypassed", 'if AIOS_DATASTORE == "supabase":\n        return False' in run),
    ("execution provenance lookup performs no Notion query", 'def _query_ai_processing_log_for_title' in engine and 'return []' in engine[engine.index('def _query_ai_processing_log_for_title'):engine.index('def _parse_importance_from_reason')]),
    ("runtime analytics provenance lookup performs no Notion query", 'def _query_ai_processing_log_for_title' in analytics and 'return []' in analytics[analytics.index('def _query_ai_processing_log_for_title'):analytics.index('def _parse_importance_from_reason')]),
    ("job config no longer requires AI log DB", 'NOTION_AI_LOG_DATABASE_ID' not in config),
    ("deployment no longer requires AI log DB", 'NOTION_AI_LOG_DATABASE_ID' not in deploy),
    ("authority audit no longer allows AI log writes", 'allowed_logging' not in audit and '_ai_log_db' not in audit),
]
failed=[]
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    if not ok: failed.append(label)
if failed:
    print("RESULT: AI PROCESSING LOG RETIREMENT V1 VALIDATION FAILED")
    raise SystemExit(1)
print("RESULT: AI PROCESSING LOG RETIREMENT V1 STRUCTURE VALID")
