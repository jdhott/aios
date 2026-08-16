from unittest.mock import patch

import aios.api.app as api


created_tasks = []
accepted_ids = []
dismissed_ids = []
processor_calls = []


class FakeTable:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.limit_count = None

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def execute(self):
        rows = [
            row for row in self.rows
            if all(
                row.get(field) == value
                for field, value in self.filters
            )
        ]

        if self.limit_count is not None:
            rows = rows[:self.limit_count]

        class Result:
            data = [dict(row) for row in rows]

        return Result()


class FakeClient:
    def __init__(self):
        self.proposals = [
            {
                "id": "proposal-1",
                "project_id": "project-1",
                "title": "Create a potluck sign-up list",
                "status": "proposed",
            },
            {
                "id": "proposal-2",
                "project_id": "project-1",
                "title": "Prepare a family photo display",
                "status": "proposed",
            },
        ]

    def table(self, name):
        assert name == "project_work_proposals"
        return FakeTable(self.proposals)


class FakeStore:
    def __init__(self):
        self.client = FakeClient()


store = FakeStore()


def fake_create_project_task(
    passed_store,
    *,
    title,
    project_id,
    importance=None,
    urgency=None,
    due_at=None,
):
    assert passed_store is store

    task = {
        "id": "task-1",
        "title": title,
        "project_id": project_id,
        "parent_task_id": None,
        "task_role": None,
        "is_just_do_it": False,
        "generated_source": "project_work",
        "is_open": True,
        "is_done": False,
        "is_archived": False,
    }

    created_tasks.append(task)
    return task


def fake_accept(passed_store, proposal_id):
    assert passed_store is store
    accepted_ids.append(proposal_id)

    return {
        "id": proposal_id,
        "project_id": "project-1",
        "title": "Create a potluck sign-up list",
        "status": "accepted",
    }


def fake_dismiss(passed_store, proposal_id):
    assert passed_store is store
    dismissed_ids.append(proposal_id)

    return {
        "id": proposal_id,
        "project_id": "project-1",
        "title": "Prepare a family photo display",
        "status": "dismissed",
    }


def fake_processor():
    processor_calls.append(True)
    return {"status": "requested"}


with (
    patch.object(api, "_store", lambda: store),
    patch.object(
        api,
        "create_supabase_project_task",
        fake_create_project_task,
    ),
    patch.object(
        api,
        "accept_project_work_proposal",
        fake_accept,
    ),
    patch.object(
        api,
        "dismiss_project_work_proposal",
        fake_dismiss,
    ),
    patch.object(
        api,
        "_request_processor_run",
        fake_processor,
    ),
):
    # --------------------------------------------------------
    # Accept
    # --------------------------------------------------------

    result = api.accept_project_work_http(
        "project-1",
        "proposal-1",
    )

    assert result["accepted"] is True
    assert len(created_tasks) == 1

    task = result["task"]

    assert task["title"] == "Create a potluck sign-up list"
    assert task["project_id"] == "project-1"
    assert task["generated_source"] == "project_work"
    assert task["task_role"] is None
    assert task["parent_task_id"] is None
    assert task["is_just_do_it"] is False

    assert accepted_ids == ["proposal-1"]

    print("Accept creates normal project task: PASS")
    print("Accepted task preserves project-work semantics: PASS")
    print("Proposal marked accepted after task creation: PASS")

    # --------------------------------------------------------
    # Dismiss
    # --------------------------------------------------------

    before = len(created_tasks)

    result = api.dismiss_project_work_http(
        "project-1",
        "proposal-2",
    )

    assert result["dismissed"] is True
    assert len(created_tasks) == before
    assert dismissed_ids == ["proposal-2"]

    print("Dismiss creates no task: PASS")
    print("Dismissed proposal state persisted: PASS")

    assert processor_calls == [True]

    print("Accept requests processor refresh: PASS")


print(
    "RESULT: PROJECT WORK REVIEW ACTIONS V1 "
    "SMOKE TEST PASSED"
)
