import os

os.environ.setdefault("AIOS_WEB_USERNAME", "test")
os.environ.setdefault("AIOS_WEB_PASSWORD", "test")
os.environ.setdefault("AIOS_WEB_SESSION_SECRET", "test-session-secret")

from fastapi.testclient import TestClient
import aios.web_capture.app as web

captured = []


def fake_capture(text, *, capture_interface="cloud_run_web"):
    captured.append((text, capture_interface))
    return {"id": f"capture-{len(captured)}"}


web._capture_to_aios = fake_capture
c = TestClient(web.app)

# The current web app uses a signed session cookie rather than HTTP Basic auth.
# Log in once so subsequent requests exercise /capture/submit as an authenticated
# PWA client would.
login = c.post(
    "/login",
    data={"username": "test", "password": "test", "next": "/capture"},
    follow_redirects=False,
)
assert login.status_code == 303, login.text
assert web.SESSION_COOKIE_NAME in login.cookies, login.cookies

# TestClient does not enforce a browser's Secure-cookie transport rules, but set
# the returned cookie explicitly so this test remains deterministic.
c.cookies.set(web.SESSION_COOKIE_NAME, login.cookies.get(web.SESSION_COOKIE_NAME))

r = c.post("/capture/submit", json={"text": "Item one\nItem two"})
assert r.status_code == 200, r.text
assert r.json() == {"ok": True, "sent": 2}, r.json()
assert captured == [
    ("Item one", "capture_pwa_v1"),
    ("Item two", "capture_pwa_v1"),
], captured
print("PASS: newline creates two inbox captures")

captured.clear()
r = c.post("/capture/submit", json={"text": "• Item one\n• Item two"})
assert r.status_code == 200, r.text
assert r.json() == {"ok": True, "sent": 2}, r.json()
assert captured == [
    ("Item one", "capture_pwa_v1"),
    ("Item two", "capture_pwa_v1"),
], captured
print("PASS: bullet lines create two clean inbox captures")

captured.clear()
r = c.post("/capture/submit", json={"text": "- Item one\n\n* Item two"})
assert r.status_code == 200, r.text
assert r.json() == {"ok": True, "sent": 2}, r.json()
assert captured == [
    ("Item one", "capture_pwa_v1"),
    ("Item two", "capture_pwa_v1"),
], captured
print("PASS: blank lines and ordinary list markers are handled")

print("RESULT: CAPTURE PWA MULTILINE V1 SMOKE TEST PASSED")
