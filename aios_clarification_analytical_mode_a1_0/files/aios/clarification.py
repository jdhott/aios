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
    )


# In[50]:




def clarification_mode(task_title):
    """Return the clarification generation mode for a task title.

    procedural: concrete physical/setup tasks.
    analytical: audit/validation/review tasks where the first useful step is
    to inspect evidence and identify anomalies, not gather inputs.
    define_context: delegated to existing clarification_route().
    """
    route = clarification_route(task_title, allow_ai=True)
    if route == "define_context":
        return "define_context"

    text = (task_title or "").lower()
    analytical_terms = [
        "audit", "validate", "validation", "compare", "review", "analyze",
        "analyse", "inspect", "diagnose", "investigate", "verify", "confirm",
        "reconcile", "reconciliation", "rank", "ranking", "rankings", "metadata",
        "telemetry", "log", "logs", "report", "reports", "dashboard",
        "anomaly", "anomalies", "discrepancy", "discrepancies", "governance",
        "ontology", "baseline", "score", "scoring",
    ]
    analytical_prefixes = ("aios:", "audit ", "validate ", "verify ", "review ", "compare ")

    if text.strip().startswith(analytical_prefixes) or any(term in text for term in analytical_terms):
        return "analytical"

    return "procedural"


def clarification_prompt_for_mode(task_title):
    mode = clarification_mode(task_title)
    if mode == "define_context":
        return DEFINE_PROMPT
    if mode == "analytical":
        return ANALYTICAL_CHOOSE_PROMPT
    return CHOOSE_PROMPT

def append_clarification_blocks(page_id, original_task, suggestions):
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
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": clarification_prompt_for_mode(original_task)
                        }
                    }
                ]
            },
        },
    ]

    for suggestion in suggestions:
        children.append({
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": suggestion}}],
                "checked": False,
            },
        })

    children.extend([
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": ADD_OWN_OPTION_COMMAND}}],
                "checked": False,
            },
        },
        {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": GENERATE_MORE_COMMAND}}],
                "checked": False,
            },
        },
    ])

    response = requests.patch(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=headers,
        json={"children": children},
        timeout=30,
    )

    if response.ok:
        increment_summary("clarification_blocks_added")
        print("Added clarification blocks")
        return response.json()

    increment_summary("errors")
    print("ERROR adding clarification blocks")
    print(response.status_code, response.text)
    return None


# In[51]:


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
    mode = clarification_mode(task_title)
    print(f"[Clarification] mode={mode}; task={task_title}")

    if mode == "define_context":
        prompt = f"""
This task needs more context before it can become a clear next action.

Generate 3–4 clarification questions that would help define a real next action.

Rules:
- Each line must be a short question
- Focus on WHO, WHAT, or CONTEXT
- Do not ask clarification questions for clear setup/process/creative tasks; those should be broken down instead
- Do not suggest actions like email, call, or text
- Do not include numbering or bullets
- No extra text

Task: {task_title}
"""
    elif mode == "analytical":
        prompt = f"""
Rewrite this analytical or audit-oriented task into outcome-producing first-step options.

Goal:
Generate options that let a knowledgeable human begin evaluating the work itself, not merely gather files or open tools.

Rules:
- Generate only distinct, meaningful options (2–4 total)
- Each option must produce an evaluative outcome, finding, discrepancy, anomaly, or decision
- Prefer review, compare, validate, identify, inspect, verify, sample, or document when appropriate
- Do NOT split a combined evaluation into separate options for each field or keyword
- Do NOT suggest merely accessing, retrieving, downloading, opening, preparing, or creating a spreadsheet unless the task explicitly asks for that artifact
- Do NOT ask the user to gather prerequisites when the task already states the artifact or scope
- Start with a verb
- Be immediately executable
- Keep each option under 14 words
- Do not include numbering or bullets
- No extra text

Good examples:
Review the top-ranked tasks for obvious scoring anomalies
Compare top-ranked tasks against their underlying metadata
Identify rankings that appear inconsistent with Urgency, Importance, or Due Date
Document the first ranking discrepancy found

Task: {task_title}
"""
    else:
        prompt = f"""
Rewrite this task into a small set of clear, concrete next actions.

Rules:
- Generate only distinct, meaningful options (2–4 total)
- Do NOT repeat the same action across multiple channels
- Each option must be one concrete physical action only
- Do not combine actions with “and,” “then,” “after,” or multiple verbs
- Start with a verb
- Be immediately executable
- Do not add details not present in the task
- Avoid vague phrases like "figure out", "handle", "deal with"
- Prefer common, realistic actions
- Avoid unlikely options
- Do not send creative/design tasks here when the object is clear; those should be broken down instead
- Keep each option under 12 words
- Do not include numbering or bullets
- No extra text

Task: {task_title}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        output = response.output_text.strip()

        suggestions = [
            line.strip("- ").strip()
            for line in output.splitlines()
            if line.strip()
        ]

        print(f"[Clarification] suggestions_generated={len(suggestions[:5])}; mode={mode}")
        return suggestions[:5]

    except Exception as e:
        print("AI suggestion generation failed:", e)
        return []


# In[53]:


def get_existing_clarification_suggestions(page_id):
    blocks = get_block_children(page_id)

    suggestions = []

    for block in blocks:
        if block.get("type") != "to_do":
            continue

        text = get_block_text(block)

        if not text:
            continue

        if is_command_checkbox(text):
            continue

        suggestions.append(text)

    return suggestions


# In[54]:


def generate_more_clarification_suggestions(task_title, existing_suggestions):
    existing_text = "\n".join(f"- {s}" for s in existing_suggestions)
    mode = clarification_mode(task_title)
    print(f"[Clarification] generate_more mode={mode}; existing={len(existing_suggestions)}; task={task_title}")

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

        suggestions = [
            line.strip("- ").strip()
            for line in output.splitlines()
            if line.strip()
        ][:3]
        print(f"[Clarification] additional_suggestions_generated={len(suggestions)}; mode={mode}")
        return suggestions

    except Exception as e:
        print("AI generate-more failed:", e)
        return []


# In[55]:


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
    """Resolve checked clarification choices.

    Important behaviour:
    - Command checkboxes still run their command flows.
    - Selected questions for structurally vague tasks keep clarification open.
    - Selected action checkboxes are re-normalized before the task is marked ready.
      This lets user-added options go through the usual cleanup, date stripping,
      JDI flag handling, and Quick Win / metadata passes.
    """
    selection = get_checked_clarification_action(page["id"])

    if not selection:
        return False

    text = selection["text"].strip()

    if text == GENERATE_MORE_COMMAND:
        title = get_title(page)
        original_title = title.replace("Clarify next action:", "").strip()

        existing = get_existing_clarification_suggestions(page["id"])

        new = generate_more_clarification_suggestions(
            original_title,
            existing,
        )

        if not new:
            print("No new suggestions generated")
            return False

        all_suggestions = existing + new

        rebuild_clarification_blocks(
            page["id"],
            original_title,
            all_suggestions,
        )

        return True

    if text == ADD_OWN_OPTION_COMMAND:
        print("Add your own option selected; add a checkbox above it, then check your new option")
        return False

    title = get_title(page)
    original_title = title.replace("Clarify next action:", "").strip()

    if clarification_route(original_title, allow_ai=True) == "define_context" and text.endswith("?"):
        print("Question selected for structurally vague task → keeping clarification open")

        new_title = f"{original_title} → {text}"
        update_clarification_title(page["id"], new_title)

        combined_context = f"{original_title}\nClarify: {text}"
        suggestions = generate_clarification_suggestions(combined_context)

        rebuild_clarification_blocks(
            page["id"],
            combined_context,
            suggestions,
        )

        return True

    # Re-run the user's selected action through the same title-preparation path
    # used by new inbox items. This is especially important for user-added
    # clarification options, because they may include JDI flags, date words, or
    # still be too vague to become a Ready task.
    parsed, cleaned_title, due_date = prepare_task_title({"text": text})

    if cleaned_title.lower().startswith("clarify next action:"):
        print("Selected option still needs clarification → keeping clarification open")
        base_title = strip_due_date_phrases(parsed["clean_title"]) or parsed["clean_title"]
        update_clarification_title(page["id"], base_title)
        suggestions = generate_clarification_suggestions(base_title)
        rebuild_clarification_blocks(
            page["id"],
            base_title,
            suggestions,
        )
        return True

    increment_summary("clarification_selections_resolved")
    print("Clarification resolved →", cleaned_title)
    updated_page = update_task_from_selection(
        page["id"],
        cleaned_title,
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
        reason="User selected a clarification option; task marked Ready.",
        review_needed=False,
        confidence=1.0,
        source="Clarification",
    )

    # Run the same post-create enrichment passes used by normal task creation.
    updated_page = update_missing_metadata_if_confident(updated_page)
    update_quick_win_if_needed(updated_page)

    clear_page_children(page["id"])

    return True
