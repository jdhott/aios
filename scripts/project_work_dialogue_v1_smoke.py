from aios.project_work import generate_project_work, summarize_project_work_answer
class R:
 def __init__(self,text): self.output_text=text
class Responses:
 def __init__(self,items): self.items=list(items)
 def create(self,**kwargs): return R(self.items.pop(0))
class C:
 def __init__(self,items): self.responses=Responses(items)
# Manual audit may ask instead of inventing work.
r=generate_project_work(C(['{"state":"clarification","question":"Have you decided how potluck contributions will be coordinated?","tasks":[]}']), project_name="Jan's 90th", project_outcome='Hold family birthday party', project_context='Potluck dinner. Invitations sent; RSVPs arriving.', open_work=['Plan potluck dinner menu'], completed_work=['Send invitations'], allow_clarification=True, clarification_round=0)
assert r and r['state']=='clarification' and 'potluck' in r['question'].lower()
print('Targeted clarification returned: PASS')
# Same output is not allowed after cap.
r=generate_project_work(C(['{"state":"clarification","question":"Another question?","tasks":[]}']), project_name='P', project_outcome='O', allow_clarification=True, clarification_round=2)
assert r and r['state']=='waiting'
print('Two-round cap enforced: PASS')
# User answer becomes concise editable durable context.
s=summarize_project_work_answer(C(['{"context_update":"Potluck contributions will probably be assigned after most RSVPs are received."}']), project_context='Potluck dinner.', question='How?', answer="I'll probably wait for most RSVPs and then assign dishes.")
assert s=='Potluck contributions will probably be assigned after most RSVPs are received.'
print('Answer summarized without losing uncertainty: PASS')
print('RESULT: PROJECT WORK DIALOGUE V1 SMOKE TEST PASSED')
