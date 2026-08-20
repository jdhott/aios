import json
from types import SimpleNamespace
from aios.focus_context import generate_focus_context_from_answer

class Responses:
    def create(self, *, model, input):
        assert 'Question AIOS asked:' in input
        assert "User's answer:" in input
        assert '12 bannetons' in input
        return SimpleNamespace(output_text=json.dumps({
            'draft_context': 'Workshop is prepared; 12 bannetons still need to be arranged.',
            'question': '',
        }))
class Client:
    responses = Responses()

out = generate_focus_context_from_answer(
    Client(), title='Prepare workshop', task_context='Workshop is Sunday.',
    project_context='', draft_context='Workshop is Sunday.',
    question='What equipment remains?', answer='I still need to arrange 12 bannetons.'
)
assert '12 bannetons' in out['draft_context']
assert out['question'] == ''
print('PASS: answer is incorporated into editable context draft')
print('PASS: follow-up question can end when context is sufficient')
print('RESULT: FOCUS CONTEXT LOOP V2 SMOKE TEST PASSED')
