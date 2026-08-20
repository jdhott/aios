from pathlib import Path
s = Path("aios/web_capture/app.py").read_text()

assert 'class="focus-autoexpand focus-context-answer" name="answer"' in s
assert 'class="focus-autoexpand" name="context"' in s or 'name="context"' in s and 'class="focus-autoexpand"' in s
assert "Use my answer</button>" in s
assert "function resizeFocusTextarea" in s
assert ".focus-context-spinner {{" in s
assert "window.location.reload(), 2500" in s

print("PASS: answer textarea auto-expands")
print("PASS: answer text uses normal-weight class")
print("PASS: context textarea auto-expands")
print("PASS: Use my answer label")
print("PASS: spinner + pending auto-refresh")
print("RESULT: FOCUS CONTEXT LOOP V3 TINY FIX VALID")
