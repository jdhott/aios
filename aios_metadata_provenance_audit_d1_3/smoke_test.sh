#!/usr/bin/env bash
set -euo pipefail
cd "$(pwd)"
python3 -m py_compile execution_engine_v2.py
grep -q "BNA Metadata Provenance Audit D1.3" execution_engine_v2.py
grep -q "emit_bna_metadata_provenance_audit(winners)" execution_engine_v2.py
grep -q "NOTION_AI_LOG_DATABASE_ID" execution_engine_v2.py
echo "Smoke test passed: Metadata Provenance Audit D1.3 installed"
