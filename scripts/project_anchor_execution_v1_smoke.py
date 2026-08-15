from execution_engine_v2 import (
    filter_execution_eligible_tasks,
)


def rich_text(value):
    return {
        "type": "rich_text",
        "rich_text": (
            [{"plain_text": value}]
            if value
            else []
        ),
    }


def checkbox(value):
    return {
        "type": "checkbox",
        "checkbox": value,
    }


anchor = {
    "id": "anchor-1",
    "properties": {
        "Task Name": {
            "type": "title",
            "title": [{"plain_text": "Plan 90th birthday party for Mum"}],
        },
        "Task Role": rich_text("project_anchor"),
        "Just Do It": checkbox(False),
        "Quick Win": checkbox(False),
    },
}

normal = {
    "id": "task-2",
    "properties": {
        "Task Name": {
            "type": "title",
            "title": [{"plain_text": "Write birthday invitation"}],
        },
        "Task Role": rich_text(""),
        "Just Do It": checkbox(False),
        "Quick Win": checkbox(False),
    },
}

eligible = filter_execution_eligible_tasks(
    [anchor, normal]
)

ids = [task["id"] for task in eligible]

assert "anchor-1" not in ids
assert "task-2" in ids

print("Project anchor rejected from execution: PASS")
print("Ordinary executable task retained: PASS")
print("RESULT: PROJECT ANCHOR EXECUTION V1 SMOKE TEST PASSED")
