from pathlib import Path
from datetime import datetime
import shutil
import sys

ROOT = Path.cwd()
TARGET = ROOT / "execution_engine_v2.py"
STAMP = ROOT / ".last_evaluator_tuning_telemetry_d1_2_1_backup"
MARKER = "Evaluator Tuning Telemetry D1.2.1"

if not TARGET.exists():
    print(f"ERROR: target not found: {TARGET}")
    sys.exit(1)

text = TARGET.read_text()

required_installed = [
    MARKER,
    "def format_bna_component_breakdown",
    '"evaluator_components": orchestration.evaluator_components',
    "format_bna_component_breakdown(item)",
]
if all(item in text for item in required_installed):
    print("AIOS Evaluator Tuning Telemetry D1.2.1 already installed")
    sys.exit(0)

backup_dir = ROOT / f".evaluator_tuning_telemetry_d1_2_1_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
backup_dir.mkdir(exist_ok=False)
shutil.copy2(TARGET, backup_dir / TARGET.name)
STAMP.write_text(str(backup_dir))

# Make the visible section header current when D1.1 telemetry exists.
text = text.replace("EVALUATOR TUNING TELEMETRY — D1.1", "EVALUATOR TUNING TELEMETRY — D1.2.1")
text = text.replace('print("\\n--- Evaluator Tuning Telemetry D1.1 ---")', 'print("\\n--- Evaluator Tuning Telemetry D1.2.1 ---")')
text = text.replace('print("\\\\n--- Evaluator Tuning Telemetry D1.1 ---")', 'print("\\\\n--- Evaluator Tuning Telemetry D1.2.1 ---")')
text = text.replace("Evaluator Tuning Telemetry D1.2", "Evaluator Tuning Telemetry D1.2.1")

# Insert a durable marker comment near the top. This avoids smoke-test ambiguity if
# the D1.1 aggregate telemetry lives in a different helper/versioned section.
if MARKER not in text:
    module_banner = 'print("=== FULL EVALUATOR RANKING AUTHORITY ACTIVE ===")\n'
    marker_line = f'\n# {MARKER}: read-only per-BNA component breakdown.\n'
    if module_banner in text:
        text = text.replace(module_banner, module_banner + marker_line, 1)
    else:
        text = marker_line + text

# Insert helper after format_ranking_components.
if "def format_bna_component_breakdown" not in text:
    helper_anchor = '''def format_ranking_components(components):\n\n    if not components:\n        return "[]"\n\n    return "[" + ", ".join(\n        f"{c.name}(+{c.score})"\n        for c in components\n    ) + "]"\n'''
    helper = helper_anchor + '''\n\ndef format_bna_component_breakdown(item):\n    """Return compact per-BNA component telemetry for tuning review.\n\n    Read-only observation only. This explains the score already assigned in\n    memory and does not influence ranking, persistence, or mutations.\n    """\n    try:\n        components = item.get("evaluator_components") or []\n        if components:\n            return "; ".join(\n                f"{component.name}={component.score}"\n                for component in components\n            )\n\n        reasons = item.get("reasons") or []\n        score = item.get("score", 0) or 0\n\n        if reasons == ["baseline_executable"]:\n            return "baseline_executable=1"\n\n        if reasons:\n            return "; ".join(\n                f"{reason}=unscored"\n                for reason in reasons\n            )\n\n        return f"zero_signal={score}"\n\n    except Exception as e:\n        return f"component_breakdown_unavailable={e}"\n'''
    if helper_anchor not in text:
        print("ERROR: could not locate format_ranking_components anchor")
        sys.exit(1)
    text = text.replace(helper_anchor, helper, 1)

# Carry evaluator component objects into ranked items.
if '"evaluator_components": orchestration.evaluator_components' not in text:
    rank_anchor = '''                "reasons": reasons,\n                "legacy_score": orchestration.legacy_score,\n'''
    rank_replacement = '''                "reasons": reasons,\n                "evaluator_components": orchestration.evaluator_components,\n                "legacy_score": orchestration.legacy_score,\n'''
    if rank_anchor not in text:
        print("ERROR: could not locate ranked item anchor")
        sys.exit(1)
    text = text.replace(rank_anchor, rank_replacement, 1)

# Print component breakdown below each BNA.
if "format_bna_component_breakdown(item)" not in text:
    bna_anchor = '''        print(\n            f"BNA rank={idx} "\n            f"score={item['score']} "\n            f"title={item['title']}"\n        )\n'''
    bna_replacement = bna_anchor + '''        print(\n            "  components: "\n            f"{format_bna_component_breakdown(item)}"\n        )\n'''
    if bna_anchor not in text:
        print("ERROR: could not locate BNA print anchor")
        sys.exit(1)
    text = text.replace(bna_anchor, bna_replacement, 1)

TARGET.write_text(text)
print("Installed AIOS Evaluator Tuning Telemetry D1.2.1")
print(f"Backup: {backup_dir}")
print("Next: bash aios_evaluator_tuning_telemetry_d1_2_1/smoke_test.sh")
