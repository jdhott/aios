# AIOS Evaluator Tuning Telemetry D1.2.1

Purpose: add read-only per-BNA component breakdown telemetry.

This patch targets `execution_engine_v2.py` only.

It adds:

- `format_bna_component_breakdown(item)` helper
- evaluator component storage in ranked items
- a `components:` line after each Best Next Action printout
- a durable D1.2.1 marker so smoke tests do not depend on a separate aggregate telemetry header

Expected output:

```text
--- Best Next Actions ---
BNA rank=1 score=53 title=Send comments on wills to the lawyer
  components: high_priority=15; high_urgency=20; strategic_context=10
```

Governance:

- read-only observation
- no scoring changes
- no ranking changes
- no Notion mutations beyond the existing runtime behavior
- no execution authority impact
