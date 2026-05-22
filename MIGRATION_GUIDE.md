# Temporal Authority Production Patch

Target file:
run_aios_PHASE2_FIXED.py

## Step 1 — Add import

Find:

    from datetime import datetime, timezone

Replace with:

    from datetime import datetime, timezone, timedelta

Add:

    from core.metadata.temporal import extract_temporal_metadata

near the other imports.

---

## Step 2 — Replace explicit today/tomorrow parsing

Find blocks similar to:

    if explicit_today:
    elif explicit_tomorrow:

Replace with:

    temporal = extract_temporal_metadata(title)

    if temporal["due_date"]:
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

---

## Step 3 — Replace title cleanup

Find direct cleanup patterns like:

    title.replace("today", "")

or:

    strip_due_date_phrases(...)

Replace with:

    temporal = extract_temporal_metadata(title)
    title = temporal["cleaned_title"]

---

## Step 4 — Run tests

Recommended smoke tests:

- Buy groceries today
- Call dentist tomorrow morning
- Review bakery schedule May 28

Expected:
- cleaned titles
- due dates assigned
- no execution engine regressions