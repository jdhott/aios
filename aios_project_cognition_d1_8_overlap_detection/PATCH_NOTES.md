# Patch Notes — D1.8 Overlapping Project Neighborhood Detection

## Added

- `detect_overlapping_neighborhoods(...)` in `core/project_cognition/historical_affinity.py`.
- Weighted neighborhood profile comparison using non-weak historical terms.
- Overlap risk classification: low / medium / high.
- Compact telemetry for likely duplicate or overlapping project concepts.
- JSON output now includes `overlapping_neighborhoods`.

## Preserved

- Read-only operation.
- Zero Notion writes.
- No execution authority impact.
- D1.7 active-task runner-up ambiguity telemetry.
- Strong-domain confidence and weak-term suppression.

## Safety

This patch only emits observational telemetry. It does not merge projects, link tasks, rename projects, or mutate Notion.
