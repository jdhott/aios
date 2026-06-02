#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()
TARGET = ROOT / "execution_engine_v2.py"
VERSION = "Metadata Provenance Audit D1.3"
BACKUP_PREFIX = ".metadata_provenance_audit_d1_3_backup_"

if not TARGET.exists():
    raise SystemExit("execution_engine_v2.py not found. Run this installer from ~/LocalProjects/aios")

source = TARGET.read_text()
if "BNA Metadata Provenance Audit D1.3" in source:
    print("Metadata Provenance Audit D1.3 already installed")
    raise SystemExit(0)

backup_dir = ROOT / f"{BACKUP_PREFIX}{datetime.now().strftime('%Y%m%d_%H%M%S')}"
backup_dir.mkdir(exist_ok=False)
shutil.copy2(TARGET, backup_dir / TARGET.name)

# Add imports for log querying/parsing.
source = source.replace(
    "import os\nfrom dataclasses import dataclass, field\n",
    "import os\nimport re\n\ntry:\n    import requests\nexcept Exception:  # pragma: no cover - runtime dependency guard\n    requests = None\n\nfrom dataclasses import dataclass, field\n",
)

helpers = r'''

# ============================================================
# BNA METADATA PROVENANCE AUDIT — D1.3
# ============================================================

def _plain_text_property(prop):
    """Extract readable text from a common Notion property payload."""
    if not isinstance(prop, dict):
        return ""

    if prop.get("type") == "title":
        parts = prop.get("title") or []
        return "".join(part.get("plain_text") or part.get("text", {}).get("content", "") for part in parts)

    if prop.get("type") == "rich_text":
        parts = prop.get("rich_text") or []
        return "".join(part.get("plain_text") or part.get("text", {}).get("content", "") for part in parts)

    if "title" in prop:
        return "".join(part.get("plain_text") or part.get("text", {}).get("content", "") for part in prop.get("title") or [])

    if "rich_text" in prop:
        return "".join(part.get("plain_text") or part.get("text", {}).get("content", "") for part in prop.get("rich_text") or [])

    return ""


def _select_property_name(prop):
    if not isinstance(prop, dict):
        return ""
    select = prop.get("select") or {}
    if isinstance(select, dict):
        return select.get("name") or ""
    return ""


def _number_property_value(prop):
    if not isinstance(prop, dict):
        return None
    return prop.get("number")


def _metadata_log_headers():
    token = os.getenv("NOTION_TOKEN", "").strip()
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _query_ai_processing_log_for_title(title, page_size=8):
    """Return recent AI Processing Log entries that mention this task title.

    This is read-only observation. Failures are intentionally nonfatal because
    execution ranking and persistence must not depend on AI log availability.
    """
    if requests is None:
        return []

    database_id = os.getenv("NOTION_AI_LOG_DATABASE_ID", "").strip()
    headers = _metadata_log_headers()
    if not database_id or not headers or not title:
        return []

    title = str(title).strip()
    if not title:
        return []

    payload = {
        "page_size": page_size,
        "filter": {
            "or": [
                {"property": "Name", "title": {"contains": title}},
                {"property": "Original", "rich_text": {"contains": title}},
                {"property": "Final Task", "rich_text": {"contains": title}},
            ]
        },
        "sorts": [
            {"property": "Run Time", "direction": "descending"}
        ],
    }

    try:
        response = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=headers,
            json=payload,
            timeout=20,
        )
        if not response.ok:
            print(f"[BNA Provenance] AI log query skipped: {response.status_code}")
            return []
        return response.json().get("results") or []
    except Exception as e:
        print(f"[BNA Provenance] AI log query failed nonfatally: {e}")
        return []


def _parse_importance_from_reason(reason):
    """Parse Importance provenance from AI Processing Log reason text."""
    if not reason:
        return None

    match = re.search(r"-\s*Importance:\s*([^\n(]+)(?:\s*\(([^)]*)\))?", reason)
    if not match:
        return None

    value = match.group(1).strip()
    metadata = match.group(2) or ""
    source = ""
    confidence = None

    source_match = re.search(r"source=([^,\s)]+)", metadata)
    if source_match:
        source = source_match.group(1).strip()

    confidence_match = re.search(r"confidence=([0-9.]+)", metadata)
    if confidence_match:
        try:
            confidence = float(confidence_match.group(1))
        except Exception:
            confidence = confidence_match.group(1)

    return {
        "value": value,
        "source": source or "ai_log_metadata",
        "confidence": confidence,
        "provenance": "ai_log_metadata",
    }


def _created_original_has_marker(entries, markers):
    """Return original text from a Created row containing any marker."""
    markers = tuple(marker.lower() for marker in markers)
    for entry in entries:
        props = entry.get("properties", {}) if isinstance(entry, dict) else {}
        action = _select_property_name(props.get("Action", {})).lower()
        if action and action != "created":
            continue
        original = _plain_text_property(props.get("Original", {}))
        lower = original.lower()
        if any(marker in lower for marker in markers):
            return original
    return ""


def _extract_bna_metadata_provenance(item, entries):
    """Build compact provenance for Priority/Importance and Urgency."""
    task = item.get("task") or {}
    props = task.get("properties", {}) if isinstance(task, dict) else {}

    current_priority = safe_nested_get(props, "Priority", "select", "name") or ""
    current_urgency = safe_nested_get(props, "Urgency", "select", "name") or ""

    provenance = {
        "priority": {
            "current": current_priority or "unset",
            "provenance": "manual_or_unknown",
        },
        "urgency": {
            "current": current_urgency or "unset",
            "provenance": "manual_or_unknown",
        },
    }

    # Importance is the historical/log label that currently feeds Priority scoring.
    for entry in entries:
        props = entry.get("properties", {}) if isinstance(entry, dict) else {}
        reason = _plain_text_property(props.get("Reason", {}))
        parsed = _parse_importance_from_reason(reason)
        if parsed:
            provenance["priority"].update(parsed)
            break

    important_original = _created_original_has_marker(entries, ["important", "high importance"])
    if important_original and provenance["priority"].get("provenance") == "manual_or_unknown":
        provenance["priority"].update({
            "provenance": "explicit_marker_from_original",
            "source": "explicit_marker",
            "confidence": 1.0,
            "origin": important_original,
        })

    urgent_original = _created_original_has_marker(entries, ["urgent", "asap", "high urgency"])
    if urgent_original:
        provenance["urgency"].update({
            "provenance": "explicit_marker_from_original",
            "source": "explicit_marker",
            "confidence": 1.0,
            "origin": urgent_original,
        })

    return provenance


def _format_provenance_line(label, info):
    current = info.get("current") or "unset"
    provenance = info.get("provenance") or "manual_or_unknown"
    source = info.get("source")
    confidence = info.get("confidence")

    parts = [f"current={current}", f"provenance={provenance}"]
    if source:
        parts.append(f"source={source}")
    if confidence is not None:
        if isinstance(confidence, (int, float)):
            parts.append(f"confidence={confidence:.2f}")
        else:
            parts.append(f"confidence={confidence}")

    return f"  {label}: " + "; ".join(parts)


def emit_bna_metadata_provenance_audit(winners):
    """Emit read-only provenance telemetry for BNA metadata inputs.

    D1.3 uses the existing AI Processing Log as an event-source trail. It does
    not create/update Notion pages, change evaluator scores, or mutate task
    metadata. If log lookup is unavailable, it reports manual_or_unknown.
    """
    try:
        winners = winners or []
        print("\\n--- BNA Metadata Provenance Audit D1.3 ---")

        if not winners:
            print("[BNA Provenance] winners=0")
            print("[BNA Provenance] authority_impact=none; mutations=0; mode=read_only_observation")
            return

        for idx, item in enumerate(winners, start=1):
            title = item.get("title") or extract_title(item.get("task") or {})
            entries = _query_ai_processing_log_for_title(title)
            provenance = _extract_bna_metadata_provenance(item, entries)

            print(f"BNA provenance rank={idx} title={title}")
            print(_format_provenance_line("Priority/Importance", provenance["priority"]))
            print(_format_provenance_line("Urgency", provenance["urgency"]))
            print(f"  ai_log_matches={len(entries)}")

        print("[BNA Provenance] authority_impact=none; mutations=0; mode=read_only_observation")

    except Exception as e:
        print(f"[BNA Provenance] audit failed nonfatally: {e}")
'''

anchor = "\ndef evaluate_execution_scoring(task):\n"
if anchor not in source:
    raise SystemExit("Could not find evaluate_execution_scoring anchor")
source = source.replace(anchor, helpers + anchor, 1)

source = source.replace(
    'print("\\n--- Evaluator Tuning Telemetry D1.2.1.1 ---")',
    'print("\\n--- Evaluator Tuning Telemetry D1.3 ---")',
    1,
)

anchor_call = '''        print(
            "  components: "
            f"{format_bna_component_breakdown(item)}"
        )

    updated = 0
'''
replacement = '''        print(
            "  components: "
            f"{format_bna_component_breakdown(item)}"
        )

    emit_bna_metadata_provenance_audit(winners)

    updated = 0
'''
if anchor_call not in source:
    raise SystemExit("Could not find Best Next Actions insertion anchor")
source = source.replace(anchor_call, replacement, 1)

TARGET.write_text(source)

try:
    subprocess.run([sys.executable, "-m", "py_compile", str(TARGET)], check=True)
except subprocess.CalledProcessError as exc:
    shutil.copy2(backup_dir / TARGET.name, TARGET)
    raise SystemExit(f"Compile failed; restored backup: {exc}")

(ROOT / ".last_metadata_provenance_audit_d1_3_backup").write_text(str(backup_dir))
print("Installed AIOS Metadata Provenance Audit D1.3")
print(f"Backup: {backup_dir}")
print("Next: bash aios_metadata_provenance_audit_d1_3/smoke_test.sh")
