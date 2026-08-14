# === AIOS METADATA PERSISTENCE GUARD PHASE 2 BOOTSTRAP ===
# Must run near the top of run_aios.py before execution ranking persistence occurs.
try:
    from core.metadata.persistence_guard import install_closed_task_execution_persistence_guard
    install_closed_task_execution_persistence_guard()
except Exception as exc:
    print(f"[Metadata Persistence Guard] Bootstrap failed: {exc}")
# === END AIOS METADATA PERSISTENCE GUARD PHASE 2 BOOTSTRAP ===

print("=== EXECUTION AUTHORITY CONSOLIDATION — PHASE 6: SURFACED QUICK WIN LANE ===")
print("=== EXECUTION OVERLAY DERIVED FROM EXECUTION RANK / SCORE ===")

# ============================================================
# EXECUTION AUTHORITY CONSOLIDATION — PHASE 3
# Canonical execution authority:
# - Execution Score
# - Execution Rank
# - Best Next Action dashboard
# Legacy execution-state mutation remains disabled.
# ============================================================



def notion_paginated_query(url, headers, payload):
    """Execution Engine V2 paginated Notion query  helper."""

    all_results = []
    start_cursor = None
    page = 1

    while True:
        request_payload = dict(payload)

        if start_cursor:
            request_payload["start_cursor"] = start_cursor

        response = requests.post(
            url,
            headers=headers,
            json=request_payload
        )

        response.raise_for_status()

        data = response.json()

        batch = data.get("results", [])
        all_results.extend(batch)

        print(f"[Pagination] Page {page}: {len(batch)} results")

        if not data.get("has_more"):
            break

        start_cursor = data.get("next_cursor")
        page += 1

    print(f"[Pagination] Total results: {len(all_results)}")
    print("=== PAGINATION ACTIVE ===")

    return all_results


print("=== AIOS CLEAN CUTOVER v3 ===")
print("__file__ =", __file__)

from execution_engine_v2 import rebuild_execution_state
from aios.storage.execution_task_source import get_supabase_execution_tasks
from aios.storage.task_source import (
    get_supabase_quick_win_candidate_tasks,
    get_supabase_runtime_open_tasks,
    query_supabase_tasks_legacy,
)
from aios.storage.execution_state_writer import (
    build_execution_update_fn,
    build_quick_win_update_fn,
)
from aios.storage.task_metadata_writer import update_task_metadata
from aios.storage.task_lifecycle_writer import update_task_lifecycle
from aios.storage.task_creation_writer import (
    create_supabase_primary_task,
    create_supabase_primary_hierarchy,
)
from aios.storage.task_project_relation_writer import get_project_relation_writer
from aios.storage.project_creation_writer import create_supabase_project
from aios.storage.project_source import get_supabase_projects
from aios.storage.project_lifecycle_writer import get_project_lifecycle_writer

try:
    from core.evaluator import evaluate_task
    EVALUATOR_AVAILABLE = True
except Exception:
    EVALUATOR_AVAILABLE = False

#!/usr/bin/env python
# coding: utf-8

# # AIOS Notion Task Pipeline
# 
# Refactored notebook structure. The goal of this version is readability and safer testing; parent-child task linking is intentionally not added yet.
# 

# ## 1. Environment and global settings
# 

# In[1]:

import os
import sys
import re
import subprocess
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv, find_dotenv
try:
    from openai import OpenAI
except ModuleNotFoundError:
    OpenAI = None
from difflib import SequenceMatcher
from core.metadata.temporal import extract_temporal_metadata
from aios.ingestion.models import InboxItem

dotenv_path = find_dotenv() or ".env"
load_dotenv(dotenv_path, override=True)

def parse_env_bool(name, default=False):
    """Parse common truthy/falsey env var values safely.

    Accepts true/false, 1/0, yes/no, on/off. This avoids accidentally
    disabling features when an env var is written as RUN_FEATURE=1.
    """
    raw = os.getenv(name)
    if raw is None:
        return bool(default)

    value = str(raw).strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False

    print(f"⚠️ Unrecognized boolean value for {name}={raw!r}; using default {default}.")
    return bool(default)

# ----------------------------------------------------------------------------
# Runtime mode flags
# ----------------------------------------------------------------------------
# TEST_MODE runs the local regression harness and skips live writes later.
# TEST_ONLY is a fast path: run local tests only, with no Notion or OpenAI calls.
TEST_MODE = (
    parse_env_bool("TEST_MODE", False)
    or "--test" in sys.argv
)

TEST_ONLY = (
    parse_env_bool("TEST_ONLY", False)
    or "--test-only" in sys.argv
)

if TEST_ONLY:
    TEST_MODE = True

# -----------------------------------------------------------------------------
# Datastore authority
# -----------------------------------------------------------------------------
# Supabase is the default authoritative datastore for AIOS task and project
# state. Notion remains intentionally in use for Brain Dump, clarification,
# review, archive/context, dashboard presentation, and selected telemetry /
# logging workflows.
#
# Set AIOS_DATASTORE=notion explicitly only when the legacy Notion persistence
# path is required for fallback or testing.
AIOS_DATASTORE = (
    os.getenv("AIOS_DATASTORE", "supabase")
    .strip()
    .lower()
)

if AIOS_DATASTORE not in {"notion", "supabase"}:
    raise ValueError(
        "AIOS_DATASTORE must be 'notion' or 'supabase'"
    )

print(f"[Datastore] Configured datastore: {AIOS_DATASTORE}")

# Observational-only audit of actual Notion mutations during Supabase-mode runs.
if AIOS_DATASTORE == "supabase":
    try:
        from core.storage.supabase_authority_audit import install_supabase_authority_audit
        install_supabase_authority_audit(AIOS_DATASTORE)
    except Exception as exc:
        print(f"[Supabase Authority Audit] Bootstrap failed: {exc}")

# In TEST_ONLY mode, avoid requiring production secrets because no external API
# calls are made. In normal modes, keep failing fast if required env vars are missing.
if TEST_ONLY:
    NOTION_TOKEN = os.getenv("NOTION_TOKEN", "test-only-notion-token")
    BRAIN_DUMP_PAGE_ID = os.getenv("BRAIN_DUMP_PAGE_ID", "test-only-brain-dump-page-id")
    TASKS_DATABASE_ID = os.getenv("TASKS_DATABASE_ID", "test-only-tasks-database-id")
    ARCHIVE_TOGGLE_BLOCK_ID = os.getenv("ARCHIVE_TOGGLE_BLOCK_ID", "test-only-archive-toggle-block-id")
    AI_LOG_DATABASE_ID = os.getenv("NOTION_AI_LOG_DATABASE_ID", "")
else:
    NOTION_TOKEN = os.environ["NOTION_TOKEN"]
    BRAIN_DUMP_PAGE_ID = os.environ["BRAIN_DUMP_PAGE_ID"]
    TASKS_DATABASE_ID = os.environ["TASKS_DATABASE_ID"]
    ARCHIVE_TOGGLE_BLOCK_ID = os.environ["ARCHIVE_TOGGLE_BLOCK_ID"]
    AI_LOG_DATABASE_ID = os.getenv("NOTION_AI_LOG_DATABASE_ID", "")

AIOS_DASHBOARD_BLOCK_ID = os.getenv("AIOS_DASHBOARD_BLOCK_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# -----------------------------------------------------------------------------
# Run summary / lightweight production logging
# -----------------------------------------------------------------------------
RUN_STARTED_AT = datetime.now()

RUN_SUMMARY = {
    "inbox_extracted": 0,
    "open_tasks_found": 0,
    "matches": 0,
    "possible_matches": 0,
    "possible_duplicate_blocks_added": 0,
    "duplicate_inbox_items": 0,
    "new_items_identified": 0,
    "items_processed": 0,
    "items_left_for_later": 0,
    "tasks_created": 0,
    "breakdown_parents_created": 0,
    "breakdown_subtasks_created": 0,
    "clarification_tasks_created": 0,
    "clarification_blocks_added": 0,
    "clarification_selections_resolved": 0,
    "metadata_updates": 0,
    "importance_updates": 0,
    "metadata_log_entries": 0,
    "quick_win_updates": 0,
    "surfaced_quick_win_updates": 0,
    "matched_items_updated": 0,
    "items_archived": 0,
    "archive_runs_trimmed": 0,
    "ai_log_entries_created": 0,
    "ai_log_errors": 0,
    "task_notes_added": 0,
    "non_task_notes_routed": 0,
    "non_task_ideas_routed": 0,
    "project_candidates_detected": 0,
    "project_candidate_log_entries": 0,
    "suggested_project_updates": 0,
    "project_relation_updates": 0,
    "project_relation_skipped": 0,
    "project_records_created": 0,
    "project_record_create_skipped": 0,
    "actively_edited_skipped": 0,
    "errors": 0,
}

def increment_summary(key, amount=1):
    """Increment a run-summary counter without risking pipeline failure."""
    RUN_SUMMARY[key] = RUN_SUMMARY.get(key, 0) + amount

def _notion_rich_text(value, max_length=1900):
    """Build a safe Notion rich_text value with conservative length limits."""
    text = str(value or "")[:max_length]
    return {"rich_text": [{"type": "text", "text": {"content": text}}]} if text else {"rich_text": []}

def log_ai_processing_decision(
    original,
    final_task="",
    action="Created",
    reason="",
    review_needed=False,
    confidence=None,
    source="Brain Dump",
    suggested_project="",
):
    """Append a lightweight decision row to the AI Processing Log database.

    Logging must never block task creation, archiving, notifications, or tests.
    If NOTION_AI_LOG_DATABASE_ID is missing, logging quietly no-ops.
    """
    if TEST_MODE or DRY_RUN:
        return False

    if not AI_LOG_DATABASE_ID:
        return False

    name = str(final_task or original or "AIOS decision")[:2000]

    properties = {
        "Name": {"title": [{"type": "text", "text": {"content": name}}]},
        "Original": _notion_rich_text(original),
        "Final Task": _notion_rich_text(final_task),
        "Action": {"select": {"name": action}},
        "Reason": _notion_rich_text(reason),
        "Review Needed": {"checkbox": bool(review_needed)},
        "Run Time": {"date": {"start": datetime.now().isoformat()}},
        "Source": {"select": {"name": source}},
    }

    if suggested_project:
        properties["Suggested Project"] = _notion_rich_text(suggested_project)

    if confidence is not None:
        try:
            properties["Confidence"] = {"number": float(confidence)}
        except (TypeError, ValueError):
            pass

    try:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json={
                "parent": {"database_id": AI_LOG_DATABASE_ID},
                "properties": properties,
            },
            timeout=30,
        )

        print(
            "[Metadata PATCH Result]",
            response.status_code,
        )
        if response.ok:
            increment_summary("ai_log_entries_created")
            return True

        increment_summary("ai_log_errors")
        print("⚠️ AI processing log failed:", response.status_code, response.text)
        return False

    except Exception as e:
        increment_summary("ai_log_errors")
        print("⚠️ AI processing log failed:", e)
        return False

def task_decision_log_reason(original_title, prepared_title, decision):
    """Explain a keep / clarify / breakdown decision in plain language."""
    if decision == "breakdown":
        return "Clear multi-step task; created a parent task and ordered subtasks."
    if decision == "clarify":
        return "Missing essential context or next action; created a clarification task."
    if prepared_title != original_title:
        return "Created task after deterministic/AI title cleanup."
    return "Clear actionable task; created as a normal task."

def task_decision_review_needed(original_title, prepared_title, decision):
    """Flag only the most useful borderline items for Notion review."""
    if decision == "clarify":
        return True
    if decision == "breakdown" and rule_based_breakdown_decision(prepared_title) == "uncertain":
        return True
    if prepared_title.lower().startswith("clarify next action:"):
        return True
    return False

def _applescript_quote(text):
    """Escape text safely for an AppleScript string literal."""
    return str(text).replace("\\", "\\\\").replace('"', '\\"')

def send_macos_notification(title, subtitle, message, sound_name="Glass"):
    """Send a macOS notification without relying on Shortcuts notifications.

    This uses osascript directly, so notification permissions usually appear
    under Script Editor, Terminal, or the app that launched the script.
    """
    if TEST_ONLY or parse_env_bool("AIOS_DISABLE_NOTIFICATIONS", False):
        return False

    script = (
        f'display notification "{_applescript_quote(message)}" '
        f'with title "{_applescript_quote(title)}" '
        f'subtitle "{_applescript_quote(subtitle)}" '
        f'sound name "{_applescript_quote(sound_name)}"'
    )

    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=10)
        return True
    except Exception as e:
        print("Notification failed:", e)
        return False

def is_probably_cron_run():
    """Return True only when cron explicitly marks this as a cron run.

    Do not infer cron from TERM being absent. macOS Shortcuts can also run
    without TERM, and those manual runs should still show notifications.

    Cron suppression is controlled by setting AIOS_CRON=true in crontab.
    AIOS_FORCE_NOTIFICATIONS=true can override this for testing;
    AIOS_DISABLE_NOTIFICATIONS=true still wins inside send_macos_notification().
    """
    if parse_env_bool("AIOS_FORCE_NOTIFICATIONS", False):
        return False

    return parse_env_bool("AIOS_CRON", False)

def get_created_task_titles(limit=2):
    """Return the first created task titles for the end-of-run notification."""
    titles = []

    for task in globals().get("created_tasks", []):
        title = ""

        if isinstance(task, dict):
            title = task.get("title") or get_title(task)

        if title:
            titles.append(title)

        if len(titles) >= limit:
            break

    return titles

def build_run_notification_text():
    """Build a high-signal end-of-run macOS notification from RUN_SUMMARY."""
    created_count = RUN_SUMMARY["tasks_created"]
    clarification_count = RUN_SUMMARY["clarification_tasks_created"]
    quick_win_count = RUN_SUMMARY["quick_win_updates"]

    other_updates = (
        RUN_SUMMARY["matched_items_updated"]
        + RUN_SUMMARY["metadata_updates"]
    )

    lines = []

    if created_count > 0:
        lines.append(f"🆕 Created: {created_count}")

        for title in get_created_task_titles(limit=2):
            lines.append(f"• {title}")

        extra_created = created_count - len(get_created_task_titles(limit=2))
        if extra_created > 0:
            lines.append(f"• +{extra_created} more")

    if clarification_count > 0:
        lines.append(f"❓ Needs clarification: {clarification_count}")

    if quick_win_count > 0:
        lines.append(f"⚡ Quick Win updates: {quick_win_count}")

    if other_updates > 0:
        lines.append(f"🔄 Other updates: {other_updates}")

    if RUN_SUMMARY["items_archived"] > 0:
        lines.append(f"📦 Archived: {RUN_SUMMARY['items_archived']}")

    if RUN_SUMMARY["errors"] > 0:
        lines.append(f"⚠️ Errors: {RUN_SUMMARY['errors']}")

    if not lines:
        lines.append("No new items")

    return "\n".join(lines)

def notify_run_summary():
    """Send a concise macOS notification when a manual run finishes.

    Cron/background runs are suppressed to avoid notification spam. Cron still
    receives the normal printed run summary in the log.
    """
    if is_probably_cron_run():
        print("Notification skipped: cron/background run detected")
        return False

    elapsed_seconds = round((datetime.now() - RUN_STARTED_AT).total_seconds(), 1)
    created = RUN_SUMMARY.get("tasks_created", 0)
    errors = RUN_SUMMARY.get("errors", 0)

    if errors > 0:
        title = "AIOS ⚠️ ERROR"
        sound = "Basso"
    elif created > 0:
        title = "AIOS 🆕 Update"
        sound = "Glass"
    else:
        title = "AIOS ✓"
        sound = "Glass"

    subtitle = f"⏱ {elapsed_seconds}s"
    message = build_run_notification_text()

    return send_macos_notification(title, subtitle, message, sound_name=sound)

def print_run_summary():
    """Print a compact production summary for cron logs."""
    finished_at = datetime.now()
    elapsed_seconds = round((finished_at - RUN_STARTED_AT).total_seconds(), 1)

    print()
    print("--- Run summary ---")
    print(f"Started:  {RUN_STARTED_AT.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Finished: {finished_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Elapsed:  {elapsed_seconds}s")

    print(
        "Inbox — "
        f"Extracted: {RUN_SUMMARY['inbox_extracted']}, "
        f"New: {RUN_SUMMARY['new_items_identified']}, "
        f"Processed: {RUN_SUMMARY['items_processed']}, "
        f"Left for later: {RUN_SUMMARY['items_left_for_later']}"
    )

    print(
        "Matching — "
        f"Exact/high matches: {RUN_SUMMARY['matches']}, "
        f"Possible matches: {RUN_SUMMARY['possible_matches']}, "
        f"Duplicate inbox items: {RUN_SUMMARY['duplicate_inbox_items']}"
    )

    print(
        "Tasks — "
        f"Created: {RUN_SUMMARY['tasks_created']}, "
        f"Breakdown parents: {RUN_SUMMARY['breakdown_parents_created']}, "
        f"Breakdown subtasks: {RUN_SUMMARY['breakdown_subtasks_created']}, "
        f"Clarification tasks: {RUN_SUMMARY['clarification_tasks_created']}"
    )

    print(
        "Updates — "
        f"Matched items: {RUN_SUMMARY['matched_items_updated']}, "
        f"Metadata: {RUN_SUMMARY['metadata_updates']}, "
        f"Importance: {RUN_SUMMARY.get('importance_updates', 0)}, "
        f"Quick Win: {RUN_SUMMARY['quick_win_updates']}, "
        f"Surfaced Quick Win: {RUN_SUMMARY.get('surfaced_quick_win_updates', 0)}"
    )

    print(
        "Archive / review — "
        f"Archived items: {RUN_SUMMARY['items_archived']}, "
        f"Clarification blocks added: {RUN_SUMMARY['clarification_blocks_added']}, "
        f"Possible duplicate blocks added: {RUN_SUMMARY['possible_duplicate_blocks_added']}, "
        f"Archive runs trimmed: {RUN_SUMMARY['archive_runs_trimmed']}"
    )

    print(
        "AI log — "
        f"Entries: {RUN_SUMMARY.get('ai_log_entries_created', 0)}, "
        f"Metadata entries: {RUN_SUMMARY.get('metadata_log_entries', 0)}, "
        f"Errors: {RUN_SUMMARY.get('ai_log_errors', 0)}"
    )

    print(f"Task notes added: {RUN_SUMMARY.get('task_notes_added', 0)}")
    print(f"Non-task notes routed: {RUN_SUMMARY.get('non_task_notes_routed', 0)}")
    print(f"Non-task ideas routed: {RUN_SUMMARY.get('non_task_ideas_routed', 0)}")
    print(f"Project candidates detected: {RUN_SUMMARY.get('project_candidates_detected', 0)}")
    print(f"Suggested Project updates: {RUN_SUMMARY.get('suggested_project_updates', 0)}")
    print(f"Project relations updated: {RUN_SUMMARY.get('project_relation_updates', 0)}")
    print(f"Project records created: {RUN_SUMMARY.get('project_records_created', 0)}")
    print(f"Errors: {RUN_SUMMARY['errors']}")

    total_updates = (
        RUN_SUMMARY["matched_items_updated"]
        + RUN_SUMMARY["metadata_updates"]
        + RUN_SUMMARY["quick_win_updates"]
    )

    print(
        f"{finished_at.strftime('%Y-%m-%d %H:%M:%S')} — "
        f"Run complete — Created: {RUN_SUMMARY['tasks_created']}, "
        f"Updated: {total_updates}, "
        f"Archived: {RUN_SUMMARY['items_archived']}, "
        f"Errors: {RUN_SUMMARY['errors']}"
    )

# In[2]:

# -----------------------------------------------------------------------------
# Run mode / safety controls
# -----------------------------------------------------------------------------
# DRY_RUN = True: print what would happen without writing to Notion.
# DRY_RUN = False: create real tasks/blocks in Notion.
DRY_RUN = False

# Controlled production guardrail. When DRY_RUN is False, only this many new
# inbox items will be processed per run. Set to None later when you trust the flow.
MAX_ITEMS_PER_RUN = 5

# Keep this True for normal production. Set False only if you want to create
# tasks while leaving original Brain Dump items in place for manual inspection.
ARCHIVE_PROCESSED_ITEMS = True

# TEST_MODE and TEST_ONLY are controlled by env vars or CLI flags near the top
# of this file. Examples:
#   python run_aios.py --test
#   python run_aios.py --test-only
#   TEST_ONLY=true python run_aios.py

# Pipeline mode switches. Keep task creation on for normal Brain Dump processing.
RUN_TASK_CREATION_PIPELINE = True
if TEST_MODE:
    RUN_TASK_CREATION_PIPELINE = False

# Legacy execution-state mutation is intentionally disabled.
# Do = Today remains a manual-only Notion flag. Execution Engine V2 owns
# Execution Score / Execution Rank / Best Next Action selection.
DEFER_UNTIL_PROPERTY = "Defer Until"
DUE_DATE_PROPERTY = "Due Date"

# Execution engine properties
EXECUTION_SCORE_PROPERTY = "Execution Score"
EXECUTION_RANK_PROPERTY = "Execution Rank"

# Quick Win surfacing properties
# Quick Win = eligibility metadata. Surfaced Quick Win = capped presentation lane.
QUICK_WIN_PROPERTY = "Quick Win"
SURFACED_QUICK_WIN_PROPERTY = os.getenv("SURFACED_QUICK_WIN_PROPERTY", "Surfaced Quick Win")
SURFACED_QUICK_WIN_LIMIT = int(os.getenv("SURFACED_QUICK_WIN_LIMIT", "5"))

# Project candidate detector.
# V1 is review-only: it prints/logs candidate project groupings but does not
# create projects or change task relations.
RUN_PROJECT_CANDIDATE_DETECTOR = True
PROJECT_CANDIDATE_SCAN_LIMIT = 25
PROJECT_CANDIDATE_MAX_RELATED_TASKS = 8
PROJECT_CANDIDATE_MIN_RELATED_TASKS = 1
PROJECT_CANDIDATE_MIN_CONFIDENCE = 0.65
PROJECT_CANDIDATE_MIN_RELATED_AFTER_EXPANSION = 2

# Phase 3 project relation write-back.
# Conservative: link only to an existing active project when the candidate
# clearly matches exactly one project and the task has no existing relation.
#
# PROJECTS_DATABASE_ID used to be referenced later without being loaded here,
# which caused the project candidate detector to crash after task creation when
# relation write-back was enabled. Load it in both normal and test modes so the
# detector and its tests can safely inspect the setting.
PROJECTS_DATABASE_ID = (
    os.getenv("PROJECTS_DATABASE_ID")
    or os.getenv("PROJECT_DATABASE_ID")
    or os.getenv("NOTION_PROJECTS_DATABASE_ID")
    or os.getenv("NOTION_PROJECT_DATABASE_ID")
    or ""
)
RUN_PROJECT_RELATION_WRITEBACK = parse_env_bool("RUN_PROJECT_RELATION_WRITEBACK", True)
PROJECT_RELATION_WRITEBACK_RAW = os.getenv("RUN_PROJECT_RELATION_WRITEBACK")
SUGGESTED_PROJECT_PROPERTY = os.getenv("SUGGESTED_PROJECT_PROPERTY", "Suggested Project")
TASK_PROJECT_RELATION_PROPERTY = os.getenv("TASK_PROJECT_RELATION_PROPERTY", "Project")
PROJECT_TITLE_PROPERTY = os.getenv("PROJECT_TITLE_PROPERTY", "Project Name")
PROJECT_STATUS_PROPERTY = os.getenv("PROJECT_STATUS_PROPERTY", "Status")
PROJECT_ACTIVE_PROPERTY = os.getenv("PROJECT_ACTIVE_PROPERTY", "Active")
RUN_PROJECT_STUB_CREATION = parse_env_bool("RUN_PROJECT_STUB_CREATION", True)
PROJECT_STUB_STATUS_VALUE = os.getenv("PROJECT_STUB_STATUS_VALUE", "Someday")
PROJECT_LINK_MIN_CONFIDENCE = float(os.getenv("PROJECT_LINK_MIN_CONFIDENCE", "0.85"))
PROJECT_LINK_MIN_MATCH_SCORE = float(os.getenv("PROJECT_LINK_MIN_MATCH_SCORE", "0.92"))
PROJECT_LINK_AMBIGUITY_MARGIN = float(os.getenv("PROJECT_LINK_AMBIGUITY_MARGIN", "0.08"))
ACTIVE_PROJECT_STATUS_VALUES = {"Active", "In Progress", "Current", "Ongoing"}
INACTIVE_PROJECT_STATUS_VALUES = {"Completed", "Done", "Archived", "Paused", "Someday"}

# Project candidate detector.
# V1 is review-only: it prints/logs candidate project groupings but does not
# create projects or change task relations.

# Sequential breakdown support.
# Required Notion properties:
# - Parent Task: relation to this same Tasks database
# - Step Order: number
PARENT_TASK_PROPERTY = "Parent Task"
STEP_ORDER_PROPERTY = "Step Order"

# ## 1.1 🧪 Quick test runner / navigation
# 
# Use this section when you want to run the local task tests without hunting through the notebook.
# 
# - Set `TEST_MODE = True` in the run-mode cell above.
# - Run this quick runner cell after the notebook has loaded once, or use **Kernel → Restart & Run All**.
# - In `TEST_MODE`, live Notion writes are skipped.
# 
# You can also jump to the full section by searching for: `TASK CLASSIFICATION TEST HARNESS`.
# 

# In[3]:

# 🧪 QUICK TEST RUNNER
# Run this cell any time after the notebook has loaded once.
# On a fresh Kernel → Restart & Run All, this cell appears before the harness is
# defined, so it prints a reminder; the harness will auto-run later when loaded.

def run_tests_from_top():
    """Convenience wrapper so tests can be run from the top of the notebook."""
    if "run_task_classification_tests" not in globals():
        print(
            "Test harness is not loaded yet. Run the notebook once, or jump to "
            "the section named 'TASK CLASSIFICATION TEST HARNESS'."
        )
        return None

    print("🚀 Running local task classification tests from the top runner...")
    return run_task_classification_tests()

if TEST_MODE:
    if "run_task_classification_tests" in globals():
        run_tests_from_top()
    else:
        print(
            "TEST_MODE is ON. Tests will auto-run later at the "
            "🧪 TASK CLASSIFICATION TEST HARNESS section."
        )
else:
    print("Test runner ready. Set TEST_MODE = True, then run_tests_from_top() after the notebook has loaded.")

# ## 2. Constants and command labels
# 

# In[4]:

HIGH_MATCH_THRESHOLD = 0.90
MEDIUM_MATCH_THRESHOLD = 0.75

ACTIVE_EDIT_GRACE_SECONDS = 60

# In[5]:

POSSIBLE_DUPLICATE_HEADER = "🔁 Possible duplicate"
LINK_EXISTING_COMMAND = "✅ Use existing task"
CREATE_ANYWAY_COMMAND = "➕ Create as new task anyway"
IGNORE_DUPLICATE_COMMAND = "🚫 Ignore this inbox item"

# In[6]:

MATCH_WORD_EQUIVALENTS = {
    # verbs
    "book": "schedule",
    "schedule": "schedule",
    "reserve": "schedule",
    "arrange": "schedule",

    "ask": "contact",
    "call": "contact",
    "email": "contact",
    "message": "contact",
    "text": "contact",

    # nouns
    "visit": "appointment",
    "appt": "appointment",
    "appointment": "appointment",

    "support": "service",
    "help": "service",
}

# In[7]:

COMMON_ACTION_VERBS = [
    # Communication / admin
    "ask", "get", "call", "email", "message", "text", "reply", "follow", "schedule",
    "book", "confirm", "cancel", "reschedule",

    # Work / general tasks
    "update", "change", "review", "check", "submit", "send", "invite", "write",
    "read", "edit", "prepare", "plan", "organize", "create",
    "design", "redesign", "draft", "develop", "mockup", "research", "conduct",
    "brainstorm", "outline", "prioritize", "prioritise",
    "build", "launch", "arrange", "set", "setup", "configure", "make", "complete", "bulk",

    # Digital / systems
    "upload", "download", "install", "run", "test", "fix",
    "replace", "add", "remove", "sort", "file", "print", "backup",

    # 👉 Login / access (NEW)
    "log", "login", "sign", "signin", "sign-in",

    # Errands / life admin
    "buy", "order", "pick", "pickup", "drop", "dropoff",
    "deliver", "return", "renew", "pay", "deposit",

    # Household / physical tasks
    "pack", "unpack", "package", "label", "wrap",
    "bring", "take", "carry",
    "wash", "clean", "tidy", "wipe", "scrub", "rinse",
    "sweep", "vacuum", "mop",
    "fold", "hang", "put", "store", "tidy",
    "empty", "fill", "refill", "load", "unload",

    # Kitchen / bakery
    "cook", "bake", "prep", "mix", "shape", "grind", "brew",
    "feed", "refresh", "scale", "weigh", "mill",
    "slice", "cut", "pack", "label", "deliver",

    # Misc useful verbs
    "find", "look", "track", "measure", "record",
    "clarify"
]

# In[8]:

QUICK_WIN_ACTION_VERBS = {
    # Communication / admin
    "ask", "get", "call", "email", "message", "text", "reply", "follow", "confirm",

    # Scheduling / coordination
    "book", "schedule", "reschedule", "cancel",

    # Transactions / errands
    "get", "pay", "buy", "order", "return", "renew", "deposit",

    # Quick digital actions
    "update", "check", "submit", "send", "invite", "print", "file", "upload", "download",

    # Pickup / movement
    "pick", "pickup", "drop", "dropoff", "bring", "take",

    # Household / light physical tasks
    "pack", "unpack", "label", "wrap", "wash", "clean", "wipe", "sort", "store",

    # Simple utility actions
    "find", "look", "replace", "add", "remove", "fix", "test", "run",
}

# In[9]:

NOT_QUICK_WIN_WORDS = {
    "plan",
    "research",
    "prepare",
    "design",
    "develop",
    "figure out",
    "organize",
    "investigate",
    "explore",
    "review",
}

# In[10]:

CLARIFY_STATUS = "Needs Clarification"
READY_STATUS = "Ready"

GENERATE_MORE_COMMAND = "⚙️ Generate more options"  # legacy pages only
ADD_OWN_OPTION_COMMAND = "✏️ Add your own checkbox above, then check it"  # legacy pages only
ASK_TARGETED_QUESTION_COMMAND = "❓ Ask me one targeted question"
USE_SUGGESTION_PREFIX = "✅ Use this clarification: "

CLARIFY_HEADER = "🔍 Clarify next action"
CHOOSE_PROMPT = "💡 Choose the first action you would take:"
ANALYTICAL_CHOOSE_PROMPT = "💡 Choose the first outcome-producing step:"
DEFINE_PROMPT = "💡 Answer one question to define this task:"
CLARIFICATION_ANALYTICAL_MODE_VERSION = "clarification-proposal-first-v2.1"
print("=== CLARIFICATION PROPOSAL-FIRST V2.1 ACTIVE ===")

# In[11]:

#
# Constants
#

# In[12]:

VAGUE_WORDS = [
    "thing",
    "stuff",
    "guy",
    "someone",
    "something",
]

# In[13]:

WEAK_REFERENCE_WORDS = [
    "this",
    "that",
    "it",
]

# Non-task routing. V1 keeps this intentionally conservative: only obvious
# informational/reference bullets are moved out of task creation. Borderline
# items continue through the normal task / clarification pipeline.
NON_TASK_NOTE_SECTION_HEADER = "📝 Notes / Reference"
NON_TASK_IDEA_SECTION_HEADER = "💡 Ideas / Backlog"
NON_TASK_REVIEW_SECTION_HEADER = "❓ Needs Review"

NON_TASK_DECISIONS = {"task", "note", "idea", "review"}

# ## 3. Notion API helpers
# 
# Low-level helpers for reading block text, finding the synced Brain Dump block, querying open tasks, and archiving processed inbox items.
# 

# In[14]:

CANONICAL_BLOCK_TEXT_CALLOUT_SUPPORT = "callout-text-v1"

def get_block_text(block):
    block_type = block.get("type")

    if block_type not in [
        "paragraph",
        "bulleted_list_item",
        "numbered_list_item",
        "to_do",
        "toggle",
        "heading_1",
        "heading_2",
        "heading_3",
        "callout",
    ]:
        return ""

    rich_text = block.get(block_type, {}).get("rich_text", [])

    return "".join(
        rt.get("plain_text", "")
        for rt in rich_text
    ).strip()

# In[15]:

def get_block_children(block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    all_blocks = []

    while url:
        response = requests.get(url, headers=headers, timeout=30)

        if not response.ok:
            increment_summary("errors")
            print("ERROR fetching block children")
            print(response.status_code, response.text)
            return []

        data = response.json()
        all_blocks.extend(data.get("results", []))

        if data.get("has_more"):
            next_cursor = data.get("next_cursor")
            url = f"https://api.notion.com/v1/blocks/{block_id}/children?start_cursor={next_cursor}"
        else:
            url = None

    return all_blocks

# In[16]:

def get_block(block_id):
    """Fetch one Notion block by ID, returning {} on failure."""
    if not block_id:
        return {}

    response = requests.get(
        f"https://api.notion.com/v1/blocks/{block_id}",
        headers=headers,
        timeout=30,
    )

    if response.ok:
        return response.json()

    increment_summary("errors")
    print("ERROR fetching block:", block_id)
    print(response.status_code, response.text)
    return {}

def get_archive_sibling_parent_id():
    """Return the parent container that holds the Archive toggle.

    Persistent non-task stores should live beside Archive, not inside it.
    Notion lets us append children to either a page_id or block_id, so the
    returned parent ID can be used directly with /blocks/{id}/children.
    """
    archive_block = get_block(ARCHIVE_TOGGLE_BLOCK_ID)
    parent = archive_block.get("parent", {})

    for key in ["page_id", "block_id"]:
        if parent.get(key):
            return parent[key]

    return BRAIN_DUMP_PAGE_ID





# In[17]:

BRAIN_DUMP_TASK_BLOCK_TYPES = ["paragraph", "bulleted_list_item", "numbered_list_item", "to_do"]
BRAIN_DUMP_NOTE_BLOCK_TYPES = ["paragraph", "bulleted_list_item", "numbered_list_item", "to_do"]



# -------------------------------------------------------------------------
# Source-neutral Brain Dump ingestion boundary
# -------------------------------------------------------------------------
from aios.ingestion import notion_source as notion_inbox_source

notion_inbox_source.configure_notion_source(globals())

inbox_source = notion_inbox_source.NotionInboxSource(
    BRAIN_DUMP_PAGE_ID
)

print("[Inbox Source] Notion Brain Dump source configured")


# In[18]:

def get_open_tasks():
    """
    Return the task population used by the Brain Dump / clarification runtime.

    Preserve historical semantics exactly:
      Open Loop = True
      Done = False

    Note that this path intentionally does NOT add Archived=False because the
    legacy Notion query did not include that filter.
    """

    if AIOS_DATASTORE == "supabase":
        print(
            "[Task Read] Reading runtime open tasks "
            "from Supabase"
        )

        return (
            get_supabase_runtime_open_tasks()
        )

    url = (
        "https://api.notion.com/v1/"
        f"databases/{TASKS_DATABASE_ID}/query"
    )

    payload = {
        "filter": {
            "and": [
                {
                    "property":
                        "Open Loop",
                    "checkbox": {
                        "equals":
                            True,
                    },
                },
                {
                    "property":
                        "Done",
                    "checkbox": {
                        "equals":
                            False,
                    },
                },
            ]
        },
        "page_size": 100,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    if not response.ok:
        increment_summary(
            "errors"
        )
        print(
            "ERROR querying tasks"
        )
        print(
            response.status_code,
            response.text,
        )
        return []

    return (
        response.json()
        .get(
            "results",
            [],
        )
    )

# In[19]:

def get_title(page):
    props = page.get("properties", {})

    for prop in props.values():
        if prop.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in prop.get("title", []))

    return ""

# In[20]:


# In[21]:


# In[22]:









# In[23]:


# -------------------------------------------------------------------------
# Canonical Notion Brain Dump archive module
# -------------------------------------------------------------------------
# Archive/presentation helpers now live in aios.notion.archive. Runtime globals
# are injected conservatively so this extraction changes ownership, not behavior.
from aios.notion import archive as archive_helpers

archive_helpers.configure_archive_module(globals())

create_archive_section = archive_helpers.create_archive_section
archive_item = archive_helpers.archive_item
append_archive_toggle = archive_helpers.append_archive_toggle
find_child_toggle_by_title = archive_helpers.find_child_toggle_by_title
get_or_create_archive_toggle = archive_helpers.get_or_create_archive_toggle
archive_non_task_item = archive_helpers.archive_non_task_item
archive_non_task_note_item = archive_helpers.archive_non_task_note_item
archive_non_task_idea_item = archive_helpers.archive_non_task_idea_item
delete_original_block = archive_helpers.delete_original_block
trim_archive_runs = archive_helpers.trim_archive_runs

print("[Notion Archive Module] Canonical Brain Dump archive helpers loaded")

# Refresh Notion inbox-source dependencies now that canonical archive
# lifecycle helpers (including delete_original_block) are available.
notion_inbox_source.configure_notion_source(globals())
print("[Inbox Source] Notion lifecycle dependencies refreshed")


# ## 4. Text cleanup and actionability checks
# 
# These helpers normalize titles, detect vague wording, decide whether AI cleanup is needed, and avoid over-processing obvious tasks.
# 

# In[24]:

def normalize(text):
    text = re.sub(r"\s+", " ", text.strip().lower())

    words = text.split()

    normalized_words = [
        MATCH_WORD_EQUIVALENTS.get(word, word)
        for word in words
    ]

    return " ".join(normalized_words)

# In[25]:


def clean_task_title(text):
    title = text.strip()

    # Remove common capture prefixes
    title = re.sub(r"^(remember to|need to|i need to|todo:|to do:)\s+", "", title, flags=re.IGNORECASE)

    # Normalize spacing and separator debris
    title = sanitize_task_title_separators(title)

    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    return title

# In[26]:

def words_in(title):
    return re.findall(r"\b\w+\b", title.lower())

def contains_vague_word(title):
    words = words_in(title)
    return any(word in VAGUE_WORDS for word in words)

def contains_weak_reference(title):
    words = words_in(title)
    return any(word in WEAK_REFERENCE_WORDS for word in words)

def has_unresolved_placeholder_reference(title):
    """Return True for unrecoverably vague placeholder tasks.

    Clarification should remain a last resort. This guard only catches titles
    where the rewrite layer still has no concrete object after cleanup, e.g.:
    - Fix this
    - Deal with that
    - Look into it
    - Fix the issue
    - Resolve the problem

    Concrete domain/context nouns keep flowing normally:
    - Fix Bread Basket login issue
    - Check execution rankings for issues
    - Review ranking health
    """
    text = re.sub(r"\s+", " ", str(title or "").lower()).strip()
    words = words_in(text)

    if not words or text.startswith("clarify next action:"):
        return False

    placeholder_terms = {"this", "that", "it"}
    generic_problem_terms = {"issue", "issues", "problem", "problems"}
    filler_terms = {"the", "a", "an", "with", "about", "for", "to", "into", "on"}

    if any(w in placeholder_terms for w in words):
        # Very short action + placeholder phrases have no recoverable context.
        non_filler = [w for w in words if w not in filler_terms]
        if len(non_filler) <= 3:
            return True

    if any(w in generic_problem_terms for w in words):
        # "Fix the issue" / "Resolve problem" should clarify, but domain-rich
        # variants like "Fix Bread Basket login issue" should not.
        non_filler = [w for w in words if w not in filler_terms]
        if len(non_filler) <= 3:
            return True

    return False


def starts_with_action_verb(title):
    words = words_in(title)
    return bool(words) and words[0] in COMMON_ACTION_VERBS

def has_action_verb(title):
    words = words_in(title)
    return any(word in COMMON_ACTION_VERBS for word in words)

def title_starts_with_quick_win_verb(title):
    """Return True when a title starts with a known quick-win action verb.

    This helper is used by early title-preparation logic and by the test
    harness, so it must live before needs_soft_rewrite(), the test harness,
    clarification processing, and the main task pipeline.
    """
    if not title:
        return False

    words = words_in(title)
    if not words:
        return False

    return words[0] in QUICK_WIN_ACTION_VERBS

OBVIOUS_SINGLE_STEP_TASKS = {
    # Personal / household routines that are already actionable even when
    # written as a one-word task. Keep this list intentionally explicit so
    # genuinely vague noun-only tasks such as "Packaging labels" still clarify
    # or receive deterministic action rewriting.
    "shower",
    "brush teeth",
    "floss",
    "wash face",
    "wash hands",
    "get dressed",
    "go to bed",
    "wake up",
    "take vitamins",
    "take medication",
    "eat breakfast",
    "eat lunch",
    "eat dinner",
}

def is_obvious_single_step_task(title):
    """Return True for obvious routines that should not trigger clarification.

    These are tasks where the next action is self-evident even if the title
    does not start with a conventional action verb. This is different from
    SAFE_NOUN_TASK_ACTIONS: we preserve the user's title instead of rewriting
    "Shower" to something unnatural like "Take shower".
    """
    text = re.sub(r"\s+", " ", str(title or "").lower()).strip()

    if not text or text.startswith("clarify next action:"):
        return False

    return text in OBVIOUS_SINGLE_STEP_TASKS

OPERATIONAL_SINGLE_STEP_VERBS = {
    "refill", "fill", "empty", "load", "unload", "wash", "clean", "wipe",
    "rinse", "scrub", "sweep", "vacuum", "mop", "fold", "hang", "put",
    "store", "pack", "unpack", "label", "wrap", "slice", "cut", "scale",
    "weigh", "mill", "feed", "refresh", "mix", "shape", "bake", "prep",
    "rotate", "replace", "restock", "tidy", "bulk",
}

OPERATIONAL_COMPLETION_NOUNS = {
    "container", "containers", "bin", "bins", "jar", "jars", "bucket", "buckets",
    "tub", "tubs", "tray", "trays", "rack", "racks", "dishwasher", "sink",
    "counter", "counters", "bench", "flour", "starter", "levain", "soaker",
    "banneton", "bannetons", "pan", "pans", "tin", "tins", "bag", "bags",
    "box", "boxes", "shelf", "shelves", "tank", "bottle", "bottles",
}

def is_immediately_actionable_operational_task(title):
    """Return True for clear physical/operational tasks that need no clarification.

    These are short concrete tasks where a competent person can start and where
    completion is observable, even if the title omits location or fine detail.
    Example: "Refill container of bench flour".
    """
    text = str(title or "").strip()
    lower = text.lower()
    words = words_in(text)

    if not words or lower.startswith("clarify next action:"):
        return False

    if contains_vague_word(text) or contains_weak_reference(text):
        return False

    if words[0] not in OPERATIONAL_SINGLE_STEP_VERBS:
        return False

    if len(words) < 2 or len(words) > 8:
        return False

    # Require either a concrete operational object or an "of/with/into" object
    # phrase so generic titles like "Clean" still cannot bypass clarification.
    has_operational_object = bool(set(words[1:]) & OPERATIONAL_COMPLETION_NOUNS)
    has_object_phrase = any(w in words for w in ["of", "with", "into", "onto", "from"])

    return has_operational_object or has_object_phrase



def is_clear_preparation_task(title):
    """Return True for obvious preparation/setup tasks.

    These are concrete operational prep tasks that may omit
    fine detail but are still immediately executable.
    Examples:
    - Grind coffee beans
    - Mill flour for workshop
    - Prep bannetons
    """

    text = str(title or "").strip()
    lower = text.lower()
    words = words_in(text)

    if not words or lower.startswith("clarify next action:"):
        return False

    if contains_vague_word(text):
        return False

    first_word = words[0]

    preparation_verbs = {
        "grind",
        "mill",
        "prep",
        "prepare",
        "slice",
        "label",
        "package",
    }

    preparation_nouns = {
        "coffee",
        "beans",
        "flour",
        "starter",
        "bannetons",
        "labels",
        "dough",
        "grain",
        "grains",
    }

    if first_word not in preparation_verbs:
        return False

    return bool(set(words[1:]) & preparation_nouns)

ATOMIC_ACTION_VERBS = [
    "ask",
    "invite",
    "get",
    "open",
    "reopen",
    "restart",
    "call",
    "email",
    "text",
    "check",
    "review",
    "change",
    "replace",
    "print",
    "buy",
    "order",
    "book",
    "pay",
    "submit",
    "schedule",
    "cancel",
    "renew",
    "pair",
    "connect",
    "move",
    "relocate",
]

def is_atomic_action(title):
    """Return True for clear, single-execution tasks that should not clarify.

    This is a hard override for tasks like:
    - Open Cardwise app on Mum's phone
    - Restart Mum's phone
    - Call dentist office
    - Email school about bread order
    - Change furnace filter
    - Move furniture from furnace room

    These may be short or imperfect, but a reasonable person can start them
    without extra clarification, so the automation should create a normal task.
    """
    text = title.lower().strip()
    words = words_in(title)

    if not words or text.startswith("clarify next action:"):
        return False

    first_word = words[0]

    if first_word not in ATOMIC_ACTION_VERBS:
        return False

    # Keep genuinely vague placeholders in the clarification path.
    if contains_vague_word(title) or has_unresolved_placeholder_reference(title):
        return False

    # If the task starts with a concrete verb and contains more than just the verb,
    # treat it as executable even if it mentions a weak-ish reference elsewhere.
    return len(words) >= 2

def is_creative_task(title):
    """Return True for clear creative/design work that should not be clarified.

    Creative tasks are often open-ended, but that does not make them vague.
    Example: "Design new label for 50% Whole Wheat Sourdough Tin Loaf" can be
    started without asking a question, so it should become a task or breakdown.

    Still clarify tasks with genuinely missing references such as:
    - "Design thing"
    - "Create stuff"
    - "Draft email to guy"
    """
    text = title.lower().strip()
    words = words_in(title)

    if not text or text.startswith("clarify next action:"):
        return False

    # If the task contains vague placeholders, keep the clarify path.
    if contains_vague_word(title) or contains_weak_reference(title):
        return False

    creative_verbs = [
        "design",
        "redesign",
        "create",
        "draft",
        "develop",
        "mockup",
        "mock",
        "write",
        "edit",
        "revise",
    ]

    creative_objects = [
        "label",
        "labels",
        "logo",
        "brand",
        "branding",
        "canva",
        "caption",
        "post",
        "copy",
        "description",
        "announcement",
        "menu",
        "flyer",
        "poster",
        "layout",
        "mockup",
        "graphic",
        "document",
        "guide",
        "handout",
        "page",
        "website",
    ]

    starts_with_creative_verb = bool(words) and words[0] in creative_verbs
    mentions_creative_object = any(obj in text for obj in creative_objects)

    return starts_with_creative_verb and mentions_creative_object

def is_process_task(title):
    """Return True for clear process/project tasks.

    Key principle:
    - Vague/missing-context tasks should clarify.
    - Clear setup/process/creative tasks should not clarify.
    - Whether they break down is decided later by needs_breakdown().
    """
    text = title.lower().strip()

    if not text or text.startswith("clarify next action:"):
        return False

    # Atomic tasks are actionable but not process/project tasks.
    if is_atomic_action(title):
        return False

    # If it uses vague placeholders, let clarification handle it.
    if contains_vague_word(title) or contains_weak_reference(title):
        return False

    process_keywords = [
        "setup",
        "set up",
        "install",
        "configure",
        "prepare",
        "plan",
        "organize",
        "build",
        "launch",
    ]

    if any(keyword in text for keyword in process_keywords):
        return True

    if is_creative_task(title):
        return True

    return False

SAFE_NOUN_TASK_ACTIONS = [
    # Keep this list small and conservative. It is now only a guardrail for
    # noun phrases where the action is obvious without inventing context.
    (r"\b(grocery|shopping|packing|to[- ]do)\s+list\b", "Create"),
    (r"\bmeal\s+plan\b", "Create"),
    (r"\b(canva\s+)?draft\b", "Create"),
    (r"\bprinter\s+drivers?\b", "Install"),
    (r"\bearbuds?\b", "Set up"),
    (r"\b(tax\s+)?documents?\b", "Review"),
    (r"\bforms?\b", "Review"),
    (r"\bschool\s+bread\s+order\b", "Prepare"),
    (r"\bbread\s+order\b", "Prepare"),
]

NOUN_REWRITE_DECISIONS = {"rewrite", "clarify", "keep", "uncertain"}

def preferred_action_for_noun_task(title):
    """Return a safe deterministic verb for obvious noun-only task titles.

    This is deliberately conservative. It should handle repeatable, low-risk
    nouns such as "Grocery list" while leaving ambiguous nouns such as
    "Packaging labels" for the noun decision layer instead of growing another
    large keyword list.
    """
    text = title.lower().strip()

    if not text or starts_with_action_verb(title):
        return None

    if contains_vague_word(title) or contains_weak_reference(title):
        return None

    for pattern, action in SAFE_NOUN_TASK_ACTIONS:
        if re.search(pattern, text):
            return action

    return None

def rule_based_noun_rewrite_decision(title):
    """Classify a title for noun-phrase handling.

    Returns rewrite / clarify / keep / uncertain. Lists remain only as safe
    guardrails; unclear noun phrases can be handled by AI in production or by
    normal clarification when running locally without AI.
    """
    text = str(title or "").strip()

    if not text:
        return "clarify"

    if starts_with_action_verb(text) or is_atomic_action(text) or is_obvious_single_step_task(text) or is_immediately_actionable_operational_task(text):
        return "keep"

    if contains_vague_word(text) or contains_weak_reference(text):
        return "clarify"

    if looks_like_descriptive_concept_fragment(text):
        return "clarify"

    if preferred_action_for_noun_task(text):
        return "rewrite"

    if is_process_task(text):
        return "keep"

    if is_bare_noun_phrase(text):
        return "uncertain"

    return "keep"

def apply_noun_action_rewrite(title, action):
    """Apply a safe action verb to a noun phrase."""
    if not title or not action:
        return title

    words = words_in(title)
    if words and words[0].lower() == action.lower():
        return title

    return f"{action} {title[0].lower()}{title[1:]}"

def rewrite_safe_noun_task(title, allow_ai=True):
    """Rewrite safe noun-only tasks, or leave uncertain nouns for clarification.

    Deterministic safe rewrites still happen immediately. For uncertain noun
    phrases, production can ask AI for a tightly constrained noun decision if
    the helper is loaded; test-only mode falls back safely by leaving the title
    unchanged, which allows later clarification rules to catch it.
    """
    decision = rule_based_noun_rewrite_decision(title)

    if decision == "rewrite":
        return apply_noun_action_rewrite(title, preferred_action_for_noun_task(title))

    if decision in {"keep", "clarify"}:
        return title

    if allow_ai and "ask_ai_noun_rewrite_decision" in globals():
        try:
            result = ask_ai_noun_rewrite_decision(title)
            ai_decision = result.get("decision")
            ai_title = result.get("title")

            if ai_decision == "rewrite" and ai_title:
                return restore_preferred_proper_nouns(strip_due_date_phrases(ai_title))

            return title
        except Exception as e:
            print("AI noun rewrite decision failed:", e)
            return title

    return title

def looks_like_url_or_reference(text):
    """Return True for obvious reference captures rather than tasks."""
    t = str(text or "").strip()
    lower = t.lower()

    if re.search(r"https?://\S+|www\.\S+", lower):
        return True

    if re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", t, flags=re.IGNORECASE):
        return True

    if re.search(r"\b\d{3}[-.)\s]*\d{3}[-.\s]*\d{4}\b", t):
        return True

    return False

def looks_like_idea_or_backlog(text):
    """Return True for idea/backlog concepts that are not yet executable tasks.

    These are captured thoughts about possible improvements, enhancements,
    systems, workflows, or concepts. They should not become clarification tasks
    just because they lack a leading action verb.
    """
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    lower = t.lower()

    if not t:
        return False

    # Explicit idea/backlog prefixes are user intent.
    if re.match(r"^(idea|concept|enhancement|improvement|feature|backlog|proposal|thought)\s*[:\-–—]", lower):
        return True

    idea_start_patterns = [
        r"^(idea|concept|enhancement|improvement|feature|proposal)\s+for\b",
        r"^(possible|potential)\s+(workflow|process|feature|enhancement|improvement|idea|approach)\s+for\b",
        r"^(thought|note)\s+about\s+(improving|enhancing|adding|routing|building|creating)\b",
    ]
    if any(re.search(pattern, lower) for pattern in idea_start_patterns):
        return True

    # Capability-shaped fragments: "Enhancement for AIOS to route non-tasks".
    if re.search(r"^(enhancement|improvement|feature|concept|proposal)\s+for\s+.+\s+to\s+\w+", lower):
        return True

    # Backlog-ish wording without a concrete action owner.
    if re.search(r"\b(backlog|someday|future improvement|feature request)\b", lower):
        return True

    return False


def looks_like_descriptive_concept_fragment(text):
    """Return True for captured concept/observation fragments, not tasks.

    These usually start with a domain noun and describe attributes using
    connectors such as "that", "which", "with", "but", or "like". They are
    often useful notes/R&D prompts, but adding a verb such as "Develop" would
    invent intent.
    """
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    lower = t.lower()
    words = words_in(t)

    if not t or starts_with_action_verb(t):
        return False

    if len(words) < 5:
        return False

    # Descriptive relative-clause / attribute patterns, e.g.
    # "Dough that behaves like spelt but has high enzymatic activity"
    # "Flour that feels strong but tears easily"
    # "Bread with soft crumb but strong crust"
    descriptive_patterns = [
        r"\bthat\b.+\b(but|and|with|like|has|feels|behaves|acts|seems)\b",
        r"\bwhich\b.+\b(but|and|with|like|has|feels|behaves|acts|seems)\b",
        r"\bwith\b.+\b(but|and|like|high|low|strong|weak|soft|hard|fast|slow)\b",
        r"\blike\b.+\b(but|and|with|high|low|strong|weak|soft|hard|fast|slow)\b",
    ]

    if not any(re.search(pattern, lower) for pattern in descriptive_patterns):
        return False

    # Avoid catching normal tasks that happen to contain these words after a
    # recognized action verb; starts_with_action_verb already handles that.
    return True

def looks_like_observation_or_note(text):
    """Return True for clear notes that should not become tasks.

    This is deliberately narrow. It catches statements, measurements, reminders
    of facts, and reference snippets, but avoids routing ambiguous noun phrases
    such as "Packaging labels" away from the existing clarification flow.
    """
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    lower = t.lower()
    words = words_in(t)

    if not t:
        return False

    if looks_like_url_or_reference(t):
        return True

    # Explicit note/reference prefixes are user intent, not task intent.
    if re.match(r"^(note|notes|reference|observation|remember)\s*[:\-–—]", lower):
        return True

    # Captured facts / observations, e.g. "Rye seems to ferment faster...".
    observation_patterns = [
        r"\bseems? to\b",
        r"\bappears? to\b",
        r"\blooks? like\b",
        r"\bi noticed\b",
        r"\bnote that\b",
        r"\bremember that\b",
        r"\bfor reference\b",
        r"\bfyi\b",
        r"\binteresting\b",
    ]
    if any(re.search(pattern, lower) for pattern in observation_patterns):
        return True

    # Definitional / status statements with a normal subject + linking verb.
    if re.search(r"\b(is|are|was|were)\b", lower) and not starts_with_action_verb(t):
        if len(words) >= 4:
            return True

    # Measurement / inventory-style notes that lack an action verb.
    if not starts_with_action_verb(t) and re.search(r"\b\d+(?:\.\d+)?\s*(g|kg|lb|lbs|oz|ml|l|°c|°f|c|f|%)\b", lower):
        return True

    # Qualitative operations observations, e.g.
    # "Too many seed and inclusion breads in this rotation".
    # These are useful planning signals, but they do not name an executable next
    # action. Keep this structural rather than bakery-specific: comparator +
    # plural/object context + no leading action verb.
    qualitative_observation_starts = (
        "too many", "too much", "too few", "too little",
        "not enough", "fewer", "more", "less",
    )
    if not starts_with_action_verb(t) and lower.startswith(qualitative_observation_starts):
        if len(words) >= 4:
            return True

    return False

def rule_based_non_task_decision(text):
    """Return task / note / review before normal task classification.

    V1 goal: prevent obvious non-tasks from becoming clarification tasks.
    Obvious observations route to Notes / Reference. Idea/backlog concepts
    route to Ideas / Backlog. Everything else remains a task candidate.
    """
    t = str(text or "").strip()

    if not t:
        return "review"

    parsed = parse_task_flags(t)
    clean_title = strip_due_date_phrases(parsed["clean_title"])

    # A previously-created clarification title may later be re-reviewed as a
    # Brain Dump item. Classify the underlying content, not the wrapper phrase.
    if clean_title.lower().startswith("clarify next action:"):
        clean_title = clean_title.split(":", 1)[-1].strip()

    # Descriptive concept fragments should stay notes before the broad
    # actionability checks below. Some domain nouns can accidentally look like
    # short actions, but adding a verb such as "Develop" would invent intent.
    if looks_like_descriptive_concept_fragment(clean_title):
        return "note"

    # Respect clear task signals first.
    if starts_with_action_verb(clean_title) or is_atomic_action(clean_title) or is_process_task(clean_title) or is_obvious_single_step_task(clean_title):
        return "task"

    if looks_like_idea_or_backlog(clean_title):
        return "idea"

    if looks_like_observation_or_note(clean_title):
        return "note"

    return "task"

def is_non_task_note_item(item):
    return rule_based_non_task_decision(item.get("text", "")) == "note"

def is_non_task_idea_item(item):
    return rule_based_non_task_decision(item.get("text", "")) == "idea"

def needs_action_verb(title):
    """Return True when a title has no leading action verb and needs intervention.

    JDI and Quick Win are execution flags, not permission to create noun-only
    tasks. This check intentionally runs before those flags are applied.
    """
    words = words_in(title)

    if not words:
        return True

    if starts_with_action_verb(title):
        return False

    if is_atomic_action(title) or is_process_task(title) or is_obvious_single_step_task(title) or is_immediately_actionable_operational_task(title):
        return False

    return True

def is_bare_noun_phrase(title):
    words = words_in(title)

    if not words:
        return True

    # Clear atomic/process/setup/creative tasks are not vague.
    if is_atomic_action(title) or is_process_task(title):
        return False

    # If it starts with a known verb, it is not a bare noun phrase.
    if starts_with_action_verb(title):
        return False

    # Short concrete phrases are still noun phrases if they have no action verb.
    # They should be deterministically rewritten when safe, or sent through the
    # cleanup/clarification path when not safe.
    return True

def needs_ai_cleanup(title):
    # Unresolved placeholder objects should enter the clarification path even
    # if they start with a superficially valid action verb such as "fix".
    if has_unresolved_placeholder_reference(title):
        return True

    # Clear atomic/process/creative tasks should not go through clarification cleanup.
    if is_atomic_action(title) or is_process_task(title) or is_obvious_single_step_task(title) or is_immediately_actionable_operational_task(title):
        return False

    return (
        contains_vague_word(title)
        or contains_weak_reference(title)
        or is_bare_noun_phrase(title)
    )

def is_still_vague(title):
    lower = title.lower().strip()

    if lower.startswith("clarify next action:"):
        return True

    if has_unresolved_placeholder_reference(title):
        return True

    # Atomic/process/creative tasks can be clear without being perfectly atomic.
    if is_atomic_action(title) or is_process_task(title) or is_obvious_single_step_task(title) or is_immediately_actionable_operational_task(title):
        return False

    if contains_vague_word(title):
        return True

    if contains_weak_reference(title) and not starts_with_action_verb(title):
        return True

    if is_bare_noun_phrase(title) and not starts_with_action_verb(title):
        return True

    return False


# In[27]:

def needs_soft_rewrite(title):
    words = words_in(title)

    if needs_ai_cleanup(title):
        return False

    # Never rewrite very simple obvious tasks
    if len(words) <= 3 and title_starts_with_quick_win_verb(title):
        return False

    # Allow short action phrases that may benefit from light grammar polish
    return (
        starts_with_action_verb(title)
        and len(words) <= 5
        and not contains_vague_word(title)
        and not contains_weak_reference(title)
        and not is_bare_noun_phrase(title)
    )

# In[28]:

CLARIFICATION_ROUTES = {"define_context", "choose_next_action"}

def rule_based_clarification_route(title):
    """Return how a clarification task should be presented in the UI.

    Routes:
    - define_context: ask a question because essential context is missing.
    - choose_next_action: offer concrete first-action choices for a clear but
      open-ended task.

    This replaces the old vague-word-only structural check with a small decision
    layer. Keyword checks remain only as guardrails for obvious placeholders.
    """
    text = str(title or "").strip()
    lower = text.lower()
    words = words_in(text)

    if not text:
        return "define_context"

    if lower.startswith("clarify next action:"):
        text = text.split(":", 1)[-1].strip()
        lower = text.lower()
        words = words_in(text)

    # Obvious missing-context placeholders should ask a defining question.
    if contains_vague_word(text) or contains_weak_reference(text):
        return "define_context"

    # Clear issue-resolution tasks usually need a first-action choice rather
    # than another defining question. Keep this as a small semantic guardrail,
    # not a broad project keyword list.
    if any(word in words for word in ["issue", "problem", "error", "bug"]):
        return "choose_next_action"

    # Clear action tasks that somehow reached clarification should offer next
    # actions, not context questions.
    if starts_with_action_verb(text) or is_atomic_action(text) or is_process_task(text):
        return "choose_next_action"

    # Noun fragments and missing-action titles need definition first.
    if is_bare_noun_phrase(text) or needs_action_verb(text):
        return "define_context"

    return "choose_next_action"

def clarification_route(title, allow_ai=False):
    """Return define_context or choose_next_action for clarification UI.

    The default is deterministic so test-only mode stays API-free. Production
    can pass allow_ai=True once ask_ai_clarification_route is available.
    """
    route = rule_based_clarification_route(title)

    if allow_ai and "ask_ai_clarification_route" in globals():
        try:
            ai_route = ask_ai_clarification_route(title)
            if ai_route in CLARIFICATION_ROUTES:
                return ai_route
        except Exception as e:
            print("AI clarification route failed:", e)

    return route

def is_structurally_vague(title):
    """Compatibility wrapper for older call sites.

    True now means the clarification UI should ask the user to define context.
    """
    return clarification_route(title, allow_ai=False) == "define_context"

# ## 5. Task flags, dates, icons, and breakdown rules
# 

# In[29]:

# Legacy guardrail only. The main effort/duration logic now uses
# structural task decisions instead of treating verbs as the source of truth.
SMALL_EFFORT_KEYWORDS = [
    "call",
    "email",
    "book",
    "pay",
    "submit",
    "schedule",
    "cancel",
    "renew",
    "pick up",
    "drop off",
    "update",
]

EFFORT_DECISIONS = {"small", "medium", "large", "uncertain"}
VALID_EFFORT_VALUES = {"Small Effort", "Medium Effort", "Large Effort"}
VALID_DURATION_VALUES = {"15 min", "30 min", "60 min"}
VALID_IMPORTANCE_VALUES = {"High Importance"}

def extract_explicit_duration(text):
    """Return an explicit duration select value when the title contains one.

    Regex is the right tool here because explicit time markers are literal user
    intent, not task classification guesses.
    """
    t = str(text or "").lower()

    if re.search(r"\b(15|fifteen)\s*(min|mins|minute|minutes)\b", t):
        return "15 min"

    if re.search(r"\b(30|thirty)\s*(min|mins|minute|minutes)\b|\bhalf an hour\b", t):
        return "30 min"

    if re.search(r"\b(45|60|sixty)\s*(min|mins|minute|minutes)\b|\b1\s*(hour|hr)\b|\bone hour\b", t):
        return "60 min"

    return None

def effort_from_duration(duration):
    if duration == "15 min":
        return "Small Effort"
    if duration == "30 min":
        return "Medium Effort"
    if duration == "60 min":
        return "Large Effort"
    return None

def rule_based_effort_duration_decision(title):
    """Infer effort/duration using structure first, keywords second.

    Returns a dict:
    {
      "decision": "small" | "medium" | "large" | "uncertain",
      "effort": Notion select value or None,
      "duration": Notion select value or None,
      "confidence": float,
      "source": short string
    }

    Design goal: effort is based on task shape, complexity, and explicit time,
    not on large keyword lists. The old keyword list remains only as a conservative
    fallback for obvious small admin tasks.
    """
    title = str(title or "").strip()

    empty_result = {
        "decision": "uncertain",
        "effort": None,
        "duration": None,
        "confidence": 0.0,
        "source": "empty",
    }

    if not title:
        return empty_result

    if title.lower().startswith("clarify next action:"):
        return {
            "decision": "uncertain",
            "effort": None,
            "duration": None,
            "confidence": 0.0,
            "source": "clarify_task",
        }

    explicit_duration = extract_explicit_duration(title)
    if explicit_duration:
        return {
            "decision": {"15 min": "small", "30 min": "medium", "60 min": "large"}[explicit_duration],
            "effort": effort_from_duration(explicit_duration),
            "duration": explicit_duration,
            "confidence": 0.95,
            "source": "explicit_duration",
        }

    words = words_in(title)
    word_count = len(words)

    # Use the task router as the main signal. If it needs clarification, effort
    # metadata should not be guessed yet. If it needs breakdown, it is not small.
    task_route = decide_task_action(title, title, allow_ai=False) if "decide_task_action" in globals() else "keep"

    if task_route == "clarify":
        return {
            "decision": "uncertain",
            "effort": None,
            "duration": None,
            "confidence": 0.0,
            "source": "needs_clarification",
        }

    if task_route == "breakdown" or needs_breakdown(title):
        # Parent tasks with subtasks should not be treated as 15-minute quick wins.
        return {
            "decision": "medium",
            "effort": "Medium Effort",
            "duration": "60 min",
            "confidence": 0.8,
            "source": "breakdown_task",
        }

    # Clear single-execution tasks are usually small.
    if is_obvious_single_step_task(title) or is_immediately_actionable_operational_task(title):
        return {
            "decision": "small",
            "effort": "Small Effort",
            "duration": "15 min",
            "confidence": 0.9,
            "source": "obvious_single_step",
        }

    if is_atomic_action(title):
        # Short atomic tasks get a duration. Longer atomic tasks get effort only;
        # AI can refine duration later if needed.
        return {
            "decision": "small",
            "effort": "Small Effort",
            "duration": "15 min" if word_count <= 6 else None,
            "confidence": 0.85 if word_count <= 6 else 0.75,
            "source": "atomic_action",
        }

    if is_single_session_task(title):
        return {
            "decision": "medium",
            "effort": "Medium Effort",
            "duration": "30 min",
            "confidence": 0.75,
            "source": "single_session",
        }

    # Legacy guardrail: only use verb/phrase keywords after structural checks.
    # This catches very common small admin tasks without letting the list dominate
    # classification.
    t = title.lower()
    if word_count <= 7 and any(keyword in t for keyword in SMALL_EFFORT_KEYWORDS):
        return {
            "decision": "small",
            "effort": "Small Effort",
            "duration": "15 min",
            "confidence": 0.7,
            "source": "legacy_small_guardrail",
        }

    return {
        "decision": "uncertain",
        "effort": None,
        "duration": None,
        "confidence": 0.0,
        "source": "uncertain",
    }

def classify_effort_duration(text):
    """Return deterministic effort/duration metadata when confidence is useful."""
    result = rule_based_effort_duration_decision(text)

    if result.get("decision") in ["small", "medium", "large"]:
        return {
            "effort": result.get("effort"),
            "duration": result.get("duration"),
            "confidence": result.get("confidence", 0),
            "source": result.get("source"),
        }

    return {"effort": None, "duration": None, "confidence": 0, "source": result.get("source")}

def classify_effort(text):
    """Backward-compatible effort helper used during initial task creation."""
    return classify_effort_duration(text).get("effort")




IMPORTANCE_HIGH_DOMAIN_PATTERNS = [
    # Financial responsibility is intentionally action/context-sensitive. This
    # catches obligations like paying bills/invoices/card balances without
    # making generic research or filing tasks important merely because they
    # mention invoices or credit cards.
    (r"\b(tax|taxes|accountant|accounting|legal|lawyer|insurance|claim|government|permit|license|licence|bank|banking|payroll)\b", "Financial, legal, government, insurance, or payroll responsibility"),
    (r"(?:\b(?:pay|settle|submit|send)\b.*\b(?:bill|bills|invoice|invoices|statement|mastercard|visa|amex|credit card|card balance|payment)\b)|(?:\b(?:mastercard|visa|amex|credit card|card balance)\b.*\b(?:bill|payment|statement|balance|due)\b)|(?:\b(?:bill|invoice|statement)\b.*\b(?:due|payment|pay)\b)", "Bill, invoice, credit-card, or payment obligation"),
    (r"\b(doctor|medical|clinic|appointment|pharmacy|prescription|health|dentist)\b", "Health or appointment responsibility"),
    (r"\b(school|breakfast program|bread delivery|school bread)\b", "External school or bread-program commitment"),
    (r"\b(customer|client|pickup issue|order issue|workshop|students|class|catering|organizer)\b", "External customer, workshop, class, or community commitment"),
    (r"\b(critical|must|deadline|blocked|blocking|failure|failed|broken|outage)\b", "Explicit consequence, blocker, or reliability signal"),
]

def infer_importance(title, explicit_important=False):
    """Return conservative Importance metadata for a task title.

    Importance measures consequence/value, not time pressure or effort. V1 only
    writes High Importance when there is explicit user intent or a strong
    high-confidence domain signal. Otherwise it leaves the property blank.
    """
    clean_title = str(title or "").strip()

    if not clean_title or clean_title.lower().startswith("clarify next action:"):
        return {"importance": None, "confidence": 0.0, "reason": "No importance inference for blank or clarification tasks", "source": "none"}

    if explicit_important:
        return {
            "importance": "High Importance",
            "confidence": 1.0,
            "reason": "Explicit importance marker supplied in Brain Dump",
            "source": "explicit_marker",
        }

    lower_title = clean_title.lower()
    for pattern, reason in IMPORTANCE_HIGH_DOMAIN_PATTERNS:
        if re.search(pattern, lower_title, flags=re.IGNORECASE):
            return {
                "importance": "High Importance",
                "confidence": 0.9,
                "reason": reason,
                "source": "conservative_rule",
            }

    return {"importance": None, "confidence": 0.0, "reason": "No high-confidence importance signal", "source": "none"}

def build_metadata_log_reason(title, changed_metadata, preserved_metadata=None):
    """Build one readable AI Processing Log reason for metadata updates."""
    lines = ["Metadata inference/update."]

    if changed_metadata:
        lines.append("Changed:")
        for name, details in changed_metadata.items():
            value = details.get("value")
            source = details.get("source")
            reason = details.get("reason")
            confidence = details.get("confidence")
            suffix_parts = []
            if source:
                suffix_parts.append(f"source={source}")
            if confidence is not None:
                suffix_parts.append(f"confidence={confidence:.2f}" if isinstance(confidence, (int, float)) else f"confidence={confidence}")
            suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
            lines.append(f"- {name}: {value}{suffix}")
            if reason:
                lines.append(f"  Reason: {reason}")

    if preserved_metadata:
        preserved = ", ".join(f"{k}: {v}" for k, v in preserved_metadata.items() if v)
        if preserved:
            lines.append(f"Preserved existing metadata: {preserved}")

    return "\n".join(lines)

def log_metadata_update(title, changed_metadata, preserved_metadata=None):
    """Write high-signal metadata rows to the AI Processing Log.

    First-pass noise reduction: only Importance changes are review-worthy enough
    for the Notion AI Processing Log. Routine Effort, Duration, Due Date,
    Urgency, and Quick Win updates still print to stdout/cron where they are
    useful for debugging, but they no longer create AI log rows by themselves.
    """
    if not changed_metadata:
        return False

    importance_metadata = {
        name: details
        for name, details in changed_metadata.items()
        if name == "Importance"
    }

    if not importance_metadata:
        return False

    metadata_labels = ", ".join(importance_metadata.keys())

    if TEST_MODE or DRY_RUN:
        print(f"Importance AI log skipped for {title}: test/dry-run mode")
        return False

    if not AI_LOG_DATABASE_ID:
        print(f"Importance AI log skipped for {title}: NOTION_AI_LOG_DATABASE_ID is not configured")
        return False

    confidence_values = [
        details.get("confidence")
        for details in importance_metadata.values()
        if isinstance(details.get("confidence"), (int, float))
    ]
    confidence = max(confidence_values) if confidence_values else None

    # Use a distinct row title so importance log entries are easy to spot beside
    # normal Created / Duplicate / Project Candidate entries for the same task.
    log_title = f"Importance — {title}"

    did_log = log_ai_processing_decision(
        original=title,
        final_task=log_title,
        action="Metadata",
        reason=build_metadata_log_reason(title, importance_metadata, preserved_metadata),
        review_needed=False,
        confidence=confidence,
        source="Metadata",
    )

    if did_log:
        increment_summary("metadata_log_entries")
        print(f"Importance AI log written: {title} → {metadata_labels}")
    else:
        print(f"Importance AI log NOT written: {title} → {metadata_labels}")

    return did_log

def classify_effort(text):
    t = text.lower()

    if "15 min" in t or "15 minutes" in t:
        return "Small Effort"

    if any(keyword in t for keyword in SMALL_EFFORT_KEYWORDS):
        return "Small Effort"

    return None

def pick_icon(text):
    t = text.lower()

    if any(word in t for word in ["sticker", "label", "labels"]):
        return "🏷️"

    if any(word in t for word in ["bedroom", "bed", "pillow"]):
        return "🛏️"

    if any(word in t for word in ["package", "packaging", "box", "shipping", "ship"]):
        return "📦"

    if any(word in t for word in ["plug", "charging", "charge", "power"]):
        return "🔌"

    if any(word in t for word in ["read", "instructions", "forms", "form", "paperwork"]):
        return "📄"

    if any(word in t for word in ["coffee", "tea", "caffeine"]):
        return "☕"

    if any(word in t for word in ["design", "art", "decorate"]):
        return "🎨"

    if any(word in t for word in ["laundry", "cloth", "towels", "linens", "cleaning supplies"]):
        return "🧺"

    if any(word in t for word in ["dishes", "wash", "scrub", "clean"]):
        return "🧽"

    return "📝"

# In[30]:

# Legacy keyword lists kept as narrow guardrails. The primary breakdown logic
# now uses a yes / no / uncertain decision layer below instead of depending on
# these lists as the main classifier.
LOW_EFFORT_BREAKDOWN_VERBS = [
    "setup", "set up", "install", "configure", "restart", "reopen", "open",
    "check", "call", "email", "text", "book", "buy", "print", "pay",
    "submit", "schedule", "cancel", "renew", "pair", "connect",
]

BREAKDOWN_VALUE_SIGNALS = [
    "plan", "organize", "build", "launch", "develop", "research", "prepare",
    "project", "system", "database", "automation", "workflow", "event", "trip",
    "design", "redesign", "website", "homepage", "document", "guide", "handout",
]

LOW_EFFORT_OBJECT_HINTS = [
    "earbuds", "headphones", "airpods", "phone", "iphone", "app", "printer",
    "driver", "drivers", "router", "wifi", "bluetooth",
]

SINGLE_SESSION_SIGNALS = [
    "first draft", "draft", "quick", "simple", "small", "minor", "one-off", "single",
]

BREAKDOWN_DECISIONS = {"yes", "no", "uncertain"}

def has_breakdown_value_signal(task_text):
    """Legacy guardrail: return True for phrases with known breakdown value."""
    text = task_text.lower().strip()
    return any(signal in text for signal in BREAKDOWN_VALUE_SIGNALS)

def is_single_session_task(task_text):
    """Return True when a clear task is better as one normal task."""
    text = task_text.lower().strip()

    if is_atomic_action(task_text):
        return True

    if any(signal in text for signal in SINGLE_SESSION_SIGNALS):
        return True

    # Short creative creation/drafting tasks are often one work session.
    if len(words_in(task_text)) <= 8 and any(
        text.startswith(prefix) for prefix in ["create ", "draft ", "write ", "edit "]
    ):
        return True

    return False

def is_likely_low_effort_task(task_text):
    """Return True when breakdown would probably add clutter instead of value."""
    text = task_text.lower().strip()
    word_count = len(words_in(task_text))

    if not text:
        return False

    if is_single_session_task(task_text):
        return True

    # Explicit longer-work markers should stay eligible for breakdown.
    if any(marker in text for marker in ["45 min", "60 min", "1 hour", "2 hour", "longer", "project"]):
        return False

    has_low_effort_verb = any(verb in text for verb in LOW_EFFORT_BREAKDOWN_VERBS)
    has_low_effort_object = any(obj in text for obj in LOW_EFFORT_OBJECT_HINTS)

    if word_count <= 8 and (has_low_effort_verb or has_low_effort_object):
        if has_breakdown_value_signal(task_text) and not is_single_session_task(task_text):
            return False
        return True

    return False

def rule_based_breakdown_decision(task_text):
    """Return yes / no / uncertain for parent+subtask breakdown.

    The goal is to reduce keyword dependence. Deterministic rules handle only
    obvious cases. Ambiguous clear tasks return "uncertain" so production can
    ask AI, while test-only mode remains deterministic and safe.
    """
    text = str(task_text or "").lower().strip()
    words = words_in(task_text)
    word_count = len(words)

    if not text or text.startswith("clarify next action:"):
        return "no"

    # Never break down unclear tasks here; clarification owns those.
    if is_still_vague(task_text) or needs_action_verb(task_text):
        return "no"

    # Hard no: clear atomic and routine tasks.
    if is_atomic_action(task_text) or is_obvious_single_step_task(task_text) or is_immediately_actionable_operational_task(task_text):
        return "no"

    # Hard no: tasks that explicitly indicate one session / one draft.
    if is_single_session_task(task_text) or is_likely_low_effort_task(task_text):
        return "no"

    # Hard yes: high-level process/project tasks that are already clear.
    if is_process_task(task_text) and word_count >= 2:
        return "yes"

    # Legacy signal yes, but only after the hard-no checks above.
    if has_breakdown_value_signal(task_text) and word_count >= 3:
        return "yes"

    # Long clear tasks often contain a concrete outcome plus enough context to
    # require setup/execution/review, but this is exactly where keywords used to
    # sprawl. Let AI decide in production.
    if starts_with_action_verb(task_text) and word_count >= 6:
        return "uncertain"

    return "no"

def decide_breakdown(task_text, allow_ai=True):
    """Return yes / no for whether a clear task should be broken down."""
    decision = rule_based_breakdown_decision(task_text)

    if decision in {"yes", "no"}:
        return decision

    if not allow_ai or "ask_ai_breakdown_decision" not in globals():
        return "no"

    try:
        ai_decision = ask_ai_breakdown_decision(task_text)
    except Exception as e:
        print("AI breakdown decision failed:", e)
        return "no"

    return ai_decision if ai_decision in {"yes", "no"} else "no"

def needs_breakdown(task_text):
    """Compatibility wrapper used by tests and older call sites."""

    evaluation = build_task_evaluation(task_text)

    if evaluation:
        print(
            f"[Evaluation] "
            f"JDI={evaluation.is_jdi} | "
            f"QuickWin={evaluation.is_quick_win} | "
            f"Breakdown={evaluation.should_break_down}"
        )

    return decide_breakdown(task_text, allow_ai=False) == "yes"

# ============================================================
# CENTRALIZED TASK EVALUATION (PHASE 1)
# ============================================================

def build_task_evaluation(task_title, effort=None, duration=None):
    """
    Lightweight compatibility wrapper around the new evaluator.

    IMPORTANT:
    This is intentionally non-invasive during Phase 1.
    Existing logic remains authoritative.

    The evaluator is currently used for:
    - diagnostics
    - architectural decoupling
    - gradual migration preparation
    """

    if not EVALUATOR_AVAILABLE:
        return None

    try:
        return evaluate_task({
            "Task Name": task_title,
            "Effort": effort,
            "Duration": duration,
        })
    except Exception as e:
        print(f"[Evaluator] Failed: {e}")
        return None

TASK_DECISIONS = {"keep", "clarify", "breakdown"}

def rule_based_task_decision(original_title, prepared_title=None):
    """Classify a task as keep / clarify / breakdown using deterministic rules."""
    original = restore_preferred_proper_nouns(strip_due_date_phrases(original_title or ""))
    prepared = restore_preferred_proper_nouns(strip_due_date_phrases(prepared_title or original))

    if not original and not prepared:
        return "clarify"

    # Existing hard guards first.
    if is_atomic_action(original) or is_obvious_single_step_task(original) or is_immediately_actionable_operational_task(original):
        return "keep"

    # If title preparation already decided this needs clarification, respect it
    # unless the AI decision layer overrides later.
    if prepared.lower().startswith("clarify next action:"):
        return "clarify"

    if is_still_vague(prepared) or needs_action_verb(prepared):
        return "clarify"

    breakdown_decision = rule_based_breakdown_decision(prepared)
    if breakdown_decision == "yes":
        return "breakdown"

    return "keep"

def decide_task_action(original_title, prepared_title=None, allow_ai=True):
    """Return keep / clarify / breakdown for one inbox task.

    Deterministic rules handle obvious cases. AI is used only for two risky
    middle zones:
    - rule-based clarification where the original may actually be clear
    - clear but breakdown-uncertain work where keyword lists used to sprawl
    """
    original = restore_preferred_proper_nouns(strip_due_date_phrases(original_title or ""))
    prepared = restore_preferred_proper_nouns(strip_due_date_phrases(prepared_title or original))

    decision = rule_based_task_decision(original, prepared)

    if decision == "clarify":
        if not allow_ai or "ask_ai_task_decision" not in globals():
            return decision

        try:
            ai_decision = ask_ai_task_decision(original)
        except Exception as e:
            print("AI task decision failed:", e)
            return decision

        if ai_decision in TASK_DECISIONS:
            return ai_decision

        return decision

    # Keep can still be breakdown-uncertain. Ask the dedicated breakdown
    # classifier instead of expanding keyword lists.
    if decision == "keep" and allow_ai:
        breakdown_decision = rule_based_breakdown_decision(prepared)
        if breakdown_decision == "uncertain" and decide_breakdown(prepared, allow_ai=True) == "yes":
            return "breakdown"

    return decision

# ## Classification sanity checks

# In[31]:

# Helper: remove due-date words from task titles before rewrite/classification



# In[32]:

def generate_subtasks(task_text, client):
    """Use AI to break a clear parent task into linked subtasks.

    Subtasks should stay clean enough for Notion, but also carry enough context
    to make sense when seen outside the parent page or in search results.
    """
    prompt = f"""
Break this task into 3–5 clear, actionable subtasks.

Rules:
- Do NOT invent details not present in the task.
- Do NOT ask clarifying questions.
- If a detail is missing, write a step to check or confirm it.
- Each step must start with a verb.
- Keep each step short, but not context-free.
- Each step must be understandable on its own without seeing the parent task.
- Include the key object/context from the parent when needed.
- Do NOT repeat the full parent title in every step.
- Prefer natural context, e.g. "Create label mockup in Canva" instead of "Create digital mockup".
- Avoid vague standalone steps like "Review details", "Gather materials", "Create mockup", or "Check inventory" unless the object is named.
- No fluff.
- No explanations.
- Output as a simple list with one subtask per line.
- For creative/design tasks, treat the task as actionable and suggest concrete first-draft steps.
- If the task names a tool such as Canva, include that tool in the relevant step.
- Do not add a tool that was not mentioned in the task.

Good example:
Parent: Design new label for 50% Whole Wheat Sourdough Tin Loaf in Canva
- Review required text for the bread label
- Choose layout for the tin loaf label
- Create first label draft in Canva
- Check label size against packaging
- Save finished label for printing

Bad example:
- Review details
- Choose layout
- Create mockup
- Save file

Task: {task_text}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    output = response.output_text.strip()

    # Use splitlines() rather than split("\n") to avoid separator issues and
    # handle different newline styles safely.
    subtasks = []
    for line in output.splitlines():
        cleaned = line.strip().strip("-•0123456789. ").strip()
        if cleaned:
            subtasks.append(cleaned)

    return subtasks[:MAX_SUBTASKS]

# ### Patch note: robust subtask parsing
# 
# This version uses `output.splitlines()` for AI list parsing. Restart the kernel and run the notebook from the top so the old `generate_subtasks()` definition is not still in memory.

# ### Breakdown output quality note
# 
# Subtasks are now prompted to be **standalone-clear**: clean enough to avoid long parent prefixes, but specific enough to make sense in Notion views, search results, and linked subtasks.

# In[33]:

def clean_subtasks(subtasks):
    cleaned = []

    for task in subtasks:
        task = task.strip()

        # remove bullets / numbering
        task = re.sub(r"^\s*[-*•]?\s*\d+[\.\)]\s*", "", task).strip()
        task = re.sub(r"\s+", " ", task).strip()

        if len(task) < 3:
            continue

        if task.lower().startswith(("note:", "explanation")):
            continue

        cleaned.append(task)

    return cleaned

# In[34]:

from datetime import datetime, timedelta



# -------------------------------------------------------------------------
# Canonical Brain Dump capture metadata parser
# -------------------------------------------------------------------------
from aios.ingestion import capture_metadata as capture_metadata_parser

capture_metadata_parser.configure_capture_metadata(globals())

parse_manual_project_tag = capture_metadata_parser.parse_manual_project_tag
parse_task_flags = capture_metadata_parser.parse_task_flags
sanitize_task_title_separators = capture_metadata_parser.sanitize_task_title_separators
strip_due_date_phrases = capture_metadata_parser.strip_due_date_phrases
extract_due_date = capture_metadata_parser.extract_due_date
parse_capture_metadata = capture_metadata_parser.parse_capture_metadata
CaptureMetadata = capture_metadata_parser.CaptureMetadata
MONTH_NAME_PATTERN = capture_metadata_parser.MONTH_NAME_PATTERN
MONTH_DAY_DATE_PATTERN = capture_metadata_parser.MONTH_DAY_DATE_PATTERN
DUE_DATE_WORD_PATTERNS = capture_metadata_parser.DUE_DATE_WORD_PATTERNS
_next_weekday_date = capture_metadata_parser._next_weekday_date

print("[Capture Metadata] Canonical Brain Dump parser loaded from aios.ingestion.capture_metadata")


# In[35]:

def restore_preferred_proper_nouns(text):
    """Restore household/family terms that should behave like proper nouns.

    The AI sometimes normalizes words like "Mum" and "Dad" to lowercase.
    In this workflow those are intentional names, so we fix them deterministically
    after any AI rewrite and before creating Notion tasks.
    """
    if not text:
        return text

    replacements = {
        r"\bmum\b": "Mum",
        r"\bmum's\b": "Mum's",
        r"\bdad\b": "Dad",
        r"\bdad's\b": "Dad's",
    }

    fixed = text
    for pattern, replacement in replacements.items():
        fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)

    return fixed


# In[36]:

def prepare_task_title(item, allow_ai=True):
    """Parse flags, remove due-date wording, and ensure titles are actionable.

    Keep this helper before the test harness and before clarification processing.
    It is the single title-preparation path used by both new Brain Dump items
    and checked clarification options.

    allow_ai=False is used by the local test harness so tests remain safe before
    the AI helper cells are loaded. Production callers use the default True.
    """
    parsed = parse_task_flags(item["text"])

    raw_text = item["text"]
    due_date = extract_due_date(raw_text)

    # Strip dates from both the parsed title and any later AI output. This keeps
    # due-date metadata separate from the visible task name.
    original_clean_title = strip_due_date_phrases(parsed["clean_title"])
    task_title = original_clean_title or parsed["clean_title"]

    deterministic_title = rewrite_safe_noun_task(task_title, allow_ai=allow_ai)

    if deterministic_title != task_title:
        print("Action rewrite:", task_title)
        print("→", deterministic_title)
        task_title = deterministic_title

    needs_hard_ai = needs_ai_cleanup(task_title) or needs_action_verb(task_title)
    has_hard_ai_helper = "rewrite_task_title_with_ai" in globals()
    has_soft_ai_helper = "soft_rewrite_task_title_with_ai" in globals()

    if allow_ai and needs_hard_ai and has_hard_ai_helper:
        print("AI rewriting:", task_title)
        new_title = rewrite_task_title_with_ai(task_title)
        new_title = strip_due_date_phrases(new_title)
        print("→", new_title)

        if is_still_vague(new_title) or needs_action_verb(new_title):
            print("→ Too vague or missing action verb, forcing clarify step")
            task_title = f"Clarify next action: {original_clean_title or parsed['clean_title']}"
        else:
            task_title = new_title

    elif needs_hard_ai:
        # In test mode, or before the AI helper cells are loaded, do not call AI.
        # Keep deterministic behaviour and let the caller inspect needs_ai_cleanup().
        pass

    elif allow_ai and needs_soft_rewrite(task_title) and has_soft_ai_helper:
        print("AI soft rewriting:", task_title)
        new_title = soft_rewrite_task_title_with_ai(task_title)
        new_title = strip_due_date_phrases(new_title)

        if new_title == task_title:
            print("→ no soft rewrite needed")
        else:
            print("→", new_title)
            task_title = new_title

    task_title = strip_due_date_phrases(task_title)
    task_title = restore_preferred_proper_nouns(task_title)

    if has_unresolved_placeholder_reference(task_title):
        print("[Clarification Guard] unresolved placeholder reference after rewrite; routing to clarification")
        task_title = f"Clarify next action: {original_clean_title or parsed['clean_title']}"

    return parsed, task_title, due_date


# In[37]:

# STRUCTURAL_HELPER_ORDER_TESTS
# These checks catch notebook ordering regressions before the larger test harness runs.
# They are safe to run locally and do not call Notion or AI.
required_helpers = [
    "prepare_task_title",
    "strip_due_date_phrases",
    "extract_due_date",
    "restore_preferred_proper_nouns",
    "title_starts_with_quick_win_verb",
    "is_obvious_single_step_task",
    "decide_task_action",
]

missing_helpers = [name for name in required_helpers if name not in globals()]

if missing_helpers:
    raise NameError("Missing required helper(s) before tests/pipeline: " + ", ".join(missing_helpers))

assert title_starts_with_quick_win_verb("Buy tickets") is True
assert title_starts_with_quick_win_verb("Packaging labels") is False
assert strip_due_date_phrases("Buy tickets TODAY") == "Buy tickets"
assert strip_due_date_phrases("Buy tickets this weekend") == "Buy tickets"
assert strip_due_date_phrases("Call dentist tomorrow morning") == "Call dentist"
assert strip_due_date_phrases("Buy mulch for Behram - urgent - May 10") == "Buy mulch for Behram - urgent"
assert sanitize_task_title_separators("Buy mulch for Behram - -") == "Buy mulch for Behram"
assert is_obvious_single_step_task("Shower") is True
assert needs_ai_cleanup("Shower") is False
assert needs_action_verb("Shower") is False
assert is_immediately_actionable_operational_task("Refill container of bench flour") is True
assert needs_ai_cleanup("Refill container of bench flour") is False
assert needs_action_verb("Refill container of bench flour") is False
assert starts_with_action_verb("Tidy house for Luz") is True
assert needs_ai_cleanup("Tidy house for Luz") is False
assert needs_action_verb("Tidy house for Luz") is False
assert starts_with_action_verb("Bulk up starter for workshop") is True
assert is_immediately_actionable_operational_task("Bulk up starter for workshop") is True
assert needs_ai_cleanup("Bulk up starter for workshop") is False
assert needs_action_verb("Bulk up starter for workshop") is False
assert has_unresolved_placeholder_reference("Fix this") is True
assert needs_ai_cleanup("Fix this") is True
assert is_still_vague("Fix this") is True
assert has_unresolved_placeholder_reference("Fix Bread Basket login issue") is False
assert needs_ai_cleanup("Fix Bread Basket login issue") is False
assert has_unresolved_placeholder_reference("Check execution rankings for issues") is False

# This must not require AI helper cells, which are defined later in the notebook.
_, _struct_title, _struct_due = prepare_task_title({"text": "Change furnace filter this weekend"}, allow_ai=False)
assert _struct_title == "Change furnace filter"
assert _struct_due is not None

print("Structural helper order tests passed")


# ## 5.1 Deterministic title post-processing
# 
# Small cleanup rules that should not depend on AI output.
# 

# ## 🧪 TASK CLASSIFICATION TEST HARNESS
# 
# This is the local regression test suite for task rewriting and breakdown classification.
# 
# What it checks:
# - noun-only tasks such as `Grocery list (JDI)` become actionable titles like `Create grocery list`
# - clear action tasks such as `Email dentist` are not over-rewritten
# - vague tasks such as `Email guy about thing` still trigger AI cleanup
# - known simple tasks do not get broken down unnecessarily
# 
# This section is safe: it makes no AI calls and no Notion writes. Due-date tests call `prepare_task_title(..., allow_ai=False)` so they do not depend on AI helper cells loaded later.
# 
# 

# In[38]:

# =============================================================================
# 🧪 TASK CLASSIFICATION TEST HARNESS
# =============================================================================
# Set TEST_MODE = True in the run-mode cell to run these checks safely.
# Keep this cell after the deterministic task helpers so test mode can call them.
# This cell intentionally avoids AI calls and Notion writes.

ACTION_REWRITE_TEST_CASES = [
    {
        "input": "Grocery list (JDI)",
        "expected_title": "Create grocery list",
        "expected_jdi": True,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Packing list for trip",
        "expected_title": "Create packing list for trip",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Packaging labels",
        "expected_title": "Packaging labels",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": True,
        "expected_needs_action_verb": True,
    },
    {
        "input": "Meal plan",
        "expected_title": "Create meal plan",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Email dentist",
        "expected_title": "Email dentist",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Ask Janet for Vitamin C",
        "expected_title": "Ask Janet for Vitamin C",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Invite Jennifer Birrell to the Bread Community see email from Carol",
        "expected_title": "Invite Jennifer Birrell to the Bread Community see email from Carol",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Call mom",
        "expected_title": "Call mom",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },

    {
        "input": "Shower",
        "expected_title": "Shower",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },

    {
        "input": "Change furnace filter",
        "expected_title": "Change furnace filter",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Refill container of bench flour",
        "expected_title": "Refill container of bench flour",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Tidy house for Luz",
        "expected_title": "Tidy house for Luz",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Bulk up starter for workshop",
        "expected_title": "Bulk up starter for workshop",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Buy tickets for Ottawa Titans baseball game TODAY",
        "expected_title": "Buy tickets for Ottawa Titans baseball game",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Buy tickets for Ottawa Titans baseball game this weekend",
        "expected_title": "Buy tickets for Ottawa Titans baseball game",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Buy mulch for Behram - urgent - May 10",
        "expected_title": "Buy mulch for Behram",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Call dentist by Friday",
        "expected_title": "Call dentist",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Call dentist tomorrow morning",
        "expected_title": "Call dentist",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Email guy about thing",
        "expected_title": "Email guy about thing",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": True,
        "expected_needs_action_verb": False,
    },
    {
        "input": "Brainstorm list of enhancements for AIOS",
        "expected_title": "Brainstorm list of enhancements for AIOS",
        "expected_jdi": False,
        "expected_needs_ai_cleanup": False,
        "expected_needs_action_verb": False,
    },
]

BREAKDOWN_CLASSIFICATION_TEST_CASES = [
    {"input": "Setup new earbuds for iPhone", "expected_breakdown": False},
    {"input": "Install printer drivers", "expected_breakdown": False},
    {"input": "Restart Mum's phone", "expected_breakdown": False},
    {"input": "Open Cardwise app on Mum's phone", "expected_breakdown": False},
    {"input": "Call dentist office", "expected_breakdown": False},
    {"input": "Ask Janet for Vitamin C", "expected_breakdown": False},
    {"input": "Change furnace filter", "expected_breakdown": False},
    {"input": "Refill container of bench flour", "expected_breakdown": False},
    {"input": "Tidy house for Luz", "expected_breakdown": False},
    {"input": "Bulk up starter for workshop", "expected_breakdown": False},
    {"input": "Shower", "expected_breakdown": False},
    {"input": "Email school about bread order", "expected_breakdown": False},
    {"input": "Create first draft label in Canva", "expected_breakdown": False},
    {"input": "Design new label for 50% Whole Wheat Sourdough Tin Loaf", "expected_breakdown": True},
    {"input": "Prepare school bread order", "expected_breakdown": True},
    {"input": "Plan summer trip", "expected_breakdown": True},
    {"input": "Organize pantry", "expected_breakdown": True},
    {"input": "Research new packaging options", "expected_breakdown": True},
    {"input": "Conduct photo shoot for Khorasan focaccia recipe", "expected_breakdown": False},  # AI handles this as uncertain in production
    {"input": "Brainstorm list of enhancements for AIOS", "expected_breakdown": False},
]

TASK_DECISION_TEST_CASES = [
    {"input": "Call dentist office", "prepared": "Call dentist office", "expected_decision": "keep"},
    {"input": "Ask Janet for Vitamin C", "prepared": "Ask Janet for Vitamin C", "expected_decision": "keep"},
    {"input": "Invite Jennifer Birrell to the Bread Community see email from Carol", "prepared": "Invite Jennifer Birrell to the Bread Community see email from Carol", "expected_decision": "keep"},
    {"input": "Packaging labels", "prepared": "Clarify next action: Packaging labels", "expected_decision": "clarify"},
    {"input": "Plan summer trip", "prepared": "Plan summer trip", "expected_decision": "breakdown"},
    {"input": "Create first draft label in Canva", "prepared": "Create first draft label in Canva", "expected_decision": "keep"},
    {"input": "Conduct photo shoot for Khorasan focaccia recipe", "prepared": "Conduct photo shoot for Khorasan focaccia recipe", "expected_decision": "keep"},
    {"input": "Brainstorm list of enhancements for AIOS", "prepared": "Brainstorm list of enhancements for AIOS", "expected_decision": "keep"},
    {"input": "Refill container of bench flour", "prepared": "Refill container of bench flour", "expected_decision": "keep"},
    {"input": "Move furniture from furnace room", "prepared": "Move furniture from furnace room", "expected_decision": "keep"},
    {"input": "Tidy house for Luz", "prepared": "Tidy house for Luz", "expected_decision": "keep"},
    {"input": "Bulk up starter for workshop", "prepared": "Bulk up starter for workshop", "expected_decision": "keep"},
    {"input": "Grind coffee beans - caf", "prepared": "Grind coffee beans - caf", "expected_decision": "keep"},
]

def normalize_title_for_test(raw_text):
    """Run the deterministic, pre-AI part of task-title preparation."""
    parsed = parse_task_flags(raw_text)
    title = parsed["clean_title"]
    title = strip_due_date_phrases(title)
    title = rewrite_safe_noun_task(title, allow_ai=False)
    title = restore_preferred_proper_nouns(title)
    return parsed, title

def print_test_result(ok, label, details=""):
    status = "✅ PASS" if ok else "❌ FAIL"
    suffix = f" — {details}" if details else ""
    print(f"{status}: {label}{suffix}")
    return ok

def run_action_rewrite_tests():
    """Validate noun-task action rewrites before JDI / Quick Win handling.

    This intentionally avoids AI calls and Notion writes. It tests the deterministic
    gate that should catch entries like "Grocery list (JDI)" before they become
    non-action tasks.
    """
    print("\n🧪 --- RUNNING ACTION REWRITE TESTS ---\n")

    passed = 0
    failed = 0

    for case in ACTION_REWRITE_TEST_CASES:
        parsed, title = normalize_title_for_test(case["input"])
        checks = [
            (
                title == case["expected_title"],
                f"title: {case['input']} → {title}",
                f"expected {case['expected_title']}",
            ),
            (
                parsed["jdi"] == case["expected_jdi"],
                f"JDI flag: {case['input']} → {parsed['jdi']}",
                f"expected {case['expected_jdi']}",
            ),
            (
                needs_ai_cleanup(title) == case["expected_needs_ai_cleanup"],
                f"AI cleanup: {title} → {needs_ai_cleanup(title)}",
                f"expected {case['expected_needs_ai_cleanup']}",
            ),
            (
                needs_action_verb(title) == case["expected_needs_action_verb"],
                f"needs action verb: {title} → {needs_action_verb(title)}",
                f"expected {case['expected_needs_action_verb']}",
            ),
        ]

        for ok, label, detail in checks:
            if print_test_result(ok, label, "" if ok else detail):
                passed += 1
            else:
                failed += 1

    print(f"\nAction rewrite results: {passed} passed, {failed} failed")
    return failed == 0

def run_breakdown_classification_tests():
    """Validate the no-breakdown vs breakdown classifier on known examples."""
    print("\n🧪 --- RUNNING BREAKDOWN CLASSIFICATION TESTS ---\n")

    passed = 0
    failed = 0

    for case in BREAKDOWN_CLASSIFICATION_TEST_CASES:
        actual = needs_breakdown(case["input"])
        ok = actual == case["expected_breakdown"]

        if print_test_result(
            ok,
            f"breakdown: {case['input']} → {actual}",
            "" if ok else f"expected {case['expected_breakdown']}",
        ):
            passed += 1
        else:
            failed += 1

    print(f"\nBreakdown classification results: {passed} passed, {failed} failed")
    return failed == 0

def run_breakdown_decision_layer_tests():
    """Validate yes / no / uncertain breakdown decisions without AI."""
    print("\n🧪 --- RUNNING BREAKDOWN DECISION LAYER TESTS ---\n")

    cases = [
        ("Call dentist office", "no"),
        ("Create first draft label in Canva", "no"),
        ("Plan summer trip", "yes"),
        ("Design new label for 50% Whole Wheat Sourdough Tin Loaf", "yes"),
        ("Conduct photo shoot for Khorasan focaccia recipe", "uncertain"),
    ]

    passed = 0
    failed = 0

    for raw, expected in cases:
        actual = rule_based_breakdown_decision(raw)
        ok = actual == expected

        if print_test_result(
            ok,
            f"breakdown decision: {raw} → {actual}",
            "" if ok else f"expected {expected}",
        ):
            passed += 1
        else:
            failed += 1

    print(f"\nBreakdown decision layer results: {passed} passed, {failed} failed")
    return failed == 0

def run_task_decision_tests():
    """Validate the final keep / clarify / breakdown decision layer without AI."""
    print("\n🧪 --- RUNNING TASK DECISION TESTS ---\n")

    passed = 0
    failed = 0

    for case in TASK_DECISION_TEST_CASES:
        actual = decide_task_action(
            original_title=case["input"],
            prepared_title=case["prepared"],
            allow_ai=False,
        )
        ok = actual == case["expected_decision"]

        if print_test_result(
            ok,
            f"decision: {case['input']} → {actual}",
            "" if ok else f"expected {case['expected_decision']}",
        ):
            passed += 1
        else:
            failed += 1

    print(f"\nTask decision results: {passed} passed, {failed} failed")
    return failed == 0

def run_due_date_tests():
    """Validate due-date extraction and title stripping stay in sync."""
    print("\n🧪 --- RUNNING DUE DATE TESTS ---\n")

    cases = [
        ("Buy tickets for Ottawa Titans baseball game TODAY", True, "Buy tickets for Ottawa Titans baseball game"),
        ("Buy tickets for Ottawa Titans baseball game this weekend", True, "Buy tickets for Ottawa Titans baseball game"),
        ("Call dentist by Friday", True, "Call dentist"),
        ("Change furnace filter this weekend", True, "Change furnace filter"),
        ("Buy mulch for Behram - urgent - May 10", True, "Buy mulch for Behram"),
    ]

    passed = 0
    failed = 0

    for raw, should_have_due_date, expected_title in cases:
        parsed, title, due_date = prepare_task_title({"text": raw}, allow_ai=False)
        checks = [
            (title == expected_title, f"date strip: {raw} → {title}", f"expected {expected_title}"),
            ((due_date is not None) == should_have_due_date, f"due date: {raw} → {due_date}", f"expected due_date present={should_have_due_date}"),
        ]

        for ok, label, detail in checks:
            if print_test_result(ok, label, "" if ok else detail):
                passed += 1
            else:
                failed += 1

    print(f"\nDue date results: {passed} passed, {failed} failed")
    return failed == 0

NOUN_REWRITE_DECISION_TEST_CASES = [
    {"input": "Grocery list", "expected_decision": "rewrite", "expected_title": "Create grocery list"},
    {"input": "Meal plan", "expected_decision": "rewrite", "expected_title": "Create meal plan"},
    {"input": "Printer drivers", "expected_decision": "rewrite", "expected_title": "Install printer drivers"},
    {"input": "Packaging labels", "expected_decision": "uncertain", "expected_title": "Packaging labels"},
    {"input": "Cardwise issue", "expected_decision": "uncertain", "expected_title": "Cardwise issue"},
    {"input": "Email guy about thing", "expected_decision": "keep", "expected_title": "Email guy about thing"},
]

def run_noun_rewrite_decision_tests():
    """Validate noun rewrite decisions without AI or Notion writes."""
    print("\n🧪 --- RUNNING NOUN REWRITE DECISION TESTS ---\n")

    passed = 0
    failed = 0

    for case in NOUN_REWRITE_DECISION_TEST_CASES:
        actual_decision = rule_based_noun_rewrite_decision(case["input"])
        actual_title = rewrite_safe_noun_task(case["input"], allow_ai=False)

        checks = [
            (
                actual_decision == case["expected_decision"],
                f"noun decision: {case['input']} → {actual_decision}",
                f"expected {case['expected_decision']}",
            ),
            (
                actual_title == case["expected_title"],
                f"noun title: {case['input']} → {actual_title}",
                f"expected {case['expected_title']}",
            ),
        ]

        for ok, label, detail in checks:
            if print_test_result(ok, label, "" if ok else detail):
                passed += 1
            else:
                failed += 1

    print(f"\nNoun rewrite decision results: {passed} passed, {failed} failed")
    return failed == 0



NON_TASK_ROUTING_TEST_CASES = [
    {"input": "Rye seems to ferment faster in warm weather", "expected": "note"},
    {"input": "Note: supplier prefers email orders", "expected": "note"},
    {"input": "Starter 120g after feeding", "expected": "note"},
    {"input": "Too many seed and inclusion breads in this rotation", "expected": "note"},
    {"input": "Clarify next action: Too many seed and inclusion breads in this rotation", "expected": "note"},
    {"input": "Dough that behaves like spelt but has high enzymatic activity", "expected": "note"},
    {"input": "Flour that feels strong but tears easily", "expected": "note"},
    {"input": "Bread with soft crumb but strong crust", "expected": "note"},
    {"input": "Enhancement for AIOS to route non-tasks", "expected": "idea"},
    {"input": "Idea for bakery subscription model", "expected": "idea"},
    {"input": "Possible workflow for school bread orders", "expected": "idea"},
    {"input": "Packaging labels", "expected": "task"},
    {"input": "Email school about bread order", "expected": "task"},
    {"input": "Plan summer trip", "expected": "task"},
]

def run_non_task_routing_tests():
    """Validate obvious non-task notes are routed away from task creation."""
    print("\n🧪 --- RUNNING NON-TASK ROUTING TESTS ---\n")

    passed = 0
    failed = 0

    for case in NON_TASK_ROUTING_TEST_CASES:
        actual = rule_based_non_task_decision(case["input"])
        ok = actual == case["expected"]

        if print_test_result(
            ok,
            f"non-task route: {case['input']} → {actual}",
            "" if ok else f"expected {case['expected']}",
        ):
            passed += 1
        else:
            failed += 1

    print(f"\nNon-task routing results: {passed} passed, {failed} failed")
    return failed == 0

CLARIFICATION_ROUTE_TEST_CASES = [
    {"input": "Packaging labels", "expected_route": "define_context"},
    {"input": "Email guy about thing", "expected_route": "define_context"},
    {"input": "Resolve Cardwise issue for Mum", "expected_route": "choose_next_action"},
    {"input": "Call dentist office", "expected_route": "choose_next_action"},
    {"input": "Ask Janet for Vitamin C", "expected_route": "choose_next_action"},
    {"input": "Invite Jennifer Birrell to the Bread Community see email from Carol", "expected_route": "choose_next_action"},
    {"input": "Plan summer trip", "expected_route": "choose_next_action"},
    {"input": "Brainstorm list of enhancements for AIOS", "expected_route": "choose_next_action"},
    {"input": "Refill container of bench flour", "expected_route": "choose_next_action"},
    {"input": "Tidy house for Luz", "expected_route": "choose_next_action"},
    {"input": "Bulk up starter for workshop", "expected_route": "choose_next_action"},
]

def run_clarification_route_tests():
    """Validate clarification UI routing without AI or Notion writes."""
    print("\n🧪 --- RUNNING CLARIFICATION ROUTE TESTS ---\n")

    passed = 0
    failed = 0

    for case in CLARIFICATION_ROUTE_TEST_CASES:
        actual = clarification_route(case["input"], allow_ai=False)
        ok = actual == case["expected_route"]

        if print_test_result(
            ok,
            f"clarification route: {case['input']} → {actual}",
            "" if ok else f"expected {case['expected_route']}",
        ):
            passed += 1
        else:
            failed += 1

    print(f"\nClarification route results: {passed} passed, {failed} failed")
    return failed == 0


EFFORT_DURATION_TEST_CASES = [
    {"input": "Call dentist office", "expected_decision": "small", "expected_effort": "Small Effort", "expected_duration": "15 min"},
    {"input": "Ask Janet for Vitamin C", "expected_decision": "small", "expected_effort": "Small Effort", "expected_duration": "15 min"},
    {"input": "Invite Jennifer Birrell to the Bread Community see email from Carol", "expected_decision": "small", "expected_effort": "Small Effort", "expected_duration": None},
    {"input": "Email school about bread order", "expected_decision": "small", "expected_effort": "Small Effort", "expected_duration": "15 min"},
    {"input": "Shower", "expected_decision": "small", "expected_effort": "Small Effort", "expected_duration": "15 min"},
    {"input": "Refill container of bench flour", "expected_decision": "small", "expected_effort": "Small Effort", "expected_duration": "15 min"},
    {"input": "Create first draft label in Canva", "expected_decision": "medium", "expected_effort": "Medium Effort", "expected_duration": "30 min"},
    {"input": "Conduct photo shoot for Khorasan focaccia recipe", "expected_decision": "uncertain", "expected_effort": None, "expected_duration": None},
    {"input": "Plan summer trip", "expected_decision": "medium", "expected_effort": "Medium Effort", "expected_duration": "60 min"},
    {"input": "Email guy about thing", "expected_decision": "uncertain", "expected_effort": None, "expected_duration": None},
    {"input": "Review tax documents 30 min", "expected_decision": "medium", "expected_effort": "Medium Effort", "expected_duration": "30 min"},
]

def run_effort_duration_decision_tests():
    """Validate structural effort/duration classification without AI or Notion writes."""
    print("\n🧪 --- RUNNING EFFORT / DURATION DECISION TESTS ---\n")

    passed = 0
    failed = 0

    for case in EFFORT_DURATION_TEST_CASES:
        actual = rule_based_effort_duration_decision(case["input"])
        checks = [
            (
                actual.get("decision") == case["expected_decision"],
                f"effort decision: {case['input']} → {actual.get('decision')}",
                f"expected {case['expected_decision']} from {actual.get('source')}",
            ),
            (
                actual.get("effort") == case["expected_effort"],
                f"effort value: {case['input']} → {actual.get('effort')}",
                f"expected {case['expected_effort']}",
            ),
            (
                actual.get("duration") == case["expected_duration"],
                f"duration value: {case['input']} → {actual.get('duration')}",
                f"expected {case['expected_duration']}",
            ),
        ]

        for ok, label, detail in checks:
            if print_test_result(ok, label, "" if ok else detail):
                passed += 1
            else:
                failed += 1

    print(f"\nEffort / duration decision results: {passed} passed, {failed} failed")
    return failed == 0

IMPORTANCE_DECISION_TEST_CASES = [
    {"input": "Submit tax documents to accountant", "explicit": False, "expected": "High Importance"},
    {"input": "Pay Mastercard bill", "explicit": False, "expected": "High Importance"},
    {"input": "Pay invoice for pool opening", "explicit": False, "expected": "High Importance"},
    {"input": "Email school about bread order", "explicit": False, "expected": "High Importance"},
    {"input": "Important - review school forms", "explicit": True, "expected": "High Importance"},
    {"input": "Update Important Information page", "explicit": False, "expected": None},
    {"input": "Buy pool supplies", "explicit": False, "expected": None},
    {"input": "Research credit card rewards", "explicit": False, "expected": None},
    {"input": "Sort old invoices", "explicit": False, "expected": None},
    {"input": "Buy milk", "explicit": False, "expected": None},
]

def run_importance_decision_tests():
    """Validate conservative Importance inference without AI or Notion writes."""
    print("\n🧪 --- RUNNING IMPORTANCE DECISION TESTS ---\n")

    passed = 0
    failed = 0

    for case in IMPORTANCE_DECISION_TEST_CASES:
        result = infer_importance(case["input"], explicit_important=case.get("explicit", False))
        actual = result.get("importance")
        ok = actual == case["expected"]

        if print_test_result(
            ok,
            f"importance: {case['input']} → {actual}",
            "" if ok else f"expected {case['expected']}",
        ):
            passed += 1
        else:
            failed += 1

    print(f"\nImportance decision results: {passed} passed, {failed} failed")
    return failed == 0

def run_manual_project_tag_tests():
    """Regression tests for low-friction Brain Dump project hints."""
    cases = [
        ("[Basement Recovery] Get flooring quote", "Get flooring quote", "Basement Recovery"),
        ("Get flooring quote [Basement Recovery]", "Get flooring quote", "Basement Recovery"),
        ("[basement] Call flooring contractor", "Call flooring contractor", "basement"),
        ("JDI Call flooring contractor [Basement Recovery]", "Call flooring contractor", "Basement Recovery"),
        ("[urgent] Call flooring contractor", "Call flooring contractor", ""),
        ("Call flooring contractor [important]", "Call flooring contractor", ""),
        ("Discuss [Basement Recovery] naming", "Discuss Basement Recovery naming", ""),
        ("Buy milk", "Buy milk", ""),
    ]
    ok = True
    for raw, expected_title, expected_project in cases:
        parsed = parse_task_flags(raw)
        actual_title = parsed.get("clean_title")
        actual_project = parsed.get("manual_project")
        passed = actual_title == expected_title and actual_project == expected_project
        print(
            f"{'PASS' if passed else 'FAIL'} manual project hint: {raw!r} "
            f"-> title={actual_title!r}, project={actual_project!r}"
        )
        ok = ok and passed
    return ok


def run_task_classification_tests():
    """Run all local task tests. Safe: no AI calls and no Notion writes."""
    action_ok = run_action_rewrite_tests()
    noun_ok = run_noun_rewrite_decision_tests()
    breakdown_ok = run_breakdown_classification_tests()
    breakdown_decision_ok = run_breakdown_decision_layer_tests()
    decision_ok = run_task_decision_tests()
    due_date_ok = run_due_date_tests()
    clarification_route_ok = run_clarification_route_tests()
    non_task_ok = run_non_task_routing_tests()
    effort_duration_ok = run_effort_duration_decision_tests()
    importance_ok = run_importance_decision_tests()
    manual_project_tag_ok = run_manual_project_tag_tests()

    all_ok = (
        action_ok
        and noun_ok
        and breakdown_ok
        and breakdown_decision_ok
        and decision_ok
        and due_date_ok
        and clarification_route_ok
        and non_task_ok
        and effort_duration_ok
        and importance_ok
        and manual_project_tag_ok
    )
    print("\n✅ All task classification tests passed" if all_ok else "\n❌ Some task classification tests failed")
    return all_ok

if TEST_MODE:
    TESTS_PASSED = run_task_classification_tests()



# ## 6. AI helpers
# 
# AI calls are isolated here so prompts are easier to review and tune.
# 

# In[39]:

def soft_rewrite_task_title_with_ai(title):
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""Lightly improve this task title.

Hard rules:
- Do not use title case.
- Use normal sentence case.
- Preserve capitalization of proper nouns (e.g., Mum, Cardwise).
- Only change grammar or missing possessives.
- Do not add missing context.
- Do not guess who, what, why, or where.
- Preserve the original meaning only.
- Keep it short.
- If it is already clear, return it unchanged.
- Return only the task title.
- Do not add possessives unless the original clearly refers to a person or named owner.
- Do not change noun phrases like "school bread order" into possessives.

Examples:
Check Mum Cardwise app → Check Mum's Cardwise app
Buy milk → Buy milk
Call dentist → Call dentist

Task: {title}
"""
        )

        rewritten = response.output_text.strip()

        if not rewritten or len(rewritten) < 3:
            return restore_preferred_proper_nouns(title)

        return restore_preferred_proper_nouns(rewritten)

    except Exception as e:
        print("AI soft rewrite failed:", e)
        return title

# In[40]:

if TEST_ONLY:
    client = None
elif OpenAI is None:
    if TEST_MODE:
        client = None
        print("OpenAI package not available; TEST_MODE continues without AI client.")
    else:
        raise RuntimeError("The openai package is required outside TEST_ONLY mode. Install it in your venv first.")
else:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def is_rewrite_too_different(original, rewritten):
    """Guard against AI rewrites that invent a new task.

    If the rewrite shares too little language with the original, keep the
    original instead. This prevents failures like:
    "Email guy about thing" → unrelated video/TikTok task.
    """
    original_words = set(words_in(original))
    rewritten_words = set(words_in(rewritten))

    if not original_words or not rewritten_words:
        return True

    shared = original_words & rewritten_words

    # Always allow explicit clarification wrappers around the original task.
    if rewritten.lower().startswith("clarify next action:"):
        return False

    # For very short vague inputs, require at least one meaningful shared word.
    if len(original_words) <= 4:
        return len(shared) < 1

    # For longer inputs, require at least two shared words or a decent overlap ratio.
    overlap_ratio = len(shared) / max(len(original_words), 1)
    return len(shared) < 2 and overlap_ratio < 0.35

def rewrite_task_title_with_ai(title):
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""Rewrite this as a clear, actionable task title.

Hard rules:
- Do not invent new context, projects, domains, tools, people, or details.
- Only rewrite using the exact meaning of the original task.
- Do not guess who, what, why, or where.
- Preserve the original meaning only.
- Start with a verb when possible.
- Keep it short.
- If the task is unclear, do NOT guess. Return the original task unchanged.
- Do NOT turn a vague task into an unrelated specific task.
- Do NOT return a clarification for clear atomic tasks such as open, restart, call, email, check, print, buy, book, or submit when the object is clear.
- Do NOT return a clarification for clear setup/process tasks such as setup, set up, install, configure, prepare, plan, organize, build, or launch.
- Do NOT return a clarification for creative/design tasks such as design, create, draft, develop, edit, revise, or write when the object is clear.
- Creative tasks are allowed to be open-ended; open-ended does not mean vague.
- If a task can reasonably be started without more information, keep it actionable and let later logic decide whether to break it down.
- If the task truly lacks a clear object or next action, return the original task unchanged.

Task: {title}
"""
        )

        rewritten = response.output_text.strip()

        if not rewritten or len(rewritten) < 3:
            return restore_preferred_proper_nouns(title)

        if is_rewrite_too_different(title, rewritten):
            print("→ Rewrite rejected as too different; keeping original")
            return restore_preferred_proper_nouns(title)

        return restore_preferred_proper_nouns(rewritten)

    except Exception as e:
        print("AI rewrite failed:", e)
        return title

# In[41]:

def ask_ai_noun_rewrite_decision(title):
    """Ask AI whether a noun phrase can be safely rewritten as an action."""
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""Classify this task title for a personal task pipeline.

The title may be a noun phrase rather than an action.

Return ONLY raw JSON with this shape:
{{
  "decision": "rewrite" | "clarify" | "keep",
  "title": "..."
}}

Definitions:
- rewrite = the missing verb is obvious and can be added without inventing context.
- clarify = essential action/context is missing or there are multiple plausible actions.
- keep = the title is already actionable or should be preserved as-is.

Rules:
- Do not invent people, tools, dates, projects, or details.
- If multiple actions are plausible, use clarify.
- If decision is rewrite, title must start with a verb and preserve the original meaning.
- If decision is clarify or keep, title must be the original title unchanged.

Examples:
Input: Grocery list
Output: {{"decision":"rewrite","title":"Create grocery list"}}

Input: Packaging labels
Output: {{"decision":"clarify","title":"Packaging labels"}}

Input: Cardwise issue
Output: {{"decision":"clarify","title":"Cardwise issue"}}

Input: Shower
Output: {{"decision":"keep","title":"Shower"}}

Task title: {title}
"""
        )

        import json

        raw = response.output_text.strip()
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            print("AI noun decision returned non-JSON:", raw)
            return {"decision": "clarify", "title": title}

        result = json.loads(match.group(0))
        decision = str(result.get("decision", "clarify")).strip().lower()
        new_title = str(result.get("title", title)).strip()

        if decision not in {"rewrite", "clarify", "keep"}:
            return {"decision": "clarify", "title": title}

        if decision != "rewrite":
            return {"decision": decision, "title": title}

        if not new_title or is_rewrite_too_different(title, new_title):
            print("→ AI noun rewrite rejected; keeping original")
            return {"decision": "clarify", "title": title}

        return {"decision": "rewrite", "title": restore_preferred_proper_nouns(new_title)}

    except Exception as e:
        print("AI noun rewrite decision failed:", e)
        return {"decision": "clarify", "title": title}

def ask_ai_task_decision(title):
    """Ask AI to classify one task as keep, clarify, or breakdown.

    Used only after deterministic rules land in the risky clarification path.
    Returns one of: keep, clarify, breakdown.
    """
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""Classify this task for a personal task pipeline.

Return exactly one word: keep, clarify, or breakdown.

Definitions:
- keep = clear, actionable, best as one normal task.
- clarify = missing essential context, unclear object, vague placeholder, or cannot reasonably be started.
- breakdown = clear outcome, but likely needs several meaningful steps such as planning, setup, execution, review, or follow-up.

Rules:
- Do not classify a clear task as clarify just because it is open-ended.
- Use clarify only when essential information is missing.
- Use breakdown for clear multi-step work.
- Do not invent details.

Examples:
Task: Email guy about thing
Decision: clarify

Task: Call dentist office
Decision: keep

Task: Create first draft label in Canva
Decision: keep

Task: Conduct photo shoot for Khorasan focaccia recipe
Decision: breakdown

Task: {title}
Decision:
"""
        )

        decision = response.output_text.strip().lower()
        decision = re.sub(r"[^a-z]", "", decision)

        if decision in TASK_DECISIONS:
            return decision

        print("AI task decision returned unexpected value:", response.output_text.strip())
        return "clarify"

    except Exception as e:
        print("AI task decision failed:", e)
        return "clarify"

def ask_ai_clarification_route(title):
    """Ask AI which clarification UI route fits this task.

    Returns one of: define_context, choose_next_action. Used only when the
    deterministic route wants help; test-only mode never calls this.
    """
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""Classify how this unclear task should be clarified in a personal task system.

Return exactly one value: define_context or choose_next_action.

Definitions:
- define_context = essential context is missing; ask a short question first.
- choose_next_action = the task is understandable, but user should choose the first concrete action.

Use define_context for:
- vague placeholders such as thing, stuff, guy, someone, something.
- noun fragments where the intended action is unclear.
- weak references such as this, that, or it without clear context.

Use choose_next_action for:
- clear issue-resolution tasks.
- clear open-ended tasks where the object/context is known.
- tasks that can be started but have several possible first moves.

Rules:
- Do not invent task details.
- Do not suggest the actions; only classify the route.

Examples:
Task: Packaging labels
Route: define_context

Task: Email guy about thing
Route: define_context

Task: Resolve Cardwise issue for Mum
Route: choose_next_action

Task: Call dentist office
Route: choose_next_action

Task: {title}
Route:
"""
        )

        route = response.output_text.strip().lower()
        route = re.sub(r"[^a-z_]", "", route)

        if route in CLARIFICATION_ROUTES:
            return route

        print("AI clarification route returned unexpected value:", response.output_text.strip())
        return rule_based_clarification_route(title)

    except Exception as e:
        print("AI clarification route failed:", e)
        return rule_based_clarification_route(title)

def ask_ai_breakdown_decision(title):
    """Ask AI whether a clear task should become a parent + ordered subtasks.

    Returns one of: yes, no. Used only for rule-based breakdown uncertainty.
    """
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""Classify whether this clear task should be broken down into a parent task with ordered subtasks.

Return exactly one word: yes or no.

Use yes when:
- The task likely has several meaningful phases, such as planning, setup, execution, review, or follow-up.
- Breaking it into subtasks would reduce thinking load or make the next step obvious.

Use no when:
- It is a clear atomic task.
- It is likely one sitting / one work session.
- A breakdown would add clutter.

Rules:
- Do not ask clarifying questions.
- Do not invent missing details.
- Open-ended does not automatically mean breakdown.

Examples:
Task: Call dentist office
Decision: no

Task: Create first draft label in Canva
Decision: no

Task: Plan summer trip
Decision: yes

Task: Conduct photo shoot for Khorasan focaccia recipe
Decision: yes

Task: {title}
Decision:
"""
        )

        decision = response.output_text.strip().lower()
        decision = re.sub(r"[^a-z]", "", decision)

        if decision in {"yes", "no"}:
            return decision

        print("AI breakdown decision returned unexpected value:", response.output_text.strip())
        return "no"

    except Exception as e:
        print("AI breakdown decision failed:", e)
        return "no"

def ask_ai_quick_win(title, effort, duration):
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
Classify this task as a Quick Win (true/false).

Rules:
- Quick Win = valuable, low-friction, actionable task with low activation energy
- Quick Wins may still be important; do not reject a task only because it has value
- Not Quick Win = planning, research, vague, multi-step, or requires sustained focus
- JDI/Just Do It tasks are excluded before this AI check; do not infer JDI

Title: {title}
Effort: {effort}
Duration: {duration}

Return ONLY:
true or false
"""
        )

        result = response.output_text.strip().lower()

        if result == "true":
            return True
        if result == "false":
            return False

        return False

    except Exception as e:
        print("AI Quick Win check failed:", e)
        return False

# In[42]:

def ask_ai_task_metadata(title):
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
Infer simple task metadata.

Rules:
- Do not invent details.
- Prefer null when uncertain.
- Effort must be one of: Small Effort, Medium Effort, Large Effort, null.
- Duration must be one of: 15 min, 30 min, 60 min, null.
- Confidence must be a number from 0 to 1.
- Return ONLY raw JSON.
- Do not use markdown.
- Do not wrap the JSON in ```.

Task title: {title}

JSON shape:
{{
  "effort": null,
  "duration": null,
  "confidence": 0.0
}}
"""
        )

        import json

        raw = response.output_text.strip()

        # Safety: extract JSON object if AI adds stray text
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)

        if not match:
            print("AI metadata returned non-JSON:", raw)
            return {
                "effort": None,
                "duration": None,
                "confidence": 0
            }

        return json.loads(match.group(0))

    except Exception as e:
        print("AI metadata inference failed:", e)
        return {
            "effort": None,
            "duration": None,
            "confidence": 0
        }

# ## 7. Quick Win and metadata updates
# 

# In[43]:

def get_select_name(props, property_name):
    prop = props.get(property_name, {})
    select_value = prop.get("select")

    if not select_value:
        return None

    return select_value.get("name")

def get_select_or_status_name(props, property_name):
    """Return option name from either Notion Select or Status property shapes."""
    prop = props.get(property_name, {}) if props else {}

    select_value = prop.get("select")
    if select_value:
        return select_value.get("name")

    status_value = prop.get("status")
    if status_value:
        return status_value.get("name")

    return None

def get_checkbox_value(props, property_name):
    return props.get(property_name, {}).get("checkbox", False)


def get_relation_ids(props, property_name):
    """Return relation target page IDs for a Notion relation property."""
    relation = props.get(property_name, {}).get("relation", [])
    return [item.get("id") for item in relation if item.get("id")]

def get_number_value(props, property_name):
    """Return a Notion number property, or None when blank/missing."""
    return props.get(property_name, {}).get("number")

def get_date_start_value(props, property_name):
    """Return the start date/datetime string for a Notion date property."""
    date_value = props.get(property_name, {}).get("date")
    if not date_value:
        return None
    return date_value.get("start")

def parse_notion_date_start(date_start):
    """Parse a Notion date/datetime start value into a date, or None."""
    if not date_start:
        return None

    try:
        # Notion date-only values are YYYY-MM-DD. Datetime values may include
        # a timezone or trailing Z; for defer logic we only need the local date.
        return datetime.fromisoformat(str(date_start).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(str(date_start)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

def get_defer_until_date(task):
    """Return the Defer Until date for a task, or None when blank/unparseable."""
    props = task.get("properties", {})
    return parse_notion_date_start(get_date_start_value(props, DEFER_UNTIL_PROPERTY))

def is_deferred_until_future(task, today=None):
    """Return True when a task should be hidden until a future date.

    Defer Until means: do not surface this task in automated execution views until
    that date arrives. A task deferred to today is eligible again.
    """
    defer_until = get_defer_until_date(task)
    if not defer_until:
        return False

    today = today or datetime.now().date()
    return defer_until > today

def get_parent_task_id(task):
    """Return the first Parent Task relation ID, if this task is a breakdown step."""
    parent_ids = get_relation_ids(task.get("properties", {}), PARENT_TASK_PROPERTY)
    return parent_ids[0] if parent_ids else None

def get_step_order(task):
    return get_number_value(task.get("properties", {}), STEP_ORDER_PROPERTY)

def is_open_task(task):
    props = task.get("properties", {})
    return (
        get_checkbox_value(props, "Open Loop")
        and not get_checkbox_value(props, "Done")
        and not get_checkbox_value(props, "Archived")
    )

def filter_to_next_sequence_tasks(tasks):
    """Keep standalone tasks and only the next incomplete step for each parent.

    Breakdown subtasks are treated as an ordered sequence. If a parent has
    multiple incomplete child steps, only the lowest Step Order is eligible for
    Quick Win selection. This prevents later steps from surfacing
    before earlier steps are complete.
    """
    open_tasks = [task for task in tasks if is_open_task(task) and not is_deferred_until_future(task)]

    children_by_parent = {}
    for task in open_tasks:
        parent_id = get_parent_task_id(task)
        if parent_id:
            children_by_parent.setdefault(parent_id, []).append(task)

    next_child_ids = set()
    parent_ids_with_open_children = set(children_by_parent.keys())

    for parent_id, children in children_by_parent.items():
        ordered_children = sorted(
            children,
            key=lambda task: (
                get_step_order(task) is None,
                get_step_order(task) if get_step_order(task) is not None else 9999,
                task.get("created_time", ""),
            ),
        )
        if ordered_children:
            next_child_ids.add(ordered_children[0]["id"])

    eligible = []
    for task in open_tasks:
        task_id = task["id"]
        parent_id = get_parent_task_id(task)

        # A parent with open children is a container, not the next action.
        if task_id in parent_ids_with_open_children:
            continue

        # A child task is eligible only when it is the next incomplete child.
        if parent_id:
            if task_id in next_child_ids:
                eligible.append(task)
            continue

        # Standalone task.
        eligible.append(task)

    return eligible


def title_contains_not_quick_win_word(title):
    if not title:
        return True

    title_lower = title.lower()
    return any(word in title_lower for word in NOT_QUICK_WIN_WORDS)

QUICK_WIN_DECISIONS = {"yes", "no", "uncertain"}

def rule_based_quick_win_decision(
    title,
    effort=None,
    duration=None,
    done=False,
    archived=False,
    just_do_it=False,
):
    """Return yes / no / uncertain for Quick Win classification.

    Quick Wins are valuable, low-activation-energy tasks: clear, meaningful,
    standalone, and easy to start. They are not assumed to be low importance.
    JDIs are explicit user overrides, so they are excluded before inference.
    """
    title = str(title or "").strip()

    if done or archived or just_do_it:
        return "no"

    if not title or title.lower().startswith("clarify next action:"):
        return "no"

    if effort in ["Medium Effort", "Large Effort"]:
        return "no"

    task_decision = decide_task_action(title, title, allow_ai=False)

    if task_decision in ["clarify", "breakdown"]:
        return "no"

    is_small = (effort == "Small Effort" or duration == "15 min")
    is_short = len(words_in(title)) <= 7

    # Clear structural YES: already known small + standalone.
    if is_small and (is_atomic_action(title) or is_obvious_single_step_task(title) or is_immediately_actionable_operational_task(title)):
        return "yes"

    # Legacy guardrail: high-confidence quick-win verb, but only after the
    # structural checks above have ruled out clarify/breakdown.
    if is_small and title_starts_with_quick_win_verb(title) and not title_contains_not_quick_win_word(title):
        return "yes"

    # Clear NO: not small and not obviously a tiny atomic task.
    if not is_small and not (is_atomic_action(title) and is_short):
        return "no"

    # The remaining cases are the useful AI zone. Examples:
    # - clear short task with missing metadata
    # - small task whose verb is not in the quick-win list
    # - borderline task with actionability but uncertain effort
    return "uncertain"

def classify_quick_win(task):
    props = task.get("properties", {})

    title = get_title(task)


    done = get_checkbox_value(props, "Done")
    archived = get_checkbox_value(props, "Archived")
    just_do_it = get_checkbox_value(props, "Just Do It")

    effort = get_select_name(props, "Effort")
    duration = get_select_name(props, "Duration")

    decision = rule_based_quick_win_decision(
        title,
        effort=effort,
        duration=duration,
        done=done,
        archived=archived,
        just_do_it=just_do_it,
    )

    if decision == "yes":
        return True

    if decision == "no":
        return False

    # AI fallback only for genuinely uncertain cases.
    return ask_ai_quick_win(title, effort, duration)

QUICK_WIN_DECISION_TEST_CASES = [
    {"title": "Call dentist office", "effort": "Small Effort", "duration": None, "expected": "yes"},
    {"title": "Email school about bread order", "effort": "Small Effort", "duration": "15 min", "expected": "yes"},
    {"title": "Plan summer trip", "effort": None, "duration": None, "expected": "no"},
    {"title": "Research new packaging options", "effort": None, "duration": None, "expected": "no"},
    {"title": "Shower", "effort": "Small Effort", "duration": "15 min", "expected": "yes"},
    {"title": "Refill container of bench flour", "effort": "Small Effort", "duration": "15 min", "expected": "yes"},
    {"title": "Create first draft label in Canva", "effort": None, "duration": None, "expected": "no"},
    {"title": "Call dentist office", "effort": "Small Effort", "duration": "15 min", "just_do_it": True, "expected": "no"},
]

def run_quick_win_decision_tests():
    """Validate rule-based Quick Win decisions without AI or Notion writes."""
    print("\n🧪 --- RUNNING QUICK WIN DECISION TESTS ---\n")

    passed = 0
    failed = 0

    for case in QUICK_WIN_DECISION_TEST_CASES:
        actual = rule_based_quick_win_decision(
            case["title"],
            effort=case.get("effort"),
            duration=case.get("duration"),
            just_do_it=case.get("just_do_it", False),
        )
        ok = actual == case["expected"]

        if print_test_result(
            ok,
            f"quick win: {case['title']} → {actual}",
            "" if ok else f"expected {case['expected']}",
        ):
            passed += 1
        else:
            failed += 1

    print(f"\nQuick Win decision results: {passed} passed, {failed} failed")
    return failed == 0

if TEST_MODE:
    QUICK_WIN_TESTS_PASSED = run_quick_win_decision_tests()

    if TEST_ONLY:
        print("\n🧪 TEST-ONLY MODE complete — no Notion or OpenAI calls were made.")
        raise SystemExit

# In[44]:



def update_notion_page(page_id, properties):
    # Generic Notion page property updater.

    url = f"https://api.notion.com/v1/pages/{page_id}"

    payload = {
        "properties": properties
    }

    response = requests.patch(
        url,
        headers=headers,
        json=payload,
    )

    if not response.ok:
        print("\n[Notion Update Failure]")
        print(f"Status: {response.status_code}")
        print(f"Page: {page_id}")
        print("Payload:")
        print(payload)
        print("Response:")
        print(response.text)

    response.raise_for_status()

    return response.json()



# Canonical runtime persistence functions.
#
# These are constructed once and reused by:
#   - Execution Engine V2
#   - Quick Win surfacing/reconciliation
#   - metadata reconciliation
#
# This prevents reconciliation from becoming a second persistence authority.
execution_state_update_fn = build_execution_update_fn(
    notion_update_fn=update_notion_page,
    datastore=AIOS_DATASTORE,
)

quick_win_state_update_fn = build_quick_win_update_fn(
    notion_update_fn=update_notion_page,
    datastore=AIOS_DATASTORE,
)



def update_quick_win_if_needed(task):
    if not task or task.get("dry_run"):
        return False

    props = task.get("properties", {})

    current_quick_win = get_checkbox_value(props, "Quick Win")
    new_quick_win = classify_quick_win(task)

    if current_quick_win == new_quick_win:
        return False

    try:
        update_task_metadata(
            task,
            {
                "Quick Win": {
                    "checkbox": new_quick_win
                }
            },
            datastore=AIOS_DATASTORE,
            notion_update_fn=update_notion_page,
        )

        increment_summary("quick_win_updates")
        title = get_title(task)
        print(f"Updated Quick Win: {title} → {new_quick_win}")
        log_metadata_update(
            title,
            {
                "Quick Win": {
                    "value": new_quick_win,
                    "source": "quick_win_classifier",
                    "confidence": None,
                    "reason": "Quick Win means valuable, actionable, and low activation energy; JDIs are excluded before inference.",
                }
            },
            preserved_metadata={"Previous Quick Win": current_quick_win},
        )
        return True

    except Exception as exc:
        print("ERROR updating Quick Win:", get_title(task))
        print(exc)
        return False

# In[45]:

def sort_quick_wins_by_persisted_execution_metadata(tasks):
    """Sort Quick Wins using persisted Execution Rank / Execution Score only.

    Phase 2G: Quick Win overlay must not call the execution scorer again.
    Execution cognition is owned by Execution Engine V2:
        Evaluator → Execution Score → Execution Rank

    Quick Wins are an overlay and should reuse persisted execution metadata.
    """
    def sort_key(task):
        props = task.get("properties", {})
        rank = get_number_value(props, EXECUTION_RANK_PROPERTY)
        score = get_number_value(props, EXECUTION_SCORE_PROPERTY)
        created = task.get("created_time", "")

        return (
            rank is None,
            rank if rank is not None else 999999,
            -(score if score is not None else -999999),
            created,
        )

    sorted_tasks = sorted(tasks, key=sort_key)
    ranked_count = sum(
        1 for task in sorted_tasks
        if get_number_value(task.get("properties", {}), EXECUTION_RANK_PROPERTY) is not None
    )

    print(
        f"[Quick Win Overlay] Sorted Quick Win overlay tasks from persisted "
        f"Execution Rank/Score; no scorer recomputation. "
        f"Ranked={ranked_count}/{len(sorted_tasks)}"
    )

    return sorted_tasks


def get_eligible_quick_wins():
    filter_payload = {
        "and": [
            {"property": "Open Loop", "checkbox": {"equals": True}},
            {"property": "Done", "checkbox": {"equals": False}},
            {"property": "Archived", "checkbox": {"equals": False}},
            {"property": "Just Do It", "checkbox": {"equals": False}},
        ]
    }

    if AIOS_DATASTORE == "supabase":
        print(
            "[Quick Win Read] Reading Quick Win "
            "candidate population from Supabase"
        )

        open_tasks = (
            get_supabase_quick_win_candidate_tasks()
        )

    else:
        open_tasks = query_tasks_database(
            filter_payload=filter_payload,
            sorts=[
                {
                    "timestamp": "created_time",
                    "direction": "ascending"
                }
            ],
            page_size=100,
        )

    next_sequence_tasks = filter_to_next_sequence_tasks(open_tasks)

    eligible_quick_wins = [
        task for task in next_sequence_tasks
        if get_checkbox_value(task.get("properties", {}), "Quick Win")
    ]

    return sort_quick_wins_by_persisted_execution_metadata(eligible_quick_wins)



def has_property(task, property_name):
    """Return True when a Notion page payload includes a property name."""
    return property_name in (task.get("properties", {}) or {})


def get_task_id_set(tasks):
    """Return non-empty Notion page IDs from task/page-like objects.

    Execution Engine V2 returns BNA winners as ranked-item dictionaries with the
    Notion page stored under ``item["task"]`` rather than as raw page objects.
    Quick Win surfacing consumes both shapes, so normalize IDs here before any
    overlap checks.
    """
    ids = set()
    for item in tasks or []:
        if not isinstance(item, dict):
            continue

        # Raw Notion page payload shape.
        if item.get("id"):
            ids.add(item["id"])
            continue

        # Execution Engine ranked-item shape: {"task": <Notion page>, ...}.
        nested_task = item.get("task")
        if isinstance(nested_task, dict) and nested_task.get("id"):
            ids.add(nested_task["id"])

    return ids


def quick_win_surface_sort_key(task):
    """Sort Quick Win candidates without using execution rank or BNA state.

    Quick Wins are a momentum lane, not a secondary execution ranking. Keep the
    ordering intentionally lightweight and deterministic.
    """
    props = task.get("properties", {}) or {}
    effort = get_select_name(props, "Effort") or ""
    duration = get_select_name(props, "Duration") or ""
    title = get_title(task).lower()

    effort_weight = {
        "Small Effort": 0,
        "Tiny Effort": 0,
        "Medium Effort": 5,
        "Large Effort": 10,
    }.get(effort, 2)

    duration_weight = {
        "5 min": 0,
        "10 min": 0,
        "15 min": 1,
        "30 min": 3,
        "45 min": 5,
        "1 hour": 7,
    }.get(duration, 2)

    return (
        effort_weight,
        duration_weight,
        len(words_in(title)),
        task.get("last_edited_time", ""),
        task.get("created_time", ""),
        title,
    )


def select_surfaced_quick_wins(open_tasks, bna_tasks=None, limit=None):
    """Select a capped Quick Win lane independent of BNA ranking.

    Quick Win is eligibility metadata. Surfaced Quick Win is the visible,
    capped presentation lane. BNA winners are explicitly excluded so the two
    surfaces do not overlap.
    """
    limit = SURFACED_QUICK_WIN_LIMIT if limit is None else limit
    bna_ids = get_task_id_set(bna_tasks)

    next_sequence_tasks = filter_to_next_sequence_tasks(open_tasks or [])

    candidates = []
    excluded_bna = 0
    for task in next_sequence_tasks:
        props = task.get("properties", {}) or {}

        if not get_checkbox_value(props, QUICK_WIN_PROPERTY):
            continue

        if task.get("id") in bna_ids:
            excluded_bna += 1
            continue

        candidates.append(task)

    selected = sorted(candidates, key=quick_win_surface_sort_key)[:limit]

    print("\n--- Quick Win Surfacing ---")
    print(f"Eligible Quick Wins after sequence filtering: {len(candidates) + excluded_bna}")
    print(f"Excluded BNA overlap: {excluded_bna}")
    print(f"Surfaced Quick Win target: {limit}")
    print(f"Surfaced Quick Wins selected: {len(selected)}")

    for index, task in enumerate(selected, start=1):
        print(f"QW surface {index}: {get_title(task)}")

    return selected


def refresh_surfaced_quick_wins(open_tasks, bna_tasks=None, limit=None):
    """Reconcile the capped Surfaced Quick Win presentation lane.

    This function does not mutate Do = Today, Focus, Focus Now, Execution Rank,
    Execution Score, or Best Next Action. It only maintains the dedicated
    Surfaced Quick Win checkbox when that property exists in the Tasks DB.
    """
    if TEST_MODE or DRY_RUN:
        print("TEST_MODE/DRY_RUN enabled → skipping Surfaced Quick Win reconciliation.")
        return []

    open_tasks = open_tasks or []

    if not any(has_property(task, SURFACED_QUICK_WIN_PROPERTY) for task in open_tasks):
        print(
            f"[Quick Win Surfacing] Property '{SURFACED_QUICK_WIN_PROPERTY}' not found. "
            "Create it as a checkbox property to enable capped Quick Win surfacing."
        )
        return []

    selected = select_surfaced_quick_wins(
        open_tasks=open_tasks,
        bna_tasks=bna_tasks,
        limit=limit,
    )
    selected_ids = get_task_id_set(selected)
    bna_ids = get_task_id_set(bna_tasks)

    quick_win_update_fn = quick_win_state_update_fn

    changed = 0
    quick_win_overlap_cleared = 0
    for task in open_tasks:
        props = task.get("properties", {}) or {}
        task_id = task.get("id")

        updates = {}

        # Governance rule: a task may not be both Best Next Action and Quick Win.
        # Earlier versions only excluded BNA winners from the capped
        # `Surfaced Quick Win` lane, while leaving the underlying `Quick Win`
        # eligibility checkbox set. That still allowed Notion views filtering on
        # `Quick Win` to show the same task in both sections. Clear the eligibility
        # flag for active BNA winners so both old and new Quick Win views agree.
        if (
            task_id in bna_ids
            and has_property(task, QUICK_WIN_PROPERTY)
            and get_checkbox_value(props, QUICK_WIN_PROPERTY)
        ):
            updates[QUICK_WIN_PROPERTY] = {"checkbox": False}

        if has_property(task, SURFACED_QUICK_WIN_PROPERTY):
            current = get_checkbox_value(props, SURFACED_QUICK_WIN_PROPERTY)
            desired = task_id in selected_ids
            if current != desired:
                updates[SURFACED_QUICK_WIN_PROPERTY] = {"checkbox": desired}

        if not updates:
            continue

        try:
            quick_win_update_fn(task["id"], updates)
            changed += 1
            if QUICK_WIN_PROPERTY in updates:
                quick_win_overlap_cleared += 1
                increment_summary("quick_win_updates")
                print(f"Cleared Quick Win on BNA overlap: {get_title(task)}")
            if SURFACED_QUICK_WIN_PROPERTY in updates:
                increment_summary("surfaced_quick_win_updates")
                print(
                    f"Updated Surfaced Quick Win: {get_title(task)} → "
                    f"{updates[SURFACED_QUICK_WIN_PROPERTY]['checkbox']}"
                )
        except Exception as e:
            increment_summary("errors")
            print(f"ERROR updating Quick Win surfacing metadata: {get_title(task)}")
            print(e)

    print(f"Quick Win/BNA overlaps cleared: {quick_win_overlap_cleared}")
    print(f"Surfaced Quick Win reconciliation updates: {changed}")
    return selected



def update_missing_metadata_if_confident(
    task,
    confidence_threshold=0.8,
    explicit_important=False,
    explicit_urgent=False,
    original_text=None,
):
    if not task or task.get("dry_run"):
        return task

    props = task.get("properties", {})
    title = get_title(task)


    # Preserve original inbox wording for downstream enrichment passes.
    source_text = original_text or title

    print(
        "[Metadata Source Text]",
        {
            "source_text": source_text,
        }
    )
    current_effort = get_select_name(props, "Effort")
    current_duration = get_select_name(props, "Duration")
    current_importance = get_select_name(props, "Importance")

    # -----------------------------------------------------------------
    # Explicit temporal reinforcement parsing
    # -----------------------------------------------------------------
    temporal_metadata = extract_temporal_metadata(source_text)

    normalized_source = source_text.lower()

    temporal_tokens = temporal_metadata.get(
        "temporal_tokens_found",
        [],
    )

    explicit_today = any(
        token in temporal_tokens
        for token in ["today", "tonight"]
    )

    explicit_tomorrow = any(
        "tomorrow" in token
        for token in temporal_tokens
    )

    print(
        "[TEMPORAL AUTHORITY]",
        {
            "input": source_text,
            "cleaned_title": temporal_metadata.get("cleaned_title"),
            "due_date": str(temporal_metadata.get("due_date")),
            "tokens": temporal_metadata.get("temporal_tokens_found"),
        }
    )

    updates = {}
    changed_metadata = {}
    preserved_metadata = {
        "Effort": current_effort,
        "Duration": current_duration,
        "Importance": current_importance,
    }

    # First pass: deterministic structural classifier. This avoids calling AI for
    # obvious small atomic tasks and prevents breakdown parents from being marked
    # as tiny Quick Wins just because they contain a familiar verb.
    rule_result = classify_effort_duration(title)

    if not current_effort and rule_result.get("effort") in VALID_EFFORT_VALUES:
        updates["Effort"] = {
            "select": {"name": rule_result["effort"]}
        }
        changed_metadata["Effort"] = {
            "value": rule_result["effort"],
            "source": rule_result.get("source", "rule"),
            "confidence": rule_result.get("confidence"),
            "reason": "Structural effort/duration classifier",
        }

    if not current_duration and rule_result.get("duration") in VALID_DURATION_VALUES:
        updates["Duration"] = {
            "select": {"name": rule_result["duration"]}
        }
        changed_metadata["Duration"] = {
            "value": rule_result["duration"],
            "source": rule_result.get("source", "rule"),
            "confidence": rule_result.get("confidence"),
            "reason": "Structural effort/duration classifier",
        }

    if not current_importance:
        importance_result = infer_importance(title, explicit_important=explicit_important)
        if importance_result.get("importance") in VALID_IMPORTANCE_VALUES:
            updates["Importance"] = {
                "select": {"name": importance_result["importance"]}
            }
            changed_metadata["Importance"] = {
                "value": importance_result["importance"],
                "source": importance_result.get("source"),
                "confidence": importance_result.get("confidence"),
                "reason": importance_result.get("reason"),
            }

    # -----------------------------------------------------------------
    # Explicit temporal reinforcement
    # -----------------------------------------------------------------
    if explicit_today:
        due_date = datetime.now().date()

        updates["Due Date"] = {
            "date": {
                "start": due_date.isoformat()
            }
        }

        changed_metadata["Due Date"] = {
            "value": due_date.isoformat(),
            "source": "explicit_temporal_reference",
            "reason": "Duplicate reinforcement contained explicit 'today' reference",
        }

        print(
            "[Temporal Reinforcement]",
            {
                "title": title,
                "due_date": due_date.isoformat(),
            }
        )

    elif explicit_tomorrow:
        due_date = datetime.now().date() + timedelta(days=1)

        updates["Due Date"] = {
            "date": {
                "start": due_date.isoformat()
            }
        }

        changed_metadata["Due Date"] = {
            "value": due_date.isoformat(),
            "source": "explicit_temporal_reference",
            "reason": "Duplicate reinforcement contained explicit 'tomorrow' reference",
        }

        print(
            "[Temporal Reinforcement]",
            {
                "title": title,
                "due_date": due_date.isoformat(),
            }
        )


    # If the rule pass did not fill effort/duration confidently, use AI only for
    # the remaining blanks. Existing values and deterministic updates are preserved.
    remaining_effort_missing = not current_effort and "Effort" not in updates
    remaining_duration_missing = not current_duration and "Duration" not in updates

    if remaining_effort_missing or remaining_duration_missing:
        result = ask_ai_task_metadata(title)

        if result.get("confidence", 0) >= confidence_threshold:
            if remaining_effort_missing and result.get("effort") in VALID_EFFORT_VALUES:
                updates["Effort"] = {
                    "select": {"name": result["effort"]}
                }
                changed_metadata["Effort"] = {
                    "value": result["effort"],
                    "source": "ai_metadata",
                    "confidence": result.get("confidence"),
                    "reason": "AI metadata inference filled missing effort",
                }

            if remaining_duration_missing and result.get("duration") in VALID_DURATION_VALUES:
                updates["Duration"] = {
                    "select": {"name": result["duration"]}
                }
                changed_metadata["Duration"] = {
                    "value": result["duration"],
                    "source": "ai_metadata",
                    "confidence": result.get("confidence"),
                    "reason": "AI metadata inference filled missing duration",
                }

    if not updates:
        return task

    try:
        updated_task = update_task_metadata(
            task,
            updates,
            datastore=AIOS_DATASTORE,
            notion_update_fn=update_notion_page,
        )

        increment_summary("metadata_updates")
        if "Importance" in updates:
            increment_summary("importance_updates")
        print(f"Updated metadata: {title} → {updates}")
        if "Importance" in changed_metadata:
            print(f"Importance: {title} → {changed_metadata['Importance']['value']}")
        log_metadata_update(title, changed_metadata, preserved_metadata)
        return updated_task

    except Exception as exc:
        print("ERROR updating metadata:", title)
        print(exc)
        return task

# ## 8. Clarification flow
# 
# Functions for creating clarification blocks, reading checked choices, generating more options, and converting a selected clarification into a ready task.
# 

# In[49]:

def is_command_checkbox(text):
    text = text.strip()
    return (
        GENERATE_MORE_COMMAND in text
        or ADD_OWN_OPTION_COMMAND in text
        or ASK_TARGETED_QUESTION_COMMAND in text
    )


def clarification_mode_reason(task_title):
    """Return (mode, reason) for clarification generation telemetry.

    Analytical mode is for evaluation/audit tasks. It should generate
    outcome-producing first steps, not prerequisite-gathering steps.
    """
    route = clarification_route(task_title, allow_ai=True)
    if route == "define_context":
        return "define_context", "route_define_context"

    text = (task_title or "").lower().strip()
    analytical_terms = [
        "audit", "validate", "validation", "compare", "review", "analyze",
        "analyse", "inspect", "diagnose", "investigate", "verify", "confirm",
        "reconcile", "reconciliation", "rank", "ranking", "rankings", "metadata",
        "telemetry", "log", "logs", "report", "reports", "dashboard",
        "anomaly", "anomalies", "discrepancy", "discrepancies", "governance",
        "ontology", "baseline", "score", "scoring", "quality", "health",
        "regression", "regressions", "drift", "stability",
    ]
    analytical_prefixes = (
        "aios:", "audit ", "validate ", "verify ", "review ", "compare ",
        "inspect ", "analyze ", "analyse ", "diagnose ",
    )

    if text.startswith(analytical_prefixes):
        return "analytical", "analytical_prefix"

    matches = [term for term in analytical_terms if term in text]
    if matches:
        return "analytical", "analytical_terms=" + ",".join(matches[:4])

    return "procedural", "default_procedural"


def clarification_mode(task_title):
    """Return the clarification generation mode for a task title."""
    return clarification_mode_reason(task_title)[0]


def clarification_prompt_for_mode(task_title):
    mode, reason = clarification_mode_reason(task_title)
    print(f"[Clarification Mode] version={CLARIFICATION_ANALYTICAL_MODE_VERSION}; mode={mode}; reason={reason}; task={task_title}")
    if mode == "define_context":
        return DEFINE_PROMPT
    if mode == "analytical":
        return ANALYTICAL_CHOOSE_PROMPT
    return CHOOSE_PROMPT


def clean_clarification_suggestions(raw_suggestions, mode, task_title):
    """Normalize and guard clarification suggestions.

    Prompting alone was allowing analytical tasks to degrade into tool-centric
    preparation steps such as retrieve/open/download. This post-filter keeps
    analytical options focused on outcomes: findings, discrepancies, anomalies,
    or decisions.
    """
    cleaned = []
    seen = set()
    banned_analytical_prefixes = (
        "access ", "retrieve ", "download ", "open ", "locate ", "find the ",
        "gather ", "collect ", "prepare ", "create a spreadsheet",
        "make a spreadsheet", "export ", "pull ", "get the ",
    )

    for item in raw_suggestions:
        s = (item or "").strip().strip("-•0123456789. ").strip()
        if not s:
            continue
        low = s.lower()
        if mode == "analytical" and low.startswith(banned_analytical_prefixes):
            print(f"[Clarification Filter] dropped_non_outcome_step={s}")
            continue
        if low in seen:
            continue
        seen.add(low)
        cleaned.append(s)

    if mode == "analytical" and len(cleaned) < 2:
        fallback = [
            "Review top-ranked tasks for obvious scoring anomalies",
            "Compare top-ranked tasks against their underlying metadata",
            "Identify rankings inconsistent with Urgency, Importance, or Due Date",
            "Document the first ranking discrepancy found",
        ]
        for s in fallback:
            low = s.lower()
            if low not in seen:
                cleaned.append(s)
                seen.add(low)
            if len(cleaned) >= 4:
                break
        print(f"[Clarification Fallback] analytical_defaults_applied; task={task_title}")

    limit = 5 if mode != "analytical" else 4
    return cleaned[:limit]




# In[52]:

def generate_clarification_suggestions(task_title):
    """Generate one strong clarified-task proposal.

    The list return type is retained for backward compatibility with callers
    and older package code, but proposal-first V2 intentionally returns only
    one suggestion.
    """
    mode, reason = clarification_mode_reason(task_title)
    print(f"[Clarification] version={CLARIFICATION_ANALYTICAL_MODE_VERSION}; mode={mode}; reason={reason}; task={task_title}")

    prompt = f"""
Rewrite the task below as one clear, useful next action.

Rules:
- Preserve the user's intent; do not invent facts, people, deadlines, tools, or constraints
- Make the outcome or decision clearer
- Prefer a concrete action the user can recognize and accept
- Do not turn it into a question
- Do not explain your reasoning
- Use one sentence only
- Keep it concise, normally under 20 words
- If the task is analytical, make the first evaluative outcome explicit
- If the task is broad, clarify the decision or planning outcome without guessing missing specifics

Task: {task_title}
"""

    try:
        response = client.responses.create(model="gpt-4.1-mini", input=prompt)
        proposal = response.output_text.strip().strip('"').strip()
        proposal = proposal.splitlines()[0].strip("-•0123456789. ").strip()
        if not proposal:
            return []
        print("[Clarification] proposal_generated=1")
        return [proposal]
    except Exception as e:
        print("AI clarification proposal generation failed:", e)
        return []


def generate_targeted_clarification_question(task_title):
    """Generate exactly one high-leverage question for a rejected proposal."""
    prompt = f"""
Ask exactly one concise question whose answer would let you rewrite this task
as a clear next action.

Rules:
- Ask only for the single most important missing fact
- Do not provide options
- Do not ask multiple questions
- Keep it under 14 words
- End with a question mark
- No explanation or extra text

Task: {task_title}
"""
    try:
        response = client.responses.create(model="gpt-4.1-mini", input=prompt)
        question = response.output_text.strip().splitlines()[0].strip("-•0123456789. ").strip()
        if question and not question.endswith("?"):
            question += "?"
        return question
    except Exception as e:
        print("AI targeted clarification question failed:", e)
        return "What important detail is missing from this task?"


def get_existing_clarification_suggestions(page_id):
    """Return non-command checkbox text, stripping the V2 display prefix."""
    blocks = get_block_children(page_id)
    suggestions = []
    for block in blocks:
        if block.get("type") != "to_do":
            continue
        text = get_block_text(block)
        if not text or is_command_checkbox(text):
            continue
        if text.startswith(USE_SUGGESTION_PREFIX):
            text = text[len(USE_SUGGESTION_PREFIX):].strip()
        suggestions.append(text)
    return suggestions


def generate_more_clarification_suggestions(task_title, existing_suggestions):
    existing_text = "\n".join(f"- {s}" for s in existing_suggestions)
    mode, reason = clarification_mode_reason(task_title)
    print(f"[Clarification] generate_more version={CLARIFICATION_ANALYTICAL_MODE_VERSION}; mode={mode}; reason={reason}; existing={len(existing_suggestions)}; task={task_title}")

    if mode == "define_context":
        prompt = f"""
Generate 2–3 additional clarification questions for this task that needs more context.

Rules:
- Do not repeat or lightly rephrase existing questions
- Each line must be a short question
- Focus on WHO, WHAT, or CONTEXT
- Do not suggest actions like email, call, or text
- Do not include numbering or bullets
- No extra text

Task: {task_title}

Existing questions:
{existing_text}
"""
    elif mode == "analytical":
        prompt = f"""
Generate 2–3 additional outcome-producing analytical first steps for this task.

Rules:
- Do not repeat or lightly rephrase existing suggestions
- Each option must produce an evaluative outcome, finding, discrepancy, anomaly, or decision
- Do NOT split one evaluation into separate options for each field or keyword
- Do NOT suggest merely accessing, retrieving, downloading, opening, preparing, or creating a spreadsheet unless explicitly requested
- Start with a verb
- Be immediately executable
- Keep each option under 14 words
- Do not include numbering or bullets
- No extra text

Task: {task_title}

Existing suggestions:
{existing_text}
"""
    else:
        prompt = f"""
Generate 2–3 additional clear, concrete next actions for this task.

Rules:
- Do not repeat or lightly rephrase existing suggestions
- Each option must be one concrete physical action only
- Do not combine actions with “and,” “then,” “after,” or multiple verbs
- Start with a verb
- Be immediately executable
- Keep each option under 12 words
- Do not include numbering or bullets
- Use they/them pronouns when referring to people unless specified otherwise
- No extra text

Task: {task_title}

Existing suggestions:
{existing_text}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        output = response.output_text.strip()

        raw_suggestions = [
            line.strip("- ").strip()
            for line in output.splitlines()
            if line.strip()
        ]
        suggestions = clean_clarification_suggestions(raw_suggestions, mode, task_title)[:3]
        print(f"[Clarification] additional_suggestions_generated={len(suggestions)}; raw={len(raw_suggestions)}; mode={mode}")
        return suggestions

    except Exception as e:
        print("AI generate-more failed:", e)
        return []


# In[55]:

def prepare_accepted_clarification_title(text):
    """Normalize a human-accepted clarification without re-routing it.

    Once the user explicitly checks a proposed clarification (or edits that
    checkbox and checks it), the choice is authoritative. We still parse flags,
    separate due-date metadata, strip due-date wording from the title, and
    restore preferred proper nouns, but we deliberately do not call the normal
    task-preparation/clarification router again.
    """
    parsed = parse_task_flags(text)
    due_date = extract_due_date(text)
    cleaned_title = strip_due_date_phrases(parsed["clean_title"]) or parsed["clean_title"]
    cleaned_title = restore_preferred_proper_nouns(cleaned_title.strip())
    return parsed, cleaned_title, due_date



# In[56]:


# In[57]:

def rebuild_clarification_blocks(page_id, original_task, suggestions):
    clear_page_children(page_id)

    return append_clarification_blocks(
        page_id=page_id,
        original_task=original_task,
        suggestions=suggestions,
    )

# In[58]:


# In[59]:


# -------------------------------------------------------------------------
# Canonical clarification workflow module
# -------------------------------------------------------------------------
# These six workflow/UI functions now live in aios.clarification. The module's
# conservative configure hook receives the already-initialized runtime globals
# so this refactor changes ownership, not behavior.
from aios import clarification as clarification_helpers
from aios.storage.notion_task_mirror_writer import (
    NotionTaskMirrorTitleWriter,
)

notion_task_mirror_title_writer = None
if AIOS_DATASTORE == 'supabase':
    notion_task_mirror_title_writer = NotionTaskMirrorTitleWriter(headers=headers)
    print('[Task Mirror Title] Writer configured')

from aios.review.clarification_shadow import shadow_clarification_review
from aios.review.clarification_transitions import (
    mark_clarification_awaiting_answer,
    mark_clarification_pending_confirmation,
    resolve_clarification_review,
)

clarification_helpers.configure_clarification_module(globals())

append_clarification_blocks = (
    clarification_helpers.append_clarification_blocks
)
get_checked_clarification_action = (
    clarification_helpers.get_checked_clarification_action
)
update_task_from_selection = (
    clarification_helpers.update_task_from_selection
)
clear_page_children = (
    clarification_helpers.clear_page_children
)
update_clarification_title = (
    clarification_helpers.update_clarification_title
)
process_clarification_selection = (
    clarification_helpers.process_clarification_selection
)

print("[Clarification Module] Canonical workflow functions loaded from aios.clarification")

clarification_shadow_inbox_repo = None
clarification_shadow_review_repo = None

if AIOS_DATASTORE == "supabase":
    try:
        # Local imports remove top-level execution-order dependency.
        from aios.storage.supabase_store import SupabaseStore as _ClarificationSupabaseStore
        from aios.storage.inbox_repository import InboxRepository as _ClarificationInboxRepository
        from aios.review.repository import InboxReviewRepository as _ClarificationInboxReviewRepository

        _clarification_shadow_store = _ClarificationSupabaseStore()
        clarification_shadow_inbox_repo = _ClarificationInboxRepository(
            _clarification_shadow_store
        )
        clarification_shadow_review_repo = _ClarificationInboxReviewRepository(
            _clarification_shadow_store
        )
        print("[Clarification Shadow] Bootstrap imports localized")
        print("[Clarification Shadow] Supabase shadow review repositories configured")
        print("[Clarification Shadow] State transition helpers configured")
        clarification_helpers.configure_clarification_module(globals())
        print("[Clarification Shadow] Runtime dependencies refreshed")
    except Exception as exc:
        print(f"[Clarification Shadow] Bootstrap failed: {exc}")




def token_similarity(a, b):
    set_a = set(words_in(normalize(a)))
    set_b = set(words_in(normalize(b)))

    if not set_a or not set_b:
        return 0

    return len(set_a & set_b) / len(set_a | set_b)

def find_best_task_match(task_title, existing_tasks_by_title):
    normalized_title = normalize(task_title)

    # 1) Exact match first
    if normalized_title in existing_tasks_by_title:
        return existing_tasks_by_title[normalized_title], 1.0

    # 2) Fuzzy match second
    best_task = None
    best_score = 0

    for existing_title, task in existing_tasks_by_title.items():
        score = similarity(task_title, existing_title)

        if score > best_score:
            best_score = score
            best_task = task

    return best_task, best_score

# In[61]:

def get_match_title(match):
    return get_title(match["task"]) if match["task"] else "None"

# In[62]:




# -------------------------------------------------------------------------
# Source-neutral duplicate-review interaction boundary
# -------------------------------------------------------------------------
from aios.notion import duplicate_review as duplicate_review_ui
from aios.storage.supabase_store import SupabaseStore
from aios.storage.inbox_repository import InboxRepository
from aios.review.repository import InboxReviewRepository

duplicate_review_ui.configure_duplicate_review_ui(globals())

inbox_review_ui = duplicate_review_ui.NotionInboxReviewUI()

possible_duplicate_shadow_inbox_repo = None
possible_duplicate_shadow_review_repo = None

if AIOS_DATASTORE == "supabase":
    try:
        _possible_duplicate_shadow_store = SupabaseStore()
        possible_duplicate_shadow_inbox_repo = InboxRepository(
            _possible_duplicate_shadow_store
        )
        possible_duplicate_shadow_review_repo = InboxReviewRepository(
            _possible_duplicate_shadow_store
        )
        print("[Possible Duplicate Shadow] Supabase shadow review repositories configured")
    except Exception as exc:
        print(f"[Possible Duplicate Shadow] Bootstrap failed: {exc}")

print("[Inbox Review UI] Notion duplicate-review interface configured")


# In[63]:

def similarity(a, b):
    seq_score = SequenceMatcher(None, normalize(a), normalize(b)).ratio()
    token_score = token_similarity(a, b)

    return max(seq_score, token_score)

# In[64]:

def score_label(score):
    if score >= HIGH_MATCH_THRESHOLD:
        return "High"
    elif score >= MEDIUM_MATCH_THRESHOLD:
        return "Medium"
    else:
        return "Low"

# Possible-duplicate shadow helper must be defined before the
# top-level Brain Dump classification loop executes.
def shadow_possible_duplicate_review(match):
    """Write an observational Supabase review for a real possible duplicate.

    Notion remains the authoritative review UI. Shadow failures are non-blocking.
    """
    if AIOS_DATASTORE != "supabase":
        return None

    if DRY_RUN:
        return None

    if (
        possible_duplicate_shadow_inbox_repo is None
        or possible_duplicate_shadow_review_repo is None
    ):
        return None

    item = match["item"]
    matched_task = match["task"]
    score = match["score"]

    try:
        shadow_row = (
            possible_duplicate_shadow_inbox_repo
            .get_or_create_shadow_item(item)
        )

        existing_reviews = (
            possible_duplicate_shadow_review_repo
            .get_open_reviews_for_item(
                str(shadow_row["id"])
            )
        )

        for review in existing_reviews:
            if review.review_type == "possible_duplicate":
                print(
                    "[Possible Duplicate Shadow] Existing open review reused:",
                    item["text"],
                )
                return review

        matched_task_id = (
            matched_task.get("_supabase_id")
            or matched_task.get("id")
        )

        payload = {
            "original_text": item["text"],
            "candidate_task_id": (
                str(matched_task_id)
                if matched_task_id
                else None
            ),
            "candidate_task_title": get_title(matched_task),
            "match_score": score,
            "confidence": score_label(score),
            "allowed_decisions": [
                "link_existing",
                "create_anyway",
                "ignore",
            ],
            "authority": "notion_shadow_only",
        }

        review = (
            possible_duplicate_shadow_review_repo
            .create_review(
                inbox_item_id=str(shadow_row["id"]),
                review_type="possible_duplicate",
                payload=payload,
            )
        )

        print(
            "[Possible Duplicate Shadow] Created Supabase review:",
            item["text"],
        )

        return review

    except Exception as exc:
        print(
            "[Possible Duplicate Shadow] Write failed:",
            exc,
        )
        return None

print("[Possible Duplicate Shadow] Execution order fixed")


# Refresh duplicate-review UI dependencies now that score_label and
# matching thresholds/helpers are available in runtime globals.
duplicate_review_ui.configure_duplicate_review_ui(globals())
print("[Inbox Review UI] Runtime dependencies refreshed")


# ## 10. Parent-child linking
# 
# Breakdown tasks now create a parent task first, then create cleanly named subtasks linked through the existing `Parent Task` relation property.
# 

# ## 11. Pipeline run: extract inbox and process clarification selections
# 

# In[65]:

if RUN_TASK_CREATION_PIPELINE:
    inbox_items = inbox_source.list_pending_items()
else:
    inbox_items = []
    print("Task creation pipeline disabled → skipping Brain Dump extraction.")

# In[66]:

if not inbox_items:
    print("Inbox empty → no-op.")
    # raise SystemExit

# In[67]:

if TEST_MODE:
    open_tasks = []
    print("TEST_MODE is enabled → skipping open task queries.")
else:
    open_tasks = get_open_tasks()
RUN_SUMMARY["open_tasks_found"] = len(open_tasks)
print(f"Found {len(open_tasks)} open unfinished tasks")
if len(open_tasks) >= 100:
    print("=== PAGINATION WARNING ===")
    print("100+ tasks detected. Verify all historical tasks are loading.")


# In[68]:

if RUN_TASK_CREATION_PIPELINE:
    print("\n--- Processing clarification selections ---")

    for task in open_tasks:
        title = get_title(task)

        if not title.lower().startswith("clarify next action:"):
            continue

        process_clarification_selection(task)
else:
    print("Task creation pipeline disabled → skipping clarification selection processing.")

# ## 12. Pipeline run: classify inbox items against existing tasks
# 

# In[69]:

matches = []
possible_matches = []
tasks_to_create = []
duplicate_inbox_items = []

if RUN_TASK_CREATION_PIPELINE:
    seen_new_titles = set()

    # Build lookup of existing task titles → task page
    existing_tasks_by_title = {}

    for task in open_tasks:
        title = get_title(task)

        if title:
            existing_tasks_by_title[normalize(title)] = task

    non_task_note_items = []
    non_task_idea_items = []

    for item in inbox_items:
        non_task_decision = rule_based_non_task_decision(item["text"])

        if non_task_decision == "note":
            non_task_note_items.append(item)
            log_ai_processing_decision(
                original=item["text"],
                final_task="",
                action="Skipped",
                reason="Routed as Notes / Reference because this Brain Dump item is informational, not an actionable task.",
                review_needed=False,
                confidence=1.0,
            )
            print("Non-task note:", item["text"])
            continue

        if non_task_decision == "idea":
            non_task_idea_items.append(item)
            log_ai_processing_decision(
                original=item["text"],
                final_task="",
                action="Skipped",
                reason="Routed as Ideas / Backlog because this Brain Dump item describes a possible enhancement or concept, not an executable task.",
                review_needed=False,
                confidence=1.0,
            )
            print("Non-task idea:", item["text"])
            continue

        parsed = parse_task_flags(item["text"])
        task_title = strip_due_date_phrases(parsed["clean_title"])
        task_title = rewrite_safe_noun_task(task_title, allow_ai=False)
        task_title = restore_preferred_proper_nouns(task_title)

        if not task_title:
            continue

        normalized_title = normalize(task_title)

        matched_task, match_score = find_best_task_match(
            task_title,
            existing_tasks_by_title,
        )

        if matched_task and match_score >= HIGH_MATCH_THRESHOLD:
            matches.append({
                "item": item,
                "task": matched_task,
                "score": match_score,
            })

        elif matched_task and match_score >= MEDIUM_MATCH_THRESHOLD:
            possible_matches.append({
                "item": item,
                "task": matched_task,
                "score": match_score,
            })

        else:
            if normalized_title in seen_new_titles:
                duplicate_inbox_items.append(item)
                print("Duplicate within inbox:", task_title)
                log_ai_processing_decision(
                    original=item["text"],
                    final_task=task_title,
                    action="Duplicate",
                    reason="Duplicate detected within the current Brain Dump run; no new task created.",
                    review_needed=False,
                    confidence=1.0,
                )
            else:
                tasks_to_create.append(item)
                seen_new_titles.add(normalized_title)

    RUN_SUMMARY["matches"] = len(matches)
    print(f"Matches: {len(matches)}")
    for match in matches:
        print("✓", match["item"]["text"], f"(score: {match['score']:.2f})")

    RUN_SUMMARY["possible_matches"] = len(possible_matches)
    print(f"\nPossible matches (manual review): {len(possible_matches)}")
    for match in possible_matches:
        print(
            "~",
            match["item"]["text"],
            "→ possible match:",
            get_match_title(match),
            f"(score: {match['score']:.2f})"
        )

        if not DRY_RUN:
            inbox_review_ui.show_possible_duplicate(
                match["item"],
                match["task"],
                match["score"],
            )
            shadow_possible_duplicate_review(match)

    RUN_SUMMARY["duplicate_inbox_items"] = len(duplicate_inbox_items)
    print(f"\nDuplicate inbox items: {len(duplicate_inbox_items)}")
    for item in duplicate_inbox_items:
        print("=", item["text"])

    print(f"\nNon-task notes routed: {len(non_task_note_items)}")
    for item in non_task_note_items:
        print("📝", item["text"])

    print(f"\nNon-task ideas routed: {len(non_task_idea_items)}")
    for item in non_task_idea_items:
        print("💡", item["text"])

    RUN_SUMMARY["new_items_identified"] = len(tasks_to_create)
    print(f"\nNew tasks to create: {len(tasks_to_create)}")
    for item in tasks_to_create:
        print("+", item["text"])
else:
    non_task_note_items = []
    non_task_idea_items = []
    print("Task creation pipeline disabled → skipping inbox classification.")

# In[70]:

updated_matched_items = []

if RUN_TASK_CREATION_PIPELINE:
    for match in matches:
        item = match["item"]
        task = match["task"]

        parsed = parse_task_flags(item["text"])

        should_update_jdi = parsed["jdi"]
        should_update_importance = parsed.get("important", False)
        should_update_urgency = parsed.get("urgent", False)

        explicit_updates = {}
        changed_metadata = {}

        if should_update_jdi:
            explicit_updates["Just Do It"] = {"checkbox": True}
            explicit_updates["Quick Win"] = {"checkbox": False}

        if should_update_importance:
            explicit_updates["Importance"] = {"select": {"name": "High Importance"}}
            changed_metadata["Importance"] = {
                "value": "High Importance",
                "source": "explicit_marker",
                "confidence": 1.0,
                "reason": "Explicit importance marker supplied on a high-confidence existing task match",
            }

        if should_update_urgency:
            explicit_updates["Urgency"] = {"select": {"name": "High Urgency"}}
            changed_metadata["Urgency"] = {
                "value": "High Urgency",
                "source": "explicit_marker",
                "confidence": 1.0,
                "reason": "Explicit urgent/asap marker supplied on a high-confidence existing task match",
            }

        if explicit_updates:
            try:
                updated_task = update_task_metadata(
                    task,
                    explicit_updates,
                    datastore=AIOS_DATASTORE,
                    notion_update_fn=update_notion_page,
                )

                increment_summary("matched_items_updated")
                if should_update_importance:
                    increment_summary("importance_updates")
                print("Updated explicit metadata on existing task:", parsed["clean_title"], "→", explicit_updates)
                if changed_metadata:
                    log_metadata_update(get_title(updated_task), changed_metadata)

                updated_task = update_missing_metadata_if_confident(
                    updated_task,
                    explicit_important=should_update_importance,
                    explicit_urgent=should_update_urgency,
                    original_text=item["text"],
                )

                log_ai_processing_decision(
                    original=item["text"],
                    final_task=get_title(updated_task),
                    action="Duplicate",
                    reason="High-confidence existing task match; updated explicit user metadata on existing task.",
                    review_needed=False,
                    confidence=match.get("score"),
                )
                task = updated_task
                updated_matched_items.append(item)

            except Exception as exc:
                print("ERROR updating existing task:", parsed["clean_title"])
                print(response.status_code, response.text)

        else:
            increment_summary("matched_items_updated")
            print("Matched existing task:", parsed["clean_title"])
            log_ai_processing_decision(
                original=item["text"],
                final_task=get_title(task),
                action="Duplicate",
                reason="High-confidence existing task match; no new task created.",
                review_needed=False,
                confidence=match.get("score"),
            )
            task = update_missing_metadata_if_confident(
                task,
                explicit_important=should_update_importance,
                explicit_urgent=should_update_urgency,
                original_text=item["text"],
            )
            update_quick_win_if_needed(task)
            updated_matched_items.append(item)
else:
    print("Task creation pipeline disabled → skipping matched-task updates.")

# ## 12.1 Breakdown tuning update
# 
# This version separates **vague** tasks from **clear multi-step process** tasks.
# 
# Examples that should now break down instead of clarify:
# - Setup new earbuds for iPhone
# - Install printer drivers
# - Configure WiFi router
# - Organize pantry
# 

# ## 12.2 Creative task clarification tuning
# 
# Creative/design tasks with a clear object are now treated like process tasks:
# they should break down into first-draft steps instead of triggering clarification.
# 
# Examples:
# - Design new label for 50% Whole Wheat Sourdough Tin Loaf
# - Create first draft label in Canva for 50% Whole Wheat Sourdough Tin Loaf
# - Draft menu announcement for this week
# 

# ## 13. Pipeline run: create tasks and archive processed inbox blocks
# 
# Breakdown items now create one parent task plus linked subtasks. Subtasks no longer need title prefixes because the `Parent Task` relation carries that structure.
# 

# In[71]:

created_tasks = []
MAX_SUBTASKS = 5

def notion_text_rich_text(content, max_length=1900):
    """Return a Notion rich_text array for a single plain-text block."""
    safe_content = str(content or "")[:max_length]
    return [{"type": "text", "text": {"content": safe_content}}]

def append_task_notes(page_id, notes, heading="Notes"):
    """Append informational Brain Dump notes to a created task page.

    Notes are page-body context only. They do not affect task title cleanup,
    duplicate matching, clarification, breakdown, metadata, or Quick Win
    Now decisions.
    """
    cleaned_notes = [
        re.sub(r"\s+", " ", str(note or "")).strip()
        for note in (notes or [])
        if str(note or "").strip()
    ]

    if not page_id or not cleaned_notes:
        return False

    if DRY_RUN:
        print(f"[DRY RUN] Would append {len(cleaned_notes)} note(s) to task page {page_id}")
        for note in cleaned_notes:
            print(f"[DRY RUN]   - {note}")
        return True

    children = [
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": notion_text_rich_text(heading)
            },
        }
    ]

    for note in cleaned_notes:
        children.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": notion_text_rich_text(note)
            },
        })

    response = requests.patch(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=headers,
        json={"children": children},
        timeout=30,
    )

    if response.ok:
        increment_summary("task_notes_added", len(cleaned_notes))
        print(f"Added {len(cleaned_notes)} note(s) to task page")
        return True

    increment_summary("errors")
    print("ERROR adding task notes")
    print(response.status_code, response.text)
    return False

def append_notes_to_created_task_pages(created_pages, notes):
    """Attach Brain Dump notes to the first created page for an inbox item.

    For breakdowns, the first page is the parent task. This keeps the notes on
    the container rather than duplicating them across every generated subtask.
    """
    if not created_pages or not notes:
        return False

    first_page = created_pages[0]
    if not first_page:
        return False

    return append_task_notes(first_page.get("id"), notes)





def review_possible_duplicate_items(possible_matches):
    """Read checked duplicate-review commands from inbox items.

    Returns two lists:
    - reviewed_possible_items: items that can be archived without creating a new task
    - possible_items_to_create_anyway: items the user explicitly approved as new tasks
    """
    reviewed_possible_items = []
    possible_items_to_create_anyway = []

    for match in possible_matches:
        item = match["item"]
        action = inbox_review_ui.get_possible_duplicate_action(item)

        if not action:
            continue

        if action == LINK_EXISTING_COMMAND:
            print("Possible duplicate confirmed as existing:", item["text"])
            log_ai_processing_decision(
                original=item["text"],
                final_task=get_title(match["task"]),
                action="Duplicate",
                reason="User confirmed possible duplicate should use the existing task.",
                review_needed=False,
                confidence=match.get("score"),
            )
            reviewed_possible_items.append(item)

        elif action == CREATE_ANYWAY_COMMAND:
            print("Possible duplicate approved as new task:", item["text"])
            possible_items_to_create_anyway.append(item)

        elif action == IGNORE_DUPLICATE_COMMAND:
            print("Possible duplicate ignored:", item["text"])
            log_ai_processing_decision(
                original=item["text"],
                final_task=get_title(match["task"]),
                action="Skipped",
                reason="User ignored possible duplicate review item; no task created.",
                review_needed=False,
                confidence=match.get("score"),
            )
            reviewed_possible_items.append(item)

    return reviewed_possible_items, possible_items_to_create_anyway

def _create_notion_task_only(task_title, is_jdi=False, is_urgent=False, is_important=False, due_date=None, parent_task_id=None, step_order=None, manual_project=""):
    """Create one task page in Notion.

    If parent_task_id is supplied, the new task is linked to that page through
    the Notion relation property named by PARENT_TASK_PROPERTY. Breakdown
    subtasks also receive STEP_ORDER_PROPERTY so execution ordering can surface only
    the next incomplete step in sequence.
    """
    # Final deterministic cleanup before anything is written to Notion.
    task_title = restore_preferred_proper_nouns(task_title)

    effort = classify_effort(task_title)
    icon_emoji = pick_icon(task_title)

    # Importance should be available at create time, not only in the later
    # missing-metadata pass. This prevents newly-created tasks from briefly
    # missing High Importance and gives the cron log a clear create-time trace.
    importance_result = infer_importance(task_title, explicit_important=is_important)
    effective_is_important = importance_result.get("importance") == "High Importance"

    if DRY_RUN:
        print(f"[DRY RUN] Would create: {task_title}")
        if parent_task_id:
            print(f"[DRY RUN] Would link to Parent Task: {parent_task_id}")
        if step_order is not None:
            print(f"[DRY RUN] Would set Step Order: {step_order}")
        if is_urgent:
            print("Urgency: High Urgency")
        if effective_is_important:
            print("Importance: High Importance")
            print(f"Importance reason: {importance_result.get('reason')}")

        dry_run_task = {
            "id": f"dry-run-{len(created_tasks) + 1}",
            "url": None,
            "dry_run": True,
            "title": task_title,
            "urgent": is_urgent,
            "important": effective_is_important,
            "parent_task_id": parent_task_id,
            "step_order": step_order,
            "manual_project": manual_project,
        }
        if manual_project:
            print(f"[DRY RUN] Would set Suggested Project (manual): {manual_project}")
        created_tasks.append(dry_run_task)
        increment_summary("tasks_created")
        if parent_task_id:
            increment_summary("breakdown_subtasks_created")
        elif task_title.lower().startswith("clarify next action:"):
            increment_summary("clarification_tasks_created")
        return dry_run_task

    payload = {
        "parent": {"database_id": TASKS_DATABASE_ID},
        "icon": {
            "type": "emoji",
            "emoji": icon_emoji,
        },
        "properties": {
            "Task Name": {
                "title": [
                    {
                        "text": {
                            "content": task_title,
                        }
                    }
                ]
            },
            "Open Loop": {"checkbox": True},
            "Done": {"checkbox": False},
            "Just Do It": {"checkbox": is_jdi},
        },
    }

    if manual_project:
        payload["properties"][SUGGESTED_PROJECT_PROPERTY] = _notion_rich_text(manual_project)

    if parent_task_id:
        payload["properties"][PARENT_TASK_PROPERTY] = {
            "relation": [{"id": parent_task_id}]
        }

    if step_order is not None:
        payload["properties"][STEP_ORDER_PROPERTY] = {
            "number": step_order
        }

    if task_title.lower().startswith("clarify next action:"):
        payload["properties"]["Status"] = {
            "select": {"name": CLARIFY_STATUS}
        }

    if effort:
        payload["properties"]["Effort"] = {
            "select": {"name": effort}
        }

    if is_urgent:
        payload["properties"]["Urgency"] = {
            "select": {"name": "High Urgency"}
        }

    if effective_is_important:
        payload["properties"]["Importance"] = {
            "select": {"name": "High Importance"}
        }

    if due_date:
        payload["properties"]["Due Date"] = {
            "date": {"start": due_date.isoformat()}
        }

    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if response.ok:
        page = response.json()
        # Runtime-only provenance: distinguish an explicit Brain Dump [project hint]
        # from Suggested Project values later written by AI project emergence.
        # This key is never persisted to Notion.
        if manual_project:
            page["_manual_project_hint"] = manual_project
        created_tasks.append(page)
        increment_summary("tasks_created")
        if parent_task_id:
            increment_summary("breakdown_subtasks_created")
        elif task_title.lower().startswith("clarify next action:"):
            increment_summary("clarification_tasks_created")
        print("Created:", task_title)

        create_time_metadata = {}
        if effective_is_important:
            increment_summary("importance_updates")
            create_time_metadata["Importance"] = {
                "value": "High Importance",
                "source": importance_result.get("source"),
                "confidence": importance_result.get("confidence"),
                "reason": importance_result.get("reason"),
            }
            print(f"Importance: {task_title} → High Importance")
        if is_urgent:
            create_time_metadata["Urgency"] = {
                "value": "High Urgency",
                "source": "explicit_marker",
                "confidence": 1.0,
                "reason": "Explicit urgent/asap marker supplied in Brain Dump",
            }
        if due_date:
            create_time_metadata["Due Date"] = {
                "value": due_date.isoformat(),
                "source": "explicit_date",
                "confidence": 1.0,
                "reason": "Explicit due-date phrase supplied in Brain Dump",
            }
        if create_time_metadata:
            log_metadata_update(task_title, create_time_metadata)

        return page

    increment_summary("errors")
    print("ERROR creating:", task_title)
    print(response.status_code, response.text)
    log_ai_processing_decision(
        original=task_title,
        final_task=task_title,
        action="Error",
        reason=f"Notion task creation failed: {response.status_code}",
        review_needed=True,
    )
    return None


def create_notion_task(
    task_title,
    is_jdi=False,
    is_urgent=False,
    is_important=False,
    due_date=None,
    parent_task_id=None,
    step_order=None,
    manual_project="",
    supabase_primary=False,
):
    """
    Transitional creation dispatcher.

    Explicitly-approved top-level tasks are Supabase-primary, including
    clarification tasks. Their Notion pages remain temporary UI mirrors so
    clarification checkbox/block interaction can continue unchanged.

    Breakdown hierarchy creation uses its dedicated Supabase-first hierarchy
    creator. Relation-bearing ad hoc creations remain on the legacy path unless
    migrated explicitly.
    """

    can_use_supabase_primary = (
        AIOS_DATASTORE == "supabase"
        and supabase_primary
        and parent_task_id is None
        and step_order is None
        and not DRY_RUN
    )

    if can_use_supabase_primary:
        return create_supabase_primary_task(
            task_title=restore_preferred_proper_nouns(
                task_title
            ),
            is_jdi=is_jdi,
            is_urgent=is_urgent,
            is_important=is_important,
            due_date=due_date,
            manual_project=manual_project,
            notion_create_fn=_create_notion_task_only,
            notion_rollback_fn=update_notion_page,
        )

    return _create_notion_task_only(
        task_title,
        is_jdi=is_jdi,
        is_urgent=is_urgent,
        is_important=is_important,
        due_date=due_date,
        parent_task_id=parent_task_id,
        step_order=step_order,
        manual_project=manual_project,
    )

def create_and_update_task(task_title, is_jdi=False, is_urgent=False, is_important=False, due_date=None, parent_task_id=None, step_order=None, manual_project="", supabase_primary=False):
    """Create one task, then apply AI metadata and Quick Win updates."""
    page = create_notion_task(
        task_title,
        is_jdi=is_jdi,
        is_urgent=is_urgent,
        is_important=is_important,
        due_date=due_date,
        parent_task_id=parent_task_id,
        step_order=step_order,
        manual_project=manual_project,
        supabase_primary=supabase_primary,
    )

    if not page:
        return None

    page = update_missing_metadata_if_confident(page, explicit_important=is_important)
    update_quick_win_if_needed(page)
    return page



def create_breakdown_tasks(task_title, is_jdi=False, is_urgent=False, is_important=False, due_date=None, manual_project=""):
    """Create a parent task and linked child tasks for a breakdown item."""
    task_pages_created = []

    print("Breaking down:", task_title)

    try:
        subtasks = generate_subtasks(task_title, client)
        subtasks = clean_subtasks(subtasks)
        subtasks = [
            restore_preferred_proper_nouns(s)
            for s in subtasks
        ]
        subtasks = subtasks[:MAX_SUBTASKS]

        if not subtasks:
            print(
                "→ No useful subtasks returned; "
                "creating original task"
            )

            page = create_and_update_task(
                task_title,
                is_jdi=is_jdi,
                is_urgent=is_urgent,
                is_important=is_important,
                due_date=due_date,
                manual_project=manual_project,
                supabase_primary=True,
            )

            return [page] if page else []

        print("\n--- BREAKDOWN ---")
        print("Parent:", task_title)

        for subtask_title in subtasks:
            print(" -", subtask_title)

        if (
            AIOS_DATASTORE == "supabase"
            and not DRY_RUN
        ):
            def post_create(
                page,
                explicit_important,
            ):
                page = update_missing_metadata_if_confident(
                    page,
                    explicit_important=explicit_important,
                )
                update_quick_win_if_needed(
                    page
                )
                return page

            task_pages_created = (
                create_supabase_primary_hierarchy(
                    parent_title=task_title,
                    subtasks=subtasks,
                    is_jdi=is_jdi,
                    is_urgent=is_urgent,
                    is_important=is_important,
                    due_date=due_date,
                    manual_project=manual_project,
                    notion_create_fn=_create_notion_task_only,
                    post_create_fn=post_create,
                    notion_rollback_fn=update_notion_page,
                )
            )

            if task_pages_created:
                increment_summary(
                    "breakdown_parents_created"
                )

                for _ in task_pages_created[1:]:
                    increment_summary(
                        "breakdown_subtasks_created"
                    )

            return task_pages_created

        parent_page = create_and_update_task(
            task_title,
            is_jdi=is_jdi,
            is_urgent=is_urgent,
            is_important=is_important,
            due_date=due_date,
            manual_project=manual_project,
        )

        if not parent_page:
            print(
                "→ Parent task was not created; "
                "skipping linked subtasks"
            )
            return []

        increment_summary(
            "breakdown_parents_created"
        )
        task_pages_created.append(
            parent_page
        )

        parent_task_id = (
            parent_page["id"]
        )

        for step_order, subtask_title in enumerate(
            subtasks,
            start=1,
        ):
            page = create_and_update_task(
                subtask_title,
                is_jdi=is_jdi,
                is_urgent=is_urgent,
                due_date=due_date,
                parent_task_id=parent_task_id,
                step_order=step_order,
                manual_project=manual_project,
            )

            if page:
                task_pages_created.append(
                    page
                )

    except Exception as e:
        print(
            "ERROR breaking down task:",
            task_title,
        )
        print(e)

        page = create_and_update_task(
            task_title,
            is_jdi=is_jdi,
            is_urgent=is_urgent,
            is_important=is_important,
            due_date=due_date,
            manual_project=manual_project,
            supabase_primary=(
                AIOS_DATASTORE == "supabase"
            ),
        )

        if page:
            task_pages_created.append(
                page
            )

    return task_pages_created

def maybe_add_clarification_blocks(first_page, task_title, original_title, item):
    """Attach clarification choices to a newly created clarify task.

    Safety guard:
    Clear setup/process/creative tasks should never receive clarification blocks.
    They should become breakdown parents with linked subtasks instead.
    """
    if DRY_RUN:
        return

    if not first_page or not task_title.lower().startswith("clarify next action:"):
        return

    # Hard guard against accidental clarify blocks for clear atomic/process/creative work.
    if is_atomic_action(original_title) or is_process_task(original_title) or is_immediately_actionable_operational_task(original_title):
        print("Skipping clarification block for clear atomic/process/creative task:", original_title)
        return

    suggestions = generate_clarification_suggestions(original_title)

    render_result = append_clarification_blocks(
        page_id=first_page["id"],
        original_task=original_title,
        suggestions=suggestions,
    )

    if (
        render_result is not None
        and AIOS_DATASTORE == "supabase"
        and clarification_shadow_inbox_repo is not None
        and clarification_shadow_review_repo is not None
    ):
        try:
            mode, reason = clarification_mode_reason(original_title)
            review, created = shadow_clarification_review(
                inbox_repo=clarification_shadow_inbox_repo,
                review_repo=clarification_shadow_review_repo,
                item=item,
                first_page=first_page,
                task_title=task_title,
                original_title=original_title,
                suggestions=suggestions,
                clarification_mode=mode,
                clarification_reason=reason,
            )

            if created:
                print(
                    "[Clarification Shadow] Created Supabase review:",
                    original_title,
                )
            else:
                print(
                    "[Clarification Shadow] Existing open review reused:",
                    original_title,
                )
        except Exception as exc:
            print(
                "[Clarification Shadow] Write failed:",
                exc,
            )

def process_task_item(item):
    """Create Notion task page(s) for one inbox item.

    Classification order matters:
    1. If the original task is a clear process/creative task, force breakdown.
    2. Otherwise allow true vague tasks to clarify.

    This prevents clear creative work such as
    "Design new label for 50% Whole Wheat Sourdough Tin Loaf"
    from being routed into clarification.
    """
    parsed, task_title, due_date = prepare_task_title(item)

    original_title = strip_due_date_phrases(parsed["clean_title"])
    original_title = restore_preferred_proper_nouns(original_title)

    decision = decide_task_action(
        original_title=original_title,
        prepared_title=task_title,
        allow_ai=True,
    )

    if decision in ["keep", "breakdown"] and task_title.lower().startswith("clarify next action:"):
        print(f"→ Task decision override: {decision}; using original title")
        task_title = original_title

    is_jdi = parsed["jdi"]
    is_urgent = parsed["urgent"]
    is_important = parsed.get("important", False)
    manual_project = parsed.get("manual_project", "")

    if manual_project:
        print(f"Manual project hint: {original_title} → {manual_project}")

    if decision == "breakdown":
        task_pages_created = create_breakdown_tasks(
            task_title,
            is_jdi=is_jdi,
            is_urgent=is_urgent,
            is_important=is_important,
            due_date=due_date,
            manual_project=manual_project,
        )
    elif decision == "clarify":
        if not task_title.lower().startswith("clarify next action:"):
            task_title = f"Clarify next action: {original_title}"

        page = create_and_update_task(
            task_title,
            is_jdi=is_jdi,
            is_urgent=is_urgent,
            is_important=is_important,
            due_date=due_date,
            manual_project=manual_project,
            supabase_primary=True,
        )
        task_pages_created = [page] if page else []
    else:
        task_title = original_title if task_title.lower().startswith("clarify next action:") else task_title
        page = create_and_update_task(
            task_title,
            is_jdi=is_jdi,
            is_urgent=is_urgent,
            is_important=is_important,
            due_date=due_date,
            manual_project=manual_project,
            supabase_primary=True,
        )
        task_pages_created = [page] if page else []

    if task_pages_created:
        append_notes_to_created_task_pages(task_pages_created, item.get("notes"))

        if decision == "breakdown":
            action = "Broken Down"
        elif decision == "clarify":
            action = "Clarified"
        else:
            action = "Created"

        log_ai_processing_decision(
            original=item["text"],
            final_task=task_title,
            action=action,
            reason=task_decision_log_reason(original_title, task_title, decision),
            review_needed=task_decision_review_needed(original_title, task_title, decision),
            confidence=None,
        )

        maybe_add_clarification_blocks(
            first_page=task_pages_created[0],
            task_title=task_title,
            original_title=original_title,
            item=item,
        )

    return task_pages_created

def archive_created_item(item, created_pages, archive_section_id):
    """Archive and remove the original inbox block after task creation."""
    if not created_pages:
        return

    if DRY_RUN:
        print(f"[DRY RUN] Would archive/delete original item: {item['text']}")
        return

    if not ARCHIVE_PROCESSED_ITEMS:
        print(f"[NO ARCHIVE] Leaving original item in place: {item['text']}")
        return

    if not archive_section_id:
        return

    first_task_url = created_pages[0].get("url")
    archive_item(item, archive_section_id, first_task_url)
    inbox_source.remove_item(item)

def archive_reviewed_items(items, archive_section_id):
    """Archive and remove processed inbox items that did not create new tasks."""
    if not items:
        return

    if DRY_RUN:
        for item in items:
            print(f"[DRY RUN] Would archive/delete reviewed item: {item['text']}")
        return

    if not ARCHIVE_PROCESSED_ITEMS:
        for item in items:
            print(f"[NO ARCHIVE] Leaving reviewed item in place: {item['text']}")
        return

    if not archive_section_id:
        return

    for item in items:
        archive_item(item, archive_section_id)
        inbox_source.remove_item(item)

def limit_items_for_controlled_production(items):
    """Limit how many new inbox items are processed during early production testing."""
    if DRY_RUN or MAX_ITEMS_PER_RUN is None:
        return items

    limited_items = items[:MAX_ITEMS_PER_RUN]
    skipped_count = len(items) - len(limited_items)

    print(f"Controlled production limit: processing {len(limited_items)} of {len(items)} new item(s)")

    if skipped_count > 0:
        increment_summary("items_left_for_later", skipped_count)
        print(f"Leaving {skipped_count} new item(s) in the Brain Dump for a later run")

    return limited_items

def run_task_creation_pipeline():
    """Create tasks, handle reviewed duplicates, then archive processed inbox blocks."""
    if TEST_MODE:
        print("TEST_MODE is enabled → skipping live task creation pipeline / Notion writes.")
        return None

    reviewed_possible_items, possible_items_to_create_anyway = review_possible_duplicate_items(possible_matches)

    candidate_tasks_to_create = tasks_to_create + possible_items_to_create_anyway
    final_tasks_to_create = limit_items_for_controlled_production(candidate_tasks_to_create)
    RUN_SUMMARY["items_processed"] = len(final_tasks_to_create)

    # Only archive items that are actually handled in this run. Items skipped by
    # MAX_ITEMS_PER_RUN stay in the Brain Dump for the next run.
    items_to_archive = (
        final_tasks_to_create
        + updated_matched_items
        + duplicate_inbox_items
        + reviewed_possible_items
        + non_task_note_items
        + non_task_idea_items
    )

    should_archive = (not DRY_RUN) and ARCHIVE_PROCESSED_ITEMS
    archive_section_id = create_archive_section() if should_archive and items_to_archive else None

    print("\n--- RUN MODE ---")
    print("DRY_RUN:", DRY_RUN)
    print("MAX_ITEMS_PER_RUN:", MAX_ITEMS_PER_RUN)
    print("ARCHIVE_PROCESSED_ITEMS:", ARCHIVE_PROCESSED_ITEMS)

    # 1) Create new tasks, with optional breakdown, then archive/delete them.
    for item in final_tasks_to_create:
        print(f"\nPROCESSING: {item['text']}")
        created_pages = process_task_item(item)
        archive_created_item(item, created_pages, archive_section_id)

    # 2) Archive/delete inbox items that were handled without creating new tasks.
    archive_reviewed_items(updated_matched_items, archive_section_id)
    archive_reviewed_items(duplicate_inbox_items, archive_section_id)
    archive_reviewed_items(reviewed_possible_items, archive_section_id)

    for item in non_task_note_items:
        archive_non_task_note_item(item, archive_section_id)

    for item in non_task_idea_items:
        archive_non_task_idea_item(item, archive_section_id)

    if DRY_RUN:
        print(f"[DRY RUN] Would create {len(created_tasks)} task(s)")
        print(f"[DRY RUN] Would archive {len(items_to_archive)} processed item(s)")
    else:
        print(f"Created {len(created_tasks)} task(s)")
        if ARCHIVE_PROCESSED_ITEMS:
            print(f"Archived {len(items_to_archive)} processed item(s)")
        else:
            print(f"Left {len(items_to_archive)} processed item(s) in place because ARCHIVE_PROCESSED_ITEMS=False")

    return archive_section_id

if RUN_TASK_CREATION_PIPELINE:
    archive_section_id = run_task_creation_pipeline()
else:
    archive_section_id = None
    print("Task creation pipeline disabled → no Brain Dump items processed.")


# ## 13.1 Best Next Action updater

# In[72]:


def query_tasks_database(filter_payload=None, sorts=None, page_size=100):
    """Query the Tasks database with shared pagination helper."""

    url = f"https://api.notion.com/v1/databases/{TASKS_DATABASE_ID}/query"

    payload = {"page_size": page_size}

    if filter_payload:
        payload["filter"] = filter_payload

    if sorts:
        payload["sorts"] = sorts

    print("[query_tasks_database] Using shared pagination helper")

    results = notion_paginated_query(
        url=url,
        headers=headers,
        payload=payload,
    )

    print(f"[query_tasks_database] Retrieved {len(results)} total tasks")

    return results


# Preserve the Notion implementation as an explicit fallback while routing
# migrated runtime/project-cognition task reads to Supabase.
_notion_query_tasks_database = query_tasks_database


def query_tasks_database_datastore(
    filter_payload=None,
    sorts=None,
    page_size=100,
):
    if AIOS_DATASTORE == "supabase":
        return query_supabase_tasks_legacy(
            filter_payload=filter_payload,
            sorts=sorts,
            page_size=page_size,
        )

    return _notion_query_tasks_database(
        filter_payload=filter_payload,
        sorts=sorts,
        page_size=page_size,
    )


query_tasks_database = (
    query_tasks_database_datastore
)


# Legacy execution-state mutation helpers removed in cleanup Phase 1.
# Execution state now remains in execution_engine_v2.py; Do = Today is manual-only.

# ## 13.2 Project candidate detector

from aios import projects as project_helpers

project_helpers.configure_project_module(globals())


def update_project_lifecycle_datastore(
    project_ref_id,
    *,
    status=None,
    is_active=None,
):
    """
    Datastore-aware project lifecycle persistence seam.

    Supabase mode writes status/is_active directly to Supabase.

    The current AIOS project detector does not automatically activate or
    deactivate projects; those transitions are review/UI actions. This helper
    provides the canonical Supabase mutation target for those actions without
    changing project cognition.
    """
    if AIOS_DATASTORE != "supabase":
        raise RuntimeError(
            "Project lifecycle datastore helper is "
            "currently intended for Supabase mode."
        )

    return (
        get_project_lifecycle_writer()
        .update(
            project_ref_id=project_ref_id,
            status=status,
            is_active=is_active,
        )
    )


# Make the lifecycle mutation seam available to aios.projects / future UI
# integration without changing detector behavior.
project_helpers.update_project_lifecycle_datastore = (
    update_project_lifecycle_datastore
)



# Datastore-aware project read seam. aios.projects continues to own all
# matching / activation / emergence semantics; only its project population
# source changes when Supabase is selected.
_notion_query_projects_database = (
    project_helpers.query_projects_database
)


def query_projects_database_datastore(
    page_size=100,
):
    if AIOS_DATASTORE == "supabase":
        return get_supabase_projects()

    return _notion_query_projects_database(
        page_size=page_size
    )


project_helpers.query_projects_database = (
    query_projects_database_datastore
)


# Preserve the original Notion project-stub creator for Notion mode and
# dry-run/test behavior only.
_original_create_inactive_project_stub_if_missing = (
    project_helpers.create_inactive_project_stub_if_missing
)


def create_inactive_project_stub_datastore(
    project_name,
    existing_projects=None,
    source_reason="",
):
    """
    Datastore-aware project-stub creation.

    notion:
      existing Notion behavior

    supabase:
      create directly in Supabase; no Notion project mirror
    """

    if AIOS_DATASTORE != "supabase":
        return (
            _original_create_inactive_project_stub_if_missing(
                project_name,
                existing_projects,
                source_reason,
            )
        )

    project_name = str(
        project_name or ""
    ).strip()

    if not project_name:
        return None

    # Keep test/dry-run semantics exactly where they were.
    if (
        TEST_MODE
        or DRY_RUN
        or not project_helpers.RUN_PROJECT_STUB_CREATION
    ):
        return (
            _original_create_inactive_project_stub_if_missing(
                project_name,
                existing_projects,
                source_reason,
            )
        )

    existing_projects = (
        existing_projects or []
    )

    existing = (
        project_helpers.find_project_by_name(
            project_name,
            existing_projects,
        )
    )

    if existing:
        return existing

    project = create_supabase_project(
        project_name=project_name,
        status_value=(
            project_helpers.PROJECT_STUB_STATUS_VALUE
        ),
        source_reason=source_reason,
    )

    # A relation writer may already be instantiated in this process.
    # Refresh its project identity cache so the brand-new native UUID can be
    # resolved immediately if the detector links a task during this run.
    try:
        get_project_relation_writer().refresh_projects()
    except Exception:
        pass

    increment_summary(
        "project_records_created"
    )

    print(
        "[Project Creation] "
        "Supabase-only project stub created"
    )

    return project


project_helpers.create_inactive_project_stub_if_missing = (
    create_inactive_project_stub_datastore
)




def set_project_relation_if_safe_datastore(
    task,
    project,
    suggested_project,
    match_score,
    source_reason="",
):
    """
    Preserve the existing project-detector guardrails while making the actual
    task -> project relation Supabase-primary when AIOS_DATASTORE=supabase.
    """
    if (
        TEST_MODE
        or DRY_RUN
        or not RUN_PROJECT_RELATION_WRITEBACK
    ):
        return False

    if (
        not task
        or task.get("dry_run")
        or not project
    ):
        return False

    title = get_title(task)

    if (
        not title
        or title.lower().startswith(
            "clarify next action:"
        )
    ):
        return False

    if project_helpers.task_has_project_relation(
        task
    ):
        increment_summary(
            "project_relation_skipped"
        )
        print(
            f"Project relation preserved: "
            f"{title} already has a project relation"
        )
        return False

    try:
        if AIOS_DATASTORE == "supabase":
            writer = get_project_relation_writer()

            writer.write_supabase(
                notion_task_id=task["id"],
                notion_project_id=project["id"],
            )

            # Keep the local legacy-shaped task coherent for this run.
            task.setdefault(
                "properties",
                {},
            )[TASK_PROJECT_RELATION_PROPERTY] = {
                "type": "relation",
                "relation": [
                    {"id": project["id"]}
                ],
            }

            print(
                "[Project Relation Write] "
                "Supabase-only project relation write"
            )

        else:
            update_notion_page(
                task["id"],
                {
                    TASK_PROJECT_RELATION_PROPERTY: {
                        "relation": [
                            {"id": project["id"]}
                        ]
                    }
                },
            )

        increment_summary(
            "project_relation_updates"
        )

        project_name = get_title(
            project
        )

        print(
            f"Set Project relation: "
            f"{title} → {project_name}"
        )

        log_ai_processing_decision(
            original=title,
            final_task=title,
            action="Project Linked",
            reason=(
                f"Linked to existing active project "
                f"'{project_name}' from Suggested Project "
                f"'{suggested_project}'. {source_reason}"
            ),
            review_needed=False,
            confidence=match_score,
            source="Project Detector",
            suggested_project=suggested_project,
        )

        return True

    except Exception as exc:
        increment_summary(
            "errors"
        )

        print(
            "ERROR setting Project relation:",
            title,
        )
        print(exc)

        return False


# Replace only the write-back mutation seam. Candidate discovery, matching,
# project activation rules and project-stub behavior remain in aios.projects.
project_helpers.set_project_relation_if_safe = (
    set_project_relation_if_safe_datastore
)


# -------------------------------------------------------------------------
# Datastore-aware Project task-state writes
# -------------------------------------------------------------------------
# Suggested Project is durable task metadata, and review-project membership is
# a real task -> project relation. In Supabase mode these writes must therefore
# be authoritative in Supabase rather than split across Notion and Supabase.
#
# Notion mode remains unchanged. Brain Dump / clarification / dashboard block
# presentation remains intentionally Notion-backed elsewhere.

_original_update_suggested_project_if_needed = (
    project_helpers.update_suggested_project_if_needed
)

_original_set_suggested_project_canonical = (
    project_helpers.set_suggested_project_canonical
)

_original_set_review_project_relation_if_empty = (
    project_helpers.set_review_project_relation_if_empty
)


def _sync_runtime_task_from_updated_copy(
    task,
    updated_task,
):
    """Mutate the current legacy-shaped task so later passes see the write."""

    if (
        not isinstance(task, dict)
        or not isinstance(updated_task, dict)
    ):
        return

    if "properties" in updated_task:
        task["properties"] = updated_task["properties"]

    for key in (
        "_source",
        "_supabase_id",
    ):
        if key in updated_task:
            task[key] = updated_task[key]


def update_suggested_project_if_needed_datastore(
    task,
    suggested_project,
    source="Project Detector",
):
    """
    Datastore-aware Suggested Project staging write.

    Supabase mode preserves the original guardrail:
    write only when Suggested Project is currently blank.
    """

    if AIOS_DATASTORE != "supabase":
        return (
            _original_update_suggested_project_if_needed(
                task,
                suggested_project,
                source,
            )
        )

    suggested_project = str(
        suggested_project or ""
    ).strip()

    if (
        not task
        or task.get("dry_run")
        or not suggested_project
    ):
        return False

    props = task.get(
        "properties",
        {},
    )

    current_value = (
        project_helpers.get_rich_text_plain_value(
            props,
            SUGGESTED_PROJECT_PROPERTY,
        )
    )

    title = get_title(task)

    if current_value:
        if current_value != suggested_project:
            print(
                f"Suggested Project preserved: "
                f"{title} already has "
                f"{current_value!r}; candidate was "
                f"{suggested_project!r}"
            )

        return False

    if TEST_MODE or DRY_RUN:
        print(
            f"[DRY RUN] Would set Suggested Project: "
            f"{title} → {suggested_project}"
        )
        return False

    try:
        updated_task = update_task_metadata(
            task,
            {
                SUGGESTED_PROJECT_PROPERTY:
                    _notion_rich_text(
                        suggested_project
                    )
            },
            datastore=AIOS_DATASTORE,
            notion_update_fn=update_notion_page,
        )

        _sync_runtime_task_from_updated_copy(
            task,
            updated_task,
        )

        increment_summary(
            "suggested_project_updates"
        )

        print(
            "[Suggested Project Write] "
            "Supabase-only staging write"
        )

        print(
            f"Set Suggested Project: "
            f"{title} → {suggested_project}"
        )

        return True

    except Exception as exc:
        increment_summary(
            "errors"
        )

        print(
            "ERROR setting Suggested Project:",
            title,
        )

        print(exc)

        return False


def set_suggested_project_canonical_datastore(
    task,
    project_name,
):
    """
    Synchronize Suggested Project to the authoritative related Project name.

    Supabase mode replaces stale staging text directly in Supabase and keeps the
    current legacy-shaped task coherent for later passes in the same run.
    """

    if AIOS_DATASTORE != "supabase":
        return (
            _original_set_suggested_project_canonical(
                task,
                project_name,
            )
        )

    project_name = str(
        project_name or ""
    ).strip()

    if (
        not task
        or not project_name
        or task.get("dry_run")
    ):
        return False

    props = (
        task.get(
            "properties",
            {},
        )
        or {}
    )

    current = (
        project_helpers.get_rich_text_plain_value(
            props,
            SUGGESTED_PROJECT_PROPERTY,
        )
    )

    if current == project_name:
        return False

    if TEST_MODE or DRY_RUN:
        print(
            f"[DRY RUN] Would sync Suggested Project: "
            f"{get_title(task)} → {project_name}"
        )
        return False

    try:
        updated_task = update_task_metadata(
            task,
            {
                SUGGESTED_PROJECT_PROPERTY:
                    _notion_rich_text(
                        project_name
                    )
            },
            datastore=AIOS_DATASTORE,
            notion_update_fn=update_notion_page,
        )

        _sync_runtime_task_from_updated_copy(
            task,
            updated_task,
        )

        increment_summary(
            "suggested_project_updates"
        )

        print(
            "[Suggested Project Write] "
            "Supabase-only canonical sync"
        )

        print(
            "Synced Suggested Project to canonical relation: "
            f"{get_title(task)} → {project_name}"
        )

        return True

    except Exception as exc:
        increment_summary(
            "errors"
        )

        print(
            "ERROR syncing Suggested Project:",
            get_title(task),
        )

        print(exc)

        return False


def set_review_project_relation_if_empty_datastore(
    task,
    project,
    suggested_project,
):
    """
    Link a task to an inactive review project.

    In Supabase mode, review membership is the same canonical structural
    relation as active-project membership; only project lifecycle/status
    distinguishes review from active.
    """

    if AIOS_DATASTORE != "supabase":
        return (
            _original_set_review_project_relation_if_empty(
                task,
                project,
                suggested_project,
            )
        )

    if not getattr(
        project_helpers,
        "PROJECT_REVIEW_LINK_STUBS",
        True,
    ):
        return False

    if (
        not task
        or not project
        or task.get("dry_run")
    ):
        return False

    if project_helpers.is_active_project(
        project
    ):
        return False

    if project_helpers.task_has_project_relation(
        task
    ):
        return False

    if TEST_MODE or DRY_RUN:
        return False

    title = get_title(task)

    try:
        writer = get_project_relation_writer()

        writer.write_supabase(
            notion_task_id=task["id"],
            notion_project_id=project["id"],
        )

        # Keep the current legacy-shaped task coherent for this run.
        task.setdefault(
            "properties",
            {},
        )[TASK_PROJECT_RELATION_PROPERTY] = {
            "type": "relation",
            "relation": [
                {
                    "id":
                        project["id"]
                }
            ],
        }

        increment_summary(
            "project_relation_updates"
        )

        print(
            "[Project Relation Write] "
            "Supabase-only REVIEW project relation"
        )

        print(
            f"Set REVIEW Project relation: "
            f"{title} → {get_title(project)} "
            "(inactive; manual review required)"
        )

        return True

    except Exception as exc:
        increment_summary(
            "errors"
        )

        print(
            "ERROR setting review Project relation:",
            title,
        )

        print(exc)

        return False


project_helpers.update_suggested_project_if_needed = (
    update_suggested_project_if_needed_datastore
)

project_helpers.set_suggested_project_canonical = (
    set_suggested_project_canonical_datastore
)

project_helpers.set_review_project_relation_if_empty = (
    set_review_project_relation_if_empty_datastore
)


# Keep the historical function name available to the orchestration section.
run_project_candidate_detector = project_helpers.run_project_candidate_detector

def run_project_candidate_detector_safely():
    """Run optional project candidate detection without crashing task ingestion.

    Project candidate detection is a maintenance/review pass. A transient Notion
    timeout here should not undo or obscure successful inbox processing.
    """
    try:
        return run_project_candidate_detector()
    except requests.exceptions.ReadTimeout as e:
        print(f"Project candidate detector skipped due to Notion timeout: {e}")
        return None
    except requests.exceptions.Timeout as e:
        print(f"Project candidate detector skipped due to Notion timeout: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Project candidate detector skipped due to Notion API error: {e}")
        return None

def run_project_candidate_detector_safety_tests():
    """Local regression tests for non-fatal project detector failures."""
    global run_project_candidate_detector

    original_detector = run_project_candidate_detector

    def assert_safe_skip(error):
        global run_project_candidate_detector

        def failing_detector():
            raise error

        run_project_candidate_detector = failing_detector
        result = run_project_candidate_detector_safely()
        assert result is None

    try:
        assert_safe_skip(requests.exceptions.ReadTimeout("simulated read timeout"))
        assert_safe_skip(requests.exceptions.ConnectionError("simulated connection error"))

        def successful_detector():
            return "ok"

        run_project_candidate_detector = successful_detector
        assert run_project_candidate_detector_safely() == "ok"
    finally:
        run_project_candidate_detector = original_detector

    print("Project candidate detector safety tests passed")
    return True

if TEST_MODE:
    PROJECT_RELATION_WRITEBACK_TESTS_PASSED = project_helpers.run_project_relation_writeback_tests()
    PROJECT_CANDIDATE_DETECTOR_SAFETY_TESTS_PASSED = run_project_candidate_detector_safety_tests()

# ## 14. Final maintenance
# 

# In[73]:

# Keep read-only execution overlays available during normal task pipeline runs.
# In TEST_MODE, skip all Notion maintenance so tests remain completely local.
if TEST_MODE:
    print("TEST_MODE is enabled → skipping Quick Win maintenance.")
else:
    if RUN_TASK_CREATION_PIPELINE:
        run_project_candidate_detector_safely()

    # New execution engine (authoritative)
    execution_engine_success = False
    try:
        if AIOS_DATASTORE == "supabase":
            print(
                "[Execution Engine] Reading execution population from Supabase"
            )

            all_open_tasks = get_supabase_execution_tasks()

        else:
            print(
                "[Execution Engine] Reading execution population from Notion"
            )
            all_open_tasks = query_tasks_database(
                filter_payload={
                    "and": [
                        {
                            "property": "Done",
                            "checkbox": {
                                "equals": False
                            }
                        }
                    ]
                }
            )

        print(f"[Execution Engine] Full task set for reconciliation: {len(all_open_tasks)}")

        global EXECUTION_ENGINE_WINNERS
        EXECUTION_ENGINE_WINNERS = []

        EXECUTION_ENGINE_WINNERS = rebuild_execution_state(
            open_tasks=all_open_tasks,
            update_fn=execution_state_update_fn,
        )

        execution_engine_success = True

        print(
            f"Execution Engine V2 completed successfully. "
            f"Winners: {len(EXECUTION_ENGINE_WINNERS)}"
        )

        refresh_surfaced_quick_wins(all_open_tasks, EXECUTION_ENGINE_WINNERS)
    except Exception as e:
        print(f"Execution Engine V2 failure: {e}")

    if RUN_TASK_CREATION_PIPELINE:
        if execution_engine_success:
            print("[Execution Flow] Canonical Execution Authority complete; Quick Win view rebalance active; legacy execution-state automation remains disabled")
        else:
            print("[Execution Flow] Canonical Execution Authority failed; legacy execution-state automation remains disabled")

# In[74]:

# Archive trimming is a live Notion maintenance action, so skip it in TEST_MODE.
if TEST_MODE:
    print("TEST_MODE is enabled → skipping archive trimming.")
elif archive_section_id:
    trim_archive_runs(keep=5)


# === AIOS METADATA RECONCILIATION PHASE 2.5 INLINE RUN ===
# Run reconciliation before summary/notification/dashboard so Notion never sees
# a late post-notification clear/rewrite cycle.
if TEST_MODE:
    print("TEST_MODE is enabled → skipping metadata reconciliation inline pass.")
else:
    try:
        from core.metadata.reconciliation import emit_metadata_reconciliation_diagnostics
        print("=== METADATA RECONCILIATION — PHASE 2.5: INLINE PRE-SUMMARY PASS ===")
        emit_metadata_reconciliation_diagnostics(globals())
    except Exception as exc:
        print(f"[Metadata Reconciliation] Inline pass skipped: {exc}")
# === END AIOS METADATA RECONCILIATION PHASE 2.5 INLINE RUN ===

# === AIOS PROJECT COGNITION D2.6 RUNTIME TELEMETRY CLEANUP + GOVERNANCE HARDENING ===
def run_project_cognition_runtime_observation():
    """Emit compact Project Cognition telemetry into normal runtime logs.

    This intentionally delegates to the dedicated project cognition report script so
    the cognition layer remains isolated from execution authority. The integration
    is non-fatal: failures are logged and do not block task processing, dashboard
    generation, metadata reconciliation, or notifications.
    """
    enabled = parse_env_bool("AIOS_PROJECT_COGNITION_RUNTIME_ENABLED", True)
    if TEST_MODE:
        print("TEST_MODE is enabled → skipping Project Cognition runtime observation.")
        return False
    if not enabled:
        print("[Project Cognition Runtime] Disabled by AIOS_PROJECT_COGNITION_RUNTIME_ENABLED=false")
        return False

    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "aios_project_affinity_report.py")
    if not os.path.exists(script_path):
        print(f"[Project Cognition Runtime] Skipped: report script not found at {script_path}")
        return False

    cmd = [sys.executable, script_path, "--runtime-summary"]
    if not parse_env_bool("AIOS_PROJECT_COGNITION_RUNTIME_WRITES", True):
        cmd.append("--no-stability-governed-writes")

    timeout_seconds = int(os.getenv("AIOS_PROJECT_COGNITION_RUNTIME_TIMEOUT", "180"))
    import time
    started_at = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:
        print(f"[Project Cognition Runtime] Observation failed: {exc}")
        return False

    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip())
    elapsed = time.monotonic() - started_at
    print(f"[Project Cognition Runtime] Observation timing: elapsed={elapsed:.1f}s; timeout={timeout_seconds}s; nonfatal=true")
    if result.returncode != 0:
        print(f"[Project Cognition Runtime] Observation exited with status={result.returncode}; core_runtime_unaffected=true")
        return False
    return True

run_project_cognition_runtime_observation()
# === END AIOS PROJECT COGNITION D2.6 RUNTIME TELEMETRY CLEANUP + GOVERNANCE HARDENING ===

print_run_summary()
notify_run_summary()

# ## 13.2 AIOS Executive Dashboard

def get_task_title(task):
    return get_title(task)



def is_breakdown_step(task):
    """Return True when a task is a child/breakdown step.

    Dashboard generation still needs this as a read-only classifier even though
    legacy execution-state automation has been removed.
    """
    return get_parent_task_id(task) is not None


def get_due_date(task):
    """Return the task due date from the canonical Due Date property."""
    props = task.get("properties", {}) or {}

    for property_name in (DUE_DATE_PROPERTY,):
        due_date = parse_notion_date_start(
            get_date_start_value(props, property_name)
        )
        if due_date:
            return due_date

    return None


def is_due_today_or_overdue(task, today=None):
    """Return True when a task's due date is today or in the past."""
    due_date = get_due_date(task)
    if not due_date:
        return False

    today = today or datetime.now().date()
    return due_date <= today


def has_near_due_date(task, today=None, days=7):
    """Return True when a task is due soon but not already due/overdue."""
    due_date = get_due_date(task)
    if not due_date:
        return False

    today = today or datetime.now().date()
    delta_days = (due_date - today).days
    return 0 < delta_days <= days


def is_high_importance(task):
    """Return True when task importance is High Importance."""
    props = task.get("properties", {}) or {}
    return get_select_or_status_name(props, "Importance") == "High Importance"


def is_high_urgency(task):
    """Return True when task urgency is High Urgency."""
    props = task.get("properties", {}) or {}
    return get_select_or_status_name(props, "Urgency") == "High Urgency"


def _task_text(execution_task):
    """Return normalized task text for lightweight pattern inference."""
    title = get_task_title(execution_task) or ""
    props = execution_task.get("properties", {}) or {}
    project = ""
    for key in ("Project", "Suggested Project", "Area", "Context"):
        try:
            project = get_select_name(props, key) or project
        except Exception:
            pass
    return f"{title} {project}".strip().lower()


def is_simple_executable_task(execution_task):
    """Return True when the title is already a clear, single-step action.

    These tasks do not benefit from AI-generated execution guidance. Showing
    extra advice for them tends to create generic or awkward text such as
    "do the smallest complete version...".
    """

    title = (get_task_title(execution_task) or "").strip()
    if not title:
        return False

    lowered = title.lower()

    # Keep technical/change-management work eligible for generated guidance.
    # A broad "check" task is often simple, but AIOS/runtime/code words usually
    # indicate diagnostic work where guidance can still help.
    complex_markers = [
        "aios", "script", "package", "install", "deploy", "debug", "diagnose",
        "investigate", "troubleshoot", "review", "logs", "telemetry",
        "master plan", "release", "migration", "rollback", "smoke test",
        "database", "firestore", "code", "execution ranking", "execution rankings",
        "runtime", "evaluator", "metadata", "governance", "notion",
    ]
    if any(marker in lowered for marker in complex_markers):
        return False

    # Direct household/admin actions generally already contain their own first
    # move. Guidance for these tends to be generic or actively silly.
    simple_starts = (
        "book ", "schedule ", "pay ", "renew ", "call ", "email ",
        "message ", "send ", "submit ", "order ", "buy ", "pick up ",
        "drop off ", "return ", "cancel ", "confirm ", "rsvp ",
        "download ", "upload ", "print ", "scan ", "file ", "check ",
        "look up ", "find ", "reply ", "reply to ", "text ",
    )

    if lowered.startswith(simple_starts):
        return True

    simple_contains = (
        "appointment", "maintenance appointment", "health claim", "health claims",
        "mileage", "audible", "invoice", "receipt", "license", "licence",
        "reservation", "booking",
    )
    if any(marker in lowered for marker in simple_contains) and len(title.split()) <= 12:
        return True

    return False


def determine_execution_strategy(execution_task):
    """Infer a broad work pattern without assuming communications or stakeholders."""

    text = _task_text(execution_task)
    props = execution_task.get("properties", {}) or {}

    effort = get_select_name(props, "Effort")
    duration = get_select_name(props, "Duration")

    if is_breakdown_step(execution_task):
        return "workflow_unblock"

    if is_simple_executable_task(execution_task):
        return "simple_executable"

    if any(word in text for word in ["install", "deploy", "package", "script", "update script", "migration", "release", "version", "smoke test"]):
        return "implementation_change"

    if any(word in text for word in ["diagnose", "debug", "troubleshoot", "inspect", "check", "review", "audit", "investigate", "why", "logs", "telemetry"]):
        return "investigation"

    if any(word in text for word in ["fix", "repair", "replace", "resolve", "correct", "cleanup bug", "bug"]):
        return "repair"

    if any(word in text for word in ["write", "draft", "document", "notes", "release notes", "master plan", "post", "email draft"]):
        return "writing_documentation"

    if any(word in text for word in ["plan", "design", "map out", "outline", "workshop", "schedule", "coordinate"]):
        return "planning"

    if any(word in text for word in ["email", "message", "call", "reply", "send", "contact"]):
        return "communication"

    if any(word in text for word in ["clean", "organize", "sort", "tidy", "archive", "delete", "remove"]):
        return "cleanup"

    if duration in ["5 min", "10 min", "15 min"]:
        return "quick_closure"

    if effort == "Large Effort":
        return "protected_work_block"

    return "single_pass"


def _strip_leading_action(title):
    """Return a compact object phrase from a task title for generated guidance.

    The returned phrase is normalized enough to avoid awkward combinations like
    "current updated script" when guidance prepends words such as "current".
    """
    cleaned = (title or "this task").strip()
    lowered = cleaned.lower()
    for prefix in (
        "install ", "deploy ", "update ", "review ", "check ", "inspect ",
        "diagnose ", "debug ", "troubleshoot ", "fix ", "repair ", "replace ",
        "write ", "draft ", "create ", "prepare ", "plan ", "design ",
        "clean ", "organize ", "delete ", "remove ", "send ", "reply to ",
    ):
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip() or cleaned
            lowered = cleaned.lower()
            break

    for modifier in ("updated ", "new ", "replacement ", "revised "):
        if lowered.startswith(modifier):
            cleaned = cleaned[len(modifier):].strip() or cleaned
            break

    return cleaned


def generate_execution_guidance(strategy, execution_task):
    """Generate task-specific, deterministic execution guidance.

    This intentionally avoids hard-coded guidance for individual tasks. It uses a
    broad task pattern plus the task title to produce a concrete first move and a
    simple completion cue.
    """

    title = get_task_title(execution_task) or "this task"
    target = _strip_leading_action(title)

    first_moves = {
        "simple_executable": "",
        "implementation_change": f"Locate the current {target}, the updated or replacement version, and the install or rollback instructions before changing anything.",
        "investigation": f"Start by reproducing or locating the specific symptom for {target}, then gather the relevant logs, inputs, and code path before making a change.",
        "repair": f"Identify the exact failure point for {target} and confirm the smallest safe fix before editing related pieces.",
        "writing_documentation": f"Open the current source material for {target} and mark the sections that need to change before rewriting anything.",
        "planning": f"List the required decisions for {target} first, then turn those decisions into the next concrete step.",
        "communication": f"Confirm the recipient, purpose, and one desired outcome for {target} before writing or sending anything.",
        "workflow_unblock": f"Find the downstream work currently blocked by {target} and complete the smallest step that clears that blockage.",
        "cleanup": f"Identify the exact set of items included in {target} and separate keep, change, and remove decisions before acting.",
        "quick_closure": f"Do the smallest complete version of {target} now so it can be closed without another pass.",
        "protected_work_block": f"Define the first deliverable for {target} and protect a focused block long enough to produce it.",
        "single_pass": f"Clarify the next physical or digital action for {target}, then complete that step before switching contexts.",
    }

    success_looks_like = {
        "simple_executable": "",
        "implementation_change": "The update is installed, rollback remains available, and a basic verification or smoke test passes.",
        "investigation": "The cause is identified well enough that the next fix is obvious or the task can be converted into a specific follow-up.",
        "repair": "The failing behavior is corrected and the affected path has been checked once after the change.",
        "writing_documentation": "A usable draft or updated document exists and only refinement remains.",
        "planning": "The next concrete action is clear enough to execute without re-planning.",
        "communication": "The message is sent or ready to send, and the expected response or next step is clear.",
        "workflow_unblock": "The blocked downstream work can proceed without waiting on this item.",
        "cleanup": "The target area or list is reduced to only items that still need intentional follow-up.",
        "quick_closure": "The task is fully closed and no reminder or re-entry is needed.",
        "protected_work_block": "A meaningful chunk is completed, not merely opened or skimmed.",
        "single_pass": "The next concrete step is completed and the task is either closed or clearly advanced.",
    }

    risks = {
        "implementation_change": "Skipping verification after the change or updating the wrong version.",
        "investigation": "Changing code before the symptom and code path are confirmed.",
        "repair": "Expanding the fix beyond the smallest safe correction.",
        "writing_documentation": "Rewriting before confirming what actually changed.",
        "planning": "Staying in planning mode after the next executable step is already clear.",
        "communication": "Sending a message before the desired outcome is clear.",
        "workflow_unblock": "Solving more than needed instead of clearing the immediate blocker.",
        "cleanup": "Mixing cleanup with redesign and creating a larger project than intended.",
    }

    suppress_guidance = strategy == "simple_executable"

    guidance = {
        "first_move": first_moves.get(strategy, first_moves["single_pass"]),
        "success_looks_like": success_looks_like.get(strategy, success_looks_like["single_pass"]),
        "risk_to_watch": risks.get(strategy, ""),
        "strategy": strategy,
        "suppress_guidance": suppress_guidance,
    }

    return guidance

def build_execution_dashboard_summary(execution_task):

    if not execution_task:
        return {
            "execution_task": None,
            "reasons": [],
            "guidance": {
                "first_move": "No active Best Next Action selected.",
                "success_looks_like": "",
                "risk_to_watch": "",
                "strategy": "none",
                "suppress_guidance": True,
            }
        }

    reasons = []

    if is_due_today_or_overdue(execution_task):
        reasons.append("Due today or overdue")
    elif has_near_due_date(execution_task):
        reasons.append("Time-sensitive")

    if is_high_importance(execution_task):
        reasons.append("High importance")

    if is_high_urgency(execution_task):
        reasons.append("High urgency")

    if is_breakdown_step(execution_task):
        reasons.append("Blocks downstream workflow")

    strategy = determine_execution_strategy(execution_task)

    guidance = generate_execution_guidance(
        strategy,
        execution_task,
    )

    return {
        "execution_task": execution_task,
        "reasons": reasons,
        "guidance": guidance,
    }

def replace_dashboard_blocks(block_id, dashboard_data):

    children_url = f"https://api.notion.com/v1/blocks/{block_id}/children"

    # Clear existing dashboard blocks first
    existing_response = requests.get(
        children_url,
        headers=headers,
        timeout=30,
    )

    if existing_response.ok:
        existing_children = existing_response.json().get("results", [])

        for child in existing_children:
            child_id = child.get("id")

            if child_id:
                try:
                    requests.delete(
                        f"https://api.notion.com/v1/blocks/{child_id}",
                        headers=headers,
                        timeout=30,
                    )
                except Exception as delete_error:
                    print(f"Dashboard child delete failed: {delete_error}")

    execution_task = dashboard_data["execution_task"]
    reasons = dashboard_data["reasons"]
    guidance = dashboard_data.get("guidance") or {}
    suppress_guidance = bool(guidance.get("suppress_guidance"))
    first_move = guidance.get("first_move") or "Clarify the next concrete action and complete it before switching contexts."
    success_looks_like = guidance.get("success_looks_like") or "The task is clearly advanced or closed."
    risk_to_watch = guidance.get("risk_to_watch") or ""

    payload = {
        "children": [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": "⭐ Best Next Action"}
                    }]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "mention",
                        "mention": {
                            "page": {
                                "id": execution_task["id"]
                            }
                        }
                    }]
                }
            },
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": "Why this surfaced"}
                    }]
                }
            }
        ]
    }

    for reason in reasons:
        payload["children"].append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": reason}
                }]
            }
        })

    if not suppress_guidance:
        payload["children"].extend([
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": "Suggested First Move"}
                    }]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": first_move}
                    }]
                }
            },
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": "Success Looks Like"}
                    }]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": success_looks_like}
                    }]
                }
            },
        ])

    if risk_to_watch and not suppress_guidance:
        payload["children"].extend([
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": "Risk to Watch"}
                    }]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{
                        "type": "text",
                        "text": {"content": risk_to_watch}
                    }]
                }
            },
        ])

    response = requests.patch(
        children_url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    if not response.ok:
        print("ERROR updating AIOS dashboard block")
        print(response.status_code, response.text)
        return False

    return True

def update_aios_dashboard():

    if not AIOS_DASHBOARD_BLOCK_ID:
        print("AIOS dashboard block not configured.")
        return False

    try:
        global EXECUTION_ENGINE_WINNERS

        if not EXECUTION_ENGINE_WINNERS:
            print("No Execution Engine V2 winners available.")
            return False

        execution_task = EXECUTION_ENGINE_WINNERS[0]["task"]

        dashboard_data = build_execution_dashboard_summary(
            execution_task,
        )

        success = replace_dashboard_blocks(
            AIOS_DASHBOARD_BLOCK_ID,
            dashboard_data,
        )

        if success:
            print("AIOS dashboard updated from Execution Engine V2.")
        else:
            print("AIOS dashboard update failed.")

        return success

    except Exception as e:
        print(f"AIOS dashboard generation failed: {e}")
        return False

if not TEST_MODE:
    update_aios_dashboard()

# === AIOS METADATA RECONCILIATION PHASE 2.5 BOOTSTRAP ===
# Reconciliation no longer runs via atexit.
# It is invoked inline before run summary / notification / dashboard update.
print("[Metadata Reconciliation] Inline reconciliation active; atexit hook disabled")
# === END AIOS METADATA RECONCILIATION PHASE 2.5 BOOTSTRAP ===
