#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
text = (root / "run_aios.py").read_text()
ast.parse(text)

start = text.find("def get_block_text(block):")
end = text.find("# In[15]:", start)
block = text[start:end]

checks = [
    ("canonical get_block_text exists", start >= 0),
    ("callout is supported", '"callout",' in block),
    ("support marker exists", 'CANONICAL_BLOCK_TEXT_CALLOUT_SUPPORT = "callout-text-v1"' in text),
    ("clarification runtime still configures from globals",
     "clarification_helpers.configure_clarification_module(globals())" in text),
]

for label, ok in checks:
    print(f"{'PASS' if ok else 'FAIL'}: {label}")

if not all(ok for _, ok in checks):
    raise SystemExit("RESULT: CANONICAL CALLOUT TEXT SUPPORT VALIDATION FAILED")

print("RESULT: CANONICAL CALLOUT TEXT SUPPORT STRUCTURE VALID")
