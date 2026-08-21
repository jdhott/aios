#!/usr/bin/env python3
"""Validate hidden rank/score and task-detail project names."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
api = (ROOT / "aios" / "api" / "app.py").read_text()
web = (ROOT / "aios" / "web_capture" / "app.py").read_text()

focus_meta = web.split("def _focus_card_view")[1].split("def _focus_card_fingerprint")[0]
dashboard_row = web.split("def _render_dashboard_task_row")[1].split("def _render_completed_task_row")[0]
task_detail = web.split("def _task_detail_page")[1].split("def _fetch_projects")[0]

checks = [
    ("home version bumped", 'WEB_DASHBOARD_UI_VERSION = "home-v2.7-guidance-disclosure"' in web),
    ("task detail version bumped", 'WEB_TASK_DETAIL_UI_VERSION = "task-detail-ui-v1.4-project-name"' in web),
    ("focus card hides rank tags", 'Rank {html.escape(str(focus.get' not in focus_meta),
    ("focus card hides score tags", 'Score {html.escape(str(focus.get' not in focus_meta),
    ("dashboard rows hide rank tags", 'f"Rank {html.escape(str(rank))}"' not in dashboard_row),
    ("dashboard rows hide score tags", 'f"Score {html.escape(str(score))}"' not in dashboard_row),
    ("task detail collapses guidance", 'class="guidance-details"' in task_detail),
    ("task detail no project id label", "Project ID" not in task_detail),
    ("task detail project select", 'name="project_id"' in task_detail),
    ("API returns project_name", '"project_name"' in api),
    ("API patch accepts project_id", "project_id: str | None = None" in api),
    ("project select helper", "def _project_select_options" in web),
]
failed = []
for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    if not ok:
        failed.append(label)
if failed:
    raise SystemExit("RESULT: GUIDANCE DISCLOSURE V1 VALIDATION FAILED")
print("RESULT: GUIDANCE DISCLOSURE V1 VALID")
