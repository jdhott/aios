from pathlib import Path
import ast
s=Path("aios/web_capture/app.py").read_text(); ast.parse(s)
a=s.index('_MAIN_SERVICE_WORKER'); b=s.index('_CAPTURE_PWA_MANIFEST',a); sw=s[a:b]
assert 'STATIC=[' in sw and 'if(!STATIC.includes(u.pathname))return;' in sw
assert 'u.pathname==="/capture"' in sw
assert '"/"' not in sw[sw.index('STATIC=['):sw.index('];',sw.index('STATIC=['))]
print('PASS: static PWA assets only are cached')
print('PASS: dynamic dashboard/task data are not cached')
print('PASS: Brain Dump PWA remains separately scoped')
print('RESULT: MAIN AIOS PWA V1 SMOKE TEST PASSED')
