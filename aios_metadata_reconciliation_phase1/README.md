# AIOS Metadata Reconciliation — Phase 1 Diagnostics

This package installs the first conservative step of Track A: canonical metadata reconciliation diagnostics.

## What it adds

- `core/metadata/reconciliation.py`
- a diagnostics-only bootstrap at the end of `run_aios.py`
- `tools/smoke_test_metadata_reconciliation.py`
- rollback-safe backups under `backups/metadata_reconciliation_phase1_<timestamp>/`

## What it does not do

- No Notion mutations
- No evaluator scoring changes
- No ranking changes
- No Quick Win cap changes
- No Do = Today authority changes

## Install

```bash
cd ~/LocalProjects/aios
bash /path/to/install.sh
```

Or from inside the unpacked package:

```bash
cd ~/LocalProjects/aios
bash ~/Downloads/aios_metadata_reconciliation_phase1/install.sh
```

## Test

```bash
cd ~/LocalProjects/aios
bash run.sh > ~/LocalProjects/aios/test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation" ~/LocalProjects/aios/test_run.log
```

## Expected log shape

```text
[Metadata Reconciliation] Phase 1 diagnostics registered
=== METADATA RECONCILIATION — PHASE 1: DIAGNOSTICS ONLY ===
[Metadata Reconciliation] Tasks scanned: ...
[Metadata Reconciliation] Open tasks observed: ...
[Metadata Reconciliation] Findings: ...
[Metadata Reconciliation] No Notion mutations performed.
```

If no runtime task objects are available to inspect, you may see `Tasks scanned: 0`. That is safe and tells us the next package should wire this into the canonical task collection point rather than relying on runtime object discovery.

## Rollback

```bash
cd ~/LocalProjects/aios
bash tools/rollback_metadata_reconciliation_phase1.sh
```

Or use the rollback script inside the unpacked package:

```bash
cd ~/LocalProjects/aios
bash /path/to/aios_metadata_reconciliation_phase1/rollback.sh
```
