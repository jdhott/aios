from aios.focus_activation import (
    FOCUS_ACTIVATION_SOURCE,
    create_focus_activation_child,
    get_active_focus_activation,
    list_focus_activation_children,
    next_focus_activation_step_order,
)


class Result:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.filters = []
        self.order_field = None
        self.limit_value = None
        self.insert_payload = None

    def select(self, *_args):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, field):
        self.order_field = field
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def insert(self, payload):
        self.insert_payload = dict(payload)
        return self

    def execute(self):
        rows = self.client.rows

        if self.insert_payload is not None:
            row = {
                "id": f"task-{len(rows) + 1}",
                **self.insert_payload,
            }
            rows.append(row)
            return Result([dict(row)])

        result = [
            dict(row)
            for row in rows
            if all(row.get(field) == value for field, value in self.filters)
        ]

        if self.order_field:
            result.sort(
                key=lambda row: (
                    row.get(self.order_field) is None,
                    row.get(self.order_field),
                )
            )

        if self.limit_value is not None:
            result = result[:self.limit_value]

        return Result(result)


class FakeClient:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def table(self, name):
        assert name == "tasks"
        return FakeQuery(self, name)


class FakeStore:
    def __init__(self, rows=None):
        self.client = FakeClient(rows)


PARENT = "parent-1"

store = FakeStore()

assert list_focus_activation_children(store, PARENT) == []
assert get_active_focus_activation(store, PARENT) is None
assert next_focus_activation_step_order(store, PARENT) == 1

first = create_focus_activation_child(
    store,
    parent_task_id=PARENT,
    title="Write the guest list.",
)

assert first["parent_task_id"] == PARENT
assert first["is_just_do_it"] is True
assert first["generated_source"] == FOCUS_ACTIVATION_SOURCE
assert first["step_order"] == 1
print("First activation child creation: PASS")

again = create_focus_activation_child(
    store,
    parent_task_id=PARENT,
    title="THIS MUST NOT BE CREATED",
)

assert again["id"] == first["id"]
assert len(store.client.rows) == 1
print("Active-child idempotency: PASS")

store.client.rows[0]["is_open"] = False
store.client.rows[0]["is_done"] = True
store.client.rows[0]["completed_at"] = "2026-08-15T14:00:00+00:00"

assert get_active_focus_activation(store, PARENT) is None
assert next_focus_activation_step_order(store, PARENT) == 2

second = create_focus_activation_child(
    store,
    parent_task_id=PARENT,
    title="Choose two possible dates.",
)

assert second["step_order"] == 2
assert len(store.client.rows) == 2
print("Next activation sequence: PASS")

history = list_focus_activation_children(store, PARENT)
assert [row["step_order"] for row in history] == [1, 2]
assert history[0]["is_done"] is True
assert history[1]["is_done"] is False
print("Activation history preserved: PASS")

print("RESULT: FOCUS ACTIVATION V1 SMOKE TEST PASSED")
