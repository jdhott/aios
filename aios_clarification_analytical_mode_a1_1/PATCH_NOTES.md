# AIOS Clarification Analytical Mode A1.1

## Purpose
Improves clarification option generation for analytical / audit-style tasks so AIOS proposes outcome-producing first steps rather than tool-centric prerequisites.

## Changes
- Adds `CLARIFICATION_ANALYTICAL_MODE_VERSION = clarification-analytical-mode-a1.1`.
- Adds run startup marker: `=== CLARIFICATION ANALYTICAL MODE A1.1 ACTIVE ===`.
- Adds analytical mode detection telemetry with mode and reason.
- Adds deterministic filtering of weak analytical options such as `Retrieve`, `Access`, `Download`, `Open`, `Gather`, and similar input-gathering actions.
- Adds analytical fallback options if the model output is too procedural.
- Updates both active surfaces:
  - `run_aios.py`
  - `aios/clarification.py`

## Expected log markers
When AIOS starts:

```text
=== CLARIFICATION ANALYTICAL MODE A1.1 ACTIVE ===
```

When a clarification block is generated or regenerated:

```text
[Clarification] version=clarification-analytical-mode-a1.1; mode=analytical; reason=...
[Clarification] suggestions_generated=...; raw=...; mode=analytical
```

If weak procedural suggestions are filtered:

```text
[Clarification Filter] dropped_non_outcome_step=...
```

## Notes
Clarification telemetry appears only when a task actually enters the clarification flow. The startup marker appears every run, so it confirms installation even when there are no clarification tasks.
