# AIOS Execution Engine Rank Authority — Phase 2.6

Deterministic Execution Rank Persistence.

This package moves canonical execution-rank ordering back into `execution_engine_v2.py`.

It patches `rebuild_execution_state()` so the Execution Engine persists ranks using:

```text
Execution Score DESC
Task Title ASC
Page ID ASC
```

It also adds explicit write-source logging.

Install:

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_execution_engine_rank_authority_phase2_6.tar.gz
bash aios_execution_engine_rank_authority_phase2_6/install.sh
bash aios_execution_engine_rank_authority_phase2_6/smoke_test.sh
```

Test:

```bash
bash run.sh > test_run.log 2>&1
grep -E "Execution Engine V2|Canonical rank ordering|Canonical persistence row|Write payload|Execution Rank Diagnostics|Execution rank rewrite skipped|Mutation error" test_run.log
```
