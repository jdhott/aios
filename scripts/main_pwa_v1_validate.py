from pathlib import Path
s=Path("aios/web_capture/app.py").read_text()
checks=[
("version",'WEB_MAIN_PWA_VERSION = "main-pwa-v1"' in s),
("manifest link",'<link rel="manifest" href="/manifest.webmanifest">' in s),
("standalone metadata",'apple-mobile-web-app-capable' in s),
("SW registration",'navigator.serviceWorker.register("/service-worker.js"' in s),
("manifest route","@app.get('/manifest.webmanifest')" in s),
("SW route","@app.get('/service-worker.js')" in s),
("root start",'"start_url": "/"' in s),
("standalone",'"display": "standalone"' in s),
("capture excluded",'u.pathname.startsWith("/capture/")' in s),
("network authority",'Dynamic/authenticated AIOS HTML and data stay network-authoritative' in s),
("capture PWA retained",'_CAPTURE_PWA_MANIFEST' in s and '/capture/service-worker.js' in s)]
for label,ok in checks: assert ok,f"FAIL: {label}"; print(f"PASS: {label}")
for f in ('aios-32.png','aios-192.png','aios-512.png'):
 assert (Path('aios/web_capture/static')/f).exists(),f"FAIL: {f}"; print(f"PASS: {f}")
print('RESULT: MAIN AIOS PWA V1 STRUCTURE VALID')
