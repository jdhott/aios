# AIOS Datastore Authority

## Current authority

Supabase is the default authoritative datastore for AIOS task and project state.

Unless `AIOS_DATASTORE=notion` is explicitly set, AIOS runs with:

    AIOS_DATASTORE=supabase

## Supabase owns

Supabase is authoritative for:

- task records and lifecycle state
- task metadata
- task creation
- clarification task creation
- breakdown parent/subtask creation and hierarchy
- project records and lifecycle state
- project creation and review stubs
- task-to-project relations
- Suggested Project state
- Execution Score
- Execution Rank
- Best Next Action
- Quick Win eligibility and surfaced Quick Win state
- metadata reconciliation mutations

## Notion remains an interface layer

Notion is intentionally retained for:

- Brain Dump input
- clarification checkbox/block interaction
- duplicate-review interaction
- Brain Dump archive presentation
- task-page contextual notes
- AIOS dashboard presentation
- AI Processing Log / provenance lookups
- selected project/topology telemetry

Notion task pages created during Supabase-primary task creation are transitional
mirrors and are not the authoritative task records.

## Fallback mode

The legacy persistence path remains available explicitly with:

    AIOS_DATASTORE=notion python run_aios.py

This is a fallback/testing mode, not the normal production authority.

## Authority validation

Supabase-mode runs include the Supabase Authority Audit.

A clean authority result is:

    Unexpected authoritative writes: 0
    Unclassified mutations: 0
    RESULT: SUPABASE CORE PERSISTENCE AUTHORITY CLEAN

Allowed Notion interface, telemetry, logging, or transitional mirror activity
does not violate Supabase persistence authority.
