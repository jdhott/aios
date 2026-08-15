from __future__ import annotations

import hmac
import html
import os
from typing import Annotated

import google.auth
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
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
        if not clean:
            continue

        for prefix in ("• ", "- ", "* "):
            if clean.startswith(prefix):
                clean = clean[len(prefix):].strip()
                break

        if clean:
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


def _task_detail_page(task: dict, message: str = "", error: str = "") -> str:
    task_id = html.escape(str(task.get("id") or ""))
    title = html.escape(str(task.get("title") or ""))
    due_at = html.escape(str(task.get("due_at") or "")[:10])
    defer_until = html.escape(str(task.get("defer_until") or "")[:10])
    importance = html.escape(str(task.get("importance") or ""))
    urgency = html.escape(str(task.get("urgency") or ""))
    effort = html.escape(str(task.get("effort") or ""))
    duration = html.escape(str(task.get("duration") or ""))
    checked = " checked" if task.get("is_just_do_it") else ""

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
          <a class="secondary-link" href="/">Cancel</a>
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


def _projects_page(projects: list[dict], error: str = "") -> str:
    cards = ""

    for project in projects:
        project_id = html.escape(str(project.get("id") or ""))
        name = html.escape(str(project.get("name") or "Untitled Project"))
        count = int(project.get("open_task_count") or 0)
        status = str(project.get("status") or "").strip()

        status_html = (
            f'<span class="project-status">{html.escape(status)}</span>'
            if status else ""
        )

        cards += (
            f'<a class="project-card" href="/projects/{project_id}">'
            f'<div><h2>{name}</h2>{status_html}</div>'
            f'<div class="project-count"><strong>{count}</strong>'
            f'<span>open task{"s" if count != 1 else ""}</span></div>'
            f'</a>'
        )

    if not cards:
        cards = '<div class="empty-state">No active projects with open tasks.</div>'

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
.project-card h2 {{ margin:0; color:var(--navy); font-size:1.08rem; }}
.project-status {{
  display:inline-block; margin-top:6px; color:var(--muted); font-size:.82rem;
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
      <p class="subtitle">Active projects with unfinished work.</p>
    </div>
    <a class="nav-link" href="/">Home</a>
  </div>
  {notice}
  <div class="project-list">{cards}</div>
</main>
</body>
</html>"""


def _project_detail_page(payload: dict) -> str:
    project = dict(payload.get("project") or {})
    tasks = list(payload.get("tasks") or [])

    name = html.escape(str(project.get("name") or "Untitled Project"))
    count = int(project.get("open_task_count") or 0)
    status = str(project.get("status") or "").strip()

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

        task_rows += (
            '<a class="task-row" href="/tasks/' + task_id + '">'
            '<div>'
            f'<div class="task-title">{title}</div>'
            f'<div class="task-meta">{" · ".join(meta)}</div>'
            '</div>'
            '<span class="chevron">›</span>'
            '</a>'
        )

    if not task_rows:
        task_rows = '<div class="empty-state">No open tasks in this project.</div>'

    status_html = (
        f'<span class="status">{html.escape(status)}</span>'
        if status else ""
    )

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
.task-row:last-child {{ border-bottom:0; }}
.task-row:hover {{ background:#fbfbf8; }}
.task-title {{ font-weight:700; }}
.task-meta {{
  margin-top:5px; color:var(--muted); font-size:.8rem; line-height:1.35;
}}
.chevron {{ color:var(--muted); font-size:1.6rem; }}
.empty-state {{ padding:24px; color:var(--muted); }}
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
  <div class="task-list">{task_rows}</div>
</main>
</body>
</html>"""



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

    section_specs = [
        ("Top 5", "top5"),
        ("Quick Wins", "quick_wins"),
        ("Today", "today"),
        ("Just Do It", "just_do_it"),
    ]

    task_sections = ""

    for heading, key in section_specs:
        section_tasks = tasks.get(key, [])
        if focus_id:
            section_tasks = [task for task in section_tasks if str(task.get("id") or "") != focus_id]
        if not section_tasks:
            continue

        rows_html = "".join(
            render_task(task)
            for task in section_tasks
        )

        task_sections += (
            f'<details class="task-group" data-section="{html.escape(key)}">'
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
    if focus:
        focus_id = str(focus.get("id") or "")
        safe_id = html.escape(focus_id)
        title = html.escape(str(focus.get("title") or "Untitled task"))
        meta = []
        if focus.get("execution_rank") is not None: meta.append(f"Rank {html.escape(str(focus.get('execution_rank')))}")
        if focus.get("execution_score") is not None: meta.append(f"Score {html.escape(str(focus.get('execution_score')))}")
        if focus.get("importance"): meta.append(html.escape(str(focus.get("importance"))))

        activation = dict(focus.get("activation") or {})
        activation_id = str(activation.get("id") or "")
        activation_title = str(activation.get("title") or "").strip()
        activation_pending = bool(
            focus.get("activation_pending")
        )

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
            '<div class="focus-main">'
            f'<a class="focus-title" href="/tasks/{safe_id}">{title}</a>'
            f'<div class="focus-meta">{" · ".join(meta)}</div></div>'
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
    if focus and focus.get("activation_pending"):
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
    .focus-main {{ min-width:0; }}
    .focus-title {{ color:var(--ink); text-decoration:none; font-size:1.25rem; line-height:1.3; font-weight:850; }}
    .focus-title:hover {{ text-decoration:underline; }}
    .focus-meta {{ margin-top:5px; color:var(--muted); font-size:.84rem; }}
    .focus-start {{ margin:16px 44px 0 0; padding-top:14px; border-top:1px solid rgba(38,65,85,.12); }}
    .focus-start-label {{ color:var(--navy); font-size:.82rem; font-weight:850; text-transform:uppercase; letter-spacing:.04em; }}
    .focus-start-row {{ display:grid; grid-template-columns:44px minmax(0,1fr); gap:10px; align-items:center; margin-top:8px; }}
    .focus-start-main {{ min-width:0; }}
    .focus-start-step {{ color:var(--ink); text-decoration:none; font-size:1rem; line-height:1.45; font-weight:700; }}
    .focus-start-step:hover {{ text-decoration:underline; }}
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

      const taskSections = () =>
        Array.from(document.querySelectorAll("details.task-group"));

      const expandAll = document.getElementById("expandAllSections");
      const collapseAll = document.getElementById("collapseAllSections");

      if (expandAll) {{
        expandAll.addEventListener("click", () => {{
          taskSections().forEach((section) => section.open = true);
        }});
      }}

      if (collapseAll) {{
        collapseAll.addEventListener("click", () => {{
          taskSections().forEach((section) => section.open = false);
        }});
      }}

      restoreScroll();
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
    return HTMLResponse(_page(message=message, error=error, tasks=tasks, search=search, focus=focus))





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


@app.get("/projects/{project_id}")
def project_detail_web(
    project_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
):
    try:
        return HTMLResponse(
            _project_detail_page(_fetch_project_detail(project_id))
        )
    except Exception:
        return RedirectResponse(url="/projects", status_code=303)


@app.get("/tasks/{task_id}")
def task_detail_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    message: str = "",
    error: str = "",
):
    try:
        task = _fetch_task_detail(task_id)
        return HTMLResponse(_task_detail_page(task, message=message, error=error))
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
            url="/?message=Task+updated.",
            status_code=303,
        )
    except Exception:
        return RedirectResponse(
            url=f"/tasks/{task_id}?error=Task+could+not+be+updated.",
            status_code=303,
        )


@app.post("/tasks/{task_id}/complete")
def complete_task_web(task_id: str, _user: Annotated[str, Depends(_check_basic_auth)]) -> RedirectResponse:
    try: _task_action(task_id, "complete"); return RedirectResponse(url="/?message=Task+completed.",status_code=303)
    except Exception: return RedirectResponse(url="/?error=Task+could+not+be+completed.",status_code=303)

@app.post("/tasks/{task_id}/delete")
def delete_task_web(task_id: str, _user: Annotated[str, Depends(_check_basic_auth)]) -> RedirectResponse:
    try: _task_action(task_id, "delete"); return RedirectResponse(url="/?message=Task+deleted.",status_code=303)
    except Exception: return RedirectResponse(url="/?error=Task+could+not+be+deleted.",status_code=303)


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
