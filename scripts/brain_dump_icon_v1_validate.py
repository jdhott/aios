from pathlib import Path
import ast

text = Path("aios/web_capture/app.py").read_text()

checks = [
    ("favicon link", 'href="/capture/favicon.png"' in text),
    ("apple touch icon", 'href="/capture/icon-192.png"' in text),
    ("192 manifest icon", '"src": "/capture/icon-192.png"' in text),
    ("512 manifest icon", '"src": "/capture/icon-512.png"' in text),
    ("favicon route", "@app.get('/capture/favicon.png')" in text),
    ("192 route", "@app.get('/capture/icon-192.png')" in text),
    ("512 route", "@app.get('/capture/icon-512.png')" in text),
]

failed = False

for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    failed |= not ok

for size in (32, 192, 512):
    p = Path("aios/web_capture/static") / f"brain-dump-{size}.png"
    ok = p.exists() and p.stat().st_size > 0
    print(("PASS" if ok else "FAIL") + f": {size}px icon asset exists")
    failed |= not ok

ast.parse(text)
print("web_capture app parses: PASS")

if failed:
    raise SystemExit("RESULT: BRAIN DUMP ICON V1 VALIDATION FAILED")

print("RESULT: BRAIN DUMP ICON V1 STRUCTURE VALID")
