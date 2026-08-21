from pathlib import Path
import ast
web=Path('aios/web_capture/app.py').read_text(); api=Path('aios/api/app.py').read_text(); schema=Path('aios/api/schemas.py').read_text()
checks=[('capture route',"@app.get('/capture'" in web),('submit route',"@app.post('/capture/submit')" in web),('manifest','manifest.webmanifest' in web),('service worker','service-worker.js' in web),('draft preservation','localStorage' in web),('desktop shortcut','e.metaKey||e.ctrlKey' in web),('interface schema','capture_interface: str' in schema),('PWA metadata',"capture_interface='capture_pwa_v1'" in web or "capture_interface) or 'capture_pwa_v1'" in web),('API metadata','request.capture_interface' in api)]
bad=False
for label,ok in checks: print(('PASS' if ok else 'FAIL')+': '+label); bad|=not ok
for label,text in [('web',web),('api',api),('schema',schema)]: ast.parse(text); print(label+' parses: PASS')
if bad: raise SystemExit('RESULT: AIOS CAPTURE PWA V1 VALIDATION FAILED')
print('RESULT: AIOS CAPTURE PWA V1 STRUCTURE VALID')
