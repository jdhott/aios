# AIOS Project Cognition D1.6.1 — Confidence Calibration Fix

This package fixes the D1.6 smoke-test failure by aligning the strong-domain anchor confidence threshold with the intended behavior.

## Scope

- Read-only project cognition telemetry only.
- No Notion writes.
- No execution authority impact.
- No ranking, BNA, Quick Win, or governance mutation.

## Change

D1.6 added anchor-domain confidence detection but left the high-confidence threshold too high for the intended `Organize pool equipment` case. D1.6.1 lowers the anchor-specific high-confidence threshold from 16 to 14 while keeping broad/weak terms suppressed.
