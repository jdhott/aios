# Patch Notes — D1.5 Affinity Weak-Term Weighting

## Purpose

D1.4 correctly previewed active-task affinity, but it allowed broad one-word overlaps such as `bread` to dominate matches and inflate confidence.

## Changes

- Added explicit weak-term discounting for broad umbrella terms.
- Added a small strong-signal term set for operationally meaningful tokens.
- Raised confidence requirements:
  - high confidence now requires stronger score and evidence.
  - medium confidence requires either a strong term or multiple evidence terms.
- Added telemetry line confirming weak-term weighting is active.

## Governance

This remains observational project cognition only. It does not mutate tasks, projects, execution rank, execution score, BNA, Quick Wins, or governance reconciliation.
