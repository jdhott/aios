from __future__ import annotations

import json
import os
from difflib import SequenceMatcher
from typing import Any

from aios.text_utils import normalize, words_in


DUPLICATE_AUTO_MIN_CONFIDENCE = float(
    os.getenv("DUPLICATE_AUTO_MIN_CONFIDENCE", "0.92")
)

DUPLICATE_REVIEW_MIN_CONFIDENCE = float(
    os.getenv("DUPLICATE_REVIEW_MIN_CONFIDENCE", "0.72")
)

DUPLICATE_CANDIDATE_LIMIT = 3


def _lexical_similarity(a: str, b: str) -> float:
    normalized_a = normalize(str(a or ""))
    normalized_b = normalize(str(b or ""))

    if not normalized_a or not normalized_b:
        return 0.0

    sequence_score = SequenceMatcher(
        None,
        normalized_a,
        normalized_b,
    ).ratio()

    tokens_a = set(words_in(normalized_a))
    tokens_b = set(words_in(normalized_b))

    token_score = 0.0

    if tokens_a and tokens_b:
        token_score = (
            len(tokens_a & tokens_b)
            / len(tokens_a | tokens_b)
        )

    return max(sequence_score, token_score)


def find_duplicate_candidates(
    task_title: str,
    existing_tasks: list[dict[str, Any]],
    *,
    limit: int = DUPLICATE_CANDIDATE_LIMIT,
) -> list[dict[str, Any]]:
    """Return the strongest lexical candidates for semantic review."""
    task_title = str(task_title or "").strip()

    scored: list[dict[str, Any]] = []

    for task in existing_tasks or []:
        title = str(task.get("title") or "").strip()

        if not title:
            continue

        scored.append({
            "task": task,
            "title": title,
            "lexical_score": _lexical_similarity(
                task_title,
                title,
            ),
        })

    scored.sort(
        key=lambda item: item["lexical_score"],
        reverse=True,
    )

    return scored[:max(1, int(limit))]


def judge_duplicate(
    client,
    *,
    task_title: str,
    existing_tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Determine whether a new task duplicates an existing open task.

    Non-exact lexical similarity is candidate retrieval only.
    Semantic equivalence determines duplicate state.
    """
    task_title = str(task_title or "").strip()

    if not task_title:
        return {
            "state": "distinct",
            "task": None,
            "confidence": 0.0,
            "reason": "No task title supplied.",
        }

    normalized = normalize(task_title)

    # Exact normalized equality is deterministic.
    for task in existing_tasks or []:
        existing_title = str(task.get("title") or "").strip()

        if (
            existing_title
            and normalize(existing_title) == normalized
        ):
            return {
                "state": "duplicate",
                "task": task,
                "confidence": 1.0,
                "reason": "Exact normalized task-title match.",
            }

    candidates = find_duplicate_candidates(
        task_title,
        existing_tasks,
    )

    # Avoid an AI call when there is no remotely plausible lexical candidate.
    candidates = [
        candidate
        for candidate in candidates
        if candidate["lexical_score"] >= 0.35
    ]

    if not candidates or client is None:
        return {
            "state": "distinct",
            "task": None,
            "confidence": 0.0,
            "reason": "No plausible existing-task candidate.",
        }

    candidate_by_key: dict[str, dict[str, Any]] = {}
    candidate_lines = []

    for index, candidate in enumerate(candidates, start=1):
        key = f"T{index:02d}"
        candidate_by_key[key] = candidate

        candidate_lines.append(
            f"{key} | {candidate['title']}"
        )

    prompt = f"""Determine whether a NEW task is actually the same intended
executable action as one of the EXISTING open tasks.

NEW TASK:
{task_title}

EXISTING TASK CANDIDATES:
{chr(10).join(candidate_lines)}

Return ONLY raw JSON:

{{
  "match": {{
    "task_key": "T01",
    "confidence": 0.0,
    "reason": "..."
  }}
}}

or:

{{"match": null}}

Rules:
- A duplicate means the new task and existing task represent substantially
  the SAME intended executable action or same unfinished result.
- Judge meaning, not wording. Synonymous verbs and nouns can describe the
  same action. For example, "check" vs "review", "book" vs "schedule", and
  "problems" vs "issues" should not prevent a duplicate match when the
  underlying action is the same.
- Ask this practical question: if one task were completed, would the other
  normally become unnecessary because it represents the same work?
- Tasks that are merely related, sequential, prerequisites, follow-ups,
  subtasks, or part of the same project are NOT duplicates.
- Do not merge two independently useful actions merely because they concern
  the same person, object, project, appointment, purchase, or topic.
- Do not infer missing identity or scope. If one task names a specific entity
  and the other is generic, do not assume they refer to the same entity unless
  the supplied wording establishes that. Treat plausible-but-unproven identity
  as uncertainty rather than a high-confidence duplicate.
- Use high confidence only when the same-action interpretation is directly
  supported by the supplied task wording.
- Prefer a lower-confidence match over a high-confidence match when the tasks
  may be the same but require an unstated assumption.

Confidence calibration:
- 0.92 to 1.00: The wording directly supports that these are the same
  executable action. Completing one would clearly make the other unnecessary.
- 0.72 to 0.91: They plausibly represent the same action, but an unstated
  assumption about identity, scope, timing, or intent is required.
- Below 0.72: Do not return a match unless there is still meaningful ambiguity;
  normally return null when the actions are distinct.
- Synonymous wording alone is NOT uncertainty. If "review" vs "check" and
  "problems" vs "issues" are the only differences and the action/object are
  otherwise the same, use high confidence.
- A specific-vs-generic entity mismatch IS uncertainty when the wording does
  not establish that both refer to the same entity.

- Return null when the actions are meaningfully different.
"""

    model = os.getenv(
        "AIOS_DUPLICATE_MODEL",
        "gpt-4.1-mini",
    )

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
        )

        raw = str(
            getattr(response, "output_text", "")
            or ""
        ).strip()

        if raw.startswith("```"):
            raw = raw.strip("`")

            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        data = json.loads(raw)

    except Exception as exc:
        print("[Duplicate Detection] AI error:", exc)

        # Fail open: do not suppress creation because AI failed.
        return {
            "state": "distinct",
            "task": None,
            "confidence": 0.0,
            "reason": "Semantic duplicate judgment failed.",
        }

    match = data.get("match")

    if not isinstance(match, dict):
        return {
            "state": "distinct",
            "task": None,
            "confidence": 0.0,
            "reason": "No semantic duplicate identified.",
        }

    key = str(match.get("task_key") or "").strip()

    if key not in candidate_by_key:
        return {
            "state": "distinct",
            "task": None,
            "confidence": 0.0,
            "reason": "Semantic judgment returned an unknown task.",
        }

    try:
        confidence = float(
            match.get("confidence") or 0.0
        )
    except (TypeError, ValueError):
        confidence = 0.0

    candidate = candidate_by_key[key]

    reason = str(
        match.get("reason") or ""
    ).strip()

    if confidence >= DUPLICATE_AUTO_MIN_CONFIDENCE:
        state = "duplicate"

    elif confidence >= DUPLICATE_REVIEW_MIN_CONFIDENCE:
        state = "possible_duplicate"

    else:
        state = "distinct"

    return {
        "state": state,
        "task": candidate["task"],
        "confidence": confidence,
        "reason": reason,
        "lexical_score": candidate["lexical_score"],
    }
