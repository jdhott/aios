from pathlib import Path
import ast

text = Path("aios/project_work.py").read_text()

checks = [
    ("generator requires distinct gaps", "Proposed tasks must represent DISTINCT gaps" in text),
    ("generator removes sibling overlap", "return only the clearest and most useful one" in text),
    ("project type is not grounding", "project name or project type by itself is NOT evidence" in text),
    ("validator requires explicit need basis", "identify the explicit basis for its need" in text),
    ("validator rejects generic conventional work", "even if the task would normally be sensible" in text),
    ("project-plan distinction present", "Project Work is a PROJECT PLAN, not a Best Next Action list" in text),
    ("sibling dependencies allowed", "Dependencies between sibling project tasks are allowed" in text),
    ("downstream rejection narrowed", "could make the task unnecessary or materially change what the task should be" in text),
    ("candidate-to-candidate comparison", "Compare the candidate tasks with EACH OTHER" in text),
    ("overlap keeps one", "approve only one" in text and "overlapping sibling work" in text),
    ("grounding fail-closed retained", "When uncertain whether the NEED for the task is grounded, REJECT" in text),
]

failed = False
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    failed |= not ok

ast.parse(text)
print("project_work parses: PASS")

if failed:
    raise SystemExit("RESULT: PROJECT WORK GROUNDING TUNING V3 VALIDATION FAILED")

print("RESULT: PROJECT WORK GROUNDING TUNING V3 STRUCTURE VALID")
