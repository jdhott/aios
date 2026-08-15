#!/usr/bin/env python3
import json
from aios.focus_guidance import generate_focus_guidance
class R: output_text=json.dumps({'starter_step':'List the three decisions that must be made first.','starter_minutes':9})
class RS:
    def create(self,**kwargs): return R()
class C: responses=RS()
result=generate_focus_guidance(C(),'Plan 90th birthday party for Mum')
assert result['starter_step']=='List the three decisions that must be made first.'
assert result['starter_minutes']==10
assert result['source']=='ai'
print('AI starter guidance parses: PASS')
print('Starter timebox normalizes: PASS')
print('RESULT: FOCUS GUIDANCE V1 SMOKE TEST PASSED')
