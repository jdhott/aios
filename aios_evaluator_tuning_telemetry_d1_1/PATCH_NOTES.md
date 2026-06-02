# AIOS Evaluator Tuning Telemetry D1.1

Corrected read-only evaluator tuning telemetry package targeting the active runtime:

```text
run.sh → tools/aios_runtime_lock.py → run_aios_inner.sh → run_aios.py
```

Changes:
- Patches `execution_engine_v2.py` only.
- Adds compact read-only evaluator telemetry after in-memory ranking and before BNA persistence.
- Installs a root-level `smoke_test.sh` that checks the active runtime files only.
- Does not reference `run_aios_PHASE2_FIXED.py` in active package scripts.

Safety:
- No Notion schema changes.
- No ranking/scoring changes.
- No dashboard changes.
- No project cognition changes.
- No relation mutations.
