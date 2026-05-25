# AIOS Metadata Reconciliation Phase 2.1

Adds execution-rank canonicalization on top of the validated Phase 2.0 reconciliation guard.

Install from the AIOS project root:

```bash
cd ~/LocalProjects/aios
tar -xzf ~/Downloads/aios_metadata_reconciliation_phase2_1.tar.gz
bash aios_metadata_reconciliation_phase2_1/install.sh
bash run.sh > test_run.log 2>&1
grep -E "METADATA RECONCILIATION|Metadata Reconciliation|Metadata Persistence Guard|Execution rank canonicalization|Canonicalizing Execution Rank|Closed/done|Quick Win deferred cleanup|Closed/done execution cleanup|Mutation error" test_run.log
```

Expected first run if rank gaps are present:

```text
[Metadata Reconciliation] Applying execution rank canonicalization: N
[Metadata Reconciliation] Canonicalizing Execution Rank: ... — 4 → 3
[Metadata Reconciliation] Execution ranks canonicalized: N
```

Expected second run:

```text
[Metadata Reconciliation] Execution rank canonicalization: 0
```
