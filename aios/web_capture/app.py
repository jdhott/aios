from __future__ import annotations

import hmac
import html
import os
from typing import Annotated

import google.auth
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from aios.ingestion.capture_metadata import has_meaningful_capture_text
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token
import requests


WEB_CAPTURE_VERSION = "aios-web-capture-v1"
WEB_CAPTURE_MULTILINE_VERSION = "aios-web-capture-v1.1"
WEB_TASKS_VERSION = "aios-web-tasks-v1-read-only"
WEB_TASK_ACTION_UI_VERSION = "aios-web-tasks-v1.2-checkbox-trash"
WEB_DASHBOARD_INTERACTION_VERSION = "aios-web-dashboard-v1.3-scroll-checkmark"
WEB_DASHBOARD_UI_VERSION = "dashboard-v1.4-compact-capture-toggle"
WEB_DASHBOARD_BNA_VERSION = "dashboard-bna-v1-fix1"
WEB_DASHBOARD_FOCUS_VERSION = "dashboard-focus-v1"
WEB_DASHBOARD_FOCUS_FIX_VERSION = "dashboard-focus-v1-fix1"
WEB_TASK_DETAIL_EDIT_VERSION = "task-detail-edit-v1"
WEB_TASK_DETAIL_UI_VERSION = "task-detail-ui-v1.1-return-to-list"
WEB_PROJECTS_VERSION = "projects-v1"
WEB_CREATE_TASK_VERSION = "create-task-v1"

app = FastAPI(
    title="AIOS Brain Dump",
    version=WEB_CAPTURE_VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

security = HTTPBasic()


def _env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"{name} is not configured")
    return value


def _check_basic_auth(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
) -> str:
    expected_username = _env("AIOS_WEB_USERNAME")
    expected_password = _env("AIOS_WEB_PASSWORD")

    username_ok = hmac.compare_digest(
        credentials.username.encode("utf-8"),
        expected_username.encode("utf-8"),
    )
    password_ok = hmac.compare_digest(
        credentials.password.encode("utf-8"),
        expected_password.encode("utf-8"),
    )

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


def _api_url() -> str:
    return _env("AIOS_API_URL").rstrip("/")


def _identity_token(audience: str) -> str:
    request = GoogleAuthRequest()
    return id_token.fetch_id_token(
        request,
        audience,
    )


def _fetch_focus() -> dict | None:
    api_url = _api_url()
    token = _identity_token(api_url)
    response = requests.get(f"{api_url}/focus", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if not response.ok:
        raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    value = (response.json() or {}).get("focus")
    return dict(value) if value else None


def _fetch_open_tasks(*, search: str = "", limit: int = 50) -> list[dict]:
    api_url=_api_url(); token=_identity_token(api_url)
    response=requests.get(f"{api_url}/tasks", headers={"Authorization": f"Bearer {token}"}, params={"limit": limit, "search": search}, timeout=30)
    if not response.ok:
        raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    payload = response.json() or {}
    return dict(payload.get("sections") or {})


def _task_action(task_id: str, action: str) -> dict:
    api_url=_api_url()
    token=_identity_token(api_url)
    response=requests.post(f"{api_url}/tasks/{task_id}/{action}",headers={"Authorization":f"Bearer {token}"},timeout=30)
    if not response.ok: raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    return response.json()


def _snooze_task(task_id: str, preset: str, custom_date: str = "") -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)
    payload = {"preset": preset}
    if custom_date:
        payload["custom_date"] = custom_date
    response = requests.post(
        f"{api_url}/tasks/{task_id}/snooze",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )
    return response.json()


class BreakdownActionError(RuntimeError):
    pass


def _breakdown_action(task_id: str, action: str, payload: dict | None = None) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)
    response = requests.post(
        f"{api_url}/tasks/{task_id}/breakdown/{action}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=(payload or {}),
        timeout=30,
    )
    if not response.ok:
        detail = "Breakdown request could not be saved."
        try:
            body = response.json()
            candidate = str(body.get("detail") or "").strip() if isinstance(body, dict) else ""
            if candidate:
                detail = candidate
        except Exception:
            pass
        raise BreakdownActionError(detail)
    return response.json()


def _capture_to_aios(text: str) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/inbox",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"text": text},
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return response.json()


def _split_brain_dump(text: str) -> list[str]:
    items = []

    for line in text.splitlines():
        clean = line.strip()

        if not has_meaningful_capture_text(clean):
            continue

        # Strip one ordinary Brain Dump list marker whether or not
        # the user/browser left whitespace after it.
        if clean[:1] in {"•", "-", "*"}:
            clean = clean[1:].strip()

        if not has_meaningful_capture_text(clean):
            continue

        items.append(clean)

    return items


def _capture_many(lines: list[str]) -> tuple[int, list[str]]:
    sent = 0
    failures: list[str] = []

    for line in lines:
        try:
            _capture_to_aios(line)
            sent += 1
        except Exception:
            failures.append(line)

    return sent, failures



def _fetch_task_detail(task_id: str) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.get(
        f"{api_url}/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict((response.json() or {}).get("task") or {})


def _update_task_detail(task_id: str, payload: dict) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.patch(
        f"{api_url}/tasks/{task_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict((response.json() or {}).get("task") or {})


def _safe_return_to(value: str | None) -> str:
    """Allow only local AIOS paths as task-detail return targets."""
    target = str(value or "").strip()

    if not target.startswith("/") or target.startswith("//"):
        return "/"

    return target


def _task_detail_page(
    task: dict,
    message: str = "",
    error: str = "",
    return_to: str = "/",
) -> str:
    task_id = html.escape(str(task.get("id") or ""))
    title = html.escape(str(task.get("title") or ""))
    due_at = html.escape(str(task.get("due_at") or "")[:10])
    defer_until = html.escape(str(task.get("defer_until") or "")[:10])
    importance = html.escape(str(task.get("importance") or ""))
    urgency = html.escape(str(task.get("urgency") or ""))
    effort = html.escape(str(task.get("effort") or ""))
    duration = html.escape(str(task.get("duration") or ""))
    checked = " checked" if task.get("is_just_do_it") else ""
    return_to = html.escape(
        _safe_return_to(return_to),
        quote=True,
    )

    notice = ""
    if message:
        notice = '<div class="notice success">' + html.escape(message) + "</div>"
    elif error:
        notice = '<div class="notice error">' + html.escape(error) + "</div>"

    score = html.escape(
        str(
            task.get("execution_score")
            if task.get("execution_score") is not None
            else "—"
        )
    )
    rank = html.escape(
        str(
            task.get("execution_rank")
            if task.get("execution_rank") is not None
            else "—"
        )
    )
    bna = "Yes" if task.get("best_next_action") else "No"
    quick_win = "Yes" if task.get("is_quick_win") else "No"
    surfaced_qw = "Yes" if task.get("surfaced_quick_win") else "No"
    project_id = html.escape(str(task.get("project_id") or "—"))

    breakdown_state = str(task.get("breakdown_state") or "").strip()
    has_breakdown_children = bool(task.get("has_breakdown_children"))
    breakdown_context = html.escape(str(task.get("breakdown_request_context") or ""))
    raw_proposal = task.get("breakdown_proposal") or []
    proposal_titles = [
        str(item).strip() for item in raw_proposal
        if str(item).strip()
    ] if isinstance(raw_proposal, list) else []
    proposal_text = html.escape("\n".join(proposal_titles))

    if breakdown_state == "pending":
        breakdown_body = f"""
        <p class="readonly-note">AIOS is proposing the smallest useful breakdown using your guidance. Nothing will be created until you accept it.</p>
        <div class="breakdown-pending"><span class="mini-spinner"></span> Building proposed breakdown…</div>
        <script>setTimeout(function(){{ window.location.href='/tasks/{task_id}?return_to={return_to}#breakdown'; }}, 2500);</script>
        """
    elif breakdown_state == "proposed" and proposal_titles:
        breakdown_body = f"""
        <p class="readonly-note">Edit the set below before accepting. Use one task per line; remove, add, or reorder lines as needed.</p>
        <form method="post" action="/tasks/{task_id}/breakdown/accept">
          <input type="hidden" name="return_to" value="{return_to}">
          <label>Proposed subtasks
            <textarea class="breakdown-editor" name="titles" rows="{max(4, len(proposal_titles) + 1)}" required>{proposal_text}</textarea>
          </label>
          <div class="actions">
            <button class="primary-button" type="submit">Accept Breakdown</button>
            <button class="secondary-button" type="submit" formaction="/tasks/{task_id}/breakdown/cancel" formnovalidate>Cancel</button>
          </div>
        </form>
        """
    elif breakdown_state == "accepted" or has_breakdown_children:
        children = list(task.get("breakdown_children") or [])
        completed_children = [c for c in children if c.get("is_done")]
        open_children = [c for c in children if not c.get("is_done") and c.get("is_open", True)]
        open_text = html.escape("\n".join(str(c.get("title") or "").strip() for c in open_children))
        completed_html = ""
        if completed_children:
            items = "".join(f"<li>{html.escape(str(c.get('title') or ''))} <span class='optional'>(completed)</span></li>" for c in completed_children)
            completed_html = f"<p class='readonly-note'>Completed subtasks are preserved as history and are not removed by this editor.</p><ul>{items}</ul>"
        breakdown_body = f"""
        <p class="readonly-note">Edit the open breakdown below. Use one task per line; rewrite, remove, add, or reorder lines, then save.</p>
        {completed_html}
        <form method="post" action="/tasks/{task_id}/breakdown/edit">
          <input type="hidden" name="return_to" value="{return_to}">
          <label>Open subtasks
            <textarea class="breakdown-editor" name="titles" rows="{max(4, len(open_children)+1)}">{open_text}</textarea>
          </label>
          <div class="actions"><button class="primary-button" type="submit">Save Breakdown</button></div>
        </form>
        """
    else:
        state_note = ''
        if breakdown_state == "no_proposal":
            state_note = '<div class="notice">AIOS did not find a useful breakdown. Add guidance and try again if you want.</div>'
        elif breakdown_state == "failed":
            state_note = '<div class="notice error">AIOS could not generate a breakdown. You can try again with more guidance.</div>'
        breakdown_body = f"""
        {state_note}
        <p class="readonly-note">Use this when the task would be easier to execute as a small set of meaningful steps. AIOS will propose first; nothing is created automatically.</p>
        <form method="post" action="/tasks/{task_id}/breakdown/request">
          <input type="hidden" name="return_to" value="{return_to}">
          <label>Anything AIOS should know? <span class="optional">Optional</span>
            <textarea class="breakdown-editor" name="context" rows="3" placeholder="e.g. I already bought the materials; focus on installation.">{breakdown_context}</textarea>
          </label>
          <div class="actions"><button class="secondary-button" type="submit">Break Down Task</button></div>
        </form>
        """

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#264155">
<title>AIOS Task</title>
<style>
:root {{
  --navy:#264155;
  --yellow:#ffc93c;
  --paper:#f7f7f3;
  --card:#ffffff;
  --ink:#17242d;
  --muted:#66747d;
  --border:#d9dedf;
  --border-strong:#c8d0d3;
  --success:#e8f4e8;
  --success-ink:#2f6b3a;
  --error:#fae9e7;
  --error-ink:#8a3d35;
  --shadow:0 10px 30px rgba(38,65,85,.07);
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  min-height:100vh;
  background:var(--paper);
  color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}}
main {{
  width:min(980px,100%);
  margin:0 auto;
  padding:max(26px,env(safe-area-inset-top)) 20px
          max(42px,env(safe-area-inset-bottom));
}}
.topbar {{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:16px;
  margin-bottom:24px;
}}
.back {{
  color:var(--navy);
  text-decoration:none;
  font-weight:700;
  font-size:.95rem;
}}
.back:hover {{ text-decoration:underline; }}
.page-title {{
  margin:0;
  color:var(--navy);
  font-size:clamp(2rem,5vw,2.8rem);
  letter-spacing:-.035em;
}}
.page-subtitle {{
  margin:7px 0 0;
  color:var(--muted);
  font-size:.98rem;
}}
.notice {{
  margin:18px 0 0;
  padding:13px 15px;
  border-radius:12px;
  font-weight:650;
}}
.success {{
  background:var(--success);
  color:var(--success-ink);
}}
.error {{
  background:var(--error);
  color:var(--error-ink);
}}
.layout {{
  display:grid;
  grid-template-columns:minmax(0,1.35fr) minmax(300px,.85fr);
  gap:20px;
  margin-top:22px;
  align-items:start;
}}
.card {{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:18px;
  padding:22px;
  box-shadow:var(--shadow);
}}
.card-title {{
  margin:0 0 18px;
  color:var(--navy);
  font-size:1.15rem;
}}
.form-grid {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:16px;
}}
.full {{ grid-column:1/-1; }}
label {{
  display:grid;
  gap:7px;
  color:var(--ink);
  font-size:.88rem;
  font-weight:700;
}}
input[type="text"],
input[type="date"] {{
  width:100%;
  min-height:46px;
  border:1px solid var(--border-strong);
  border-radius:12px;
  padding:0 13px;
  background:#fff;
  color:var(--ink);
  font:inherit;
  font-weight:500;
  outline:none;
}}
input:focus {{
  border-color:var(--navy);
  box-shadow:0 0 0 3px rgba(38,65,85,.10);
}}
.checkbox-row {{
  display:flex;
  align-items:center;
  gap:10px;
  min-height:46px;
  padding:2px 0;
}}
.checkbox-row input {{
  width:20px;
  height:20px;
  accent-color:var(--yellow);
}}
.actions {{
  display:flex;
  gap:10px;
  align-items:center;
  margin-top:20px;
}}
.primary-button {{
  min-height:46px;
  border:0;
  border-radius:12px;
  padding:0 18px;
  background:var(--yellow);
  color:var(--navy);
  font:inherit;
  font-weight:800;
  cursor:pointer;
}}
.primary-button:hover {{ filter:brightness(.98); }}
.secondary-button {{
  min-height:46px; border:1px solid var(--border-strong); border-radius:12px;
  padding:0 16px; background:#fff; color:var(--navy); font:inherit; font-weight:750; cursor:pointer;
}}
.breakdown-editor {{ width:100%; margin-top:7px; min-height:86px; resize:vertical; }}
.optional {{ color:var(--muted); font-weight:500; }}
.breakdown-pending {{ display:flex; align-items:center; gap:10px; font-weight:750; color:var(--navy); }}
.mini-spinner {{ width:18px; height:18px; border:3px solid var(--border); border-top-color:var(--navy); border-radius:50%; animation:spin .8s linear infinite; }}
@keyframes spin {{ to {{ transform:rotate(360deg); }} }}
.secondary-link {{
  min-height:46px;
  display:inline-flex;
  align-items:center;
  padding:0 14px;
  border:1px solid var(--border);
  border-radius:12px;
  color:var(--navy);
  text-decoration:none;
  font-weight:700;
  background:#fff;
}}
.meta-list {{
  display:grid;
  gap:0;
}}
.meta-row {{
  display:grid;
  grid-template-columns:1fr auto;
  gap:18px;
  align-items:center;
  padding:14px 0;
  border-bottom:1px solid var(--border);
}}
.meta-row:last-child {{ border-bottom:0; }}
.meta-label {{
  color:var(--muted);
  font-size:.82rem;
  font-weight:700;
}}
.meta-value {{
  color:var(--ink);
  font-weight:750;
  text-align:right;
  overflow-wrap:anywhere;
}}
.project-value {{
  max-width:260px;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:.82rem;
  font-weight:600;
}}
.readonly-note {{
  margin:-6px 0 14px;
  color:var(--muted);
  font-size:.86rem;
  line-height:1.4;
}}
@media (max-width:760px) {{
  main {{ padding-left:14px; padding-right:14px; }}
  .layout {{ grid-template-columns:1fr; }}
  .form-grid {{ grid-template-columns:1fr; }}
  .full {{ grid-column:auto; }}
  .topbar {{ align-items:flex-start; }}
  .card {{ padding:18px; border-radius:16px; }}
}}
</style>
</head>
<body>
<main>
  <div class="topbar">
    <div>
      <h1 class="page-title">Edit Task</h1>
      <p class="page-subtitle">Update task details while keeping AIOS guidance read-only.</p>
    </div>
  </div>

  {notice}

  <div class="layout">
    <form method="post" action="/tasks/{task_id}/edit">
      <input type="hidden" name="return_to" value="{return_to}">
      <section class="card">
        <h2 class="card-title">Task Details</h2>

        <div class="form-grid">
          <label class="full">
            Task
            <input type="text" name="title" value="{title}" required>
          </label>

          <label>
            Due date
            <input type="date" name="due_at" value="{due_at}">
          </label>

          <label>
            Defer until
            <input type="date" name="defer_until" value="{defer_until}">
          </label>

          <label>
            Importance
            <input type="text" name="importance" value="{importance}">
          </label>

          <label>
            Urgency
            <input type="text" name="urgency" value="{urgency}">
          </label>

          <label>
            Effort
            <input type="text" name="effort" value="{effort}">
          </label>

          <label>
            Duration
            <input type="text" name="duration" value="{duration}">
          </label>

          <label class="full">
            Just Do It
            <span class="checkbox-row">
              <input type="checkbox" name="is_just_do_it" value="true"{checked}>
              <span>Mark this task as Just Do It</span>
            </span>
          </label>
        </div>

        <div class="actions">
          <button class="primary-button" type="submit">Save Changes</button>
          <a class="secondary-link" href="{return_to}">Cancel</a>
        </div>
      </section>
    </form>

    <aside class="card">
      <h2 class="card-title">AIOS</h2>
      <p class="readonly-note">These values are calculated by AIOS and are not edited here.</p>

      <div class="meta-list">
        <div class="meta-row">
          <span class="meta-label">Execution Score</span>
          <span class="meta-value">{score}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Execution Rank</span>
          <span class="meta-value">{rank}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Best Next Action</span>
          <span class="meta-value">{bna}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Quick Win</span>
          <span class="meta-value">{quick_win}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Surfaced Quick Win</span>
          <span class="meta-value">{surfaced_qw}</span>
        </div>
        <div class="meta-row">
          <span class="meta-label">Project ID</span>
          <span class="meta-value project-value">{project_id}</span>
        </div>
      </div>
    </aside>
  </div>

  <section class="card" id="breakdown" style="margin-top:20px;">
    <h2 class="card-title">Breakdown</h2>
    {breakdown_body}
  </section>
</main>
</body>
</html>"""


def _fetch_projects() -> list[dict]:
    api_url = _api_url()
    token = _identity_token(api_url)
    response = requests.get(
        f"{api_url}/projects",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )
    return list((response.json() or {}).get("projects") or [])


def _fetch_project_detail(project_id: str) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)
    response = requests.get(
        f"{api_url}/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )
    return dict(response.json() or {})


def _update_project_outcome(
    project_id: str,
    outcome: str,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.patch(
        f"{api_url}/projects/{project_id}/outcome",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"outcome": outcome},
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict(response.json() or {})


def _update_project_context(
    project_id: str,
    context: str,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.patch(
        f"{api_url}/projects/{project_id}/context",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"context": context},
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict(response.json() or {})


def _project_work_action(
    project_id: str,
    proposal_id: str,
    action: str,
    payload: dict | None = None,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    headers = {
        "Authorization": f"Bearer {token}",
    }

    if payload is not None:
        headers["Content-Type"] = "application/json"

    response = requests.post(
        f"{api_url}/projects/{project_id}/work-proposals/{proposal_id}/{action}",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict(response.json() or {})


def _request_project_work_generation(
    project_id: str,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/projects/{project_id}/work-proposals/generate",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict(response.json() or {})


def _project_work_dialogue_action(project_id: str, action: str, payload: dict) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)
    response = requests.post(
        f"{api_url}/projects/{project_id}/work-proposals/{action}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    return dict(response.json() or {})


def _project_lifecycle_action(
    project_id: str,
    action: str,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/projects/{project_id}/{action}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict(response.json() or {})


def _projects_page(projects: list[dict], error: str = "") -> str:
    suggested_projects = [
        project for project in projects
        if not project.get("review_needed")
        and not project.get("is_active")
        and str(project.get("status") or "").strip().lower() == "someday"
    ]

    review_projects = [
        project for project in projects
        if project.get("review_needed")
    ]

    active_projects = [
        project for project in projects
        if not project.get("review_needed")
        and project.get("is_active")
    ]

    reason_labels = {
        "inactive_with_open_work": "Inactive project has current open work",
        "project_proxy_task": "An open task appears to duplicate the project outcome",
        "no_executable_tasks": "No other executable project tasks are available",
    }

    def render_cards(
        items: list[dict],
        *,
        review: bool = False,
        suggested: bool = False,
    ) -> str:
        cards = ""

        for project in items:
            project_id = html.escape(str(project.get("id") or ""))
            name = html.escape(str(project.get("name") or "Untitled Project"))
            count = int(project.get("open_task_count") or 0)
            status = str(project.get("status") or "").strip()

            status_html = (
                f'<span class="project-status">{html.escape(status)}</span>'
                if status else ""
            )

            review_html = ""
            if review:
                reasons = [
                    reason_labels.get(reason, reason.replace("_", " ").title())
                    for reason in (project.get("review_reasons") or [])
                ]

                if reasons:
                    review_html = (
                        '<ul class="review-reasons">'
                        + "".join(
                            f"<li>{html.escape(reason)}</li>"
                            for reason in reasons
                        )
                        + "</ul>"
                    )

            possible_match_html = ""

            if suggested:
                possible_name = str(
                    project.get(
                        "possible_existing_project_name"
                    )
                    or ""
                ).strip()

                possible_confidence = project.get(
                    "possible_existing_project_confidence"
                )

                if (
                    possible_name
                    and possible_confidence is not None
                ):
                    try:
                        confidence_percent = round(
                            float(possible_confidence) * 100
                        )
                    except (TypeError, ValueError):
                        confidence_percent = None

                    confidence_text = (
                        f" · {confidence_percent}% match"
                        if confidence_percent is not None
                        else ""
                    )

                    possible_match_html = (
                        '<div class="possible-match">'
                        '<div class="possible-match-label">'
                        'Possible existing project'
                        '</div>'
                        '<div class="possible-match-name">'
                        f'{html.escape(possible_name)}'
                        f'{html.escape(confidence_text)}'
                        '</div>'
                        '<div class="possible-match-actions">'
                        f'<form method="post" '
                        f'action="/projects/{project_id}/use-existing-project">'
                        '<button class="possible-match-use" type="submit">'
                        'Use existing project'
                        '</button>'
                        '</form>'
                        f'<form method="post" '
                        f'action="/projects/{project_id}/keep-separate">'
                        '<button class="possible-match-keep" type="submit">'
                        'Keep separate'
                        '</button>'
                        '</form>'
                        '</div>'
                        '</div>'
                    )

            activate_html = ""

            if suggested:
                activate_html = (
                    f'<form class="project-activate-form" method="post" '
                    f'action="/projects/{project_id}/activate">'
                    '<button class="project-activate" type="submit">'
                    'Activate'
                    '</button>'
                    '</form>'
                )

            cards += (
                '<div class="project-card-wrap">'
                f'<a class="project-card{" review-card" if review else ""}" '
                f'href="/projects/{project_id}">'
                f'<div><h2>{name}</h2>{status_html}{review_html}{possible_match_html}</div>'
                f'<div class="project-count"><strong>{count}</strong>'
                f'<span>open task{"s" if count != 1 else ""}</span></div>'
                '</a>'
                + activate_html
                + '</div>'
            )

        return cards

    suggested_cards = render_cards(
        suggested_projects,
        suggested=True,
    )

    review_cards = render_cards(
        review_projects,
        review=True,
    )

    active_cards = render_cards(
        active_projects,
    )

    if not suggested_cards:
        suggested_cards = (
            '<div class="empty-state">'
            'No suggested projects awaiting activation.'
            '</div>'
        )

    if not review_cards:
        review_cards = (
            '<div class="empty-state">'
            'No projects currently need review.'
            '</div>'
        )

    if not active_cards:
        active_cards = (
            '<div class="empty-state">'
            'No active projects with open tasks.'
            '</div>'
        )

    notice = (
        '<div class="notice error">' + html.escape(error) + '</div>'
        if error else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#264155">
<title>AIOS Projects</title>
<style>
:root {{
  --navy:#264155; --paper:#f7f7f3; --ink:#17242d;
  --muted:#66747d; --border:#d9dedf; --card:#fff; --error:#fae9e7;
  --review:#fff8dc;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}}
main {{
  width:min(900px,100%); margin:0 auto;
  padding:max(26px,env(safe-area-inset-top)) 18px 42px;
}}
.topbar {{
  display:flex; justify-content:space-between; align-items:flex-end;
  gap:16px; margin-bottom:24px;
}}
h1 {{
  margin:0; color:var(--navy); font-size:clamp(2rem,5vw,2.8rem);
  letter-spacing:-.035em;
}}
.subtitle {{ margin:7px 0 0; color:var(--muted); }}
.nav-link {{ color:var(--navy); text-decoration:none; font-weight:750; }}
.notice {{ padding:12px 14px; border-radius:12px; margin-bottom:18px; }}
.error {{ background:var(--error); }}
.section {{ margin-top:28px; }}
.section:first-of-type {{ margin-top:0; }}
.section h2 {{
  margin:0 0 12px; color:var(--navy); font-size:1.15rem;
}}
.section-note {{
  margin:-4px 0 14px; color:var(--muted); font-size:.9rem;
}}
.project-list {{ display:grid; gap:12px; }}
.project-card {{
  display:flex; align-items:center; justify-content:space-between;
  gap:20px; padding:18px 20px; background:var(--card);
  border:1px solid var(--border); border-radius:16px;
  color:inherit; text-decoration:none;
}}
.project-card:hover {{
  border-color:var(--navy); box-shadow:0 8px 24px rgba(38,65,85,.08);
}}
.project-card-wrap {{
  display:grid;
  gap:7px;
}}
.project-activate-form {{
  display:flex;
  justify-content:flex-end;
  margin:0 4px 0 0;
}}
.project-activate {{
  border:1px solid var(--navy);
  border-radius:9px;
  padding:7px 11px;
  background:white;
  color:var(--navy);
  font:inherit;
  font-size:.84rem;
  font-weight:750;
  cursor:pointer;
}}
.possible-match {{
  margin-top:12px;
  padding:11px 12px;
  border:1px solid var(--border);
  border-radius:10px;
  background:#fff;
}}
.possible-match-label {{
  color:var(--muted);
  font-size:.78rem;
  font-weight:750;
}}
.possible-match-name {{
  margin-top:3px;
  color:var(--ink);
  font-size:.88rem;
  font-weight:700;
}}
.possible-match-actions {{
  display:flex;
  gap:8px;
  margin-top:9px;
  flex-wrap:wrap;
}}
.possible-match-actions form {{
  margin:0;
}}
.possible-match-use,
.possible-match-keep {{
  border-radius:8px;
  padding:6px 10px;
  font:inherit;
  font-size:.8rem;
  font-weight:750;
  cursor:pointer;
}}
.possible-match-use {{
  border:1px solid var(--navy);
  background:var(--navy);
  color:white;
}}
.possible-match-keep {{
  border:1px solid var(--border);
  background:white;
  color:var(--navy);
}}
.review-card {{ background:var(--review); }}
.project-card h2 {{ margin:0; color:var(--navy); font-size:1.08rem; }}
.project-status {{
  display:inline-block; margin-top:6px; color:var(--muted); font-size:.82rem;
}}
.review-reasons {{
  margin:10px 0 0; padding-left:18px; color:var(--muted);
  font-size:.86rem; line-height:1.45;
}}
.project-count {{ flex:0 0 auto; display:grid; text-align:right; }}
.project-count strong {{ color:var(--navy); font-size:1.35rem; line-height:1; }}
.project-count span {{ color:var(--muted); font-size:.78rem; margin-top:4px; }}
.empty-state {{
  padding:24px; color:var(--muted); background:white;
  border:1px solid var(--border); border-radius:16px;
}}
</style>
</head>
<body>
<main>
  <div class="topbar">
    <div>
      <h1>Projects</h1>
      <p class="subtitle">Projects with unfinished work.</p>
    </div>
    <a class="nav-link" href="/">Home</a>
  </div>

  {notice}

  <section class="section">
    <h2>Suggested Projects</h2>
    <p class="section-note">
      AIOS found these projects, but they are not active until you choose to activate them.
    </p>
    <div class="project-list">{suggested_cards}</div>
  </section>

  <section class="section">
    <h2>Needs Review</h2>
    <p class="section-note">
      Projects where AIOS sees a mismatch between project state and current work.
    </p>
    <div class="project-list">{review_cards}</div>
  </section>

  <section class="section">
    <h2>Active Projects</h2>
    <div class="project-list">{active_cards}</div>
  </section>
</main>
</body>
</html>"""


def _project_detail_page(
    payload: dict,
    *,
    refresh_proposal: bool = False,
) -> str:
    project = dict(payload.get("project") or {})
    tasks = list(payload.get("tasks") or [])
    work_proposals = list(payload.get("work_proposals") or [])

    name = html.escape(str(project.get("name") or "Untitled Project"))
    project_id = html.escape(str(project.get("id") or ""))
    outcome = html.escape(str(project.get("outcome") or ""))
    context = html.escape(str(project.get("context") or ""))
    count = int(project.get("open_task_count") or 0)
    status = str(project.get("status") or "").strip()
    work_generation_state = str(
        project.get("work_generation_state") or ""
    ).strip().lower()
    work_generation_question = str(project.get("work_generation_question") or "").strip()
    work_generation_context_update = str(project.get("work_generation_context_update") or "").strip()

    task_rows = ""
    for task in tasks:
        task_id = html.escape(str(task.get("id") or ""))
        title = html.escape(str(task.get("title") or "Untitled task"))
        score = task.get("execution_score")
        rank = task.get("execution_rank")
        due = str(task.get("due_at") or "").strip()
        importance = str(task.get("importance") or "").strip()

        meta = []
        if rank is not None:
            meta.append(f"Rank {html.escape(str(rank))}")
        if score is not None:
            meta.append(f"Score {html.escape(str(score))}")
        if importance:
            meta.append(html.escape(importance))
        if due:
            meta.append("Due " + html.escape(due[:10]))
        if task.get("best_next_action"):
            meta.append("Best Next Action")
        if task.get("is_quick_win"):
            meta.append("Quick Win")
        if task.get("is_just_do_it"):
            meta.append("Just Do It")

        project_return = f"/projects/{project_id}#project-tasks"
        task_rows += (
            '<article class="task-row project-task-row">'
            f'<form class="complete-form" method="post" action="/tasks/{task_id}/complete">'
            f'<input type="hidden" name="return_to" value="{project_return}">'
            '<button class="complete-checkbox" type="submit" aria-label="Mark task done" title="Mark done">'
            '<span aria-hidden="true"></span></button></form>'
            '<div class="project-task-main">'
            f'<div class="task-title"><a class="project-task-link" href="/tasks/{task_id}?return_to={project_return}">{title}</a></div>'
            f'<div class="task-meta">{" · ".join(meta)}</div>'
            '</div>'
            f'<form class="delete-form" method="post" action="/tasks/{task_id}/delete" '
            'onsubmit="return confirm(&quot;Delete this task?&quot;);">'
            f'<input type="hidden" name="return_to" value="{project_return}">'
            '<button class="trash-button" type="submit" aria-label="Delete task" title="Delete task">'
            '<span aria-hidden="true">🗑️</span></button></form>'
            '</article>'
        )

    if not task_rows:
        task_rows = '<div class="empty-state">No open tasks in this project.</div>'

    proposal_rows = ""

    for proposal in work_proposals:
        proposal_id = html.escape(
            str(proposal.get("id") or "")
        )
        proposal_title = html.escape(
            str(proposal.get("title") or "Untitled proposal")
        )

        proposal_rows += (
            '<div class="proposal-row">'

            '<div class="proposal-section">'
            '<div class="proposal-section-label">Suggested task</div>'
            f'<form class="proposal-accept-form" method="post" '
            f'action="/projects/{project_id}/work-proposals/{proposal_id}/accept">'
            f'<textarea class="proposal-title-input" '
            f'name="title" maxlength="75" required>'
            f'{proposal_title}</textarea>'
            '<div class="proposal-primary-actions">'
            '<span class="proposal-edit-note">'
            'Edit the task if needed before accepting.'
            '</span>'
            '<button class="proposal-accept" type="submit">Accept</button>'
            '</div>'
            '</form>'
            '</div>'

            '<div class="proposal-divider"></div>'

            '<div class="proposal-section">'
            '<div class="proposal-section-label">Not quite right?</div>'
            '<div class="proposal-help">'
            'Tell AIOS exactly what should change. '
            'Your correction will guide the next proposal.'
            '</div>'
            f'<form class="proposal-retry-form" method="post" '
            f'action="/projects/{project_id}/work-proposals/{proposal_id}/retry">'
            '<textarea name="feedback" required '
            'placeholder="What should AIOS change?"></textarea>'
            '<div class="proposal-action-row">'
            '<button class="proposal-retry" type="submit">Try Again</button>'
            '</form>'
            f'<form method="post" '
            f'action="/projects/{project_id}/work-proposals/{proposal_id}/dismiss">'
            '<button class="proposal-dismiss" type="submit">Dismiss</button>'
            '</form>'
            '</div>'
            '</div>'

            '</div>'
        )

    status_html = (
        f'<span class="status">{html.escape(status)}</span>'
        if status else ""
    )

    proposal_pending = bool(
        refresh_proposal
        and work_generation_state in {"pending", "answer_pending"}
    )

    pending_html = (
        '<section class="proposal-card proposal-pending-card">'
        '<h2>Suggested project work</h2>'
        '<div class="proposal-pending">'
        '<span class="proposal-spinner" aria-hidden="true"></span>'
        '<div>'
        '<strong>Looking for missing project work…</strong>'
        '<div class="proposal-pending-note">'
        'AIOS is reviewing the project outcome, context, open work, and completed work.'
        '</div>'
        '</div>'
        '</div>'
        '</section>'
        if proposal_pending
        else ""
    )

    generation_result_html = ""
    if refresh_proposal and not work_proposals:
        if work_generation_state == "clarification" and work_generation_question:
            generation_result_html = (
                '<section class="proposal-card"><h2>AIOS needs one thing from you</h2>'
                f'<p class="proposal-note"><strong>{html.escape(work_generation_question)}</strong></p>'
                f'<form method="post" action="/projects/{project_id}/work-proposals/answer">'
                '<textarea name="answer" required placeholder="Your answer"></textarea>'
                '<div class="context-actions"><button class="context-save" type="submit">Continue</button></div></form></section>'
            )
        elif work_generation_state == "answer_pending":
            generation_result_html = '<section class="proposal-card"><h2>Suggested project work</h2><p class="proposal-note">AIOS is turning your answer into reusable project context…</p></section>'
        elif work_generation_state == "context_review" and work_generation_context_update:
            generation_result_html = (
                '<section class="proposal-card"><h2>Add to Project Context</h2>'
                '<p class="proposal-note">AIOS summarized your answer into durable project knowledge. Edit it if needed before saving.</p>'
                f'<form method="post" action="/projects/{project_id}/work-proposals/context">'
                f'<textarea name="context_update" required>{html.escape(work_generation_context_update)}</textarea>'
                '<div class="context-actions"><button class="context-save" type="submit">Add &amp; Continue</button></div></form></section>'
            )
        elif work_generation_state == "waiting":
            generation_result_html = (
                '<section class="proposal-card">'
                '<h2>Suggested project work</h2>'
                '<p class="proposal-note" style="margin-bottom:0">'
                '<strong>No missing project work found.</strong><br>'
                'AIOS did not identify additional actionable work beyond what is already planned or completed.'
                '</p>'
                '</section>'
            )
        elif work_generation_state == "failed":
            generation_result_html = (
                '<section class="proposal-card">'
                '<h2>Suggested project work</h2>'
                '<p class="proposal-note" style="margin-bottom:0">'
                '<strong>Project work could not be generated.</strong><br>'
                'Check that the project has a clear outcome, then try again.'
                '</p>'
                '</section>'
            )

    if proposal_pending:
        pending_refresh_script = """
<script>
(() => {
  const key = "aios-project-proposal-refresh-count";
  const count = Number(sessionStorage.getItem(key) || "0");

  if (count < 45) {
    sessionStorage.setItem(key, String(count + 1));
    setTimeout(() => window.location.reload(), 2000);
  }
})();
</script>
"""
    else:
        pending_refresh_script = """
<script>
sessionStorage.removeItem("aios-project-proposal-refresh-count");
</script>
"""

    if refresh_proposal:
        pending_refresh_script += """
<script>
(() => {
  const results = document.getElementById("project-work-results");
  if (!results) return;
  requestAnimationFrame(() => results.scrollIntoView({ block: "start" }));
})();
</script>
"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#264155">
<title>{name} · AIOS</title>
<style>
:root {{
  --navy:#264155; --paper:#f7f7f3; --ink:#17242d;
  --muted:#66747d; --border:#d9dedf; --card:#fff;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}}
main {{
  width:min(900px,100%); margin:0 auto;
  padding:max(26px,env(safe-area-inset-top)) 18px 42px;
}}
.back {{ color:var(--navy); text-decoration:none; font-weight:750; }}
.header {{ margin:22px 0; }}
h1 {{
  margin:0; color:var(--navy); font-size:clamp(1.8rem,5vw,2.5rem);
  letter-spacing:-.03em;
}}
.summary {{
  display:flex; align-items:center; gap:10px;
  margin-top:8px; color:var(--muted); font-size:.9rem;
}}
.status {{
  padding:3px 8px; background:#fff; border:1px solid var(--border);
  border-radius:999px; font-size:.78rem;
}}
.task-list {{
  overflow:hidden; background:var(--card);
  border:1px solid var(--border); border-radius:16px;
}}
.task-row {{
  display:flex; align-items:center; justify-content:space-between;
  gap:16px; padding:16px 18px; color:inherit;
  text-decoration:none; border-bottom:1px solid var(--border);
}}
.project-task-row {{ display:grid; grid-template-columns:44px minmax(0,1fr) 44px; gap:10px; }}
.project-task-main {{ min-width:0; }}
.project-task-link {{ color:inherit; text-decoration:none; }}
.project-task-link:hover {{ text-decoration:underline; }}
.complete-form, .delete-form {{ display:flex; margin:0; align-items:center; justify-content:center; }}
.complete-checkbox, .trash-button {{ width:44px; height:44px; min-height:44px; padding:0; border:0; border-radius:10px; background:transparent; display:flex; align-items:center; justify-content:center; cursor:pointer; }}
.complete-checkbox span {{ width:20px; height:20px; border:2px solid #89959b; border-radius:6px; display:block; }}
.complete-checkbox:hover, .complete-checkbox:focus-visible, .trash-button:hover, .trash-button:focus-visible {{ background:#eceeed; }}
.trash-button {{ font-size:1.08rem; opacity:.72; }}
.task-row:last-child {{ border-bottom:0; }}
.task-row:hover {{ background:#fbfbf8; }}
.task-title {{ font-weight:700; }}
.task-meta {{
  margin-top:5px; color:var(--muted); font-size:.8rem; line-height:1.35;
}}
.chevron {{ color:var(--muted); font-size:1.6rem; }}
.empty-state {{ padding:24px; color:var(--muted); }}
.context-card {{
  margin:0 0 22px; padding:18px;
  background:var(--card); border:1px solid var(--border);
  border-radius:16px;
}}
.context-card h2 {{
  margin:0 0 6px; color:var(--navy); font-size:1rem;
}}
.context-note {{
  margin:0 0 12px; color:var(--muted);
  font-size:.84rem; line-height:1.4;
}}
.context-card textarea {{
  width:100%; min-height:130px; resize:vertical;
  padding:12px 13px; border:1px solid var(--border);
  border-radius:10px; font:inherit; line-height:1.45;
  color:var(--ink); background:#fff;
}}
.context-actions {{
  display:flex; justify-content:flex-end;
  margin-top:10px;
}}
.context-save {{
  border:0; border-radius:10px;
  padding:9px 14px; background:var(--navy); color:white;
  font:inherit; font-weight:750; cursor:pointer;
}}
.context-save:hover {{ opacity:.92; }}
.proposal-card {{
  margin:0 0 22px;
  padding:22px;
  background:var(--card);
  border:1px solid var(--border);
  border-radius:16px;
}}

.proposal-card h2 {{
  margin:0 0 6px;
  color:var(--navy);
  font-size:1.08rem;
}}

.proposal-note {{
  margin:0 0 18px;
  color:var(--muted);
  font-size:.9rem;
  line-height:1.45;
}}

.proposal-row {{
  display:grid;
  gap:22px;
  padding-top:18px;
  border-top:1px solid var(--border);
}}

.proposal-section {{
  display:grid;
  gap:9px;
}}

.proposal-section-label {{
  color:var(--navy);
  font-size:.95rem;
  font-weight:800;
}}

.proposal-help,
.proposal-edit-note {{
  color:var(--muted);
  font-size:.84rem;
  line-height:1.4;
}}

.proposal-accept-form,
.proposal-retry-form {{
  display:grid;
  gap:10px;
}}

.proposal-title-input,
.proposal-retry-form textarea {{
  width:100%;
  resize:vertical;
  padding:12px 14px;
  border:1px solid var(--border);
  border-radius:12px;
  background:#fff;
  color:var(--ink);
  font:inherit;
  line-height:1.45;
}}

.proposal-title-input {{
  min-height:76px;
  font-weight:700;
}}

.proposal-retry-form textarea {{
  min-height:96px;
}}

.proposal-primary-actions {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:14px;
}}

.proposal-action-row {{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:12px;
}}

.proposal-divider {{
  height:1px;
  background:var(--border);
}}

.proposal-accept,
.proposal-retry,
.proposal-dismiss {{
  min-height:42px;
  border-radius:10px;
  padding:0 15px;
  font:inherit;
  font-size:.86rem;
  font-weight:750;
  cursor:pointer;
}}

.proposal-accept {{
  border:0;
  background:var(--navy);
  color:white;
}}

.proposal-retry {{
  border:1px solid var(--navy);
  background:white;
  color:var(--navy);
}}

.proposal-dismiss {{
  border:0;
  background:transparent;
  color:var(--muted);
  padding-left:8px;
  padding-right:8px;
}}

.proposal-dismiss:hover {{
  text-decoration:underline;
}}

@media (max-width:640px) {{
  .proposal-card {{
    padding:18px;
  }}

  .proposal-primary-actions {{
    align-items:flex-start;
    flex-direction:column;
  }}

  .proposal-primary-actions .proposal-accept {{
    align-self:flex-end;
  }}
}}

.proposal-pending {{
  display:flex;
  align-items:center;
  gap:12px;
  padding:12px 0 4px;
}}
.proposal-pending-note {{
  margin-top:3px;
  color:var(--muted);
  font-size:.84rem;
}}
.proposal-spinner {{
  width:18px;
  height:18px;
  flex:0 0 auto;
  border:2px solid var(--border);
  border-top-color:var(--navy);
  border-radius:50%;
  animation:proposal-spin .8s linear infinite;
}}
@keyframes proposal-spin {{
  to {{ transform:rotate(360deg); }}
}}
.project-work-results {{ scroll-margin-top:24px; }}
</style>
</head>
<body>
<main>
  <div style="display:flex;justify-content:space-between;gap:16px"><a class="back" href="/projects">← Projects</a><a class="back" href="/">Home</a></div>
  <a href="/tasks/new" style="color:var(--navy);text-decoration:none;font-weight:750;margin-top:10px;margin-left:14px">New Task</a>
  <div class="header">
    <h1>{name}</h1>
    <div class="summary">
      <span>{count} open task{"s" if count != 1 else ""}</span>
      {status_html}
    </div>
  </div>

  <section class="context-card">
    <h2>Project outcome</h2>
    <p class="context-note">
      Describe what done looks like for this project. AIOS will use this to reason about remaining work.
    </p>
    <form method="post" action="/projects/{project_id}/outcome">
      <textarea name="outcome" placeholder="What outcome should this project achieve?">{outcome}</textarea>
      <div class="context-actions">
        <button class="context-save" type="submit">Save outcome</button>
      </div>
    </form>
  </section>

  <section class="context-card">
    <h2>Project context</h2>
    <p class="context-note">
      Durable facts, decisions, and constraints AIOS should use when reasoning about this project.
    </p>
    <form method="post" action="/projects/{project_id}/context">
      <textarea name="context" placeholder="Add project facts, decisions, constraints, dates, people, or other useful context.">{context}</textarea>
      <div class="context-actions">
        <button class="context-save" type="submit">Save context</button>
      </div>
    </form>
  </section>

  <section class="context-card">
    <h2>Project work</h2>
    <p class="context-note">
      Ask AIOS to look for genuinely missing actionable work using the project outcome, context, and full task history. Existing open and completed tasks are treated as work already planned or done.
    </p>
    <form method="post" action="/projects/{project_id}/work-proposals/generate">
      <div class="context-actions">
        <button class="context-save" type="submit">Generate Project Work</button>
      </div>
    </form>
  </section>

  <div id="project-work-results" class="project-work-results">
  {
      (
          '<section class="proposal-card">'
          '<h2>Proposed project work</h2>'
          '<p class="proposal-note">'
          'AIOS found grounded work that could move this project forward. '
          'Review it before creating a real task.'
          '</p>'
          + proposal_rows
          + '</section>'
      )
      if proposal_rows and not proposal_pending
      else ''
  }

  {pending_html}
  {generation_result_html}
  </div>

  <div class="task-list" id="project-tasks">{task_rows}</div>
</main>
{pending_refresh_script}
</body>
</html>"""


def _possible_duplicate_new_task_page(review: dict) -> str:
    payload = review.get("payload") or {}
    title = html.escape(
        str(review.get("subject_text") or payload.get("original_text") or "")
    )
    original = html.escape(
        str(payload.get("original_text") or review.get("subject_text") or "")
    )
    candidate_title = html.escape(
        str(payload.get("candidate_task_title") or "")
    )
    reason = html.escape(str(payload.get("semantic_reason") or ""))

    try:
        score = float(payload.get("match_score"))
        score_text = f"{round(score * 100)}% match"
    except (TypeError, ValueError):
        score_text = ""

    comparison_html = ""
    if candidate_title:
        comparison_html = (
            '<div class="label">Possible existing task</div>'
            f'<div class="value">{candidate_title}'
            + (f' <span class="muted">{html.escape(score_text)}</span>' if score_text else '')
            + '</div>'
        )

    reason_html = ""
    if reason:
        reason_html = (
            '<div class="label">Why AIOS flagged it</div>'
            f'<div class="value">{reason}</div>'
        )

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#264155">
<title>AIOS New Task Review</title>
<style>
:root {{--navy:#264155;--paper:#f7f7f3;--ink:#17242d;--muted:#66747d;--border:#d9dedf;--card:#fff;}}
* {{box-sizing:border-box;}}
body {{margin:0;background:var(--paper);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}}
main {{width:min(760px,100%);margin:0 auto;padding:max(26px,env(safe-area-inset-top)) 18px 42px;}}
.back {{color:var(--navy);text-decoration:none;font-weight:750;}}
h1 {{margin:24px 0 6px;color:var(--navy);font-size:clamp(2rem,6vw,2.7rem);letter-spacing:-.03em;}}
.intro {{margin:0 0 22px;color:var(--muted);line-height:1.45;}}
.card {{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;margin-top:16px;}}
.label {{color:var(--muted);font-size:.78rem;font-weight:800;text-transform:uppercase;letter-spacing:.03em;margin-top:16px;}}
.label:first-child {{margin-top:0;}}
.value {{margin-top:5px;font-size:1rem;line-height:1.45;}}
.title {{font-size:1.18rem;font-weight:750;color:var(--navy);}}
.muted {{color:var(--muted);font-size:.88rem;}}
</style>
</head>
<body>
<main>
  <a class="back" href="/reviews">← Review</a>
  <h1>New task</h1>
  <p class="intro">This task has not been created yet. AIOS is holding it for your duplicate decision.</p>
  <section class="card">
    <div class="label">Proposed task</div>
    <div class="value title">{title}</div>
    <div class="label">Original Brain Dump</div>
    <div class="value">{original}</div>
    {comparison_html}
    {reason_html}
  </section>
</main>
</body>
</html>'''


def _reviews_page(
    reviews: list[dict],
    *,
    notices: list[dict] | None = None,
    error: str = "",
) -> str:
    notices = notices or []
    possible_duplicates = [
        review
        for review in reviews
        if review.get("review_type") == "possible_duplicate"
        and review.get("state") != "resolved"
    ]

    clarifications = [
        review
        for review in reviews
        if review.get("review_type") == "clarification"
        and review.get("state") != "resolved"
    ]

    cards = ""
    reevaluation_pending = False
    duplicate_creation_pending = False
    clarification_processing_pending = False

    for review in possible_duplicates:
        review_id = html.escape(str(review.get("id") or ""))
        subject = html.escape(
            str(review.get("subject_text") or "")
        )

        payload = review.get("payload") or {}

        candidate_id = html.escape(
            str(payload.get("candidate_task_id") or "")
        )
        candidate_title = html.escape(
            str(payload.get("candidate_task_title") or "")
        )

        candidate_changed = bool(
            payload.get("candidate_task_changed")
            or payload.get("source_task_changed")
        )

        if candidate_changed:
            score_html = (
                '<span class="review-score">'
                'Task changed since this match was evaluated'
                '</span>'
            )

            requested_action = str(
                payload.get("requested_action") or ""
            ).strip()

            if requested_action == "reevaluate":
                reevaluation_pending = True

                use_existing_html = (
                    '<div class="review-pending">'
                    '<span class="review-spinner" aria-hidden="true"></span>'
                    '<div>'
                    '<strong>Re-evaluating match…</strong>'
                    '<div class="review-stale-note">'
                    'AIOS is checking the updated tasks against each other.'
                    '</div>'
                    '</div>'
                    '</div>'
                )

                create_new_html = ""

            else:
                use_existing_html = f"""
                <div class="review-stale-note">
                  Re-evaluate this match before resolving it.
                </div>
                <form method="post"
                      action="/reviews/{review_id}/possible-duplicate/reevaluate">
                  <button class="review-primary" type="submit">
                    Re-evaluate match
                  </button>
                </form>
                """

                create_new_html = f"""
                <form method="post"
                      action="/reviews/{review_id}/possible-duplicate/create-new">
                  <button class="review-secondary" type="submit">
                    Keep as separate tasks
                  </button>
                </form>
                """

        else:
            try:
                score = float(payload.get("match_score"))
                score_text = f"{round(score * 100)}% match"
            except (TypeError, ValueError):
                score_text = ""

            score_html = (
                f'<span class="review-score">'
                f'{html.escape(score_text)}</span>'
                if score_text
                else ""
            )

            requested_action = str(
                payload.get("requested_action") or ""
            ).strip()

            if requested_action == "create_anyway":
                duplicate_creation_pending = True
                use_existing_html = (
                    '<div class="review-pending">'
                    '<span class="review-spinner" aria-hidden="true"></span>'
                    '<div><strong>Creating separate task…</strong>'
                    '<div class="review-stale-note">'
                    'AIOS is keeping both tasks and finishing the new task creation.'
                    '</div></div></div>'
                )
                create_new_html = ""
            else:
                use_existing_html = f'''
                <form method="post"
                      action="/reviews/{review_id}/possible-duplicate/use-existing">
                  <input type="hidden"
                         name="candidate_task_id"
                         value="{candidate_id}">
                  <input type="hidden"
                         name="candidate_task_title"
                         value="{candidate_title}">
                  <input type="hidden"
                         name="title_choice"
                         value="existing">
                  <button class="review-primary" type="submit">
                    Use existing task
                  </button>
                </form>

                <form method="post"
                      action="/reviews/{review_id}/possible-duplicate/use-existing">
                  <input type="hidden"
                         name="candidate_task_id"
                         value="{candidate_id}">
                  <input type="hidden"
                         name="candidate_task_title"
                         value="{candidate_title}">
                  <input type="hidden"
                         name="title_choice"
                         value="new">
                  <button class="review-secondary" type="submit">
                    Replace with new wording
                  </button>
                </form>
                '''

                create_new_html = f"""
                <form method="post"
                      action="/reviews/{review_id}/possible-duplicate/create-new">
                  <button class="review-secondary" type="submit">
                    Keep as separate tasks
                  </button>
                </form>
                """

        cards += f'''
        <section class="review-card">
          <div class="review-label">Possible duplicate</div>

          <div class="review-section-label">Existing task</div>
          <div class="review-existing">
            <strong>
              <a class="review-task-link"
                 href="/tasks/{candidate_id}?return_to=%2Freviews">
                {candidate_title}
              </a>
            </strong>
            {score_html}
          </div>

          <div class="review-section-label">New task</div>
          <div class="review-task">
            <a class="review-task-link"
               href="/reviews/{review_id}/possible-duplicate/new-task">
              {subject}
            </a>
          </div>

          <div class="review-actions">
            {use_existing_html}
            {create_new_html}
          </div>
        </section>
        '''

    for review in clarifications:
        review_id = html.escape(
            str(review.get("id") or "")
        )

        payload = review.get("payload") or {}

        task_id = html.escape(
            str(
                payload.get("task_id")
                or ""
            ),
            quote=True,
        )

        state = str(
            review.get("state") or "pending"
        ).strip()

        requested_action = str(
            payload.get("requested_action")
            or ""
        ).strip()

        original_text = html.escape(
            str(
                payload.get("original_text")
                or review.get("subject_text")
                or ""
            )
        )

        proposed_raw = str(
            payload.get("proposed_text")
            or ""
        ).strip()

        proposed_text = html.escape(
            proposed_raw
        )

        # -------------------------------------------------------------
        # Processor is generating the targeted question.
        # -------------------------------------------------------------
        if (
            state == "pending"
            and requested_action == "ask_question"
        ):
            clarification_processing_pending = True

            clarification_action_html = """
            <div class="review-pending">
              <span class="review-spinner"
                    aria-hidden="true"></span>
              <div>
                <strong>
                  Generating one targeted question…
                </strong>
                <div class="review-stale-note">
                  AIOS is identifying the one piece of
                  information it needs most.
                </div>
              </div>
            </div>
            """

        # -------------------------------------------------------------
        # Initial proposal.
        # -------------------------------------------------------------
        elif state == "pending":
            selected_value = html.escape(
                proposed_raw,
                quote=True,
            )

            clarification_action_html = f"""
            <form method="post"
                  action="/reviews/{review_id}/clarification/use">
              <input type="hidden"
                     name="selected_text"
                     value="{selected_value}">

              <label class="review-section-label"
                     for="clarification-{review_id}">
                AIOS suggests this clearer next action
              </label>

              <textarea
                id="clarification-{review_id}"
                class="clarification-edit"
                name="accepted_text"
                required>{proposed_text}</textarea>

              <div class="review-stale-note">
                You can edit the wording before accepting it.
              </div>

              <div class="review-actions">
                <button class="review-primary"
                        type="submit">
                  Use this clarification
                </button>
              </div>
            </form>

            <form method="post"
                  action="/reviews/{review_id}/clarification/request-question">
              <div class="review-actions">
                <button class="review-secondary"
                        type="submit">
                  Ask me one targeted question
                </button>
              </div>
            </form>
            """

        # -------------------------------------------------------------
        # Processor is converting the user's answer to a proposal.
        # -------------------------------------------------------------
        elif (
            state == "awaiting_answer"
            and requested_action == "process_answer"
        ):
            clarification_processing_pending = True

            clarification_action_html = """
            <div class="review-pending">
              <span class="review-spinner"
                    aria-hidden="true"></span>
              <div>
                <strong>
                  Turning your answer into a clearer task…
                </strong>
                <div class="review-stale-note">
                  AIOS is preparing a revised next action
                  for you to review.
                </div>
              </div>
            </div>
            """

        # -------------------------------------------------------------
        # Targeted question ready for the user.
        # -------------------------------------------------------------
        elif state == "awaiting_answer":
            question = html.escape(
                str(payload.get("question") or "")
            )

            clarification_action_html = f"""
            <div class="review-section-label">
              One targeted question
            </div>

            <div class="review-existing">
              {question}
            </div>

            <form method="post"
                  action="/reviews/{review_id}/clarification/answer">
              <label class="review-section-label"
                     for="clarification-answer-{review_id}">
                Your answer
              </label>

              <textarea
                id="clarification-answer-{review_id}"
                class="clarification-edit"
                name="answer"
                placeholder="Type your answer here"
                required></textarea>

              <div class="review-actions">
                <button class="review-primary"
                        type="submit">
                  Continue
                </button>
              </div>
            </form>
            """

        # -------------------------------------------------------------
        # Revised proposal after the targeted answer.
        # -------------------------------------------------------------
        elif state == "pending_confirmation":
            selected_value = html.escape(
                proposed_raw,
                quote=True,
            )

            answer = html.escape(
                str(payload.get("answer") or "")
            )

            clarification_action_html = f"""
            <div class="review-section-label">
              Your clarification
            </div>
            <div class="review-existing">
              {answer}
            </div>

            <form method="post"
                  action="/reviews/{review_id}/clarification/use">
              <input type="hidden"
                     name="selected_text"
                     value="{selected_value}">

              <label class="review-section-label"
                     for="clarification-{review_id}">
                AIOS suggests this revised next action
              </label>

              <textarea
                id="clarification-{review_id}"
                class="clarification-edit"
                name="accepted_text"
                required>{proposed_text}</textarea>

              <div class="review-stale-note">
                You can edit the wording before accepting it.
              </div>

              <div class="review-actions">
                <button class="review-primary"
                        type="submit">
                  Use this clarification
                </button>
              </div>
            </form>
            """

        else:
            clarification_action_html = ""

        cards += f"""
        <section class="review-card">
          <div class="review-label">
            Clarification needed
          </div>

          <div class="review-section-label">
            Original task
          </div>

          <div class="review-task-row">
            {
                f'<a class="review-task-link" '
                f'href="/tasks/{task_id}?return_to=%2Freviews">'
                f'{original_text}</a>'
                if task_id
                else f'<div class="review-task">{original_text}</div>'
            }

            {
                f'<form method="post" '
                f'action="/reviews/{review_id}/clarification/delete-task" '
                f'onsubmit="return confirm(&quot;Delete this task?&quot;);">'
                f'<button class="review-delete-button" '
                f'type="submit" '
                f'aria-label="Delete task" '
                f'title="Delete task">🗑️</button>'
                f'</form>'
                if task_id
                else ''
            }
          </div>

          {clarification_action_html}
        </section>
        """

    if not cards:
        cards = (
            '<div class="empty-state">'
            'No possible duplicate reviews need attention.'
            '</div>'
        )

    auto_notice_html = ""

    for auto_notice in notices:
        notice_id = html.escape(
            str(auto_notice.get("id") or "")
        )
        candidate_title = html.escape(
            str(
                auto_notice.get(
                    "candidate_task_title"
                )
                or ""
            )
        )

        try:
            score = float(
                auto_notice.get("match_score")
            )
            score_text = (
                f" ({round(score * 100)}% match)"
            )
        except (TypeError, ValueError):
            score_text = ""

        auto_notice_html += f"""
        <div class="auto-merge-notice"
             data-auto-merge-id="{notice_id}">
          <strong>Merged automatically</strong>
          <div>
            AIOS matched this task to
            <strong>{candidate_title}</strong>{score_text}
            and kept the existing wording.
          </div>
        </div>
        """

    notice = (
        '<div class="notice">'
        + html.escape(error)
        + '</div>'
        if error
        else ""
    )

    if (
        reevaluation_pending
        or duplicate_creation_pending
        or clarification_processing_pending
    ):
        pending_refresh_script = """
<script>
(() => {
  const key = "aios-review-processing-refresh-count";
  const count = Number(sessionStorage.getItem(key) || "0");

  if (count < 45) {
    sessionStorage.setItem(key, String(count + 1));
    setTimeout(() => window.location.reload(), 2000);
  }
})();
</script>
"""
    else:
        pending_refresh_script = """
<script>
sessionStorage.removeItem(
  "aios-review-processing-refresh-count"
);
</script>
"""

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#264155">
<title>AIOS Review</title>
<style>
:root {{
  --navy:#264155;
  --paper:#f7f7f3;
  --ink:#17242d;
  --muted:#66747d;
  --border:#d9dedf;
  --card:#fff;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0;
  background:var(--paper);
  color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}}
main {{
  width:min(760px,100%);
  margin:0 auto;
  padding:max(26px,env(safe-area-inset-top)) 18px 42px;
}}
.back {{
  color:var(--navy);
  text-decoration:none;
  font-weight:750;
}}
h1 {{
  margin:22px 0 6px;
}}
.intro {{
  margin:0 0 22px;
  color:var(--muted);
}}
.auto-merge-notice {{
  display:none;
  background:#fff;
  border:1px solid var(--border);
  border-left:4px solid var(--navy);
  border-radius:12px;
  padding:14px 16px;
  margin:0 0 16px;
  line-height:1.45;
}}
.auto-merge-notice strong {{
  color:var(--navy);
}}
.auto-merge-notice > strong {{
  display:block;
  margin-bottom:4px;
}}
.review-task-row {{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:12px;
  margin-bottom:4px;
}}
.review-task-row .review-task-link {{
  flex:1;
  font-size:1.05rem;
}}
.review-delete-button {{
  width:40px;
  height:40px;
  flex:0 0 40px;
  padding:0;
  border:0;
  border-radius:9px;
  background:transparent;
  cursor:pointer;
  font-size:1rem;
  opacity:.68;
}}
.review-delete-button:hover,
.review-delete-button:focus-visible {{
  opacity:1;
  background:#eceeed;
}}
.clarification-edit {{
  width:100%;
  min-height:88px;
  margin:8px 0 4px;
  padding:11px 12px;
  border:1px solid var(--border);
  border-radius:10px;
  background:#fff;
  color:var(--ink);
  font:inherit;
  line-height:1.45;
  resize:vertical;
}}
.clarification-edit:focus {{
  outline:2px solid rgba(38,65,85,.18);
  border-color:var(--navy);
}}
.review-card {{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:14px;
  padding:18px;
  margin-bottom:14px;
}}
.review-label {{
  color:var(--muted);
  font-size:.8rem;
  font-weight:800;
  text-transform:uppercase;
  letter-spacing:.03em;
  margin-bottom:16px;
}}
.review-section-label {{
  color:var(--muted);
  font-size:.78rem;
  font-weight:750;
  margin-top:10px;
}}
.review-task,
.review-existing {{
  margin-top:4px;
  font-size:1rem;
  line-height:1.4;
}}
.review-existing {{
  display:flex;
  gap:9px;
  align-items:baseline;
  flex-wrap:wrap;
}}
.review-task-link {{
  color:var(--navy);
  text-decoration:none;
}}
.review-task-link:hover {{
  text-decoration:underline;
}}
.review-score {{
  color:var(--muted);
  font-size:.82rem;
}}
.review-pending {{
  display:flex;
  gap:12px;
  align-items:center;
  padding:8px 0;
}}
.review-spinner {{
  width:20px;
  height:20px;
  flex:0 0 20px;
  border:3px solid var(--border);
  border-top-color:var(--navy);
  border-radius:50%;
  animation:review-spin .8s linear infinite;
}}
@keyframes review-spin {{
  to {{ transform:rotate(360deg); }}
}}
.review-stale-note {{
  color:var(--muted);
  font-size:.88rem;
  line-height:1.4;
  padding:8px 0;
}}
.review-actions {{
  display:flex;
  gap:9px;
  flex-wrap:wrap;
  margin-top:18px;
}}
.review-actions form {{
  margin:0;
}}
.review-primary,
.review-secondary {{
  border-radius:9px;
  padding:8px 12px;
  font:inherit;
  font-weight:750;
  cursor:pointer;
}}
.review-primary {{
  border:1px solid var(--navy);
  background:var(--navy);
  color:white;
}}
.review-secondary {{
  border:1px solid var(--border);
  background:white;
  color:var(--navy);
}}
.empty-state {{
  padding:20px;
  background:white;
  border:1px solid var(--border);
  border-radius:12px;
  color:var(--muted);
}}
.notice {{
  margin:14px 0;
  padding:12px;
  background:white;
  border:1px solid var(--border);
  border-radius:10px;
}}
</style>
</head>
<body>
<main>
  <a class="back" href="/">← Home</a>
  <h1>Review</h1>
  <p class="intro">
    Resolve tasks that AIOS thinks may already exist.
  </p>
  {notice}
  {auto_notice_html}
  {cards}
</main>
{pending_refresh_script}
<script>
(() => {{
  document
    .querySelectorAll(".auto-merge-notice")
    .forEach((notice) => {{
      const id = notice.dataset.autoMergeId;
      if (!id) return;

      const key = "aios-auto-merge-notice-" + id;

      if (sessionStorage.getItem(key)) {{
        notice.remove();
        return;
      }}

      notice.style.display = "block";
      sessionStorage.setItem(key, "seen");
    }});
}})();
</script>
</body>
</html>'''


def _fetch_reviews() -> list[dict]:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.get(
        f"{api_url}/reviews",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return list(response.json() or [])


def _fetch_review_notices() -> list[dict]:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.get(
        f"{api_url}/reviews/notices/recent",
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return list(
        (response.json() or {}).get(
            "notices",
            [],
        )
    )


def _request_possible_duplicate_reevaluation(
    review_id: str,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/reviews/{review_id}/possible-duplicate/reevaluate",
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict(response.json() or {})


def _request_possible_duplicate_create_new(
    review_id: str,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/reviews/{review_id}/possible-duplicate/create-new",
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict(response.json() or {})


def _resolve_possible_duplicate(
    review_id: str,
    *,
    action: str,
    candidate_task_id: str | None = None,
    candidate_task_title: str | None = None,
    title_choice: str | None = None,
    created_task_ids: list[str] | None = None,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/reviews/{review_id}/possible-duplicate",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "action": action,
            "candidate_task_id": candidate_task_id,
            "candidate_task_title": candidate_task_title,
            "title_choice": title_choice,
            "created_task_ids": created_task_ids or [],
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict(response.json() or {})


def _delete_clarification_task(
    review_id: str,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/reviews/{review_id}/clarification/delete-task",
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return dict(response.json() or {})


def _request_clarification_question(
    review_id: str,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/reviews/{review_id}/clarification/request-question",
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return dict(response.json() or {})


def _submit_clarification_answer(
    review_id: str,
    *,
    answer: str,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/reviews/{review_id}/clarification/answer",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "answer": answer,
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return dict(response.json() or {})


def _resolve_clarification(
    review_id: str,
    *,
    selected_text: str,
    accepted_text: str,
) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/reviews/{review_id}/clarification/resolve",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "selected_text": selected_text,
            "accepted_text": accepted_text,
        },
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned "
            f"{response.status_code}: "
            f"{response.text}"
        )

    return dict(response.json() or {})


def _fetch_project_options() -> list[dict]:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.get(
        f"{api_url}/projects",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return list((response.json() or {}).get("projects") or [])


def _create_task(payload: dict) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/tasks",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"AIOS API returned {response.status_code}: {response.text}"
        )

    return dict((response.json() or {}).get("task") or {})


def _create_task_page(
    projects: list[dict],
    *,
    error: str = "",
) -> str:
    options = '<option value="">No project</option>'

    for project in projects:
        project_id = html.escape(str(project.get("id") or ""))
        name = html.escape(str(project.get("name") or "Untitled Project"))
        options += f'<option value="{project_id}">{name}</option>'

    notice = (
        '<div class="notice error">' + html.escape(error) + '</div>'
        if error else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#264155">
<title>New Task · AIOS</title>
<style>
:root {{
  --navy:#264155; --yellow:#ffc93c; --paper:#f7f7f3;
  --ink:#17242d; --muted:#66747d; --border:#d9dedf;
  --card:#fff; --error:#fae9e7;
}}
* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}}
main {{
  width:min(760px,100%); margin:0 auto;
  padding:max(26px,env(safe-area-inset-top)) 18px 42px;
}}
.header {{
  display:flex; justify-content:space-between; align-items:flex-start;
  gap:16px; margin-bottom:22px;
}}
h1 {{
  margin:0; color:var(--navy); font-size:clamp(2rem,5vw,2.7rem);
  letter-spacing:-.035em;
}}
.subtitle {{ margin:7px 0 0; color:var(--muted); }}
.home-link {{
  color:var(--navy); text-decoration:none; font-weight:750; margin-top:8px;
}}
.notice {{ padding:12px 14px; border-radius:12px; margin-bottom:16px; }}
.error {{ background:var(--error); }}
.card {{
  background:var(--card); border:1px solid var(--border);
  border-radius:18px; padding:22px;
  box-shadow:0 10px 30px rgba(38,65,85,.06);
}}
.grid {{
  display:grid; grid-template-columns:1fr 1fr; gap:16px;
}}
.full {{ grid-column:1/-1; }}
label {{
  display:grid; gap:7px; color:var(--ink); font-size:.88rem; font-weight:700;
}}
input[type="text"], input[type="date"], select {{
  width:100%; min-height:46px; border:1px solid var(--border);
  border-radius:12px; padding:0 13px; background:#fff;
  color:var(--ink); font:inherit;
}}
.checkbox-row {{
  display:flex; align-items:center; gap:10px; min-height:44px;
}}
.checkbox-row input {{
  width:20px; height:20px; accent-color:var(--yellow);
}}
.actions {{
  display:flex; gap:10px; margin-top:20px;
}}
button {{
  min-height:46px; border:0; border-radius:12px;
  padding:0 18px; background:var(--yellow);
  color:var(--navy); font:inherit; font-weight:800; cursor:pointer;
}}
.cancel {{
  min-height:46px; display:inline-flex; align-items:center;
  padding:0 14px; border:1px solid var(--border); border-radius:12px;
  color:var(--navy); text-decoration:none; font-weight:700; background:#fff;
}}
@media (max-width:600px) {{
  .grid {{ grid-template-columns:1fr; }}
  .full {{ grid-column:auto; }}
}}
</style>
</head>
<body>
<main>
  <div class="header">
    <div>
      <h1>New Task</h1>
      <p class="subtitle">Create a task directly when you already know what needs to be done.</p>
    </div>
    <a class="home-link" href="/">Home</a>
  </div>

  {notice}

  <form method="post" action="/tasks/new">
    <section class="card">
      <div class="grid">
        <label class="full">
          Task
          <input type="text" name="title" required autofocus>
        </label>

        <label>
          Due date
          <input type="date" name="due_at">
        </label>

        <label>
          Defer until
          <input type="date" name="defer_until">
        </label>

        <label>
          Importance
          <input type="text" name="importance" placeholder="e.g. High Importance">
        </label>

        <label>
          Urgency
          <input type="text" name="urgency">
        </label>

        <label>
          Effort
          <input type="text" name="effort" placeholder="e.g. Small Effort">
        </label>

        <label>
          Duration
          <input type="text" name="duration" placeholder="e.g. 15 min">
        </label>

        <label class="full">
          Project
          <select name="project_id">{options}</select>
        </label>

        <label class="full">
          Just Do It
          <span class="checkbox-row">
            <input type="checkbox" name="is_just_do_it" value="true">
            <span>Mark this task as Just Do It</span>
          </span>
        </label>
      </div>

      <div class="actions">
        <button type="submit">Create Task</button>
        <a class="cancel" href="/">Cancel</a>
      </div>
    </section>
  </form>
</main>
</body>
</html>"""


def _page(
    *,
    message: str = "",
    error: str = "",
    tasks: dict[str, list[dict]] | None = None,
    search: str = "",
    focus: dict | None = None,
    refresh_focus: bool = False,
    review_count: int = 0,
) -> str:
    tasks = tasks or {}
    focus_id = str(focus.get("id") or "") if focus else ""

    def render_task(task: dict) -> str:
        title = html.escape(
            str(task.get("title") or "Untitled task")
        )
        task_id = html.escape(str(task.get("id") or ""))
        due_at = str(task.get("due_at") or "").strip()
        importance = str(task.get("importance") or "").strip()
        score = task.get("execution_score")
        rank = task.get("execution_rank")

        meta_parts = []

        if score is not None:
            meta_parts.append(
                f"Score {html.escape(str(score))}"
            )

        if rank is not None:
            meta_parts.append(
                f"Rank {html.escape(str(rank))}"
            )

        if importance:
            meta_parts.append(
                html.escape(importance)
            )

        if due_at:
            meta_parts.append(
                f"Due {html.escape(due_at[:10])}"
            )

        if task.get("best_next_action"):
            meta_parts.append("Best Next Action")
        elif task.get("surfaced_quick_win"):
            meta_parts.append("Surfaced Quick Win")

        if task.get("is_just_do_it"):
            meta_parts.append("Just Do It")

        meta = " · ".join(meta_parts)
        meta_html = (
            f'<div class="task-meta">{meta}</div>'
            if meta
            else ""
        )

        return (
            '<article class="task-row">'
            + f'<form class="complete-form" method="post" action="/tasks/{task_id}/complete">'
            + '<button class="complete-checkbox" type="submit" aria-label="Mark task done" title="Mark done">'
            + '<span aria-hidden="true"></span></button></form>'
            + '<div class="task-main">'
            + f'<div class="task-title"><a class="task-link" href="/tasks/{task_id}">{title}</a></div>'
            + meta_html
            + '</div>'
            + f'<form class="delete-form" method="post" action="/tasks/{task_id}/delete" '
            + 'onsubmit="return confirm(&quot;Delete this task?&quot;);">'
            + '<button class="trash-button" type="submit" aria-label="Delete task" title="Delete task">'
            + '<span aria-hidden="true">🗑️</span></button></form>'
            + '</article>'
        )

    section_specs = (
        [(f'Search Results for “{search}”', "search_results")]
        if search
        else [
            ("Top 5", "top5"),
            ("Quick Wins", "quick_wins"),
            ("Today", "today"),
            ("Just Do It", "just_do_it"),
        ]
    )

    task_sections = ""

    for heading, key in section_specs:
        section_tasks = tasks.get(key, [])
        # Rank 1 is presented separately as the Best Next Action. Today is
        # intentionally allowed to overlap because it is the complete calendar
        # view of tasks due today or overdue.
        if focus_id and key not in {"today", "search_results"}:
            section_tasks = [task for task in section_tasks if str(task.get("id") or "") != focus_id]
        if not section_tasks:
            continue

        rows_html = "".join(
            render_task(task)
            for task in section_tasks
        )

        search_open = ' open' if key == "search_results" else ''
        task_sections += (
            f'<details class="task-group" data-section="{html.escape(key)}"'
            + (' id="search-results"' if key == "search_results" else '')
            + f'{search_open}>'
            f'<summary class="task-group-heading">'
            f'<span>{html.escape(heading)}</span>'
            f'<span class="section-count">{len(section_tasks)}</span>'
            f'</summary>'
            + rows_html
            + "</details>"
        )

    if not task_sections:
        task_sections = (
            '<div class="empty-state">'
            'No matching tasks found.'
            '</div>'
        )

    focus_card = ""
    focus_id = ""

    activation = (
        dict(focus.get("activation") or {})
        if focus
        else {}
    )
    activation_id = str(activation.get("id") or "")
    refresh_pending = bool(
        refresh_focus
        and (
            not focus
            or bool(focus.get("activation_pending"))
            or not activation_id
        )
    )

    if refresh_pending:
        focus_card = (
            '<section class="focus-card">'
            '<div class="focus-label">⭐ Best Next Action</div>'
            '<div class="focus-pending"><span class="mini-spinner"></span> Updating your focus…</div>'
            '</section>'
        )

    if focus and not refresh_pending:
        focus_id = str(focus.get("id") or "")
        safe_id = html.escape(focus_id)
        title = html.escape(str(focus.get("title") or "Untitled task"))
        meta = []
        if focus.get("execution_rank") is not None: meta.append(f"Rank {html.escape(str(focus.get('execution_rank')))}")
        if focus.get("execution_score") is not None: meta.append(f"Score {html.escape(str(focus.get('execution_score')))}")
        if focus.get("importance"): meta.append(html.escape(str(focus.get("importance"))))

        activation_title = str(activation.get("title") or "").strip()
        activation_pending = bool(focus.get("activation_pending"))

        # Activation child is canonical. Never fall back to stale legacy
        # guidance while the processor is generating the next activation.
        if activation_title:
            starter = activation_title
        elif activation_pending:
            starter = ""
        else:
            starter = str(
                focus.get("starter_step") or ""
            ).strip()

        activation_duration = str(activation.get("duration") or "").strip()
        if activation_pending:
            timebox_text = ""
        elif activation_duration:
            timebox_text = activation_duration
        else:
            legacy_minutes = focus.get("starter_minutes")
            timebox_text = (
                f"{legacy_minutes} min"
                if legacy_minutes
                else ""
            )

        starter_html = ""

        if activation_pending:
            starter_html = (
                '<div class="focus-start">'
                '<div class="focus-start-label">Start here</div>'
                '<div class="focus-pending">'
                'Finding your next step…'
                '</div>'
                '</div>'
            )

        if starter:
            if activation_id:
                safe_activation_id = html.escape(activation_id)
                starter_html = (
                    '<div class="focus-start">'
                    '<div class="focus-start-label">Start here</div>'
                    '<div class="focus-start-row">'
                    f'<form class="complete-form focus-activation-complete" method="post" action="/tasks/{safe_activation_id}/complete">'
                    '<button class="complete-checkbox" type="submit" aria-label="Complete starting step" title="Complete starting step"><span aria-hidden="true"></span></button>'
                    '</form>'
                    '<div class="focus-start-main">'
                    f'<a class="focus-start-step" href="/tasks/{safe_activation_id}">{html.escape(starter)}</a>'
                    '</div>'
                    f'<form class="focus-not-now-form" method="post" action="/tasks/{safe_activation_id}/not-now">'
                    '<button class="focus-not-now" type="submit">Not now</button>'
                    '</form>'
                    '</div>'
                    '</div>'
                )
            else:
                starter_html = (
                    '<div class="focus-start">'
                    '<div class="focus-start-label">Start here</div>'
                    f'<div class="focus-start-step">{html.escape(starter)}</div>'
                    '</div>'
                )

        timebox_html = (
            f'<div class="focus-timebox">Give it {html.escape(timebox_text)}'
            '<span> — only for this starting move.</span></div>'
        ) if timebox_text else ""

        focus_card = (
            '<section class="focus-card">'
            '<div class="focus-label">⭐ Best Next Action</div>'
            '<div class="focus-task-row focus-parent-row">'
            f'<form class="complete-form focus-parent-complete" method="post" action="/tasks/{safe_id}/complete">'
            '<button class="complete-checkbox" type="submit" aria-label="Complete Best Next Action" title="Complete Best Next Action"><span aria-hidden="true"></span></button>'
            '</form>'
            '<div class="focus-main">'
            f'<a class="focus-title" href="/tasks/{safe_id}">{title}</a>'
            f'<div class="focus-meta">{" · ".join(meta)}</div>'
            '<div class="focus-parent-actions">'
            '<details class="focus-snooze">'
            '<summary>Snooze</summary>'
            '<div class="focus-snooze-menu">'
            f'<form method="post" action="/tasks/{safe_id}/snooze"><input type="hidden" name="preset" value="later_today"><button type="submit">Later today</button></form>'
            f'<form method="post" action="/tasks/{safe_id}/snooze"><input type="hidden" name="preset" value="tomorrow"><button type="submit">Tomorrow</button></form>'
            f'<form method="post" action="/tasks/{safe_id}/snooze"><input type="hidden" name="preset" value="three_days"><button type="submit">3 days</button></form>'
            f'<form method="post" action="/tasks/{safe_id}/snooze"><input type="hidden" name="preset" value="one_week"><button type="submit">1 week</button></form>'
            f'<form class="focus-snooze-date" method="post" action="/tasks/{safe_id}/snooze"><input type="hidden" name="preset" value="pick_date"><input type="date" name="custom_date" required><button type="submit">Pick date</button></form>'
            '</div></details></div></div>'
            f'<form class="delete-form focus-delete" method="post" action="/tasks/{safe_id}/delete" onsubmit="return confirm(&quot;Delete this task?&quot;);">'
            '<button class="trash-button" type="submit" aria-label="Delete task" title="Delete task"><span aria-hidden="true">🗑️</span></button></form>'
            '</div>'
            + starter_html
            + timebox_html
            + '</section>'
        )

    notice = ""
    if message:
        notice = (
            '<div class="notice success">'
            + html.escape(message)
            + "</div>"
        )
    elif error:
        notice = (
            '<div class="notice error">'
            + html.escape(error)
            + "</div>"
        )

    pending_refresh_script = ""

    refresh_needed = refresh_pending

    if refresh_needed:
        pending_refresh_script = """
<script>
(() => {
  const key = "aios-focus-activation-refresh-count";
  const count = Number(sessionStorage.getItem(key) || "0");
  if (count < 10) {
    sessionStorage.setItem(key, String(count + 1));
    setTimeout(() => window.location.reload(), 2000);
  }
})();
</script>
"""
    else:
        pending_refresh_script = """
<script>
sessionStorage.removeItem("aios-focus-activation-refresh-count");
</script>
"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#264155">
  <title>AIOS Brain Dump</title>
  <style>
    :root {{
      color-scheme: light;
      --navy: #264155;
      --yellow: #ffc93c;
      --paper: #f7f7f3;
      --ink: #17242d;
      --muted: #66747d;
      --border: #d9dedf;
      --success: #e8f4e8;
      --error: #fae9e7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--paper);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(720px, 100%);
      margin: 0 auto;
      padding: max(24px, env(safe-area-inset-top)) 18px
               max(32px, env(safe-area-inset-bottom));
    }}
    .dashboard-header {{
      display:flex;
      justify-content:space-between;
      align-items:flex-start;
      gap:18px;
      margin-bottom:22px;
    }}
    .dashboard-subtitle {{
      margin:4px 0 0;
      color:var(--muted);
      font-size:.98rem;
    }}
    .dashboard-nav {{
      display:flex;
      align-items:center;
      gap:10px;
      margin-top:7px;
    }}
    .dashboard-nav a {{
      min-height:40px;
      display:inline-flex;
      align-items:center;
      padding:0 13px;
      border-radius:10px;
      color:var(--navy);
      text-decoration:none;
      font-weight:750;
      white-space:nowrap;
    }}
    .dashboard-nav a:hover {{ background:#eceeed; }}
    .dashboard-nav .new-task-link {{ background:var(--yellow); }}
    .dashboard-nav .new-task-link:hover {{ background:#f6bf2d; }}
    .capture-heading {{
      display:flex;
      justify-content:space-between;
      align-items:flex-end;
      margin-bottom:10px;
    }}
    .capture-heading h2 {{
      margin:0;
      color:var(--navy);
      font-size:1.2rem;
    }}
    .capture-heading p {{
      margin:4px 0 0;
      color:var(--muted);
      font-size:.86rem;
    }}
    .bna-card {{
      margin:0 0 20px;
      padding:18px 20px;
      border:1px solid rgba(255,201,60,.72);
      border-radius:16px;
      background:#fff8dc;
      box-shadow:0 4px 18px rgba(38,65,85,.05);
    }}
    .bna-eyebrow {{ margin-bottom:8px; color:var(--navy); font-size:.88rem; font-weight:800; }}
    .bna-title {{ display:inline-block; color:var(--ink); text-decoration:none; font-size:1.2rem; line-height:1.3; font-weight:800; }}
    .bna-title:hover {{ text-decoration:underline; }}
    .bna-context {{ margin-top:7px; color:var(--muted); font-size:.84rem; }}
    .bna-why {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:13px; color:var(--ink); font-size:.88rem; }}
    .bna-why-label {{ color:var(--navy); font-weight:800; }}
    .bna-open {{ display:inline-block; margin-top:13px; color:var(--navy); text-decoration:none; font-size:.86rem; font-weight:800; }}
    .bna-open:hover {{ text-decoration:underline; }}
    .focus-card {{ margin:0 0 20px; padding:18px 20px; border:1px solid rgba(255,201,60,.72); border-radius:16px; background:#fff8dc; box-shadow:0 4px 18px rgba(38,65,85,.05); }}
    .focus-label {{ margin-bottom:12px; color:var(--navy); font-size:.9rem; font-weight:850; }}
    .focus-task-row {{ display:grid; grid-template-columns:minmax(0,1fr) 44px; gap:10px; align-items:center; }}
    .focus-parent-row {{ grid-template-columns:44px minmax(0,1fr) 44px; }}
    .focus-main {{ min-width:0; }}
    .focus-title {{ color:var(--ink); text-decoration:none; font-size:1.25rem; line-height:1.3; font-weight:850; }}
    .focus-title:hover {{ text-decoration:underline; }}
    .focus-meta {{ margin-top:5px; color:var(--muted); font-size:.84rem; }}
    .focus-parent-actions {{ display:flex; gap:10px; margin-top:9px; }}
    .focus-snooze {{ position:relative; }}
    .focus-snooze > summary {{ list-style:none; cursor:pointer; color:var(--navy); font-size:.84rem; font-weight:800; }}
    .focus-snooze > summary::-webkit-details-marker {{ display:none; }}
    .focus-snooze > summary:hover {{ text-decoration:underline; }}
    .focus-snooze-menu {{ position:absolute; z-index:20; top:28px; left:0; width:210px; padding:8px; border:1px solid var(--border); border-radius:12px; background:white; box-shadow:0 8px 24px rgba(38,65,85,.14); }}
    .focus-snooze-menu form {{ display:block; margin:0; }}
    .focus-snooze-menu button {{ width:100%; border:0; border-radius:8px; background:transparent; color:var(--ink); font:inherit; font-size:.86rem; font-weight:700; text-align:left; cursor:pointer; padding:9px 10px; }}
    .focus-snooze-menu button:hover {{ background:#f3f4f2; }}
    .focus-snooze-date {{ display:grid !important; grid-template-columns:1fr auto; gap:6px !important; padding:6px 4px 2px; }}
    .focus-snooze-date input[type="date"] {{ width:100%; min-width:0; border:1px solid var(--border); border-radius:8px; padding:7px; font:inherit; font-size:.8rem; }}
    .focus-snooze-date button {{ width:auto; white-space:nowrap; }}
    .focus-start {{ margin:16px 44px 0 0; padding-top:14px; border-top:1px solid rgba(38,65,85,.12); }}
    .focus-start-label {{ color:var(--navy); font-size:.82rem; font-weight:850; text-transform:uppercase; letter-spacing:.04em; }}
    .focus-start-row {{ display:grid; grid-template-columns:44px minmax(0,1fr) auto; gap:10px; align-items:center; margin-top:8px; }}
    .focus-start-main {{ min-width:0; }}
    .focus-start-step {{ color:var(--ink); text-decoration:none; font-size:1rem; line-height:1.45; font-weight:700; }}
    .focus-start-step:hover {{ text-decoration:underline; }}
    .focus-not-now-form {{ display:block; }}
    .focus-not-now {{
      border:0; background:transparent; color:var(--muted);
      font:inherit; font-size:.84rem; font-weight:700;
      cursor:pointer; padding:7px 4px;
    }}
    .focus-not-now:hover {{ color:var(--navy); text-decoration:underline; }}
    .focus-timebox {{ margin:10px 44px 0 54px; color:var(--navy); font-size:.88rem; font-weight:800; }}
    .focus-timebox span {{ color:var(--muted); font-weight:500; }}
    .brand {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 8vw, 3.25rem);
      letter-spacing: -0.04em;
      color: var(--navy);
    }}
    .subtitle {{
      margin: 0 0 28px;
      color: var(--muted);
      font-size: 1rem;
    }}
    form {{
      display: grid;
      gap: 14px;
    }}
    textarea {{
      width: 100%;
      min-height: 150px;
      max-height: 280px;
      resize: vertical;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      background: white;
      color: var(--ink);
      font: inherit;
      font-size: 1.08rem;
      line-height: 1.5;
      box-shadow: 0 1px 2px rgba(0,0,0,.03);
    }}
    textarea:focus {{
      outline: 3px solid rgba(255,201,60,.35);
      border-color: var(--yellow);
    }}
    button {{
      min-height: 54px;
      border: 0;
      border-radius: 14px;
      background: var(--yellow);
      color: #17242d;
      font: inherit;
      font-weight: 750;
      font-size: 1.05rem;
      cursor: pointer;
    }}
    button:disabled {{
      opacity: .65;
      cursor: wait;
    }}
    .notice {{
      margin: 0 0 18px;
      padding: 13px 15px;
      border-radius: 12px;
      line-height: 1.35;
    }}
    .success {{ background: var(--success); }}
    .error {{ background: var(--error); }}
    .hint {{
      color: var(--muted);
      font-size: .9rem;
      text-align: center;
    }}

    .tasks-section {{ margin-top:38px; padding-top:28px; border-top:1px solid var(--border); }}
    .tasks-heading {{ margin:0 0 14px; font-size:1.35rem; color:var(--navy); }}
    .task-group {{ margin-top:24px; }}
    .task-group:first-of-type {{ margin-top:16px; }}
    .task-group-heading {{ margin:0; padding:0 0 7px; color:var(--navy); font-size:.92rem; font-weight:750; letter-spacing:.04em; text-transform:uppercase; border-bottom:2px solid var(--yellow); }}
    .task-search {{ display:flex; gap:10px; margin-bottom:14px; }}
    .task-search input {{ flex:1; min-width:0; min-height:44px; border:1px solid var(--border); border-radius:12px; padding:0 13px; background:white; color:var(--ink); font:inherit; }}
    .task-search button {{ min-height:44px; padding:0 16px; border-radius:12px; font-size:.95rem; }}
    .task-row {{ display:grid; grid-template-columns:44px minmax(0,1fr) 44px; gap:10px; align-items:center; padding:12px 0; border-bottom:1px solid var(--border); }}
    .task-title {{ font-size:1rem; line-height:1.35; }}
    .task-link {{ color:inherit; text-decoration:none; }}
    .task-link:hover {{ text-decoration:underline; }}
    .task-meta {{ margin-top:5px; color:var(--muted); font-size:.82rem; }}
    .task-main {{ min-width:0; }}
    .complete-form, .delete-form {{ display:flex; margin:0; align-items:center; justify-content:center; }}
    .complete-checkbox, .trash-button {{ width:44px; height:44px; min-height:44px; padding:0; border:0; border-radius:10px; background:transparent; display:flex; align-items:center; justify-content:center; cursor:pointer; }}
    .complete-checkbox span {{ width:22px; height:22px; border:2px solid var(--navy); border-radius:6px; background:white; display:block; }}
    .complete-checkbox:hover span, .complete-checkbox:focus-visible span {{ border-color:var(--yellow); box-shadow:0 0 0 3px rgba(255,201,60,.28); }}
    .complete-checkbox.is-completing span {{
      background:var(--yellow);
      border-color:var(--yellow);
      position:relative;
    }}
    .complete-checkbox.is-completing span::after {{
      content:"✓";
      position:absolute;
      inset:0;
      display:flex;
      align-items:center;
      justify-content:center;
      color:var(--navy);
      font-size:16px;
      font-weight:800;
      line-height:1;
    }}
    .trash-button {{ font-size:1.08rem; opacity:.72; }}
    .trash-button:hover, .trash-button:focus-visible {{ opacity:1; background:#eceeed; }}
    .tasks-toolbar {{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:16px;
      margin-bottom:8px;
    }}
    .section-toggle-controls {{
      display:flex;
      gap:6px;
    }}
    .section-toggle-controls button {{
      min-height:34px;
      width:auto;
      padding:0 10px;
      border:1px solid var(--border);
      border-radius:9px;
      background:white;
      color:var(--navy);
      font:inherit;
      font-size:.8rem;
      font-weight:700;
      cursor:pointer;
    }}
    details.task-group {{
      margin-top:18px;
    }}
    details.task-group > summary {{
      list-style:none;
      cursor:pointer;
      user-select:none;
    }}
    details.task-group > summary::-webkit-details-marker {{ display:none; }}
    details.task-group > summary.task-group-heading {{
      display:flex;
      justify-content:space-between;
      align-items:center;
      gap:12px;
      padding-bottom:9px;
      border-bottom:3px solid var(--yellow);
    }}
    details.task-group > summary.task-group-heading::after {{
      content:"▾";
      color:var(--muted);
      font-size:.9rem;
      margin-left:auto;
    }}
    details.task-group:not([open]) > summary.task-group-heading::after {{
      content:"▸";
    }}
    .section-count {{
      min-width:26px;
      height:26px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border-radius:999px;
      background:#eceeed;
      color:var(--navy);
      font-size:.76rem;
      font-weight:800;
    }}
    @media (max-width:560px) {{
      .dashboard-header {{ flex-direction:column; }}
      .dashboard-nav {{ margin-top:0; }}
      .tasks-toolbar {{ align-items:flex-start; }}
      .section-toggle-controls {{ flex-direction:column; }}
    }}
    .empty-state {{ padding:18px 0; color:var(--muted); }}
  </style>
</head>
<body>
  <main>
    <div class="dashboard-header">
      <div>
        <h1 class="brand">Dashboard</h1>
        <p class="dashboard-subtitle">Capture, prioritize, and act.</p>
      </div>
      <nav class="dashboard-nav" aria-label="Primary">
        <a href="/projects">Projects</a>
        <a href="/reviews">{f"Reviews ({review_count})" if review_count else "Reviews"}</a>
        <a class="new-task-link" href="/tasks/new">New Task</a>
      </nav>
    </div>
    {notice}
    {focus_card}
    <form method="post" action="/submit" onsubmit="submitButton.disabled=true;">
      <div class="capture-heading">
        <div>
          <h2>Brain Dump</h2>
          <p>One task per bullet. Send several at once.</p>
        </div>
      </div>
      <textarea
        id="brainDumpText"
        name="text"
        required
        autofocus
        maxlength="10000"
        placeholder="• First task&#10;• Second task"
        aria-label="Brain dump text"
      >• </textarea>
      <button id="submitButton" name="submitButton" type="submit">
        Submit to AIOS
      </button>
    </form>
    <p class="hint">AIOS will process this automatically.</p>
    <section class="tasks-section">
      <div class="tasks-toolbar">
        <h2 class="tasks-heading">Tasks</h2>
        <div class="section-toggle-controls">
          <button type="button" id="expandAllSections">Expand all</button>
          <button type="button" id="collapseAllSections">Collapse all</button>
        </div>
      </div>
      <form class="task-search" method="get" action="/">
        <input name="search" value="{html.escape(search)}" placeholder="Search open tasks" aria-label="Search open tasks">
        <button type="submit">Search</button>
        {('<a class="button secondary" href="/">Clear</a>' if search else '')}
      </form>
      {task_sections}
    </section>
  </main>
  <script>
    (() => {{
      const scrollKey = "aios-task-scroll-y";

      const saveScroll = () => {{
        sessionStorage.setItem(scrollKey, String(window.scrollY));
      }};

      const restoreScroll = () => {{
        const saved = sessionStorage.getItem(scrollKey);
        if (saved === null) return;
        sessionStorage.removeItem(scrollKey);
        const y = Number(saved);
        if (Number.isFinite(y)) {{
          requestAnimationFrame(() => {{
            requestAnimationFrame(() => {{
              window.scrollTo(0, Math.min(y, document.documentElement.scrollHeight));
            }});
          }});
        }}
      }};

      document.querySelectorAll(".complete-form").forEach((form) => {{
        const button = form.querySelector(".complete-checkbox");
        if (!button) return;

        button.addEventListener("click", (event) => {{
          event.preventDefault();
          if (button.dataset.submitting === "1") return;
          button.dataset.submitting = "1";
          saveScroll();
          button.classList.add("is-completing");
          button.setAttribute("aria-label", "Task completed");
          window.setTimeout(() => form.submit(), 180);
        }});
      }});

      document.querySelectorAll(".delete-form").forEach((form) => {{
        form.addEventListener("submit", () => saveScroll());
      }});

      const brainDump = document.getElementById("brainDumpText");
      if (brainDump) {{
        brainDump.addEventListener("keydown", (event) => {{
          if (event.key !== "Enter") return;
          event.preventDefault();

          const start = brainDump.selectionStart;
          const end = brainDump.selectionEnd;
          const value = brainDump.value;
          const insertion = "\\n• ";

          brainDump.value =
            value.slice(0, start) + insertion + value.slice(end);

          const next = start + insertion.length;
          brainDump.selectionStart = next;
          brainDump.selectionEnd = next;
        }});
      }}

      const sectionStateKey = "aios-dashboard-section-state-v1";
      const taskSections = () =>
        Array.from(document.querySelectorAll("details.task-group"));

      const readSectionState = () => {{
        try {{
          return JSON.parse(localStorage.getItem(sectionStateKey) || "{{}}") || {{}};
        }} catch (_error) {{
          return {{}};
        }}
      }};

      const saveSectionState = () => {{
        const state = {{}};
        taskSections().forEach((section) => {{
          const key = section.dataset.section;
          if (key) state[key] = section.open;
        }});
        localStorage.setItem(sectionStateKey, JSON.stringify(state));
      }};

      const restoreSectionState = () => {{
        const state = readSectionState();
        taskSections().forEach((section) => {{
          const key = section.dataset.section;
          if (key === "search_results") {{
            section.open = true;
          }} else if (key && Object.prototype.hasOwnProperty.call(state, key)) {{
            section.open = Boolean(state[key]);
          }}
          section.addEventListener("toggle", saveSectionState);
        }});
      }};

      const expandAll = document.getElementById("expandAllSections");
      const collapseAll = document.getElementById("collapseAllSections");

      if (expandAll) {{
        expandAll.addEventListener("click", () => {{
          taskSections().forEach((section) => section.open = true);
          saveSectionState();
        }});
      }}

      if (collapseAll) {{
        collapseAll.addEventListener("click", () => {{
          taskSections().forEach((section) => section.open = false);
          saveSectionState();
        }});
      }}

      restoreSectionState();

      const activeSearchResults = document.getElementById("search-results");
      if (activeSearchResults) {{
        sessionStorage.removeItem(scrollKey);
        requestAnimationFrame(() => {{
          requestAnimationFrame(() => {{
            activeSearchResults.scrollIntoView({{ block: "start" }});
          }});
        }});
      }} else {{
        restoreScroll();
      }}
    }})();
  </script>
{pending_refresh_script}
</body>
</html>"""


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "aios-web-capture",
        "version": WEB_CAPTURE_VERSION,
    }


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> HTMLResponse:
    message=request.query_params.get("message", "")
    error=request.query_params.get("error", "")
    search=request.query_params.get("search", "").strip()
    try:
        tasks=_fetch_open_tasks(search=search, limit=50)
    except Exception:
        tasks=[]
        if not error: error="Open tasks could not be loaded."
    try:
        focus=_fetch_focus()
    except Exception as focus_exc:
        print("[Dashboard Focus] Focus could not be loaded:", focus_exc)
        focus=None

    try:
        review_count = len(
            [
                review
                for review in _fetch_reviews()
                if review.get("state") != "resolved"
            ]
        )
    except Exception as review_exc:
        print(
            "[Dashboard] Review count could not be loaded:",
            review_exc,
        )
        review_count = 0

    refresh_focus = (
        request.query_params.get("refresh_focus") == "1"
    )

    return HTMLResponse(
        _page(
            message=message,
            error=error,
            tasks=tasks,
            search=search,
            focus=focus,
            refresh_focus=refresh_focus,
            review_count=review_count,
        )
    )





@app.get("/tasks/new")
def new_task_web(
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        projects = _fetch_project_options()
    except Exception:
        projects = []

    return HTMLResponse(_create_task_page(projects))


@app.post("/tasks/new")
def create_task_web(
    _user: Annotated[str, Depends(_check_basic_auth)],
    title: Annotated[str, Form()],
    due_at: Annotated[str, Form()] = "",
    defer_until: Annotated[str, Form()] = "",
    importance: Annotated[str, Form()] = "",
    urgency: Annotated[str, Form()] = "",
    effort: Annotated[str, Form()] = "",
    duration: Annotated[str, Form()] = "",
    project_id: Annotated[str, Form()] = "",
    is_just_do_it: Annotated[str | None, Form()] = None,
):
    payload = {
        "title": title.strip(),
        "due_at": due_at,
        "defer_until": defer_until,
        "importance": importance,
        "urgency": urgency,
        "effort": effort,
        "duration": duration,
        "project_id": project_id,
        "is_just_do_it": is_just_do_it == "true",
    }

    try:
        _create_task(payload)
        return RedirectResponse(
            url="/?message=Task+created.",
            status_code=303,
        )
    except Exception:
        try:
            projects = _fetch_project_options()
        except Exception:
            projects = []

        return HTMLResponse(
            _create_task_page(
                projects,
                error="Task could not be created.",
            ),
            status_code=200,
        )


@app.get("/projects")
def projects_web(
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        return HTMLResponse(_projects_page(_fetch_projects()))
    except Exception:
        return HTMLResponse(
            _projects_page([], error="Projects could not be loaded."),
            status_code=200,
        )



@app.get("/reviews")
def reviews_web(
    _user: Annotated[str, Depends(_check_basic_auth)],
    error: str = "",
):
    try:
        reviews = _fetch_reviews()

        try:
            notices = _fetch_review_notices()
        except Exception as exc:
            print(
                "[Review] Notice load failed:",
                exc,
            )
            notices = []

        # A duplicate review stores the candidate title as it existed
        # when the match was evaluated. Refresh the current task title
        # and mark the review stale if that title has since changed.
        for review in reviews:
            if review.get("review_type") != "possible_duplicate":
                continue

            payload = dict(review.get("payload") or {})

            candidate_id = str(
                payload.get("candidate_task_id") or ""
            ).strip()

            if not candidate_id:
                continue

            stored_title = str(
                payload.get("candidate_task_title") or ""
            ).strip()

            try:
                current_task = _fetch_task_detail(candidate_id)

                current_title = str(
                    current_task.get("title") or ""
                ).strip()

                if current_title:
                    payload["candidate_task_changed"] = (
                        bool(stored_title)
                        and current_title != stored_title
                    )
                    payload["stored_candidate_task_title"] = (
                        stored_title
                    )
                    payload["candidate_task_title"] = (
                        current_title
                    )

                    source_task_id = str(
                        payload.get("source_task_id")
                        or ""
                    ).strip()

                    source_stored_title = str(
                        payload.get("source_task_title")
                        or ""
                    ).strip()

                    source_task_changed = False

                    if source_task_id:
                        try:
                            source_task = _fetch_task_detail(
                                source_task_id
                            )

                            source_current_title = str(
                                source_task.get("title")
                                or ""
                            ).strip()

                            if source_current_title:
                                source_task_changed = (
                                    bool(source_stored_title)
                                    and source_current_title
                                    != source_stored_title
                                )

                                payload[
                                    "current_source_task_title"
                                ] = source_current_title

                        except Exception as exc:
                            print(
                                "[Review] Source task refresh failed:",
                                source_task_id,
                                exc,
                            )

                    payload["source_task_changed"] = (
                        source_task_changed
                    )

                    review["payload"] = payload

            except Exception as exc:
                print(
                    "[Review] Candidate task refresh failed:",
                    candidate_id,
                    exc,
                )

        return HTMLResponse(
            _reviews_page(
                reviews,
                notices=notices,
                error=error,
            )
        )
    except Exception as exc:
        print("[Review] Load failed:", exc)
        return HTMLResponse(
            _reviews_page(
                [],
                error="Reviews could not be loaded.",
            )
        )

@app.get(
    "/reviews/{review_id}/possible-duplicate/new-task"
)
def possible_duplicate_new_task_detail_web(
    review_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        review = next(
            (
                row
                for row in _fetch_reviews()
                if str(row.get("id") or "") == review_id
                and row.get("review_type") == "possible_duplicate"
            ),
            None,
        )

        if review is None:
            return RedirectResponse(
                url="/reviews?error=Duplicate+review+could+not+be+found.",
                status_code=303,
            )

        return HTMLResponse(
            _possible_duplicate_new_task_page(review)
        )

    except Exception as exc:
        print(
            "[Possible Duplicate] New task detail failed:",
            exc,
        )
        return RedirectResponse(
            url="/reviews?error=New+task+details+could+not+be+loaded.",
            status_code=303,
        )


@app.post(
    "/reviews/{review_id}/possible-duplicate/reevaluate"
)
def possible_duplicate_reevaluate_web(
    review_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        _request_possible_duplicate_reevaluation(
            review_id
        )

        return RedirectResponse(
            url="/reviews",
            status_code=303,
        )

    except Exception as exc:
        print(
            "[Possible Duplicate] Re-evaluate failed:",
            exc,
        )

        return RedirectResponse(
            url=(
                "/reviews?"
                "error=Duplicate+match+could+not+be+re-evaluated."
            ),
            status_code=303,
        )


@app.post(
    "/reviews/{review_id}/possible-duplicate/use-existing"
)
def possible_duplicate_use_existing_web(
    review_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    candidate_task_id: Annotated[str, Form()] = "",
    candidate_task_title: Annotated[str, Form()] = "",
    title_choice: Annotated[str, Form()] = "existing",
):
    try:
        _resolve_possible_duplicate(
            review_id,
            action="link_existing",
            candidate_task_id=candidate_task_id.strip() or None,
            candidate_task_title=candidate_task_title.strip() or None,
            title_choice=title_choice.strip() or "existing",
        )

        return RedirectResponse(
            url="/reviews",
            status_code=303,
        )

    except Exception as exc:
        print(
            "[Possible Duplicate] Use existing failed:",
            exc,
        )

        return RedirectResponse(
            url="/reviews?error=Duplicate+review+could+not+be+resolved.",
            status_code=303,
        )


@app.post(
    "/reviews/{review_id}/possible-duplicate/create-new"
)
def possible_duplicate_create_new_web(
    review_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        _request_possible_duplicate_create_new(
            review_id
        )

        return RedirectResponse(
            url="/reviews",
            status_code=303,
        )

    except Exception as exc:
        print(
            "[Possible Duplicate] Create new failed:",
            exc,
        )

        return RedirectResponse(
            url=(
                "/reviews?"
                "error=New+task+could+not+be+requested."
            ),
            status_code=303,
        )


@app.post(
    "/reviews/{review_id}/clarification/delete-task"
)
def clarification_delete_task_web(
    review_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        _delete_clarification_task(
            review_id
        )

        return RedirectResponse(
            url="/reviews",
            status_code=303,
        )

    except Exception as exc:
        print(
            "[Clarification] "
            "Delete task failed:",
            exc,
        )

        return RedirectResponse(
            url=(
                "/reviews?"
                "error=Clarification+task+could+not+be+deleted."
            ),
            status_code=303,
        )


@app.post(
    "/reviews/{review_id}/clarification/request-question"
)
def clarification_request_question_web(
    review_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        _request_clarification_question(
            review_id
        )

        return RedirectResponse(
            url="/reviews",
            status_code=303,
        )

    except Exception as exc:
        print(
            "[Clarification] "
            "Request question failed:",
            exc,
        )

        return RedirectResponse(
            url=(
                "/reviews?"
                "error=Clarification+question+could+not+be+generated."
            ),
            status_code=303,
        )


@app.post(
    "/reviews/{review_id}/clarification/answer"
)
def clarification_answer_web(
    review_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    answer: Annotated[str, Form()] = "",
):
    clean_answer = answer.strip()

    if not clean_answer:
        return RedirectResponse(
            url=(
                "/reviews?"
                "error=Clarification+answer+cannot+be+blank."
            ),
            status_code=303,
        )

    try:
        _submit_clarification_answer(
            review_id,
            answer=clean_answer,
        )

        return RedirectResponse(
            url="/reviews",
            status_code=303,
        )

    except Exception as exc:
        print(
            "[Clarification] "
            "Submit answer failed:",
            exc,
        )

        return RedirectResponse(
            url=(
                "/reviews?"
                "error=Clarification+answer+could+not+be+processed."
            ),
            status_code=303,
        )


@app.post(
    "/reviews/{review_id}/clarification/use"
)
def clarification_use_web(
    review_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    selected_text: Annotated[str, Form()] = "",
    accepted_text: Annotated[str, Form()] = "",
):
    selected = selected_text.strip()
    accepted = accepted_text.strip()

    if not accepted:
        return RedirectResponse(
            url=(
                "/reviews?"
                "error=Clarification+cannot+be+blank."
            ),
            status_code=303,
        )

    try:
        _resolve_clarification(
            review_id,
            selected_text=selected or accepted,
            accepted_text=accepted,
        )

        return RedirectResponse(
            url="/reviews",
            status_code=303,
        )

    except Exception as exc:
        print(
            "[Clarification] Use clarification failed:",
            exc,
        )

        return RedirectResponse(
            url=(
                "/reviews?"
                "error=Clarification+could+not+be+accepted."
            ),
            status_code=303,
        )


@app.post("/projects/{project_id}/outcome")
def update_project_outcome_web(
    project_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    outcome: Annotated[str, Form()] = "",
):
    try:
        _update_project_outcome(
            project_id,
            outcome.strip(),
        )
        return RedirectResponse(
            url=f"/projects/{project_id}?message=Project+outcome+saved.",
            status_code=303,
        )
    except Exception as exc:
        print("[Project Outcome] Update failed:", exc)
        return RedirectResponse(
            url=f"/projects/{project_id}?error=Project+outcome+could+not+be+saved.",
            status_code=303,
        )


@app.post("/projects/{project_id}/context")
def update_project_context_web(
    project_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    context: Annotated[str, Form()] = "",
):
    try:
        _update_project_context(
            project_id,
            context.strip(),
        )
        return RedirectResponse(
            url=f"/projects/{project_id}?message=Project+context+saved.",
            status_code=303,
        )
    except Exception as exc:
        print("[Project Context] Update failed:", exc)
        return RedirectResponse(
            url=f"/projects/{project_id}?error=Project+context+could+not+be+saved.",
            status_code=303,
        )



@app.post("/projects/{project_id}/work-proposals/generate")
def generate_project_work_web(
    project_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        _request_project_work_generation(project_id)
        return RedirectResponse(
            url=f"/projects/{project_id}?refresh_proposal=1#project-work-results",
            status_code=303,
        )
    except Exception as exc:
        print("[Project Work] Manual generation request failed:", exc)
        return RedirectResponse(
            url=(
                f"/projects/{project_id}"
                "?error=Project+work+could+not+be+requested."
            ),
            status_code=303,
        )



@app.post("/projects/{project_id}/work-proposals/answer")
def answer_project_work_question_web(project_id: str, _user: Annotated[str, Depends(_check_basic_auth)], answer: Annotated[str, Form()] = ""):
    try:
        _project_work_dialogue_action(project_id, "answer", {"answer": answer.strip()})
        return RedirectResponse(url=f"/projects/{project_id}?refresh_proposal=1#project-work-results", status_code=303)
    except Exception as exc:
        print("[Project Work] Answer failed:", exc)
        return RedirectResponse(url=f"/projects/{project_id}?error=Project+work+answer+could+not+be+saved.", status_code=303)

@app.post("/projects/{project_id}/work-proposals/context")
def accept_project_work_context_web(project_id: str, _user: Annotated[str, Depends(_check_basic_auth)], context_update: Annotated[str, Form()] = ""):
    try:
        _project_work_dialogue_action(project_id, "context", {"context_update": context_update.strip()})
        return RedirectResponse(url=f"/projects/{project_id}?refresh_proposal=1#project-work-results", status_code=303)
    except Exception as exc:
        print("[Project Work] Context continuation failed:", exc)
        return RedirectResponse(url=f"/projects/{project_id}?error=Project+context+could+not+be+added.", status_code=303)

@app.post(
    "/projects/{project_id}/work-proposals/{proposal_id}/accept"
)
def accept_project_work_web(
    project_id: str,
    proposal_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    title: Annotated[str, Form()],
):
    try:
        _project_work_action(
            project_id,
            proposal_id,
            "accept",
            {"title": title.strip()},
        )
        return RedirectResponse(
            url=f"/projects/{project_id}?message=Project+task+created.",
            status_code=303,
        )
    except Exception as exc:
        print("[Project Work] Accept failed:", exc)
        return RedirectResponse(
            url=f"/projects/{project_id}?error=Project+task+could+not+be+created.",
            status_code=303,
        )



@app.post(
    "/projects/{project_id}/work-proposals/{proposal_id}/retry"
)
def retry_project_work_web(
    project_id: str,
    proposal_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    feedback: Annotated[str, Form()],
):
    try:
        _project_work_action(
            project_id,
            proposal_id,
            "retry",
            {"feedback": feedback.strip()},
        )
        return RedirectResponse(
            url=(
                f"/projects/{project_id}"
                "?refresh_proposal=1"
            ),
            status_code=303,
        )
    except Exception as exc:
        print("[Project Work] Retry failed:", exc)
        return RedirectResponse(
            url=(
                f"/projects/{project_id}"
                "?error=Feedback+could+not+be+saved."
            ),
            status_code=303,
        )


@app.post(
    "/projects/{project_id}/work-proposals/{proposal_id}/dismiss"
)
def dismiss_project_work_web(
    project_id: str,
    proposal_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        _project_work_action(
            project_id,
            proposal_id,
            "dismiss",
        )
        return RedirectResponse(
            url=f"/projects/{project_id}?message=Proposal+dismissed.",
            status_code=303,
        )
    except Exception as exc:
        print("[Project Work] Dismiss failed:", exc)
        return RedirectResponse(
            url=f"/projects/{project_id}?error=Proposal+could+not+be+dismissed.",
            status_code=303,
        )




@app.post("/projects/{project_id}/use-existing-project")
def use_existing_project_web(
    project_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        _project_lifecycle_action(
            project_id,
            "use-existing-project",
        )

        return RedirectResponse(
            url="/projects",
            status_code=303,
        )

    except Exception as exc:
        print(
            "[Project Review] Use existing project failed:",
            exc,
        )

        return RedirectResponse(
            url="/projects?error=Project+could+not+be+merged.",
            status_code=303,
        )


@app.post("/projects/{project_id}/keep-separate")
def keep_project_separate_web(
    project_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        _project_lifecycle_action(
            project_id,
            "keep-separate",
        )

        return RedirectResponse(
            url="/projects",
            status_code=303,
        )

    except Exception as exc:
        print(
            "[Project Review] Keep separate failed:",
            exc,
        )

        return RedirectResponse(
            url="/projects?error=Project+review+could+not+be+saved.",
            status_code=303,
        )


@app.post("/projects/{project_id}/activate")
def activate_project_web(
    project_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        _project_lifecycle_action(
            project_id,
            "activate",
        )

        return RedirectResponse(
            url="/projects",
            status_code=303,
        )

    except Exception as exc:
        print("[Project Activation] Activate failed:", exc)

        return RedirectResponse(
            url="/projects?error=Project+could+not+be+activated.",
            status_code=303,
        )


@app.get("/projects/{project_id}")
def project_detail_web(
    project_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    refresh_proposal: bool = False,
):
    try:
        return HTMLResponse(
            _project_detail_page(
                _fetch_project_detail(project_id),
                refresh_proposal=refresh_proposal,
            )
        )
    except Exception:
        return RedirectResponse(url="/projects", status_code=303)


@app.get("/tasks/{task_id}")
def task_detail_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    message: str = "",
    error: str = "",
    return_to: str = "/",
):
    try:
        task = _fetch_task_detail(task_id)
        return HTMLResponse(
            _task_detail_page(
                task,
                message=message,
                error=error,
                return_to=return_to,
            )
        )
    except Exception as exc:
        print("[Task Detail] Render failed:", exc)
        return RedirectResponse(
            url="/?error=Task+could+not+be+loaded.",
            status_code=303,
        )


@app.post("/tasks/{task_id}/edit")
def edit_task_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    title: Annotated[str, Form()],
    due_at: Annotated[str, Form()] = "",
    defer_until: Annotated[str, Form()] = "",
    importance: Annotated[str, Form()] = "",
    urgency: Annotated[str, Form()] = "",
    effort: Annotated[str, Form()] = "",
    duration: Annotated[str, Form()] = "",
    is_just_do_it: Annotated[str | None, Form()] = None,
    return_to: Annotated[str, Form()] = "/",
):
    payload = {
        "title": title.strip(),
        "due_at": due_at,
        "defer_until": defer_until,
        "importance": importance,
        "urgency": urgency,
        "effort": effort,
        "duration": duration,
        "is_just_do_it": is_just_do_it == "true",
    }
    try:
        _update_task_detail(task_id, payload)
        return RedirectResponse(
            url=_safe_return_to(return_to),
            status_code=303,
        )
    except Exception:
        safe_return = _safe_return_to(return_to)
        return RedirectResponse(
            url=(
                f"/tasks/{task_id}"
                f"?error=Task+could+not+be+updated."
                f"&return_to={safe_return}"
            ),
            status_code=303,
        )


@app.post("/tasks/{task_id}/breakdown/request")
def request_breakdown_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    context: Annotated[str, Form()] = "",
    return_to: Annotated[str, Form()] = "/",
) -> RedirectResponse:
    try:
        _breakdown_action(task_id, "request", {"context": context.strip() or None})
        return RedirectResponse(
            url=f"/tasks/{task_id}?return_to={_safe_return_to(return_to)}#breakdown",
            status_code=303,
        )
    except BreakdownActionError as exc:
        error_text = quote(str(exc), safe="")
        return RedirectResponse(
            url=f"/tasks/{task_id}?error={error_text}&return_to={_safe_return_to(return_to)}#breakdown",
            status_code=303,
        )
    except Exception:
        return RedirectResponse(
            url=f"/tasks/{task_id}?error=Breakdown+request+could+not+reach+AIOS.&return_to={_safe_return_to(return_to)}#breakdown",
            status_code=303,
        )


@app.post("/tasks/{task_id}/breakdown/accept")
def accept_breakdown_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    titles: Annotated[str, Form()],
    return_to: Annotated[str, Form()] = "/",
) -> RedirectResponse:
    items = [line.strip() for line in titles.splitlines() if line.strip()]
    try:
        _breakdown_action(task_id, "accept", {"titles": items})
        return RedirectResponse(
            url=f"/tasks/{task_id}?message=Breakdown+created.&return_to={_safe_return_to(return_to)}#breakdown",
            status_code=303,
        )
    except Exception:
        return RedirectResponse(
            url=f"/tasks/{task_id}?error=Breakdown+could+not+be+created.&return_to={_safe_return_to(return_to)}#breakdown",
            status_code=303,
        )


@app.post("/tasks/{task_id}/breakdown/edit")
def edit_breakdown_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    titles: Annotated[str, Form()] = "",
    return_to: Annotated[str, Form()] = "/",
):
    items = [line.strip() for line in titles.splitlines() if line.strip()]
    try:
        _breakdown_action(task_id, "edit", {"titles": items})
        return RedirectResponse(url=f"/tasks/{task_id}?message=Breakdown+updated.&return_to={_safe_return_to(return_to)}#breakdown", status_code=303)
    except BreakdownActionError as exc:
        from urllib.parse import quote_plus
        return RedirectResponse(url=f"/tasks/{task_id}?error={quote_plus(str(exc))}&return_to={_safe_return_to(return_to)}#breakdown", status_code=303)


@app.post("/tasks/{task_id}/breakdown/cancel")
def cancel_breakdown_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    return_to: Annotated[str, Form()] = "/",
) -> RedirectResponse:
    try:
        _breakdown_action(task_id, "cancel")
    except Exception:
        pass
    return RedirectResponse(
        url=f"/tasks/{task_id}?return_to={_safe_return_to(return_to)}#breakdown",
        status_code=303,
    )


@app.post("/tasks/{task_id}/complete")
def complete_task_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    return_to: Annotated[str, Form()] = "",
) -> RedirectResponse:
    target = _safe_return_to(return_to) if return_to else "/"
    try:
        _task_action(task_id, "complete")
        if target != "/":
            return RedirectResponse(url=target, status_code=303)
        return RedirectResponse(
            url="/?message=Task+completed.&refresh_focus=1",
            status_code=303,
        )
    except Exception:
        if target != "/":
            return RedirectResponse(url=target, status_code=303)
        return RedirectResponse(
            url="/?error=Task+could+not+be+completed.",
            status_code=303,
        )


@app.post("/tasks/{task_id}/not-now")
def not_now_task_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> RedirectResponse:
    try:
        _task_action(task_id, "not-now")
        return RedirectResponse(
            url="/?message=Finding+a+different+step.&refresh_focus=1",
            status_code=303,
        )
    except Exception:
        return RedirectResponse(
            url="/?error=Task+could+not+be+skipped.",
            status_code=303,
        )


@app.post("/tasks/{task_id}/snooze")
def snooze_task_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    preset: Annotated[str, Form()] = "",
    custom_date: Annotated[str, Form()] = "",
) -> RedirectResponse:
    try:
        _snooze_task(task_id, preset, custom_date)
        return RedirectResponse(
            url="/?message=Best+Next+Action+snoozed.&refresh_focus=1",
            status_code=303,
        )
    except Exception:
        return RedirectResponse(
            url="/?error=Task+could+not+be+snoozed.",
            status_code=303,
        )


@app.post("/tasks/{task_id}/delete")
def delete_task_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    return_to: Annotated[str, Form()] = "",
) -> RedirectResponse:
    target = _safe_return_to(return_to) if return_to else "/"
    try:
        _task_action(task_id, "delete")
        return RedirectResponse(
            url=target if target != "/" else "/?message=Task+deleted.",
            status_code=303,
        )
    except Exception:
        return RedirectResponse(
            url=target if target != "/" else "/?error=Task+could+not+be+deleted.",
            status_code=303,
        )


@app.post("/submit")
def submit(
    _user: Annotated[str, Depends(_check_basic_auth)],
    text: Annotated[str, Form(min_length=1, max_length=10000)],
) -> RedirectResponse:
    lines = _split_brain_dump(text)

    if not lines:
        return RedirectResponse(
            url="/?error=Please+enter+something.",
            status_code=303,
        )

    sent, failures = _capture_many(lines)

    if failures and sent == 0:
        return RedirectResponse(
            url="/?error=AIOS+could+not+accept+the+items.+Please+try+again.",
            status_code=303,
        )

    if failures:
        return RedirectResponse(
            url=(
                f"/?error={sent}+item%28s%29+sent%2C+"
                f"{len(failures)}+failed.+Please+retry+the+failed+lines."
            ),
            status_code=303,
        )

    label = "item" if sent == 1 else "items"

    return RedirectResponse(
        url=f"/?message={sent}+{label}+sent+to+AIOS.",
        status_code=303,
    )
