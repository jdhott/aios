# AIOS Legacy Metadata Diagnostic Cleanup — Phase 1

This is a governed installer package for the first post-audit cleanup step.

Install from the AIOS project root:

```bash
cd ~/LocalProjects/aios
bash install.sh
bash smoke_test.sh
```

Or pass the project root explicitly:

```bash
bash install.sh ~/LocalProjects/aios
bash smoke_test.sh ~/LocalProjects/aios
```

Rollback:

```bash
bash rollback.sh ~/LocalProjects/aios
```
