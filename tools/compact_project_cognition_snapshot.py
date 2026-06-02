#!/usr/bin/env python3
"""
AIOS Project Cognition Snapshot Compaction

Compacts logs/project_cognition_snapshot.jsonl by semantic observation identity.

This is local telemetry hygiene only:
- no Notion writes
- no Project relation mutation
- no execution/evaluator/dashboard changes
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


SNAPSHOT_PATH = Path("logs/project_cognition_snapshot.jsonl")


def semantic_fingerprint(row: Mapping[str, Any]) -> str:
    """Semantic Project Cognition observation identity.

    Excludes observed_at and run-local counters so repeated stable observations
    collapse to one retained row.
    """
    stable = {
        "source": row.get("source", ""),
        "task_id": row.get("task_id", ""),
        "task_title": row.get("task_title", ""),
        "suggested_project": row.get("suggested_project", ""),
        "existing_suggested_project": row.get("existing_suggested_project", ""),
        "score": row.get("score", ""),
        "ambiguity": row.get("ambiguity", ""),
        "confidence": row.get("confidence", ""),
        "runner_up": row.get("runner_up", ""),
        "runner_up_margin": row.get("runner_up_margin", ""),
        "reason": row.get("reason", ""),
        "project_key": row.get("project_key", ""),
        "execution_authority_impact": row.get("execution_authority_impact", ""),
        "relation_mutations": row.get("relation_mutations", ""),
    }
    return json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str)


def load_rows(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    malformed = 0

    if not path.exists():
        return rows, malformed

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
            except Exception:
                malformed += 1
                continue
            if isinstance(parsed, dict):
                rows.append(parsed)
            else:
                malformed += 1

    return rows, malformed


def compact_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    compacted: list[dict[str, Any]] = []

    for row in rows:
        fingerprint = semantic_fingerprint(row)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        compacted.append(row)

    removed = len(rows) - len(compacted)
    return compacted, removed


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Report compaction statistics without rewriting the file.")
    parser.add_argument("--path", default=str(SNAPSHOT_PATH), help="Snapshot JSONL path.")
    args = parser.parse_args()

    path = Path(args.path)
    rows, malformed = load_rows(path)
    compacted, removed = compact_rows(rows)

    print("=== AIOS PROJECT COGNITION SNAPSHOT COMPACTION ===")
    print(f"Snapshot path: {path}")
    print(f"Rows read: {len(rows)}")
    print(f"Malformed rows skipped: {malformed}")
    print(f"Semantic duplicates: {removed}")
    print(f"Rows after compaction: {len(compacted)}")

    if args.check:
        print("Mode: check only")
        return 0

    if not path.exists():
        print("No snapshot file found; nothing to compact.")
        return 0

    backup = path.with_suffix(path.suffix + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(path, backup)
    write_rows(path, compacted)

    print(f"Backup written: {backup}")
    print("Compaction complete.")
    print("Governance status: local telemetry only; relation_mutations=0; execution_authority_impact=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
