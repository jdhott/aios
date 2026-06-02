# AIOS Project Cognition D3.0 — Relation Label Resolution Hygiene

## Purpose

Fix `unresolved_relation:<id>` labels in Project Cognition ontology telemetry/reporting without changing cognition scoring,
execution authority, dashboard behavior, or Project relations.

## Diagnosis

`unresolved_relation:<id>` is a telemetry/name-resolution artifact. It can occur when a relation/project ID is present
but no readable project name is available at the moment the snapshot row is written or reported.

## What This Package Does

1. Installs:

```text
tools/repair_project_cognition_snapshot_labels.py
```

This repairs local snapshot rows when another row with the same `project_key` has a readable label.

2. Replaces:

```text
tools/ontology_stabilization_report.py
```

with an enhanced version that resolves unresolved relation labels in-memory before counting domains.

3. Patches:

```text
scripts/aios_project_affinity_report.py
```

to increase project-name resolution query limits from 100 to 500 when the exact pattern exists.

4. Runs a one-time snapshot label repair during install.

## Governance Boundaries

This package does not:

- mutate Project relations
- merge projects
- change evaluator scoring
- alter execution ranking
- affect dashboard generation
- change Suggested Project write gating

It only improves local telemetry readability and report quality.

## Rollback

Rollback restores:

- `tools/ontology_stabilization_report.py`
- `scripts/aios_project_affinity_report.py`

Snapshot repair backups remain in `logs/` as `.label_repair_bak_*`.
