from unittest.mock import patch

import aios.api.app as api
import aios.web_capture.app as web


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
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
        self.limit_count = int(count)
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

        return FakeResult([dict(row) for row in rows])


class FakeClient:
    def __init__(self):
        self.proposals = [
            {
                "id": "proposal-1",
                "project_id": "project-1",
                "title": "Assign dishes to guests",
                "status": "proposed",
            },
            {
                "id": "proposal-2",
                "project_id": "project-1",
                "title": "Create decorations checklist",
                "status": "proposed",
            },
            {
                "id": "proposal-3",
                "project_id": "project-1",
                "title": "Another proposal",
                "status": "proposed",
            },
        ]

    def table(self, name):
        assert name == "project_work_proposals"
        return FakeQuery(self.proposals)


class FakeStore:
    def __init__(self):
        self.client = FakeClient()


store = FakeStore()

created = []
accepted = []
retried = []
dismissed = []
processor_calls = []


def fake_create(
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
        "generated_source": "project_work",
        "task_role": None,
        "is_just_do_it": False,
        "parent_task_id": None,
    }

    created.append(task)
    return task


def fake_accept(passed_store, proposal_id):
    assert passed_store is store
    accepted.append(proposal_id)
    return {
        "id": proposal_id,
        "project_id": "project-1",
        "status": "accepted",
    }


def fake_retry(
    passed_store,
    proposal_id,
    *,
    feedback,
):
    assert passed_store is store
    retried.append((proposal_id, feedback))
    return {
        "id": proposal_id,
        "project_id": "project-1",
        "status": "dismissed",
        "feedback": feedback,
    }


def fake_dismiss(passed_store, proposal_id):
    assert passed_store is store
    dismissed.append(proposal_id)
    return {
        "id": proposal_id,
        "project_id": "project-1",
        "status": "dismissed",
        "feedback": None,
    }


def fake_processor():
    processor_calls.append(True)
    return {"status": "requested"}


with (
    patch.object(api, "_store", lambda: store),
    patch.object(
        api,
        "create_supabase_project_task",
        fake_create,
    ),
    patch.object(
        api,
        "accept_project_work_proposal",
        fake_accept,
    ),
    patch.object(
        api,
        "retry_project_work_proposal",
        fake_retry,
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
    # Edited Accept
    # --------------------------------------------------------

    result = api.accept_project_work_http(
        "project-1",
        "proposal-1",
        api.ProjectWorkAcceptRequest(
            title="Create a potluck sign-up sheet",
        ),
    )

    assert result["accepted"] is True
    assert len(created) == 1
    assert (
        created[0]["title"]
        == "Create a potluck sign-up sheet"
    )
    assert accepted == ["proposal-1"]

    print("Edited proposal title used on Accept: PASS")

    # --------------------------------------------------------
    # Try Again
    # --------------------------------------------------------

    result = api.retry_project_work_http(
        "project-1",
        "proposal-2",
        api.ProjectWorkRetryRequest(
            feedback=(
                "Guests should self-select. "
                "Use a sign-up mechanism instead."
            ),
        ),
    )

    assert result["retry_requested"] is True
    assert retried == [
        (
            "proposal-2",
            "Guests should self-select. "
            "Use a sign-up mechanism instead.",
        )
    ]

    print("Try Again stores feedback: PASS")

    # --------------------------------------------------------
    # Dismiss
    # --------------------------------------------------------

    result = api.dismiss_project_work_http(
        "project-1",
        "proposal-3",
    )

    assert result["dismissed"] is True
    assert dismissed == ["proposal-3"]

    print("Dismiss remains separate from feedback rejection: PASS")

    # Accept + retry trigger processor; plain dismiss does not.
    assert processor_calls == [True, True]

    print("Accept and Try Again request processor refresh: PASS")


# ------------------------------------------------------------
# UI rendering
# ------------------------------------------------------------

html = web._project_detail_page({
    "project": {
        "id": "project-1",
        "name": "Test Project",
        "open_task_count": 0,
    },
    "tasks": [],
    "work_proposals": [{
        "id": "proposal-1",
        "title": "Assign dishes to guests",
        "status": "proposed",
    }],
})

assert 'name="title"' in html
assert (
    '<textarea class="proposal-title-input" '
    'name="title" maxlength="75" required>'
    'Assign dishes to guests</textarea>'
    in html
)
assert ">Accept</button>" in html

assert 'name="feedback"' in html
assert ">Try Again</button>" in html

assert ">Dismiss</button>" in html

print("Editable Accept UI renders: PASS")
print("Try Again feedback UI renders: PASS")
print("Dismiss UI retained: PASS")

print(
    "RESULT: PROJECT WORK REVIEW UI V2 "
    "SMOKE TEST PASSED"
)
