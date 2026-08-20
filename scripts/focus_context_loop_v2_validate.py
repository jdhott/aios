from pathlib import Path

fc = Path('aios/focus_context.py').read_text()
api = Path('aios/api/app.py').read_text()
web = Path('aios/web_capture/app.py').read_text()
act = Path('aios/focus_activation.py').read_text()
mig = Path('migrations/20260820_focus_context_loop_v2.sql').read_text()

checks = [
    ('V2 helper version', 'focus-context-help-v2' in fc),
    ('answer incorporation generator', 'generate_focus_context_from_answer' in fc),
    ('answer pending processor state', 'answer_pending' in fc),
    ('answer API endpoint', '/focus-context/answer' in api),
    ('answer request body', 'class FocusContextAnswerRequest(BaseModel)' in api),
    ('Not useful API endpoint', '/not-useful' in api),
    ('Not useful records disposition', '"activation_disposition": "not_useful"' in api),
    ('Not useful starts coaching', '"focus_context_help_state": "pending"' in api),
    ('activation waits for coaching', 'Waiting for context coaching' in act),
    ('Not useful excluded from repeat suggestions', '{"not_now", "not_useful"}' in act),
    ('V2 help label', 'Help me improve this context' in web),
    ('dedicated answer field', 'Your answer' in web and 'name="answer"' in web),
    ('answer incorporation action', 'Use my answer' in web),
    ('Not useful UI', '>Not useful</button>' in web),
    ('old confusing label removed', 'Suggest context / ask me a question' not in web),
    ('answer migration', 'focus_context_answer text' in mig),
]
for label, ok in checks:
    assert ok, label
    print('PASS:', label)
print('RESULT: FOCUS CONTEXT LOOP V2 STRUCTURE VALID')
