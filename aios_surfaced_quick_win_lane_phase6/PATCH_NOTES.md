# AIOS Surfaced Quick Win Lane — Phase 6

## Purpose

Adds a dedicated, capped Quick Win presentation lane independent of Best Next Actions.

This separates:

```text
Quick Win = eligibility metadata
Surfaced Quick Win = visible/capped presentation lane
```

from:

```text
Execution Score / Execution Rank / Best Next Action = execution authority
```

## What changed

- Adds `SURFACED_QUICK_WIN_PROPERTY`, defaulting to `Surfaced Quick Win`.
- Adds `SURFACED_QUICK_WIN_LIMIT`, defaulting to `5`.
- Selects up to 5 surfaced Quick Wins.
- Excludes current BNA winners from the surfaced Quick Win lane.
- Does not use `Execution Rank` to select Quick Wins.
- Does not mutate `Do = Today`, `Focus`, `Focus Now`, `Execution Rank`, `Execution Score`, or `Best Next Action`.
- Clears stale `Surfaced Quick Win` flags that are no longer selected.

## Required Notion setup

Create a checkbox property in the Tasks database:

```text
Surfaced Quick Win
```

Then set the Quick Wins view filter to:

```text
Surfaced Quick Win is checked
Done is unchecked
```

Do not filter this view by `Execution Rank`.

## Install

```bash
cd ~/LocalProjects/aios
bash /path/to/aios_surfaced_quick_win_lane_phase6/install.sh
bash /path/to/aios_surfaced_quick_win_lane_phase6/smoke_test.sh
```

Or, from inside the package folder:

```bash
bash install.sh ~/LocalProjects/aios
bash smoke_test.sh ~/LocalProjects/aios
```

## Rollback

```bash
bash rollback.sh ~/LocalProjects/aios
```
