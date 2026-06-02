# AIOS Evaluator Tuning Telemetry D1.2 — BNA Component Breakdown

## Goal

Expand evaluator tuning telemetry so each Best Next Action shows the scoring components that explain why it won.

## Change

Patches `execution_engine_v2.py` only.

Adds read-only per-BNA component output:

```text
BNA rank=3 score=50 title=Order a new band for my Apple Watch
  components: high_urgency=25; high_priority=25
```

Also carries evaluator component objects forward in the in-memory ranked item so the output can include component scores, not just reason names.

## Governance

- No ranking changes
- No evaluator weight changes
- No Notion schema changes
- No metadata mutations beyond existing execution persistence
- No project cognition changes
- No relation mutations
- Read-only observation only

## Rollback

Run:

```bash
bash aios_evaluator_tuning_telemetry_d1_2/rollback.sh
```
