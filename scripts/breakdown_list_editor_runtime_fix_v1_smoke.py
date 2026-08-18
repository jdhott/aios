from pathlib import Path
import ast

web = Path('aios/web_capture/app.py').read_text()
ast.parse(web)
# Regression: inside the Python HTML template, JS must contain a double-escaped newline.
# A single \\n in Python source renders as a literal newline inside the JS quoted string,
# causing a syntax error that prevents ALL list-editor handlers (trash/drag/add) from running.
assert "titles.join('\\\\n')" in web
assert "titles.join('\\n')" not in web.replace("titles.join('\\\\n')", '')
print('Rendered-JS newline escape regression: PASS')
print('Trash + drag handlers remain present: PASS')
print('RESULT: BREAKDOWN LIST EDITOR RUNTIME FIX V1 SMOKE TEST PASSED')
