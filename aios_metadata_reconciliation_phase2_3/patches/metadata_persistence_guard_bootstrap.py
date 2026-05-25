# === AIOS METADATA PERSISTENCE GUARD PHASE 2 BOOTSTRAP ===
# Must run near the top of run_aios.py before execution ranking persistence occurs.
try:
    from core.metadata.persistence_guard import install_closed_task_execution_persistence_guard
    install_closed_task_execution_persistence_guard()
except Exception as exc:
    print(f"[Metadata Persistence Guard] Bootstrap failed: {exc}")
# === END AIOS METADATA PERSISTENCE GUARD PHASE 2 BOOTSTRAP ===
