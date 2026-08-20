import os
os.environ.setdefault("AIOS_WEB_USERNAME","test-user")
os.environ.setdefault("AIOS_WEB_PASSWORD","test-password")
os.environ.setdefault("AIOS_WEB_SESSION_SECRET","test-session-secret-123456789")
from aios.web_capture import app as a
t=a._encode_session("test-user")
assert a._decode_session(t)=="test-user"
print("Signed session round trip: PASS")
bad=t[:-1]+("0" if t[-1]!="0" else "1")
assert a._decode_session(bad) is None
print("Tampered session rejected: PASS")
assert a._safe_login_next("/capture")=="/capture"
assert a._safe_login_next("//evil")=="/"
print("Safe return path: PASS")
print("RESULT: PERSISTENT WEB SESSION V1 SMOKE TEST PASSED")
