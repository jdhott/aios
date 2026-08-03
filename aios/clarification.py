"""Clarification UI and selection workflow helpers for AIOS.

This module is intentionally thin: the functions below were extracted from
run_aios.py without behavioural changes. configure_clarification_module()
injects the runtime dependencies supplied by run_aios.py so the extraction can
stay conservative while the rest of the codebase is modularized.
"""


def configure_clarification_module(namespace):
    """Provide run_aios runtime globals used by the clarification helpers."""
    globals().update(namespace)


def is_command_checkbox(text):
    text = text.strip()
    return (
        GENERATE_MORE_COMMAND in text
        or ADD_OWN_OPTION_COMMAND in text
        or ASK_TARGETED_QUESTION_COMMAND in text
    )


def clarification_mode_reason(task_title):
    """Return (mode, reason) for clarification generation telemetry.

    Analytical mode is for evaluation/audit tasks. It should generate
    outcome-producing first steps, not prerequisite-gathering steps.
    """
    route = clarification_route(task_title, allow_ai=True)
    if route == "define_context":
        return "define_context", "route_define_context"

    text = (task_title or "").lower().strip()
    analytical_terms = [
        "audit", "validate", "validation", "compare", "review", "analyze",
        "analyse", "inspect", "diagnose", "investigate", "verify", "confirm",
        "reconcile", "reconciliation", "rank", "ranking", "rankings", "metadata",
        "telemetry", "log", "logs", "report", "reports", "dashboard",
        "anomaly", "anomalies", "discrepancy", "discrepancies", "governance",
        "ontology", "baseline", "score", "scoring", "quality", "health",
        "regression", "regressions", "drift", "stability",
    ]
    analytical_prefixes = (
        "aios:", "audit ", "validate ", "verify ", "review ", "compare ",
        "inspect ", "analyze ", "analyse ", "diagnose ",
    )

    if text.startswith(analytical_prefixes):
        return "analytical", "analytical_prefix"

    matches = [term for term in analytical_terms if term in text]
    if matches:
        return "analytical", "analytical_terms=" + ",".join(matches[:4])

    return "procedural", "default_procedural"


def clarification_mode(task_title):
    """Return the clarification generation mode for a task title."""
    return clarification_mode_reason(task_title)[0]


def clarification_prompt_for_mode(task_title):
    mode, reason = clarification_mode_reason(task_title)
    print(f"[Clarification Mode] version={CLARIFICATION_ANALYTICAL_MODE_VERSION}; mode={mode}; reason={reason}; task={task_title}")
    if mode == "define_context":
        return DEFINE_PROMPT
    if mode == "analytical":
        return ANALYTICAL_CHOOSE_PROMPT
    return CHOOSE_PROMPT


def clean_clarification_suggestions(raw_suggestions, mode, task_title):
    """Normalize and guard clarification suggestions.

    Prompting alone was allowing analytical tasks to degrade into tool-centric
    preparation steps such as retrieve/open/download. This post-filter keeps
    analytical options focused on outcomes: findings, discrepancies, anomalies,
    or decisions.
    """
    cleaned = []
    seen = set()
    banned_analytical_prefixes = (
        "access ", "retrieve ", "download ", "open ", "locate ", "find the ",
        "gather ", "collect ", "prepare ", "create a spreadsheet",
        "make a spreadsheet", "export ", "pull ", "get the ",
    )

    for item in raw_suggestions:
        s = (item or "").strip().strip("-•0123456789. ").strip()
        if not s:
            continue
        low = s.lower()
        if mode == "analytical" and low.startswith(banned_analytical_prefixes):
            print(f"[Clarification Filter] dropped_non_outcome_step={s}")
            continue
        if low in seen:
            continue
        seen.add(low)
        cleaned.append(s)

    if mode == "analytical" and len(cleaned) < 2:
        fallback = [
            "Review top-ranked tasks for obvious scoring anomalies",
            "Compare top-ranked tasks against their underlying metadata",
            "Identify rankings inconsistent with Urgency, Importance, or Due Date",
            "Document the first ranking discrepancy found",
        ]
        for s in fallback:
            low = s.lower()
            if low not in seen:
                cleaned.append(s)
                seen.add(low)
            if len(cleaned) >= 4:
                break
        print(f"[Clarification Fallback] analytical_defaults_applied; task={task_title}")

    limit = 5 if mode != "analytical" else 4
    return cleaned[:limit]

def append_clarification_blocks(page_id, original_task, suggestions):
    """Render a proposal-first clarification UI in Notion.

    The first checkbox contains the AI's proposed clarified task. The user may
    edit that checkbox text directly before checking it, so the checked text is
    always the answer AIOS consumes. A separate command requests one targeted
    question only when the proposal is not useful.

    This function is intentionally idempotent: if a clarification UI is already
    present on the page, do not append a second copy. Rebuild flows clear the
    existing children first, then call this function.
    """
    existing_blocks = get_block_children(page_id)
    if any(
        block.get("type") == "heading_3"
        and get_block_text(block) == CLARIFY_HEADER
        for block in existing_blocks
    ):
        print("Clarification UI already present; skipping duplicate append")
        return {"results": existing_blocks}

    proposal = suggestions[0].strip() if suggestions else original_task.strip()
    proposal_text = f"{USE_SUGGESTION_PREFIX}{proposal}"

    children = [
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": CLARIFY_HEADER}}]
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": f"Original: {original_task}"}}]
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "AIOS suggests this clearer next action:"}}]
            },
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": proposal_text}}],
                "checked": False,
            },
        },
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "✏️"},
                "rich_text": [{
                    "type": "text",
                    "text": {"content": "To change it, edit the checkbox text above, then check it. AIOS uses the exact checked text."},
                }],
            },
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": ASK_TARGETED_QUESTION_COMMAND}}],
                "checked": False,
            },
        },
    ]

    response = requests.patch(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=headers,
        json={"children": children},
        timeout=30,
    )

    if response.ok:
        increment_summary("clarification_blocks_added")
        print("Added proposal-first clarification blocks")
        return response.json()

    increment_summary("errors")
    print("ERROR adding clarification blocks")
    print(response.status_code, response.text)
    return None


def get_checked_clarification_action(page_id):
    blocks = get_block_children(page_id)

    for block in blocks:
        if block.get("type") != "to_do":
            continue

        todo = block.get("to_do", {})

        if not todo.get("checked"):
            continue

        text = get_block_text(block)

        if not text:
            continue

        if is_command_checkbox(text):
            return {
                "type": "command",
                "text": text,
                "block_id": block["id"],
            }

        return {
            "type": "action",
            "text": text,
            "block_id": block["id"],
        }

    return None


# In[52]:


def generate_clarification_suggestions(task_title):
    """Generate one strong clarified-task proposal.

    The list return type is retained for backward compatibility with callers
    and older package code, but proposal-first V2 intentionally returns only
    one suggestion.
    """
    mode, reason = clarification_mode_reason(task_title)
    print(f"[Clarification] version={CLARIFICATION_ANALYTICAL_MODE_VERSION}; mode={mode}; reason={reason}; task={task_title}")

    prompt = f"""
Rewrite the task below as one clear, useful next action.

Rules:
- Preserve the user's intent; do not invent facts, people, deadlines, tools, or constraints
- Make the outcome or decision clearer
- Prefer a concrete action the user can recognize and accept
- Do not turn it into a question
- Do not explain your reasoning
- Use one sentence only
- Keep it concise, normally under 20 words
- If the task is analytical, make the first evaluative outcome explicit
- If the task is broad, clarify the decision or planning outcome without guessing missing specifics

Task: {task_title}
"""

    try:
        response = client.responses.create(model="gpt-4.1-mini", input=prompt)
        proposal = response.output_text.strip().strip('"').strip()
        proposal = proposal.splitlines()[0].strip("-•0123456789. ").strip()
        if not proposal:
            return []
        print("[Clarification] proposal_generated=1")
        return [proposal]
    except Exception as e:
        print("AI clarification proposal generation failed:", e)
        return []


def generate_targeted_clarification_question(task_title):
    """Generate exactly one high-leverage question for a rejected proposal."""
    prompt = f"""
Ask exactly one concise question whose answer would let you rewrite this task
as a clear next action.

Rules:
- Ask only for the single most important missing fact
- Do not provide options
- Do not ask multiple questions
- Keep it under 14 words
- End with a question mark
- No explanation or extra text

Task: {task_title}
"""
    try:
        response = client.responses.create(model="gpt-4.1-mini", input=prompt)
        question = response.output_text.strip().splitlines()[0].strip("-•0123456789. ").strip()
        if question and not question.endswith("?"):
            question += "?"
        return question
    except Exception as e:
        print("AI targeted clarification question failed:", e)
        return "What important detail is missing from this task?"


def get_existing_clarification_suggestions(page_id):
    """Return non-command checkbox text, stripping the V2 display prefix."""
    blocks = get_block_children(page_id)
    suggestions = []
    for block in blocks:
        if block.get("type") != "to_do":
            continue
        text = get_block_text(block)
        if not text or is_command_checkbox(text):
            continue
        if text.startswith(USE_SUGGESTION_PREFIX):
            text = text[len(USE_SUGGESTION_PREFIX):].strip()
        suggestions.append(text)
    return suggestions


def generate_more_clarification_suggestions(task_title, existing_suggestions):
    existing_text = "\n".join(f"- {s}" for s in existing_suggestions)
    mode, reason = clarification_mode_reason(task_title)
    print(f"[Clarification] generate_more version={CLARIFICATION_ANALYTICAL_MODE_VERSION}; mode={mode}; reason={reason}; existing={len(existing_suggestions)}; task={task_title}")

    if mode == "define_context":
        prompt = f"""
Generate 2–3 additional clarification questions for this task that needs more context.

Rules:
- Do not repeat or lightly rephrase existing questions
- Each line must be a short question
- Focus on WHO, WHAT, or CONTEXT
- Do not suggest actions like email, call, or text
- Do not include numbering or bullets
- No extra text

Task: {task_title}

Existing questions:
{existing_text}
"""
    elif mode == "analytical":
        prompt = f"""
Generate 2–3 additional outcome-producing analytical first steps for this task.

Rules:
- Do not repeat or lightly rephrase existing suggestions
- Each option must produce an evaluative outcome, finding, discrepancy, anomaly, or decision
- Do NOT split one evaluation into separate options for each field or keyword
- Do NOT suggest merely accessing, retrieving, downloading, opening, preparing, or creating a spreadsheet unless explicitly requested
- Start with a verb
- Be immediately executable
- Keep each option under 14 words
- Do not include numbering or bullets
- No extra text

Task: {task_title}

Existing suggestions:
{existing_text}
"""
    else:
        prompt = f"""
Generate 2–3 additional clear, concrete next actions for this task.

Rules:
- Do not repeat or lightly rephrase existing suggestions
- Each option must be one concrete physical action only
- Do not combine actions with “and,” “then,” “after,” or multiple verbs
- Start with a verb
- Be immediately executable
- Keep each option under 12 words
- Do not include numbering or bullets
- Use they/them pronouns when referring to people unless specified otherwise
- No extra text

Task: {task_title}

Existing suggestions:
{existing_text}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        output = response.output_text.strip()

        raw_suggestions = [
            line.strip("- ").strip()
            for line in output.splitlines()
            if line.strip()
        ]
        suggestions = clean_clarification_suggestions(raw_suggestions, mode, task_title)[:3]
        print(f"[Clarification] additional_suggestions_generated={len(suggestions)}; raw={len(raw_suggestions)}; mode={mode}")
        return suggestions

    except Exception as e:
        print("AI generate-more failed:", e)
        return []


# In[55]:


def prepare_accepted_clarification_title(text):
    """Normalize a human-accepted clarification without re-routing it.

    Once the user explicitly checks a proposed clarification (or edits that
    checkbox and checks it), the choice is authoritative. We still parse flags,
    separate due-date metadata, strip due-date wording from the title, and
    restore preferred proper nouns, but we deliberately do not call the normal
    task-preparation/clarification router again.
    """
    parsed = parse_task_flags(text)
    due_date = extract_due_date(text)
    cleaned_title = strip_due_date_phrases(parsed["clean_title"]) or parsed["clean_title"]
    cleaned_title = restore_preferred_proper_nouns(cleaned_title.strip())
    return parsed, cleaned_title, due_date


def update_task_from_selection(page_id, new_title, is_jdi=False, is_urgent=False, is_important=False, due_date=None):
    properties = {
        "Task Name": {
            "title": [{"text": {"content": new_title}}]
        },
        "Status": {
            "select": {"name": READY_STATUS}
        },
        "Just Do It": {"checkbox": is_jdi},
    }

    if is_urgent:
        properties["Urgency"] = {"select": {"name": "High Urgency"}}

    if is_important:
        properties["Importance"] = {"select": {"name": "High Importance"}}

    if due_date:
        properties["Due Date"] = {"date": {"start": due_date.isoformat()}}

    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=headers,
        json={"properties": properties},
        timeout=30,
    )

    if response.ok:
        print("Updated task →", new_title)
        return response.json()

    increment_summary("errors")
    print("ERROR updating task")
    print(response.status_code, response.text)
    return None


# In[56]:


def clear_page_children(page_id):
    blocks = get_block_children(page_id)

    for block in blocks:
        requests.delete(
            f"https://api.notion.com/v1/blocks/{block['id']}",
            headers=headers,
            timeout=30,
        )

    print("Cleared clarification blocks")


# In[57]:


def rebuild_clarification_blocks(page_id, original_task, suggestions):
    clear_page_children(page_id)

    return append_clarification_blocks(
        page_id=page_id,
        original_task=original_task,
        suggestions=suggestions,
    )


# In[58]:


def update_clarification_title(page_id, clarification_text):
    new_title = f"Clarify next action: {clarification_text}"

    response = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=headers,
        json={
            "properties": {
                "Task Name": {
                    "title": [{"text": {"content": new_title}}]
                },
                "Status": {
                    "select": {"name": CLARIFY_STATUS}
                }
            }
        },
        timeout=30,
    )

    if response.ok:
        print("Updated clarification title →", new_title)
        return True

    increment_summary("errors")
    print("ERROR updating clarification title")
    print(response.status_code, response.text)
    return False


# In[59]:


def process_clarification_selection(page):
    """Resolve proposal-first clarification choices.

    Users accept the proposal by checking it, or edit that checkbox text before
    checking it. The exact checked text becomes the candidate task. If the user
    requests a question, AIOS replaces the proposal UI with one targeted prompt
    and an explicit answer placeholder checkbox that the user edits and checks.
    Legacy clarification pages remain readable.
    """
    selection = get_checked_clarification_action(page["id"])
    if not selection:
        return False

    text = selection["text"].strip()
    title = get_title(page)
    original_title = title.replace("Clarify next action:", "").strip()

    if text == ASK_TARGETED_QUESTION_COMMAND:
        question = generate_targeted_clarification_question(original_title)
        clear_page_children(page["id"])
        children = [
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "text": {"content": CLARIFY_HEADER}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": f"Original: {original_title}"}}]},
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": question}}]},
            },
            {
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": f"{USE_SUGGESTION_PREFIX}[type your answer here]"}}],
                    "checked": False,
                },
            },
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "✏️"},
                    "rich_text": [{"type": "text", "text": {"content": "Replace the placeholder with your answer, then check it."}}],
                },
            },
        ]
        response = requests.patch(
            f"https://api.notion.com/v1/blocks/{page['id']}/children",
            headers=headers,
            json={"children": children},
            timeout=30,
        )
        if response.ok:
            print("Added one targeted clarification question")
            return True
        increment_summary("errors")
        print("ERROR adding targeted clarification question")
        print(response.status_code, response.text)
        return False

    # Legacy command support.
    if text == GENERATE_MORE_COMMAND:
        suggestions = generate_clarification_suggestions(original_title)
        rebuild_clarification_blocks(page["id"], original_title, suggestions)
        return True
    if text == ADD_OWN_OPTION_COMMAND:
        print("Legacy add-own-option selected; edit a proposal checkbox and check it instead")
        return False

    if text.startswith(USE_SUGGESTION_PREFIX):
        text = text[len(USE_SUGGESTION_PREFIX):].strip()

    if not text or text == "[type your answer here]":
        print("Clarification answer placeholder is still empty")
        return False

    # If this was an answer to a targeted question rather than a full task,
    # combine it with the original task and let AI propose the final wording.
    blocks = get_block_children(page["id"])
    has_targeted_question_ui = any(
        block.get("type") == "callout"
        and "Replace the placeholder" in get_block_text(block)
        for block in blocks
    )
    if has_targeted_question_ui:
        combined = f"Original task: {original_title}\nUser clarification: {text}"
        proposals = generate_clarification_suggestions(combined)
        if not proposals:
            return False
        rebuild_clarification_blocks(page["id"], original_title, proposals)
        print("Used clarification answer to generate a revised proposal")
        return True

    # Human acceptance is authoritative. Do not send the accepted wording back
    # through prepare_task_title(), because that function may decide the task
    # still needs clarification and create an endless clarification loop.
    parsed, cleaned_title, due_date = prepare_accepted_clarification_title(text)

    if not cleaned_title:
        print("Accepted clarification produced an empty task title")
        return False

    increment_summary("clarification_selections_resolved")
    print("Clarification resolved →", cleaned_title)
    updated_page = update_task_from_selection(
        page["id"], cleaned_title,
        is_jdi=parsed["jdi"],
        is_urgent=parsed["urgent"],
        is_important=parsed.get("important", False),
        due_date=due_date,
    )
    if not updated_page:
        return False

    log_ai_processing_decision(
        original=original_title,
        final_task=cleaned_title,
        action="Created",
        reason="User accepted or edited the AI clarification proposal; task marked Ready.",
        review_needed=False,
        confidence=1.0,
        source="Clarification",
    )
    updated_page = update_missing_metadata_if_confident(updated_page)
    update_quick_win_if_needed(updated_page)
    clear_page_children(page["id"])
    return True

