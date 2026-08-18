from aios.task_writing import AI_TASK_TITLE_GUIDANCE
assert '4–8 words' in AI_TASK_TITLE_GUIDANCE
assert '55 characters' in AI_TASK_TITLE_GUIDANCE
from aios.api.app import TaskDetailUpdate
x=TaskDetailUpdate(title='Confirm baking components are ready', context='Verify prepared ingredients and tools before beginning the bake.')
assert x.context and len(x.title)<55
print('Concise title guidance: PASS')
print('Task context API contract: PASS')
print('RESULT: TASK CONTEXT + CONCISE TITLES V1 SMOKE TEST PASSED')
