#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys
import re

ROOT = Path.cwd()
PACKAGE_DIR = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / ".aios_project_cognition_d3_0_relation_label_resolution_backup"

AFFINITY = ROOT / "scripts" / "aios_project_affinity_report.py"
REPORT = ROOT / "tools" / "ontology_stabilization_report.py"


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


if not (ROOT / "run_aios.py").exists():
    fail("Run this installer from the AIOS project root, e.g. ~/LocalProjects/aios")

BACKUP_DIR.mkdir(exist_ok=True)

if AFFINITY.exists():
    shutil.copy2(AFFINITY, BACKUP_DIR / "aios_project_affinity_report.py")

if REPORT.exists():
    shutil.copy2(REPORT, BACKUP_DIR / "ontology_stabilization_report.py")

# Install tools
tools_dir = ROOT / "tools"
tools_dir.mkdir(exist_ok=True)

shutil.copy2(PACKAGE_DIR / "files" / "tools" / "repair_project_cognition_snapshot_labels.py", tools_dir / "repair_project_cognition_snapshot_labels.py")
shutil.copy2(PACKAGE_DIR / "files" / "tools" / "ontology_stabilization_report.py", tools_dir / "ontology_stabilization_report.py")

(tools_dir / "repair_project_cognition_snapshot_labels.py").chmod(0o755)
(tools_dir / "ontology_stabilization_report.py").chmod(0o755)

# Conservative source patch: increase project name resolution page limit if exact patterns are present.
if AFFINITY.exists():
    text = AFFINITY.read_text(encoding="utf-8")
    original = text
    text = text.replace("page_size=100", "page_size=500")
    text = text.replace('"page_size": 100', '"page_size": 500')
    text = text.replace("'page_size': 100", "'page_size': 500")
    if text != original:
        AFFINITY.write_text(text, encoding="utf-8")
        print("Patched project-name resolution page size from 100 to 500 where present.")
    else:
        print("No page-size pattern found to patch in project affinity report; continuing.")

print(f"Backup written to: {BACKUP_DIR}")
print("Installed D3.0 relation label resolution tools.")
