from pathlib import Path

text = Path("aios/project_work.py").read_text()

assert "Proposed tasks must represent DISTINCT gaps" in text
assert "project name or project type by itself is NOT evidence" in text
assert "Project Work is a PROJECT PLAN, not a Best Next Action list" in text
assert "Compare the candidate tasks with EACH OTHER" in text
assert "When uncertain whether the NEED for the task is grounded, REJECT" in text
assert "[Project Work][Generator]" in text
assert "[Project Work][Validator]" in text

print("Sibling semantic dedup guidance: PASS")
print("Generic-work grounding tightened: PASS")
print("Project-plan sequencing semantics: PASS")
print("Diagnostics retained: PASS")
print("RESULT: PROJECT WORK GROUNDING TUNING V3 SMOKE TEST PASSED")
