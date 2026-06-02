#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
PYTHON_BIN="${PYTHON_BIN:-./venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="python3"
fi

$PYTHON_BIN - <<'PY'
from core.project_cognition.historical_affinity import HistoricalTask, summarize_historical_affinity

tasks = [
    HistoricalTask(id='h1', title='Check skimmer basket in pool', done=True, project_ids=('11111111-1111-1111-1111-111111111111',)),
    HistoricalTask(id='h2', title='Brush pool and check chlorine', done=True, project_ids=('11111111-1111-1111-1111-111111111111',)),
    HistoricalTask(id='h3', title='Vacuum pool and clean filter', done=True, project_ids=('11111111-1111-1111-1111-111111111111',)),
    HistoricalTask(id='h4', title='Test pool water and chlorine', done=True, project_ids=('11111111-1111-1111-1111-111111111111',)),
    HistoricalTask(id='h5', title='Organize pool equipment', done=True, project_ids=('11111111-1111-1111-1111-111111111111',)),
    HistoricalTask(id='h6', title='Pool chemicals and water test', done=True, suggested_project='pool maintenance and supplies'),
    HistoricalTask(id='h7', title='Store pool chemicals and supplies', done=True, suggested_project='pool maintenance and supplies'),
    HistoricalTask(id='h10', title='Pool water and botboy prep', done=True, suggested_project='pool maintenance and preparation'),
    HistoricalTask(id='h11', title='Prepare pool water and botboy', done=True, suggested_project='pool maintenance and preparation'),
    HistoricalTask(id='h8', title='Print packaging labels', done=True, project_ids=('22222222-2222-2222-2222-222222222222',)),
    HistoricalTask(id='h9', title='Create packaging stickers', done=True, project_ids=('22222222-2222-2222-2222-222222222222',)),
    HistoricalTask(id='a1', title='Check skimmer basket in pool', done=False, suggested_project='Pool Maintenance and Supplies'),
    HistoricalTask(id='a2', title='Organize pool equipment', done=False, suggested_project='Pool Maintenance and Opening'),
    HistoricalTask(id='a3', title='Create packaging labels', done=False, suggested_project='Bakery Operations and Supplies'),
    HistoricalTask(id='a4', title='Move extra workshop bins to the basement', done=False, suggested_project='Workshops and Teaching'),
    HistoricalTask(id='a5', title='Unpack bins from the workshop', done=False, suggested_project='Workshops and Teaching'),
    HistoricalTask(id='a6', title='Write summary of workshop for Gaby', done=False),
    HistoricalTask(id='h12', title='Move workshop bins to basement', done=True, project_ids=('33333333-3333-3333-3333-333333333333',)),
    HistoricalTask(id='h13', title='Unpack workshop bins', done=True, project_ids=('33333333-3333-3333-3333-333333333333',)),
    HistoricalTask(id='h14', title='Write workshop summary', done=True, project_ids=('33333333-3333-3333-3333-333333333333',)),
]
summary = summarize_historical_affinity(
    tasks,
    project_name_by_id={
        '11111111-1111-1111-1111-111111111111': 'Pool Opening and Maintenance',
        '22222222-2222-2222-2222-222222222222': 'Bakery Operations and Supplies',
        '33333333-3333-3333-3333-333333333333': 'Workshops and Teaching',
    },
)
lines = '\n'.join(summary.telemetry_lines())
assert 'D2.4' in lines, lines
assert 'Stability-governed persistence' in lines, lines
assert hasattr(summary, 'canonical_project_preferences')
prefs = summary.canonical_project_preferences
assert prefs['enabled'] is True, prefs
assert len(prefs['preferences']) >= 1, prefs
assert any(p['canonical_project'] == 'Pool Opening and Maintenance' for p in prefs['preferences']), prefs
assert 'project_relation_mutation=disabled' in lines, lines
assert 'Stability-governed Suggested Project persistence: enabled=true' in lines, lines
assert hasattr(summary, 'canonical_preference_assistance')
assert summary.canonical_preference_assistance['enabled'] is True
assert hasattr(summary, 'stability_governed_persistence')
sgp = summary.stability_governed_persistence
assert sgp['enabled'] is True, sgp
assert sgp['auto_apply_default'] is True, sgp
assert any(item['suggested_project'] == 'Workshops and Teaching' for item in sgp['eligible_writes']), sgp
print('D2.4 smoke test passed: stability-governed Suggested Project persistence telemetry is safe and bounded.')
PY

grep -q "D2.4" scripts/aios_project_affinity_report.py
$PYTHON_BIN -m py_compile scripts/aios_project_affinity_report.py core/project_cognition/historical_affinity.py
