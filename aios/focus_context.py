from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

FOCUS_CONTEXT_HELP_VERSION = "focus-context-help-v2"


def _resolve_task(store, task: dict[str, Any]) -> dict[str, Any] | None:
    task_id = str(task.get("id") or "").strip()
    if not task_id:
        return None
    fields = (
        "id,title,context,project_id,legacy_notion_id,"
        "focus_context_help_state,focus_context_draft,focus_context_question,"
        "focus_context_answer"
    )
    rows = store.client.table("tasks").select(fields).eq("id", task_id).limit(1).execute().data or []
    if rows:
        return dict(rows[0])
    rows = store.client.table("tasks").select(fields).eq("legacy_notion_id", task_id).limit(1).execute().data or []
    return dict(rows[0]) if rows else None


def _project_context(store, project_id: str | None) -> str:
    project_id = str(project_id or "").strip()
    if not project_id:
        return ""
    rows = store.client.table("projects").select("context").eq("id", project_id).limit(1).execute().data or []
    return str(rows[0].get("context") or "").strip() if rows else ""


def _json_response(client, prompt: str) -> dict[str, str] | None:
    if client is None:
        return None
    model = os.getenv("AIOS_FOCUS_GUIDANCE_MODEL", "gpt-4.1-mini")
    try:
        response = client.responses.create(model=model, input=prompt)
        raw = (response.output_text or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        data = json.loads(raw)
        return {
            "draft_context": str(data.get("draft_context") or "").strip()[:2000],
            "question": str(data.get("question") or "").strip()[:500],
        }
    except Exception as exc:
        print(f"[Focus Context] AI generation failed: {exc}")
        return None


def generate_focus_context_help(client, *, title: str, task_context: str = "", project_context: str = "") -> dict[str, str] | None:
    prompt = f'''Help the user improve durable Task Context so AIOS can generate a better immediate starting action.

Task:
{title}

Existing Task Context:
{task_context or "(none)"}

Relevant Project Context:
{project_context or "(none)"}

Return JSON only:
{{"draft_context":"...","question":"..."}}

Rules:
- Task Context is durable supporting information: decisions, constraints, current state, what is already done/decided, or what remains relevant.
- Treat existing Task Context and Project Context as authoritative.
- Never invent facts, decisions, people, dates, tools, preferences, or constraints.
- draft_context must preserve useful existing Task Context.
- You may incorporate Project Context only when it is clearly relevant to this task.
- Keep draft_context concise and useful; do not rewrite into impersonal third-person prose merely for style.
- Ask exactly one targeted question whose answer would most improve AIOS's ability to suggest a useful next starting action.
- Do not ask for information already present in the supplied context.
- If the supplied context is already sufficient, question may be an empty string.
- If there is not enough grounded information to draft useful context, draft_context may be empty; use the question to uncover the missing information.
'''
    return _json_response(client, prompt)


def generate_focus_context_from_answer(client, *, title: str, task_context: str, project_context: str, draft_context: str, question: str, answer: str) -> dict[str, str] | None:
    prompt = f'''Update an editable Task Context draft using the user's answer to one coaching question.

Task:
{title}

Durable Task Context before coaching:
{task_context or "(none)"}

Relevant Project Context:
{project_context or "(none)"}

Current editable draft:
{draft_context or task_context or "(none)"}

Question AIOS asked:
{question}

User's answer:
{answer}

Return JSON only:
{{"draft_context":"...","question":"..."}}

Rules:
- Incorporate the user's answer intelligently into the editable draft; do not merely append a Q&A transcript.
- Preserve useful facts, decisions, constraints, and current state already present.
- Treat the user's answer as authoritative.
- Never invent facts or silently change the user's meaning.
- Keep the draft natural and concise. First-person wording is fine when it preserves the user's voice.
- Ask one new targeted question only if an important ambiguity still blocks a useful immediate next action; otherwise return an empty question.
- The result is still only a draft. It does not become durable Task Context until the user saves it.
'''
    return _json_response(client, prompt)


def ensure_focus_context_help(store, client, execution_task: dict[str, Any]) -> dict[str, Any] | None:
    resolved = _resolve_task(store, execution_task)
    state = str((resolved or {}).get("focus_context_help_state") or "")
    if not resolved or state not in {"pending", "answer_pending"}:
        return None
    task_id = str(resolved["id"])
    title = str(resolved.get("title") or "").strip() or "Untitled task"
    task_context = str(resolved.get("context") or "").strip()
    project_context = _project_context(store, resolved.get("project_id"))
    if state == "answer_pending":
        answer = str(resolved.get("focus_context_answer") or "").strip()
        question = str(resolved.get("focus_context_question") or "").strip()
        if not answer or not question:
            generated = None
        else:
            generated = generate_focus_context_from_answer(
                client, title=title, task_context=task_context, project_context=project_context,
                draft_context=str(resolved.get("focus_context_draft") or "").strip(),
                question=question, answer=answer,
            )
    else:
        generated = generate_focus_context_help(
            client, title=title, task_context=task_context, project_context=project_context,
        )
    now = datetime.now(timezone.utc).isoformat()
    if not generated:
        store.client.table("tasks").update({"focus_context_help_state": "idle", "focus_context_answer": None, "focus_context_help_updated_at": now}).eq("id", task_id).execute()
        return None
    store.client.table("tasks").update({
        "focus_context_help_state": "ready",
        "focus_context_draft": generated["draft_context"] or None,
        "focus_context_question": generated["question"] or None,
        "focus_context_answer": None,
        "focus_context_help_updated_at": now,
    }).eq("id", task_id).execute()
    print(f"[Focus Context] Prepared context help for: {title}")
    return generated
