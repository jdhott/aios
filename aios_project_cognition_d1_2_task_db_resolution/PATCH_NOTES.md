# Patch Notes — D1.2 Task DB Resolution

## Problem

The D1 project affinity report failed when `TASKS_DATABASE_ID` pointed to a stale or unshared Notion database.

## Fix

The report now:

1. checks whether the configured Tasks DB is accessible;
2. confirms it looks like the AIOS Tasks schema;
3. searches accessible Notion databases as a fallback;
4. prints actionable diagnostics when no accessible Tasks DB can be found.

## Safety

- Read-only Notion calls only: `GET /databases`, `POST /search`, `POST /databases/{id}/query`.
- No page updates.
- No project writes.
- No ranking changes.
- No dashboard changes.
