# OLD

if explicit_today:
    due_date = datetime.now().date()

# NEW

temporal = extract_temporal_metadata(title)

if temporal["due_date"]:
    due_date = temporal["due_date"]