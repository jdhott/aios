# AIOS Runtime Analytics A1.0

Purpose:
- Consolidate execution/evaluator telemetry into a local analytics ledger.
- Create one CSV row per run and a latest JSON snapshot.
- Print a compact end-of-run analytics summary.

Files added:
- core/runtime_analytics.py

Files patched:
- execution_engine_v2.py

Outputs:
- logs/runtime_analytics.csv
- logs/runtime_analytics_latest.json
- "=== AIOS RUNTIME ANALYTICS SUMMARY A1.0 ===" in standard run logs

Governance:
- Read-only local file writes only.
- No Notion mutations.
- No ranking changes.
- No evaluator weight changes.
- No metadata changes.
- authority_impact=none; mutations=0

A1.0 focuses on canonical execution/evaluator runtime data available in memory:
ranked pool, BNA winners, score bands, scoring sources, signal distribution,
BNA signal distribution, low-signal BNA count, and BNA titles/details.
