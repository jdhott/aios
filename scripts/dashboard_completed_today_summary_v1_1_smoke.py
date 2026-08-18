from datetime import datetime, timezone
from aios.daily_completion_summary import completion_fingerprint, generate_daily_summary

rows = [
    {"id":"b", "title":"Bake bread", "completed_at":"2026-08-18T14:00:00+00:00"},
    {"id":"a", "title":"Clean bakery table", "completed_at":"2026-08-18T13:00:00+00:00"},
]
f1 = completion_fingerprint(rows)
f2 = completion_fingerprint(list(reversed(rows)))
assert f1 == f2
print("Stable completion fingerprint: PASS")

class FakeResponses:
    def create(self, **kwargs):
        class R:
            output_text = "Today's completed work focused on bakery preparation and cleanup."
        return R()
class FakeClient:
    responses = FakeResponses()

summary = generate_daily_summary(FakeClient(), rows)
assert "bakery" in summary.lower()
print("Bounded AI summary generation: PASS")
assert generate_daily_summary(FakeClient(), rows[:1]) == ""
print("Single-task AI call skipped: PASS")
print("RESULT: COMPLETED TODAY SUMMARY V1.1 SMOKE TEST PASSED")
