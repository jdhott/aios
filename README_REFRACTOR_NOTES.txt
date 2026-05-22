AIOS package-aware project module refactor — 2026-05-11

Install layout:
- run_aios.py -> project root
- sync_reminders_to_notion.py -> project root
- aios/__init__.py -> aios package folder
- aios/classification.py -> aios package folder
- aios/text_utils.py -> aios package folder
- aios/projects.py -> aios package folder

Key import update:
- run_aios.py now imports project helpers with:
  from aios import projects as project_helpers

Validation performed:
- python -m py_compile run_aios.py sync_reminders_to_notion.py aios/*.py
- TEST_ONLY=true python run_aios.py --test-only
