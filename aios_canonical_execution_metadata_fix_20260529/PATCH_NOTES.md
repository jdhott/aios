# AIOS Canonical Execution Metadata Fix — 2026-05-29

## Purpose
Align Best Next Action / execution scoring with the canonical task metadata model.

Canonical execution inputs are now:

- `Urgency`
- `Importance`
- `Due Date`

Legacy/non-canonical execution inputs removed from these paths:

- `Priority`
- `Due`

## Changes
- `execution_engine_v2.py`
  - Scores `Importance`, not `Priority`.
  - Scores `Due Date`, not `Due`.
  - Fixes date-only `Due Date` scoring so Notion dates such as `2026-05-29` are scored correctly.
  - Updates BNA provenance logging from `Priority/Importance` to `Importance`.
- `core/evaluator.py`
  - Replaces `score_priority()` with `score_importance()`.
  - Evaluator ranking reads `Importance` only.
- `run_aios.py`
  - Stops writing `Priority` when urgency is detected.
  - Stops writing `Priority` for explicit urgency updates on existing tasks.
  - Stops writing `Priority` at create time.
  - Updates `is_high_importance()` to read `Importance`.
  - Removes legacy `Due` fallback in `get_due_date()`.
- `aios/clarification.py`
  - Stops writing `Priority` when urgency is detected.

## Expected behaviour
A task with:

- `Urgency = High Urgency`
- `Importance = High Importance`
- empty `Due Date`

should score from both canonical fields. A task with legacy `Priority` alone should no longer receive execution score from that legacy field.
