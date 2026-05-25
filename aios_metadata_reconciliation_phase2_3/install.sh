#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$PWD}"
PACKAGE_DIR="$(cd "$(dirname "$0")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$PROJECT_ROOT/backups/metadata_reconciliation_phase2_3_$STAMP"
RUN_FILE="$PROJECT_ROOT/run_aios.py"
RECON_BOOTSTRAP_FILE="$PACKAGE_DIR/patches/metadata_reconciliation_bootstrap.py"
GUARD_BOOTSTRAP_FILE="$PACKAGE_DIR/patches/metadata_persistence_guard_bootstrap.py"
RECON_MARKER="AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP"
GUARD_MARKER="AIOS METADATA PERSISTENCE GUARD PHASE 2 BOOTSTRAP"

cd "$PROJECT_ROOT"
mkdir -p "$BACKUP_DIR"

echo "=== AIOS Metadata Reconciliation Phase 2.3 Installer ==="
echo "Project root: $PROJECT_ROOT"
echo "Backup dir:   $BACKUP_DIR"

if [[ ! -f "$RUN_FILE" ]]; then
  echo "ERROR: run_aios.py not found in $PROJECT_ROOT"
  echo "Run this installer from ~/LocalProjects/aios or pass the project root as the first argument."
  exit 1
fi

cp "$RUN_FILE" "$BACKUP_DIR/run_aios.py.bak"
if [[ -d "$PROJECT_ROOT/core" ]]; then
  cp -R "$PROJECT_ROOT/core" "$BACKUP_DIR/core.bak"
fi

mkdir -p "$PROJECT_ROOT/core/metadata"
if [[ ! -f "$PROJECT_ROOT/core/__init__.py" ]]; then
  cp "$PACKAGE_DIR/core/__init__.py" "$PROJECT_ROOT/core/__init__.py"
fi
if [[ ! -f "$PROJECT_ROOT/core/metadata/__init__.py" ]]; then
  cp "$PACKAGE_DIR/core/metadata/__init__.py" "$PROJECT_ROOT/core/metadata/__init__.py"
fi
cp "$PACKAGE_DIR/core/metadata/reconciliation.py" "$PROJECT_ROOT/core/metadata/reconciliation.py"
cp "$PACKAGE_DIR/core/metadata/persistence_guard.py" "$PROJECT_ROOT/core/metadata/persistence_guard.py"

mkdir -p "$PROJECT_ROOT/tools"
cp "$PACKAGE_DIR/tools/smoke_test_metadata_reconciliation.py" "$PROJECT_ROOT/tools/smoke_test_metadata_reconciliation.py"
cp "$PACKAGE_DIR/tools/smoke_test_metadata_persistence_guard.py" "$PROJECT_ROOT/tools/smoke_test_metadata_persistence_guard.py"
cp "$PACKAGE_DIR/rollback.sh" "$PROJECT_ROOT/tools/rollback_metadata_reconciliation_phase2_3.sh"
chmod +x "$PROJECT_ROOT/tools/smoke_test_metadata_reconciliation.py"
chmod +x "$PROJECT_ROOT/tools/smoke_test_metadata_persistence_guard.py"
chmod +x "$PROJECT_ROOT/tools/rollback_metadata_reconciliation_phase2_3.sh"

# The persistence guard must run before the main runtime begins. Insert it at the top.
if grep -q "$GUARD_MARKER" "$RUN_FILE"; then
  echo "Phase 2 persistence guard already present in run_aios.py; leaving existing early hook in place."
else
  TMP_FILE="$(mktemp)"
  cat "$GUARD_BOOTSTRAP_FILE" > "$TMP_FILE"
  printf '\n' >> "$TMP_FILE"
  cat "$RUN_FILE" >> "$TMP_FILE"
  mv "$TMP_FILE" "$RUN_FILE"
  echo "Installed early closed-task persistence guard into run_aios.py"
fi

# Keep / add the exit reconciliation diagnostics hook.
if grep -q "$RECON_MARKER" "$RUN_FILE"; then
  echo "Metadata reconciliation bootstrap already present in run_aios.py; leaving existing hook in place."
else
  cat "$RECON_BOOTSTRAP_FILE" >> "$RUN_FILE"
  echo "Installed metadata reconciliation bootstrap into run_aios.py"
fi

cat > "$BACKUP_DIR/ROLLBACK_INSTRUCTIONS.txt" <<EOF
Rollback created by metadata reconciliation phase 2.2 installer.

To rollback:
  cd "$PROJECT_ROOT"
  cp "$BACKUP_DIR/run_aios.py.bak" "$PROJECT_ROOT/run_aios.py"
  if [ -d "$BACKUP_DIR/core.bak" ]; then rm -rf "$PROJECT_ROOT/core" && cp -R "$BACKUP_DIR/core.bak" "$PROJECT_ROOT/core"; fi
EOF

echo "$BACKUP_DIR" > "$PROJECT_ROOT/.metadata_reconciliation_phase2_3_last_backup"

echo "Running smoke tests..."
"${PYTHON:-python3}" "$PROJECT_ROOT/tools/smoke_test_metadata_reconciliation.py"
"${PYTHON:-python3}" "$PROJECT_ROOT/tools/smoke_test_metadata_persistence_guard.py"

echo "Install complete. Next test command:"
echo "cd $PROJECT_ROOT"
echo "bash run.sh > test_run.log 2>&1"
echo "grep -E 'METADATA RECONCILIATION|Metadata Reconciliation|Metadata Persistence Guard|Execution Rank Diagnostics|Execution Rank Diagnostics|Execution Rank Diagnostics|Applying true execution rank rewrite|Canonical rank assignment preview|Execution ranks rewritten canonically|Closed/done|Quick Win deferred cleanup|Closed/done execution cleanup|Mutation error' test_run.log"
