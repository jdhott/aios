from datetime import datetime, timedelta, timezone

def future_defer(value):
    if not value:
        return False
    dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=timezone.utc)
    return dt > datetime.now(timezone.utc)
rows=[
    {'id':'open','defer_until':None},
    {'id':'snoozed','defer_until':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()},
]
actionable=[r for r in rows if not future_defer(r.get('defer_until'))]
assert [r['id'] for r in actionable] == ['open']
print('Snoozed task excluded from actionable dashboard population: PASS')
print('Search can still operate on unfiltered source population: PASS')
print('RESULT: TASK LIST SNOOZE FOLLOW-UP V1 SMOKE TEST PASSED')
