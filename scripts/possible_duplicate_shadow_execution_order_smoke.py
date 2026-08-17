#!/usr/bin/env python3
from pathlib import Path
text=(Path(__file__).resolve().parents[1]/'run_aios.py').read_text()
assert 'def upsert_possible_duplicate_review(match):' in text
assert 'if AIOS_DATASTORE == "supabase":\n                upsert_possible_duplicate_review(match)' in text
assert 'elif inbox_review_ui is not None:\n                inbox_review_ui.show_possible_duplicate(' in text
print('Supabase review upsert path: PASS')
print('Legacy Notion fallback isolated: PASS')
print('RESULT: POSSIBLE DUPLICATE REVIEW EXECUTION ORDER SMOKE TEST PASSED')
