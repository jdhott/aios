"""
Audit remaining Notion dependencies in the AIOS Python source tree.

This script is READ ONLY. It scans source files and classifies likely Notion
touchpoints so the remaining migration work can be prioritized by evidence
instead of assumption.

Run:
    python -m scripts.notion_dependency_audit

Optional:
    python -m scripts.notion_dependency_audit --root .
    python -m scripts.notion_dependency_audit --show-context
    python -m scripts.notion_dependency_audit --json notion_audit.json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}


@dataclass
class Finding:
    file: str
    line: int
    operation: str
    category: str
    symbol: str
    code: str
    context: str = ""


PATTERNS = [
    (
        re.compile(r"api\.notion\.com"),
        "Direct Notion API",
        "core_or_ui",
        "api.notion.com",
    ),
    (
        re.compile(r"\bquery_tasks_database\s*\("),
        "Task database read",
        "core_persistence",
        "query_tasks_database",
    ),
    (
        re.compile(r"\bquery_projects_database\s*\("),
        "Project database read",
        "core_persistence",
        "query_projects_database",
    ),
    (
        re.compile(r"\bupdate_notion_page\s*\("),
        "Notion page update",
        "core_or_ui",
        "update_notion_page",
    ),
    (
        re.compile(r"\bcreate_notion_task\s*\("),
        "Notion task creation",
        "core_persistence",
        "create_notion_task",
    ),
    (
        re.compile(r"\b_create_notion_task_only\s*\("),
        "Notion task mirror creation",
        "ui_workflow",
        "_create_notion_task_only",
    ),
    (
        re.compile(r"\bappend_children\b|\bblocks/.+/children\b"),
        "Notion block append",
        "ui_workflow",
        "block append",
    ),
    (
        re.compile(r"\bdelete_block\b|/blocks/.+DELETE|requests\.delete"),
        "Notion block delete",
        "ui_workflow",
        "block delete",
    ),
    (
        re.compile(r"\barchive\b.*notion|notion.*\barchive\b"),
        "Notion archive operation",
        "ui_workflow",
        "archive",
    ),
    (
        re.compile(r"\bAI Log\b|\bAI_LOG\b|log_ai_"),
        "AI log write/read",
        "telemetry_logging",
        "AI log",
    ),
    (
        re.compile(r"\btelemetry\b", re.IGNORECASE),
        "Telemetry dependency",
        "telemetry_logging",
        "telemetry",
    ),
    (
        re.compile(r"\bBrain Dump\b|\bBRAIN_DUMP\b|synced block", re.IGNORECASE),
        "Brain Dump / synced-block dependency",
        "ui_workflow",
        "Brain Dump",
    ),
    (
        re.compile(r"\bclarification\b", re.IGNORECASE),
        "Clarification workflow dependency",
        "ui_workflow",
        "clarification",
    ),
    (
        re.compile(r"\bdashboard\b", re.IGNORECASE),
        "Dashboard dependency",
        "ui_presentation",
        "dashboard",
    ),
    (
        re.compile(r"\bPROJECTS_DATABASE_ID\b|\bTASKS_DATABASE_ID\b"),
        "Notion database identifier",
        "configuration",
        "database id",
    ),
]


CATEGORY_ORDER = {
    "core_persistence": 0,
    "core_or_ui": 1,
    "ui_workflow": 2,
    "ui_presentation": 3,
    "telemetry_logging": 4,
    "configuration": 5,
}


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        # Skip extracted installer/package directories to avoid duplicate hits.
        if any(
            part.startswith("aios_")
            and part not in {"aios"}
            for part in path.parts
        ):
            continue

        yield path


def enclosing_function_map(source: str) -> dict[int, str]:
    """
    Map source line -> nearest function/class-qualified name.
    """
    result: dict[int, str] = {}

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result

    def visit(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                name = (
                    f"{prefix}.{child.name}"
                    if prefix
                    else child.name
                )

                start = getattr(child, "lineno", None)
                end = getattr(child, "end_lineno", start)

                if start is not None:
                    for line in range(start, (end or start) + 1):
                        result[line] = name

                visit(child, name)
            else:
                visit(child, prefix)

    visit(tree)
    return result


def classify_direct_api_line(code: str, category: str) -> str:
    """
    Refine direct Notion API calls when the line itself makes the purpose clear.
    """
    lowered = code.casefold()

    if any(
        token in lowered
        for token in (
            "blocks/",
            "children",
            "synced",
        )
    ):
        return "ui_workflow"

    if "telemetry" in lowered or "ai_log" in lowered:
        return "telemetry_logging"

    if "dashboard" in lowered:
        return "ui_presentation"

    return category


def scan_file(
    root: Path,
    path: Path,
    show_context: bool,
) -> list[Finding]:
    try:
        source = path.read_text(
            encoding="utf-8"
        )
    except UnicodeDecodeError:
        return []

    lines = source.splitlines()
    function_map = enclosing_function_map(
        source
    )

    findings: list[Finding] = []
    seen = set()

    for lineno, code in enumerate(
        lines,
        start=1,
    ):
        stripped = code.strip()

        if not stripped:
            continue

        for (
            pattern,
            operation,
            category,
            symbol,
        ) in PATTERNS:
            if not pattern.search(code):
                continue

            final_category = category

            if symbol == "api.notion.com":
                final_category = (
                    classify_direct_api_line(
                        code,
                        category,
                    )
                )

            key = (
                lineno,
                operation,
                symbol,
            )

            if key in seen:
                continue

            seen.add(key)

            context = ""

            if show_context:
                start = max(
                    0,
                    lineno - 2,
                )
                end = min(
                    len(lines),
                    lineno + 1,
                )

                context = "\n".join(
                    f"{i + 1:>5}: {lines[i]}"
                    for i in range(
                        start,
                        end,
                    )
                )

            findings.append(
                Finding(
                    file=str(
                        path.relative_to(root)
                    ),
                    line=lineno,
                    operation=operation,
                    category=final_category,
                    symbol=symbol,
                    code=stripped,
                    context=context,
                )
            )

    return findings


def summarize(findings: list[Finding]) -> None:
    print("=" * 88)
    print("AIOS NOTION DEPENDENCY AUDIT")
    print("=" * 88)
    print("\nREAD ONLY.\n")

    if not findings:
        print("No Notion-related dependencies found.")
        return

    counts: dict[str, int] = {}

    for finding in findings:
        counts[finding.category] = (
            counts.get(
                finding.category,
                0,
            )
            + 1
        )

    print("Summary by category:")

    for category in sorted(
        counts,
        key=lambda value: (
            CATEGORY_ORDER.get(
                value,
                99,
            ),
            value,
        ),
    ):
        print(
            f"  {category:<20} "
            f"{counts[category]:>4}"
        )

    print(
        f"\nTotal findings: {len(findings)}"
    )

    print("\nDetailed findings:\n")

    for finding in sorted(
        findings,
        key=lambda item: (
            CATEGORY_ORDER.get(
                item.category,
                99,
            ),
            item.file,
            item.line,
        ),
    ):
        print(
            f"[{finding.category}] "
            f"{finding.file}:{finding.line}"
        )
        print(
            f"  Operation: {finding.operation}"
        )
        print(
            f"  Symbol:    {finding.symbol}"
        )
        print(
            f"  Scope:     "
            f"{_scope_label(finding)}"
        )
        print(
            f"  Code:      {finding.code}"
        )

        if finding.context:
            print("  Context:")
            for line in finding.context.splitlines():
                print(
                    f"    {line}"
                )

        print()


def _scope_label(
    finding: Finding,
) -> str:
    # Function/class scope is injected by enrich_scope.
    return getattr(
        finding,
        "_scope",
        "(module)",
    )


def enrich_scope(
    root: Path,
    findings: list[Finding],
) -> None:
    by_file: dict[str, list[Finding]] = {}

    for finding in findings:
        by_file.setdefault(
            finding.file,
            [],
        ).append(
            finding
        )

    for relative, items in by_file.items():
        path = root / relative

        try:
            source = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            continue

        mapping = enclosing_function_map(
            source
        )

        for finding in items:
            setattr(
                finding,
                "_scope",
                mapping.get(
                    finding.line,
                    "(module)",
                ),
            )


def write_json(
    path: Path,
    findings: list[Finding],
) -> None:
    payload = []

    for finding in findings:
        item = asdict(
            finding
        )
        item["scope"] = (
            _scope_label(
                finding
            )
        )
        payload.append(
            item
        )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit remaining Notion dependencies "
            "in the AIOS Python source tree."
        )
    )

    parser.add_argument(
        "--root",
        default=".",
        help=(
            "Repository root to scan "
            "(default: current directory)."
        ),
    )

    parser.add_argument(
        "--show-context",
        action="store_true",
        help=(
            "Show surrounding source lines "
            "for each finding."
        ),
    )

    parser.add_argument(
        "--json",
        dest="json_path",
        help=(
            "Optional path for machine-readable "
            "JSON findings."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    root = Path(
        args.root
    ).resolve()

    if not root.exists():
        raise SystemExit(
            f"Root does not exist: {root}"
        )

    findings: list[Finding] = []

    for path in iter_python_files(
        root
    ):
        findings.extend(
            scan_file(
                root,
                path,
                args.show_context,
            )
        )

    enrich_scope(
        root,
        findings,
    )

    summarize(
        findings
    )

    if args.json_path:
        output_path = Path(
            args.json_path
        )

        if not output_path.is_absolute():
            output_path = (
                root
                / output_path
            )

        write_json(
            output_path,
            findings,
        )

        print(
            f"JSON written: {output_path}"
        )


if __name__ == "__main__":
    main()
