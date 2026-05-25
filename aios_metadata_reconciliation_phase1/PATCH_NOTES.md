# Patch Notes — Metadata Reconciliation Phase 1

## Purpose

Begin Track A: Canonical Metadata Reconciliation.

## Design

This is a diagnostics-first package. It introduces a passive reconciliation authority module but does not yet perform cleanup. This keeps the first step architecture-safe while exposing stale or contradictory metadata.

## Diagnostic categories

- Done tasks with active presentation metadata
- Done tasks with execution metadata
- JDI tasks with forbidden execution metadata
- Deferred future tasks still surfaced
- Best Next Action without Execution Rank
- Best Next Action without Execution Score
- Do = Today without Best Next Action
- Legacy Focus/Focus Now metadata still present
- Done tasks still marked Quick Win

## Safety

- No writes
- No Notion API calls
- No evaluator changes
- No ranking changes
- Rollback-safe installer
