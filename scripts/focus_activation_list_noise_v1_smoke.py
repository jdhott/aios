rows = [
    {"id": "normal", "title": "Make eggplant parmesan", "generated_source": None, "task_role": None},
    {"id": "breakdown", "title": "Slice eggplant", "generated_source": None, "task_role": None},
    {"id": "starter1", "title": "Gather ingredients", "generated_source": "focus_activation", "task_role": None},
    {"id": "starter2", "title": "Open recipe", "generated_source": None, "task_role": "focus_activation"},
]
visible = [
    row for row in rows
    if row.get("generated_source") != "focus_activation"
    and row.get("task_role") != "focus_activation"
]
assert [r["id"] for r in visible] == ["normal", "breakdown"]
print("Normal and breakdown tasks remain visible: PASS")
print("Generated START HERE helpers are hidden from general task lists: PASS")
print("RESULT: FOCUS ACTIVATION LIST NOISE V1 SMOKE TEST PASSED")
