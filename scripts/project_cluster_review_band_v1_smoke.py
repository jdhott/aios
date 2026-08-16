from aios import projects


# ------------------------------------------------------------
# Minimal injected runtime helpers
# ------------------------------------------------------------

def get_title(item):
    return str(item.get("title") or item.get("name") or "").strip()


def find_project_by_name(name, projects_list):
    wanted = str(name or "").strip().lower()

    for project in projects_list:
        if get_title(project).lower() == wanted:
            return project

    return None


def find_existing_project_match(_candidate, _active):
    return None, 0.40, "No strong name-based match."


def build_contexts(_all_projects, _open_tasks):
    return [{
        "project": active_project,
        "project_name": active_project["name"],
        "active": True,
        "member_titles": [
            "Maintain recipe documentation",
            "Organize recipe development records",
        ],
    }]


def cluster_match(
    candidate_name,
    candidate_titles,
    project_contexts,
    ai_client,
):
    assert candidate_name == "Bread Baking and Recipe Development"
    assert candidate_titles
    assert project_contexts
    assert ai_client is fake_client

    return (
        active_project,
        0.85,
        "Plausible related project, below auto-match threshold.",
        False,
    )


created = []
relations = []
suggested_updates = []


def create_stub(
    project_name,
    existing_projects=None,
    source_reason="",
    possible_existing_project=None,
    possible_existing_project_confidence=None,
):
    created.append({
        "project_name": project_name,
        "possible_existing_project": possible_existing_project,
        "possible_existing_project_confidence": (
            possible_existing_project_confidence
        ),
        "source_reason": source_reason,
    })

    return {
        "id": "review-project",
        "name": project_name,
        "status": "Someday",
        "is_active": False,
    }


def update_suggested(task, project_name):
    suggested_updates.append(
        (task["id"], project_name)
    )
    return True


def set_review_relation(task, project, project_name):
    relations.append(
        (task["id"], project["id"], project_name)
    )
    return True


def set_active_relation(*_args, **_kwargs):
    raise AssertionError(
        "Review-band match must not auto-link to active project"
    )


active_project = {
    "id": "active-project",
    "_supabase_id": "active-project",
    "name": "Recipe and Documentation Management",
}

seed_task = {
    "id": "t1",
    "title": "Design focaccia art topping",
}

related_task = {
    "id": "t2",
    "title": "Make cookie batter",
}

result = {
    "project_name": "Bread Baking and Recipe Development",
    "related_titles": [
        "Make cookie batter",
    ],
    "expanded_related_titles": [],
}

fake_client = object()

# ------------------------------------------------------------
# Inject only what this transitional module currently expects
# ------------------------------------------------------------

injected = {
    "get_title": get_title,
    "find_project_by_name": find_project_by_name,
    "find_existing_project_match": find_existing_project_match,
    "build_incremental_project_contexts": build_contexts,
    "find_existing_project_cluster_match": cluster_match,
    "create_inactive_project_stub_if_missing": create_stub,
    "update_suggested_project_if_needed": update_suggested,
    "set_review_project_relation_if_empty": set_review_relation,
    "set_project_relation_if_safe": set_active_relation,
    "increment_summary": lambda *_args, **_kwargs: None,
    "client": fake_client,
    "RUN_PROJECT_RELATION_WRITEBACK": True,
    "PROJECT_CLUSTER_REVIEW_MIN_CONFIDENCE": 0.75,
}

old_values = {
    name: getattr(projects, name, None)
    for name in injected
}

had_values = {
    name: hasattr(projects, name)
    for name in injected
}

for name, value in injected.items():
    setattr(projects, name, value)

try:
    updated = projects.apply_project_candidate_writeback(
        seed_task,
        result,
        [related_task],
        [active_project],
        [active_project],
    )
finally:
    for name in injected:
        if had_values[name]:
            setattr(projects, name, old_values[name])
        else:
            delattr(projects, name)


# ------------------------------------------------------------
# Assertions
# ------------------------------------------------------------

assert len(created) == 1

created_stub = created[0]

assert (
    created_stub["project_name"]
    == "Bread Baking and Recipe Development"
)

assert (
    created_stub["possible_existing_project"]
    is active_project
)

assert (
    created_stub["possible_existing_project_confidence"]
    == 0.85
)

# It remains its own review-stage project.
assert relations == [
    (
        "t1",
        "review-project",
        "Bread Baking and Recipe Development",
    ),
    (
        "t2",
        "review-project",
        "Bread Baking and Recipe Development",
    ),
]

# Suggested Project remains the proposed new project name.
assert suggested_updates == [
    ("t1", "Bread Baking and Recipe Development"),
    ("t2", "Bread Baking and Recipe Development"),
]

assert updated == 4

print("0.85 match does not auto-merge: PASS")
print("Someday review stub is created: PASS")
print("Possible existing project is preserved: PASS")
print("Possible-match confidence is preserved: PASS")
print("Tasks remain attached to review project: PASS")
print("RESULT: PROJECT CLUSTER REVIEW BAND V1 SMOKE TEST PASSED")
