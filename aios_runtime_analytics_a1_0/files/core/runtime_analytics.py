"""
AIOS Runtime Analytics A1.0

Read-only analytics ledger for execution/evaluator telemetry.
Writes:
- logs/runtime_analytics.csv
- logs/runtime_analytics_latest.json
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _score_band(score: int) -> str:
    try:
        score = int(score or 0)
    except Exception:
        score = 0
    if score <= 3:
        return "low_1_3"
    if score <= 10:
        return "medium_4_10"
    if score <= 25:
        return "high_11_25"
    return "very_high_26_plus"


def _component_pairs(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        components = item.get("evaluator_components") or []
        for component in components:
            name = getattr(component, "name", None)
            score = getattr(component, "score", None)
            if name is not None:
                out.append({"name": str(name), "score": score})
        if out:
            return out

        reasons = item.get("reasons") or []
        for reason in reasons:
            out.append({"name": str(reason), "score": None})
    except Exception as exc:
        out.append({"name": "component_extract_failed", "score": str(exc)})
    return out


def _counter_from_reasons(items: Iterable[Dict[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for item in items:
        for reason in item.get("reasons") or []:
            counter[str(reason)] += 1
    return counter


def _counter_from_score_bands(items: Iterable[Dict[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for item in items:
        counter[_score_band(item.get("score", 0))] += 1
    return counter


def _scoring_sources(items: Iterable[Dict[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for item in items:
        score = item.get("score", 0) or 0
        evaluator_score = item.get("evaluator_score", 0) or 0
        legacy_score = item.get("legacy_score", 0) or 0
        reasons = item.get("reasons") or []

        if reasons == ["baseline_executable"]:
            counter["baseline_fallback"] += 1
        elif evaluator_score and score == evaluator_score:
            counter["evaluator"] += 1
        elif legacy_score and score == legacy_score:
            counter["legacy_fallback"] += 1
        elif evaluator_score:
            counter["evaluator"] += 1
        elif legacy_score:
            counter["legacy_fallback"] += 1
        else:
            counter["zero_signal"] += 1
    return counter


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _ensure_fieldnames(path: Path, fieldnames: List[str]) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()


def write_runtime_analytics(
    ranked: List[Dict[str, Any]],
    winners: List[Dict[str, Any]],
    *,
    project_root: str | None = None,
    run_label: str = "runtime",
) -> Dict[str, Any]:
    """Write one run-level analytics row and latest JSON snapshot.

    Read-only local analytics. No Notion mutations, no ranking changes.
    """
    root = Path(project_root or os.getcwd())
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    score_bands = _counter_from_score_bands(ranked)
    scoring_sources = _scoring_sources(ranked)
    signal_distribution = _counter_from_reasons(ranked)
    bna_signal_distribution = _counter_from_reasons(winners)
    low_signal_bna_count = sum(
        1
        for item in winners
        if (item.get("score", 0) or 0) <= 3 or (item.get("reasons") or []) == ["baseline_executable"]
    )

    bna_details = []
    for idx, item in enumerate(winners, start=1):
        bna_details.append({
            "rank": idx,
            "title": item.get("title", ""),
            "score": item.get("score", 0),
            "reasons": [str(r) for r in (item.get("reasons") or [])],
            "components": _component_pairs(item),
        })

    analytics = {
        "version": "aios-runtime-analytics-a1.0",
        "run_timestamp_utc": now,
        "run_label": run_label,
        "ranked_count": len(ranked),
        "bna_winner_count": len(winners),
        "score_bands": dict(sorted(score_bands.items())),
        "scoring_sources": dict(sorted(scoring_sources.items())),
        "signal_distribution": dict(sorted(signal_distribution.items())),
        "bna_signal_distribution": dict(sorted(bna_signal_distribution.items())),
        "low_signal_bna_count": low_signal_bna_count,
        "bna_titles": [item.get("title", "") for item in winners],
        "bna_details": bna_details,
        "authority_impact": "none",
        "mutations": 0,
        "mode": "read_only_analytics_ledger",
    }

    latest_json = logs_dir / "runtime_analytics_latest.json"
    latest_json.write_text(json.dumps(analytics, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    csv_path = logs_dir / "runtime_analytics.csv"
    fieldnames = [
        "run_timestamp_utc",
        "run_label",
        "ranked_count",
        "bna_winner_count",
        "low_signal_bna_count",
        "score_bands_json",
        "scoring_sources_json",
        "signal_distribution_json",
        "bna_signal_distribution_json",
        "bna_titles_json",
        "authority_impact",
        "mutations",
        "mode",
    ]
    _ensure_fieldnames(csv_path, fieldnames)
    row = {
        "run_timestamp_utc": now,
        "run_label": run_label,
        "ranked_count": len(ranked),
        "bna_winner_count": len(winners),
        "low_signal_bna_count": low_signal_bna_count,
        "score_bands_json": _safe_json(analytics["score_bands"]),
        "scoring_sources_json": _safe_json(analytics["scoring_sources"]),
        "signal_distribution_json": _safe_json(analytics["signal_distribution"]),
        "bna_signal_distribution_json": _safe_json(analytics["bna_signal_distribution"]),
        "bna_titles_json": _safe_json(analytics["bna_titles"]),
        "authority_impact": "none",
        "mutations": 0,
        "mode": "read_only_analytics_ledger",
    }
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writerow(row)

    print("\n=== AIOS RUNTIME ANALYTICS SUMMARY A1.0 ===")
    print(f"[Runtime Analytics] ledger: {csv_path}")
    print(f"[Runtime Analytics] latest_json: {latest_json}")
    print(
        "[Runtime Analytics] execution: "
        f"ranked={len(ranked)}; winners={len(winners)}; low_signal_bna={low_signal_bna_count}"
    )
    print(
        "[Runtime Analytics] score_bands: "
        + ("; ".join(f"{k}={v}" for k, v in sorted(score_bands.items())) or "none")
    )
    print(
        "[Runtime Analytics] bna_signals: "
        + ("; ".join(f"{k}={v}" for k, v in sorted(bna_signal_distribution.items())) or "none")
    )
    print("[Runtime Analytics] authority_impact=none; mutations=0; mode=read_only_analytics_ledger")

    return analytics
