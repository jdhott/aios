from pathlib import Path
root = Path('.')
fa=(root/'aios/focus_activation.py').read_text()
api=(root/'aios/api/app.py').read_text()
web=(root/'aios/web_capture/app.py').read_text()
checks=[
('active resolver keeps rejected open','A Start Here marked not useful remains open while context coaching' in fa),
('Not useful no longer closes immediately','the exact suggestion the user said was not useful' in api),
('save preserves not-useful history','.eq("activation_disposition", "not_useful")' in api),
('web recognizes rejected state','activation_not_useful = activation_disposition == "not_useful"' in web),
('rejected label','Marked not useful' in web),
('help hidden during active coaching','{"pending", "answer_pending", "ready"}' in web),
]
for label,ok in checks:
    assert ok, f'FAIL: {label}'
    print(f'PASS: {label}')
print('RESULT: FOCUS CONTEXT V2 NOT-USEFUL FIX STRUCTURE VALID')
