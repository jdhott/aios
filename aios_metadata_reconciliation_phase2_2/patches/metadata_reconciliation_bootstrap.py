# === AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP ===
# Registers metadata reconciliation at process exit. Mutations are narrowly governed inside core.metadata.reconciliation.
try:
    import atexit as _aios_metadata_reconciliation_atexit

    def _aios_emit_metadata_reconciliation_phase1_diagnostics():
        try:
            from core.metadata.reconciliation import emit_metadata_reconciliation_diagnostics
            emit_metadata_reconciliation_diagnostics(globals())
        except Exception as exc:
            print(f"[Metadata Reconciliation] Diagnostics skipped: {exc}")

    _aios_metadata_reconciliation_atexit.register(_aios_emit_metadata_reconciliation_phase1_diagnostics)
    print("[Metadata Reconciliation] Phase 1 diagnostics registered")
except Exception as exc:
    print(f"[Metadata Reconciliation] Bootstrap registration failed: {exc}")
# === END AIOS METADATA RECONCILIATION PHASE 1 BOOTSTRAP ===
