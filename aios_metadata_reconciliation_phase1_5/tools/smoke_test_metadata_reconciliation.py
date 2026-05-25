#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.metadata.reconciliation import scan_pages, format_summary, collect_quick_win_deferred_cleanup_actions


def prop_checkbox(value):
    return {"checkbox": value}


def prop_number(value):
    return {"number": value}


def prop_title(value):
    return {"title": [{"plain_text": value}]}


def prop_date(value):
    return {"date": {"start": value}}


sample_pages = [
    {"id": "1", "properties": {"Task Name": prop_title("Completed stale task"), "Done": prop_checkbox(True), "Do = Today": prop_checkbox(True), "Execution Rank": prop_number(1)}},
    {"id": "2", "properties": {"Task Name": prop_title("JDI clean counter"), "Done": prop_checkbox(False), "JDI": prop_checkbox(True), "Execution Score": prop_number(75)}},
    {"id": "3", "properties": {"Task Name": prop_title("Deferred surfaced task"), "Done": prop_checkbox(False), "Defer Until": prop_date("2099-01-01"), "Best Next Action": prop_checkbox(True), "Do = Today": prop_checkbox(True), "Quick Win": prop_checkbox(True), "Execution Rank": prop_number(2)}},
    {"id": "4", "properties": {"Task Name": prop_title("Closed stale task"), "Open Loop": prop_checkbox(False), "Do = Today": prop_checkbox(True), "Execution Score": prop_number(12)}},
]

summary = scan_pages(sample_pages)
for line in format_summary(summary):
    print(line)

assert summary.scanned == 4
assert summary.findings["done_presentation"].count == 1
assert summary.findings["closed_presentation_preview"].count == 2
assert summary.findings["closed_execution_preview"].count == 2
assert summary.findings["jdi_execution"].count == 1
assert summary.findings["deferred_surface"].count == 1
assert summary.findings["would_clear_quick_win_deferred"].count == 1
actions = collect_quick_win_deferred_cleanup_actions(sample_pages)
assert len(actions) == 1
assert actions[0]["title"] == "Deferred surfaced task"
assert actions[0]["quick_win_property"] == "Quick Win"
assert actions[0]["defer_until"] == "2099-01-01"
assert "Defer Until=2099-01-01" in summary.findings["deferred_surface"].examples[0]
assert "Best Next Action=true" in summary.findings["deferred_surface"].examples[0]
assert "Execution Rank=2" in summary.findings["deferred_surface"].examples[0]
assert "Reason: deferred until future date" in summary.findings["would_clear_quick_win_deferred"].examples[0]
assert "Quick Win=true" in summary.findings["would_clear_quick_win_deferred"].examples[0]
formatted = "\n".join(format_summary(summary))
assert "PHASE 1.5" in formatted
assert "Closed/done tasks observed:" in formatted
assert "Closed stale task" in formatted
assert "[Metadata Reconciliation] Finding detail:" in formatted
assert "Deferred surfaced task" in formatted
print("Smoke test passed")
