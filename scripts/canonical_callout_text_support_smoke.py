#!/usr/bin/env python3
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
run_path = root / "run_aios.py"
text = run_path.read_text()
tree = ast.parse(text)

node = next(
    (
        n for n in tree.body
        if isinstance(n, ast.FunctionDef)
        and n.name == "get_block_text"
    ),
    None,
)
if node is None:
    raise RuntimeError("Canonical get_block_text() not found.")

module = ast.Module(body=[node], type_ignores=[])
ns = {}
exec(compile(module, str(run_path), "exec"), ns)
get_block_text = ns["get_block_text"]

callout = {
    "type": "callout",
    "callout": {
        "rich_text": [
            {
                "plain_text": "Replace the placeholder with your answer, then check it."
            }
        ]
    },
}

value = get_block_text(callout)
expected = "Replace the placeholder with your answer, then check it."

if value != expected:
    raise RuntimeError(f"Canonical callout extraction failed: {value!r}")

clar_text = (root / "aios/clarification.py").read_text()
if '"Replace the placeholder" in get_block_text(block)' not in clar_text:
    raise RuntimeError(
        "Clarification targeted-question detector no longer uses get_block_text()."
    )

print("Canonical callout rich-text extraction: PASS")
print("Clarification detector uses canonical helper: PASS")
print("RESULT: CANONICAL CALLOUT TEXT SUPPORT SMOKE TEST PASSED")
