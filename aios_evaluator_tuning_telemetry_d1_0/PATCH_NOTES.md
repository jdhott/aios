# AIOS Evaluator Tuning Telemetry D1.0

## Purpose

Adds compact, read-only evaluator tuning telemetry to Execution Engine V2 so future evaluator tuning can be based on observed signal distribution instead of guesswork.

## What changes

- Adds `emit_evaluator_tuning_summary(...)` to `execution_engine_v2.py`.
- Emits a compact runtime section after BNA selection and before execution-rank persistence:
  - ranked pool count
  - persisted rank count
  - BNA count
  - score-band distribution
  - BNA score-band distribution
  - ranking signal distribution
  - BNA signal distribution
  - scoring source health
  - low-signal BNA count
- Tracks score source internally:
  - `primary_evaluator`
  - `legacy_fallback`
  - `baseline_executable`
  - `legacy`

## Governance boundaries

This package is observational only.

It does **not** change:

- task eligibility
- execution score calculation
- execution rank ordering
- Best Next Action selection
- Quick Win behavior
- Do = Today behavior
- Notion relation mutation
- project cognition
- metadata reconciliation policy

## Install

From the AIOS project root:

```bash
cd ~/LocalProjects/aios
bash /path/to/aios_evaluator_tuning_telemetry_d1_0/install.sh
bash smoke_test.sh
```

Or from inside the unpacked package:

```bash
cd ~/LocalProjects/aios
bash /path/to/package/install.sh ~/LocalProjects/aios
bash /path/to/package/smoke_test.sh ~/LocalProjects/aios
```

## Runtime verification

After a normal AIOS run, check:

```bash
grep -E "Evaluator Tuning|Best Next Actions|Errors:" test_run.log
```

Expected new section:

```text
--- Evaluator Tuning Telemetry ---
[Evaluator Tuning] Pool: ranked=...; persisted=...; bna=...
[Evaluator Tuning] Score bands: ...
[Evaluator Tuning] BNA score bands: ...
[Evaluator Tuning] Signal distribution: ...
[Evaluator Tuning] BNA signal distribution: ...
[Evaluator Tuning] Scoring source health: ...
[Evaluator Tuning] Low-signal BNA count: ...
```

## Rollback

From the AIOS project root:

```bash
cd ~/LocalProjects/aios
bash /path/to/aios_evaluator_tuning_telemetry_d1_0/rollback.sh
```
