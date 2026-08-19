import os
os.environ.setdefault('AIOS_WEB_USERNAME','test'); os.environ.setdefault('AIOS_WEB_PASSWORD','test')
from fastapi.testclient import TestClient
import aios.web_capture.app as web
web._capture_to_aios=lambda text,capture_interface='': {'id':'capture-1'}
c=TestClient(web.app); auth=('test','test')
r=c.get('/capture',auth=auth); assert r.status_code==200 and 'Brain Dump' in r.text and 'localStorage' in r.text
r=c.get('/capture/manifest.webmanifest'); assert r.status_code==200 and 'standalone' in r.text
r=c.get('/capture/service-worker.js'); assert r.status_code==200 and 'aios-capture-v1' in r.text
r=c.post('/capture/submit',auth=auth,json={'text':'Buy milk'}); assert r.status_code==200 and r.json()['ok'] is True
print('Capture screen renders: PASS'); print('Manifest + service worker render: PASS'); print('Canonical capture submit: PASS'); print('RESULT: AIOS CAPTURE PWA V1 SMOKE TEST PASSED')
