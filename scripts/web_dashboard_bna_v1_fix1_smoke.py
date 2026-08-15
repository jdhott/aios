#!/usr/bin/env python3
import base64, os
from unittest.mock import patch
from fastapi.testclient import TestClient
import aios.web_capture.app as web
def basic(u,p):
    return {"Authorization":"Basic "+base64.b64encode(f"{u}:{p}".encode()).decode()}
env={"AIOS_WEB_USERNAME":"aios","AIOS_WEB_PASSWORD":"test-password","AIOS_API_URL":"https://example.run.app"}
sections={"top5":[
{"id":"t3","title":"Rank three","due_at":None,"importance":"High Importance","is_quick_win":False,"is_just_do_it":False,"execution_score":28,"execution_rank":3,"best_next_action":True,"surfaced_quick_win":False},
{"id":"t1","title":"Plan 90th birthday party for Mum","due_at":"2026-08-20","importance":"High Importance","is_quick_win":False,"is_just_do_it":False,"execution_score":36,"execution_rank":1,"best_next_action":True,"surfaced_quick_win":False},
{"id":"t2","title":"Rank two","due_at":None,"importance":"High Importance","is_quick_win":False,"is_just_do_it":False,"execution_score":32,"execution_rank":2,"best_next_action":True,"surfaced_quick_win":False}
],"quick_wins":[],"today":[],"just_do_it":[]}
with patch.dict(os.environ,env,clear=False), patch.object(web,"_fetch_open_tasks",lambda **k:sections):
    with TestClient(web.app) as client:
        r=client.get("/",headers=basic("aios","test-password"))
assert r.status_code==200
assert "⭐ Best Next Action" in r.text
assert "Plan 90th birthday party for Mum" in r.text
assert "Rank 1" in r.text
assert "Score 36" in r.text
start=r.text.find('class="bna-card"')
end=r.text.find("</section>",start)
card=r.text[start:end]
assert "Rank three" not in card and "Rank two" not in card
print("Lowest execution rank selected: PASS")
print("BNA card renders at runtime: PASS")
print("RESULT: DASHBOARD BNA V1 FIX1 SMOKE TEST PASSED")
