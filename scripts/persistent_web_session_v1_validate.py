from pathlib import Path
import ast
w=Path("aios/web_capture/app.py").read_text()
d=Path("scripts/deploy_cloud_run_web.sh").read_text()
checks=[
("cookie",'SESSION_COOKIE_NAME = "aios_session"' in w),
("secret",'AIOS_WEB_SESSION_SECRET' in w),
("hmac","hashlib.sha256" in w and "hmac.new(" in w),
("30 days","SESSION_DEFAULT_DAYS = 30" in w),
("secure","secure=True" in w),
("httponly","httponly=True" in w),
("samesite",'samesite="lax"' in w),
("login get",'@app.get("/login"' in w),
("login post",'@app.post("/login")' in w),
("logout",'@app.post("/logout")' in w),
("dependency","def _check_basic_auth(request: Request)" in w),
("no basic challenge",'"WWW-Authenticate": "Basic"' not in w),
("deploy secret",'AIOS_WEB_SESSION_SECRET=${SESSION_SECRET}:latest' in d),
]
bad=False
for n,ok in checks:
    print(("PASS" if ok else "FAIL")+": "+n); bad|=not ok
ast.parse(w); print("web parses: PASS")
if bad: raise SystemExit("RESULT: PERSISTENT WEB SESSION V1 VALIDATION FAILED")
print("RESULT: PERSISTENT WEB SESSION V1 STRUCTURE VALID")
