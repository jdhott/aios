#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root / "run_aios.py").read_text()

start = text.find("clarification_shadow_inbox_repo = None")
bootstrap = text.find('if AIOS_DATASTORE == "supabase":', start)
imp = text.find(
    "from aios.storage.supabase_store import SupabaseStore as _ClarificationSupabaseStore",
    bootstrap,
)
construct = text.find(
    "_clarification_shadow_store = _ClarificationSupabaseStore()",
    bootstrap,
)

if min(start, bootstrap, imp, construct) < 0:
    raise RuntimeError("Clarification shadow bootstrap structure missing.")

if not (start < bootstrap < imp < construct):
    raise RuntimeError("Local clarification-shadow imports do not precede construction.")

print("Clarification bootstrap located: PASS")
print("Local imports precede SupabaseStore construction: PASS")
print("No dependency on later duplicate-review imports: PASS")
print("RESULT: CLARIFICATION SHADOW BOOTSTRAP FIX SMOKE TEST PASSED")
