#!/usr/bin/env python3
"""Validate progressive home task disclosure."""

from __future__ import annotations

from pathlib import Path

WEB = (Path(__file__).resolve().parents[1] / "aios" / "web_capture" / "app.py").read_text()

checks = [
    ("home v2 marker", 'WEB_DASHBOARD_UI_VERSION = "home-v2.2"' in WEB),
    ("focus only control", 'id="homeTasksCollapse"' in WEB and "Focus Only" in WEB),
    ("collapse helper", "collapseHomeProgressiveTasks" in WEB),
    ("section order constant", "_HOME_TASK_SECTION_ORDER" in WEB),
    ("focus-first shell class", "home-focus-first" in WEB),
    ("search mode shell class", "home-search-mode" in WEB),
    ("reveal button copy", "Show More" in WEB),
    ("reveal at panel end", "home-tasks-panel-content" in WEB),
    ("progressive hidden sections", 'data-progressive-hidden="true"' in WEB),
    ("home shell config", "window.__AIOS_HOME_SHELL__" in WEB),
    ("progressive sync helper", "syncHomeProgressiveTasks" in WEB),
    ("section order in config", '"sectionOrder"' in WEB),
]

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

if failed:
    print("\nRESULT: HOME PROGRESSIVE V1 VALIDATION FAILED")
    raise SystemExit(1)

print("\nRESULT: HOME PROGRESSIVE V1 STRUCTURE VALID")
