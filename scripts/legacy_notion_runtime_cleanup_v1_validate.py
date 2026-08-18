from pathlib import Path
root = Path(__file__).resolve().parents[1]
run = (root/'run_aios.py').read_text()
notion_source = (root/'aios/ingestion/notion_source.py').read_text()
checks = [
    ('processor rejects Notion datastore', 'AIOS_DATASTORE != "supabase"' in run and 'supports AIOS_DATASTORE=supabase only' in run),
    ('Supabase is default inbox', 'os.getenv("AIOS_INBOX_SOURCE", "supabase")' in run),
    ('legacy clarification import removed', 'from aios import clarification as clarification_helpers' not in run),
    ('legacy duplicate UI import removed', 'from aios.notion import duplicate_review' not in run),
    ('legacy archive module import removed', 'from aios.notion import archive' not in run),
    ('Notion dashboard execution removed', 'if not TEST_MODE and AIOS_DATASTORE == "notion"' not in run),
    ('source cleanup is adapter-owned', 'Notion inbox source cleanup failed' in notion_source),
    ('legacy duplicate module deleted', not (root/'aios/notion/duplicate_review.py').exists()),
    ('legacy archive module deleted', not (root/'aios/notion/archive.py').exists()),
    ('legacy clarification module deleted', not (root/'aios/clarification.py').exists()),
    ('legacy mirror writer deleted', not (root/'aios/storage/notion_task_mirror_writer.py').exists()),
    ('historical identity retained', 'legacy_notion_id' in (root/'aios/models.py').read_text()),
]
failed=[]
for name,ok in checks:
    print(('PASS' if ok else 'FAIL')+': '+name)
    if not ok: failed.append(name)
if failed: raise SystemExit('RESULT: LEGACY NOTION RUNTIME CLEANUP V1 VALIDATION FAILED')
print('RESULT: LEGACY NOTION RUNTIME CLEANUP V1 STRUCTURE VALID')
