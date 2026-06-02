# AIOS Clarification Analytical Mode A1.0

## Purpose
Adds an analytical clarification mode for audit, validation, ranking, metadata, telemetry, governance, and similar knowledge-work tasks.

## Problem addressed
The clarification generator was decomposing analytical work into procedural prerequisite steps such as retrieving lists, opening dashboards, or splitting a combined validation across individual metadata fields. This made AIOS governance tasks feel technically correct but operationally weak.

## Changes
- Adds deterministic clarification mode routing:
  - `define_context` remains unchanged.
  - `procedural` remains the default for ordinary physical/setup tasks.
  - `analytical` is selected for audit/review/validate/compare/ranking/metadata/telemetry/governance style tasks.
- Adds an analytical prompt that prefers outcome-producing steps:
  - review for anomalies
  - compare rankings against metadata
  - identify discrepancies
  - document findings
- Prevents common bad analytical options:
  - merely accessing/retrieving/downloading/opening artifacts
  - splitting one combined validation into separate field-by-field subtasks
  - preparing spreadsheets unless explicitly requested
- Adds compact logging:
  - `[Clarification] mode=...`
  - suggestion counts
  - generate-more mode and counts
- Updates the user-facing prompt for analytical tasks to:
  - `💡 Choose the first outcome-producing step:`

## Files changed
- `run_aios.py`
- `aios/clarification.py`

## Expected behavior
For a task such as:

`AIOS: Compare the Top 25 execution rankings against their underlying metadata`

The clarifier should prefer options like:

- `Review the top-ranked tasks for obvious scoring anomalies`
- `Compare top-ranked tasks against their underlying metadata`
- `Identify rankings that appear inconsistent with Urgency, Importance, or Due Date`

rather than:

- `Retrieve the Top 25 execution rankings list`
- `Access the corresponding metadata files`
- `Prepare a spreadsheet`

## Rollback
Use `rollback.sh` from this package. It restores the timestamped backup created during install.
