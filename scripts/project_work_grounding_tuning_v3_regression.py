from pathlib import Path

text = Path("aios/project_work.py").read_text()

expected = [
    "Treat the Known project context as authoritative facts, decisions, and constraints.",
    "Current open work is ALREADY PLANNED.",
    "An unresolved fact may itself justify a task to resolve that uncertainty.",
    "Do NOT reject a task merely because information is unresolved",
    "Project Work is a PROJECT PLAN, not a Best Next Action list.",
    "Compare the candidate tasks with EACH OTHER.",
]

for marker in expected:
    assert marker in text, marker

print("Context authority retained: PASS")
print("Open-work duplicate guard retained: PASS")
print("Uncertainty-resolution work retained: PASS")
print("Grounding validator retained: PASS")
print("V3 project-plan semantics retained: PASS")
print("RESULT: PROJECT WORK GROUNDING V3 REGRESSION MARKERS PASSED")
