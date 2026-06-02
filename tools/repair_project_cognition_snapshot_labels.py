#!/usr/bin/env python3
"""
AIOS Project Cognition Snapshot Label Repair

Repairs local telemetry rows where suggested_project is unresolved_relation:<id>
when another row with the same project_key has a readable label.

Local telemetry only:
- no Notion writes
- no Project relation mutation
- no execution/evaluator/dashboard changes
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


DEFAULT_SNAPSHOT = Path("logs/project_cognition_snapshot.jsonl")


def is_unresolved_label(label: str) -> bool:
    return str(label or "").startswith("unresolved_relation:")


def is_readable_label(label: str) -> bool:
    value = str(label or "").strip()
    if not value:
        return False
    if is_unresolved_label(value):
        return False
    if value.startswith("relation:"):
        return False
    return True


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except Exception:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def build_relation_label_map(rows: list[Mapping[str, Any]]) -> dict[str, str]:
    labels_by_key: dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        project_key = str(row.get("project_key") or "").strip()
        label = str(row.get("suggested_project") or "").strip()
        if not project_key.startswith("relation:"):
            continue
        if is_readable_label(label):
            labels_by_key[project_key][label] += 1

    resolved: dict[str, str] = {}
    for project_key, counts in labels_by_key.items():
        if counts:
            resolved[project_key] = counts.most_common(1)[0][0]

    return resolved


def repair_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, dict[str, str]]:
    label_by_key = build_relation_label_map(rows)
    repaired = 0
    output: list[dict[str, Any]] = []

    for row in rows:
        new_row = dict(row)
        project_key = str(new_row.get("project_key") or "").strip()
        label = str(new_row.get("suggested_project") or "").strip()

        if project_key in label_by_key and is_unresolved_label(label):
            new_row["suggested_project"] = label_by_key[project_key]
            new_row["label_repaired_from"] = label
            repaired += 1

        output.append(new_row)

    return output, repaired, label_by_key


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=str(DEFAULT_SNAPSHOT), help="Snapshot JSONL path.")
    parser.add_argument("--check", action="store_true", help="Report possible repairs without rewriting.")
    args = parser.parse_args()

    path = Path(args.path)
    rows = load_rows(path)
    repaired_rows, repaired_count, label_by_key = repair_rows(rows)

    unresolved_before = sum(1 for row in rows if is_unresolved_label(str(row.get("suggested_project") or "")))
    unresolved_after = sum(1 for row in repaired_rows if is_unresolved_label(str(row.get("suggested_project") or "")))

    print("=== AIOS PROJECT COGNITION SNAPSHOT LABEL REPAIR ===")
    print(f"Snapshot path: {path}")
    print(f"Rows read: {len(rows)}")
    print(f"Relation label mappings available: {len(label_by_key)}")
    print(f"Unresolved labels before: {unresolved_before}")
    print(f"Rows repairable: {repaired_count}")
    print(f"Unresolved labels after: {unresolved_after}")

    if args.check:
        print("Mode: check only")
        return 0

    if not rows:
        print("No snapshot rows found; nothing to repair.")
        return 0

    if repaired_count == 0:
        print("No repairable unresolved labels found.")
        return 0

    backup = path.with_suffix(path.suffix + f".label_repair_bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(path, backup)
    write_rows(path, repaired_rows)

    print(f"Backup written: {backup}")
    print("Label repair complete.")
    print("Governance status: local telemetry only; relation_mutations=0; execution_authority_impact=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
