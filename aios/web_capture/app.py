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
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


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


def _page(
    *,
    message: str = "",
    error: str = "",
    tasks: dict[str, list[dict]] | None = None,
    search: str = "",
) -> str:
    tasks = tasks or {}
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
            + f'<div class="task-title">{title}</div>'
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
        if not section_tasks:
            continue

        rows_html = "".join(
            render_task(task)
            for task in section_tasks
        )

        task_sections += (
            '<section class="task-group">'
            f'<h3 class="task-group-heading">{html.escape(heading)}</h3>'
            f'{rows_html}'
            '</section>'
        )

    if not task_sections:
        task_sections = (
            '<div class="empty-state">'
            'No matching tasks found.'
            '</div>'
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
      min-height: 48vh;
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
    .empty-state {{ padding:18px 0; color:var(--muted); }}
  </style>
</head>
<body>
  <main>
    <h1 class="brand">Brain Dump</h1>
    <p class="subtitle">One line per task. Send several at once.</p>
    {notice}
    <form method="post" action="/submit" onsubmit="submitButton.disabled=true;">
      <textarea
        name="text"
        required
        autofocus
        maxlength="10000"
        placeholder="One task per line…"
        aria-label="Brain dump text"
      ></textarea>
      <button id="submitButton" name="submitButton" type="submit">
        Submit to AIOS
      </button>
    </form>
    <p class="hint">AIOS will process this automatically.</p>
    <section class="tasks-section">
      <h2 class="tasks-heading">Tasks</h2>
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

      restoreScroll();
    }})();
  </script>
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
    return HTMLResponse(_page(message=message, error=error, tasks=tasks, search=search))


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
