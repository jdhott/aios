from pathlib import Path

web = Path('aios/web_capture/app.py').read_text()
checks = [
    ('shared Brain Dump splitter exists', 'def _split_brain_dump(' in web),
    ('capture-many accepts interface', 'capture_interface: str = "cloud_run_web"' in web),
    ('capture-many forwards interface', '_capture_to_aios(line, capture_interface=capture_interface)' in web),
    ('PWA splits multiline input', 'lines = _split_brain_dump(text)' in web),
    ('PWA uses shared capture-many', "_capture_many(lines, capture_interface='capture_pwa_v1')" in web),
    ('PWA reports sent count', "return {'ok': True, 'sent': sent}" in web),
]
for label, ok in checks:
    if not ok:
        raise SystemExit(f'FAIL: {label}')
    print(f'PASS: {label}')
print('RESULT: CAPTURE PWA MULTILINE V1 STRUCTURE VALID')
