# AIOS Metadata Provenance Audit D1.3

## Purpose

Adds read-only BNA metadata provenance telemetry using the existing AI Processing Log.

## What changes

Patches `execution_engine_v2.py` to add a new telemetry section after Best Next Actions:

```text
--- BNA Metadata Provenance Audit D1.3 ---
BNA provenance rank=1 title=Send comments on wills to the lawyer
  Priority/Importance: current=High Priority; provenance=ai_log_metadata; source=explicit_marker; confidence=1.00
  Urgency: current=High Urgency; provenance=explicit_marker_from_original; source=explicit_marker; confidence=1.00
  ai_log_matches=2
[BNA Provenance] authority_impact=none; mutations=0; mode=read_only_observation
```

## Governance

- Read-only observation only
- No evaluator weight changes
- No execution score/rank changes
- No Notion task mutations
- No AI Processing Log writes
- Nonfatal if AI log lookup is unavailable

## Notes

The current AI Processing Log records `Importance` provenance, while the evaluator component is named `high_priority`. D1.3 reports this as `Priority/Importance` to preserve that distinction.

Urgency is inferred from Created log rows when the original Brain Dump text contains explicit markers such as `urgent` or `asap`. If no evidence is found, the audit reports `manual_or_unknown`.
