"""Small behavior smoke for the V1 breakdown policy without network calls."""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]
source = (root / "run_aios.py").read_text()

# Policy-level assertions are intentionally independent of OpenAI/network calls.
assert "return \"uncertain\"" in source[source.index("def rule_based_breakdown_decision"):source.index("def decide_breakdown")]
print("Broad/process wording requires confidence layer: PASS")

prompt = source[source.index("def ask_ai_breakdown_decision"):source.index("def ask_ai_quick_win")]
assert "ALL are true" in prompt
assert "When uncertain, return no" in prompt
assert "generic, obvious, or mostly procedural filler" in prompt
print("Automatic breakdown threshold is conservative: PASS")

generator = source[source.index("def generate_subtasks"):source.index("def clean_subtasks")]
assert "2–5" in generator
assert "Prefer fewer meaningful steps" in generator
assert "manual_context" in generator
print("Manual proposal supports guidance and small useful sets: PASS")

# Parse the changed runtime files to catch syntax issues without importing the processor.
for rel in ["run_aios.py", "aios/api/app.py", "aios/web_capture/app.py", "aios/storage/task_creation_writer.py"]:
    ast.parse((root / rel).read_text())
print("Changed Python files parse: PASS")
print("RESULT: MANUAL BREAKDOWN PROPOSAL V1 SMOKE TEST PASSED")
