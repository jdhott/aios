
from pathlib import Path

repo = Path.home() / "LocalProjects" / "aios"
target = repo / "run_aios_PHASE2_FIXED.py"

text = target.read_text()

bad_block = """temporal = extract_temporal_metadata(source_text)"""

if bad_block in text:
    text = text.replace(bad_block, "# temporal extraction moved into runtime processing path")

old = """    normalized_source = source_text.lower()

    explicit_today = "today" in normalized_source
    explicit_tomorrow = "tomorrow" in normalized_source"""

new = """    temporal = extract_temporal_metadata(source_text)

    explicit_today = False
    explicit_tomorrow = False"""

text = text.replace(old, new)

old2 = """    # -----------------------------------------------------------------
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
"""

new2 = """    # -----------------------------------------------------------------
    # Canonical temporal authority
    # -----------------------------------------------------------------
    if temporal.get("cleaned_title"):
        title = temporal["cleaned_title"]

    if temporal.get("due_date"):
        due_date = temporal["due_date"]

        updates["Due Date"] = {
            "date": {
                "start": due_date.isoformat()
            }
        }

        changed_metadata["Due Date"] = {
            "value": due_date.isoformat(),
            "source": "canonical_temporal_authority",
            "reason": "Canonical temporal extraction",
        }

        print(
            "[Temporal Authority Applied]",
            {
                "title": title,
                "due_date": due_date.isoformat(),
                "signals": temporal.get("signals", []),
            }
        )
"""

text = text.replace(old2, new2)

if "from core.metadata.temporal import extract_temporal_metadata" not in text:
    text = text.replace(
        "from difflib import SequenceMatcher",
        "from difflib import SequenceMatcher\nfrom core.metadata.temporal import extract_temporal_metadata"
    )

target.write_text(text)
print("Patched run_aios_PHASE2_FIXED.py")
