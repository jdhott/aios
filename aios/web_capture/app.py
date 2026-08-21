from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import html
import os
import subprocess
from pathlib import Path
from typing import Annotated
from urllib.parse import quote_plus

import google.auth
from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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
WEB_OPTIMISTIC_COMPLETE_VERSION = "optimistic-complete-v1"
WEB_OPTIMISTIC_SNOOZE_VERSION = "optimistic-snooze-v1"
WEB_MAIN_PWA_VERSION = "main-pwa-v1"
WEB_DASHBOARD_UI_VERSION = "dashboard-v1.4-compact-capture-toggle"
WEB_DASHBOARD_BNA_VERSION = "dashboard-bna-v1-fix1"
WEB_DASHBOARD_FOCUS_VERSION = "dashboard-focus-v1"
WEB_DASHBOARD_FOCUS_FIX_VERSION = "dashboard-focus-v1-fix1"
WEB_TASK_DETAIL_EDIT_VERSION = "task-detail-edit-v1"
WEB_TASK_DETAIL_UI_VERSION = "task-detail-ui-v1.3-form-layout-fix"
WEB_PROJECTS_VERSION = "projects-v1"
WEB_CREATE_TASK_VERSION = "create-task-v1"
WEB_DASHBOARD_TASKS_POLL_VERSION = "dashboard-tasks-poll-v1"
WEB_DASHBOARD_ASYNC_V2A_VERSION = "dashboard-async-v2a"
WEB_PENDING_FRAGMENT_POLL_VERSION = "pending-fragment-poll-v2b"
WEB_TASK_DETAIL_OPTIMISTIC_SAVE_VERSION = "task-detail-async-save-v3"
WEB_DARK_MODE_VERSION = "dark-mode-v1"
WEB_ABOUT_PAGE_VERSION = "about-page-v1"

app = FastAPI(
    title="AIOS Brain Dump",
    version=WEB_CAPTURE_VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

SESSION_COOKIE_NAME = "aios_session"
SESSION_DEFAULT_DAYS = 30

def _env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"{name} is not configured")
    return value

def _session_secret() -> bytes:
    return _env("AIOS_WEB_SESSION_SECRET").encode("utf-8")

def _session_days() -> int:
    raw = (os.getenv("AIOS_WEB_SESSION_DAYS") or "").strip()
    try:
        value = int(raw) if raw else SESSION_DEFAULT_DAYS
    except ValueError:
        value = SESSION_DEFAULT_DAYS
    return min(max(value, 1), 365)

def _session_cookie_secure() -> bool:
    raw = (os.getenv("AIOS_WEB_COOKIE_SECURE") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _encode_session(username: str) -> str:
    exp = int(time.time()) + (_session_days() * 86400)
    payload = json.dumps(
        {"u": username, "exp": exp},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        _session_secret(),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded}.{signature}"

def _decode_session(value: str | None) -> str | None:
    token = str(value or "").strip()
    if "." not in token:
        return None
    encoded, signature = token.rsplit(".", 1)
    expected = hmac.new(
        _session_secret(),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        padded = encoded + ("=" * (-len(encoded) % 4))
        payload = json.loads(
            base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        )
        username = str(payload.get("u") or "")
        expires_at = int(payload.get("exp") or 0)
    except Exception:
        return None
    if expires_at <= int(time.time()):
        return None
    expected_username = _env("AIOS_WEB_USERNAME")
    if not hmac.compare_digest(
        username.encode("utf-8"),
        expected_username.encode("utf-8"),
    ):
        return None
    return username

def _safe_login_next(value: str | None) -> str:
    target = str(value or "").strip()
    if not target.startswith("/") or target.startswith("//"):
        return "/"
    return target


_DARK_DESIGN_TOKENS = """
      --navy: #9fc2d8;
      --ink: #edf2f2;
      --muted: #aab6bb;
      --paper: #111719;
      --surface: #182126;
      --border: #34434a;
      --focus-yellow: #d4a832;
      --focus-bg: #2a2618;
      --accent-soft: rgba(159, 194, 216, 0.10);
      --highlight: #1e282d;
      --success: #1a2a22;
      --error: #2a1e1c;
      --ok: #8bd3a8;
      --shadow: 0 4px 24px rgba(0, 0, 0, 0.28);
      --shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.36);
      --nav-bg: rgba(24, 33, 38, 0.96);
      --nav-border: rgba(159, 194, 216, 0.12);
      --nav-shadow: 0 16px 48px rgba(0, 0, 0, 0.38);
      --nav-add-shadow: 0 10px 28px rgba(0, 0, 0, 0.42);
      --focus-ring: rgba(159, 194, 216, 0.35);
      --focus-ring-shadow: rgba(159, 194, 216, 0.14);
      --check-border: rgba(159, 194, 216, 0.35);
      --check-border-hover: rgba(159, 194, 216, 0.65);
      --check-glow: rgba(159, 194, 216, 0.14);
      --button-hover: #243038;
      --row-hover: #1a2328;
      --menu-hover: #243038;
      --toast-error: #4a2828;
      --theme-color: #182126;
      --focus-card-glow: rgba(212, 168, 50, 0.22);
"""


def _theme_init_script() -> str:
    return """<script>(function(){try{var t=localStorage.getItem("aios-theme");if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t);}catch(e){}})();</script>"""


def _theme_meta_tags() -> str:
    return """
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#264155" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#182126" media="(prefers-color-scheme: dark)">
"""


def _theme_head_extras() -> str:
    return _theme_init_script() + _theme_meta_tags()


def _theme_toggle_script() -> str:
    return """
<script>
(() => {
  const STORAGE_KEY = "aios-theme";

  function themeLabel(mode) {
    if (mode === "light") return "Light";
    if (mode === "dark") return "Dark";
    return "System";
  }

  function storedTheme() {
    try {
      const value = localStorage.getItem(STORAGE_KEY);
      return value === "light" || value === "dark" ? value : "system";
    } catch (_error) {
      return "system";
    }
  }

  function applyTheme(mode, persist) {
    if (mode === "light" || mode === "dark") {
      document.documentElement.setAttribute("data-theme", mode);
      if (persist) localStorage.setItem(STORAGE_KEY, mode);
    } else {
      document.documentElement.removeAttribute("data-theme");
      if (persist) localStorage.removeItem(STORAGE_KEY);
    }
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.textContent = "Appearance: " + themeLabel(mode);
    });
  }

  function cycleTheme() {
    const current = storedTheme();
    const next = current === "light" ? "dark" : current === "dark" ? "system" : "light";
    applyTheme(next, true);
  }

  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", cycleTheme);
  });
  applyTheme(storedTheme(), false);
})();
</script>
"""


def _mobile_design_tokens() -> str:
    return f"""
    :root {{
      color-scheme: light dark;
      --navy: #264155;
      --ink: #25333D;
      --muted: #687780;
      --paper: #F7F6F1;
      --surface: #FFFFFF;
      --border: #D9DDDC;
      --focus-yellow: #FFC93C;
      --focus-bg: #FFF8DC;
      --charcoal: var(--navy);
      --card: var(--surface);
      --accent: var(--navy);
      --accent-soft: rgba(38, 65, 85, 0.08);
      --highlight: #F0EFEA;
      --success: #EEF6F0;
      --error: #FAEFED;
      --ok: #2d6a4f;
      --shadow: 0 4px 24px rgba(38, 65, 85, 0.08);
      --shadow-lg: 0 12px 40px rgba(38, 65, 85, 0.12);
      --nav-bg: rgba(255, 255, 255, 0.96);
      --nav-border: rgba(38, 65, 85, 0.10);
      --nav-shadow: 0 16px 48px rgba(38, 65, 85, 0.14);
      --nav-add-shadow: 0 10px 28px rgba(38, 65, 85, 0.22);
      --focus-ring: rgba(44, 44, 44, 0.22);
      --focus-ring-shadow: rgba(44, 44, 44, 0.10);
      --check-border: rgba(37, 51, 61, 0.32);
      --check-border-hover: rgba(38, 65, 85, 0.58);
      --check-glow: rgba(38, 65, 85, 0.12);
      --button-hover: #eceeed;
      --row-hover: #fbfbf8;
      --menu-hover: #f3f4f2;
      --on-accent: #ffffff;
      --toast-error: #5C3333;
      --theme-color: #264155;
      --focus-card-glow: rgba(255, 201, 60, 0.18);
      --radius-2xl: 20px;
      --line-body: 1.7;
      --line-relaxed: 1.85;
      --nav-offset: calc(108px + env(safe-area-inset-bottom));
    }}
    @media (prefers-color-scheme: dark) {{
      :root:not([data-theme="light"]) {{
        {_DARK_DESIGN_TOKENS}
      }}
    }}
    :root[data-theme="dark"] {{
        {_DARK_DESIGN_TOKENS}
    }}
    :root[data-theme="light"] {{
      color-scheme: light;
    }}
    """


def _web_build_info() -> dict[str, str | None]:
    return {
        "git_sha": (os.getenv("AIOS_WEB_GIT_SHA") or "").strip() or None,
        "built_at": (os.getenv("AIOS_WEB_BUILD_TIME") or "").strip() or None,
        "revision": (os.getenv("K_REVISION") or "").strip() or None,
        "service": (os.getenv("K_SERVICE") or "").strip() or None,
    }


def _web_version_groups() -> list[dict[str, object]]:
    return [
        {
            "title": "App",
            "items": [
                {"label": "Web shell", "version": WEB_CAPTURE_VERSION},
                {"label": "Main PWA", "version": WEB_MAIN_PWA_VERSION},
                {"label": "About page", "version": WEB_ABOUT_PAGE_VERSION},
            ],
        },
        {
            "title": "Dashboard",
            "items": [
                {"label": "UI", "version": WEB_DASHBOARD_UI_VERSION},
                {"label": "Focus card", "version": WEB_DASHBOARD_FOCUS_VERSION},
                {"label": "Task list polling", "version": WEB_DASHBOARD_TASKS_POLL_VERSION},
                {"label": "Async actions", "version": WEB_DASHBOARD_ASYNC_V2A_VERSION},
                {"label": "Fragment polling", "version": WEB_PENDING_FRAGMENT_POLL_VERSION},
                {"label": "Optimistic complete", "version": WEB_OPTIMISTIC_COMPLETE_VERSION},
                {"label": "Optimistic snooze", "version": WEB_OPTIMISTIC_SNOOZE_VERSION},
            ],
        },
        {
            "title": "Tasks",
            "items": [
                {"label": "Task detail edit", "version": WEB_TASK_DETAIL_EDIT_VERSION},
                {"label": "Task detail UI", "version": WEB_TASK_DETAIL_UI_VERSION},
                {"label": "Async save", "version": WEB_TASK_DETAIL_OPTIMISTIC_SAVE_VERSION},
                {"label": "Create task", "version": WEB_CREATE_TASK_VERSION},
            ],
        },
        {
            "title": "Experience",
            "items": [
                {"label": "Dark mode", "version": WEB_DARK_MODE_VERSION},
                {"label": "Projects", "version": WEB_PROJECTS_VERSION},
            ],
        },
    ]


def _web_about_payload() -> dict[str, object]:
    build = _web_build_info()
    return {
        "status": "ok",
        "service": "aios-web-capture",
        "version": WEB_CAPTURE_VERSION,
        "about_page": WEB_ABOUT_PAGE_VERSION,
        "build": build,
        "feature_groups": _web_version_groups(),
    }


def _about_version_rows(groups: list[dict[str, object]]) -> str:
    sections: list[str] = []
    for group in groups:
        title = html.escape(str(group.get("title") or ""))
        items = group.get("items") or []
        rows: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            label = html.escape(str(item.get("label") or ""))
            version = html.escape(str(item.get("version") or ""))
            rows.append(
                f'<div class="about-row"><span class="about-label">{label}</span>'
                f'<span class="about-value">{version}</span></div>'
            )
        if not rows:
            continue
        sections.append(
            f'<section class="surface-card about-group">'
            f'<h2 class="about-group-title">{title}</h2>'
            f'<div class="about-list">{"".join(rows)}</div>'
            f"</section>"
        )
    return "".join(sections)


def _about_build_rows(build: dict[str, str | None]) -> str:
    labels = {
        "git_sha": "Git commit",
        "built_at": "Built at (UTC)",
        "revision": "Cloud Run revision",
        "service": "Cloud Run service",
    }
    rows: list[str] = []
    for key, label in labels.items():
        value = str(build.get(key) or "").strip()
        if not value:
            continue
        rows.append(
            f'<div class="about-row"><span class="about-label">{html.escape(label)}</span>'
            f'<span class="about-value mono">{html.escape(value)}</span></div>'
        )
    if not rows:
        rows.append(
            '<p class="about-note">Build metadata appears after the next deploy.</p>'
        )
        return "".join(rows)
    return f'<div class="about-list">{"".join(rows)}</div>'


def _about_page(payload: dict[str, object]) -> str:
    build = dict(payload.get("build") or {})
    groups = list(payload.get("feature_groups") or [])
    version_sections = _about_version_rows(groups)
    build_section = _about_build_rows(build)
    shell_version = html.escape(str(payload.get("version") or ""))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
{_theme_head_extras()}
<title>About · AIOS</title>
<style>
{_mobile_shell_css()}
.about-intro {{
  margin:0 0 24px;
  color:var(--muted);
  font-size:.96rem;
  line-height:var(--line-relaxed);
}}
.about-group {{
  margin-bottom:20px;
  padding:22px 20px;
}}
.about-group-title {{
  margin:0 0 14px;
  font-size:1rem;
  font-weight:700;
  color:var(--charcoal);
}}
.about-list {{
  display:grid;
  gap:0;
}}
.about-row {{
  display:grid;
  grid-template-columns:minmax(0,1fr) auto;
  gap:16px;
  align-items:start;
  padding:12px 0;
  border-bottom:1px solid var(--border);
  line-height:var(--line-body);
}}
.about-row:last-child {{ border-bottom:0; padding-bottom:0; }}
.about-label {{
  color:var(--ink);
  font-size:.92rem;
  font-weight:600;
}}
.about-value {{
  color:var(--muted);
  font-size:.84rem;
  font-weight:600;
  text-align:right;
  overflow-wrap:anywhere;
}}
.about-value.mono {{
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:.78rem;
}}
.about-note {{
  margin:0;
  color:var(--muted);
  font-size:.9rem;
  line-height:var(--line-relaxed);
}}
.about-links {{
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  margin-top:8px;
}}
.about-links a {{
  min-height:44px;
  display:inline-flex;
  align-items:center;
  padding:0 16px;
  border:1px solid var(--border);
  border-radius:999px;
  color:var(--charcoal);
  text-decoration:none;
  font-weight:600;
  background:var(--card);
}}
</style>
</head>
<body>
<main>
  <div class="page-heading">
    <h1 class="brand">About</h1>
    <p class="subtitle">Running build <span class="about-value mono">{shell_version}</span></p>
  </div>

  <p class="about-intro">
    Use this page to confirm which AIOS web build is live after deploy,
    especially when testing on a phone or installed PWA.
  </p>

  <section class="surface-card about-group">
    <h2 class="about-group-title">Build</h2>
    {build_section}
  </section>

  {version_sections}

  <section class="surface-card about-group">
    <h2 class="about-group-title">Links</h2>
    <div class="about-links">
      <a href="/capture">Brain Dump</a>
      <a href="/">Dashboard</a>
    </div>
  </section>
</main>
{_bottom_nav_html(active="about")}
</body>
</html>"""


def _bottom_nav_css() -> str:
    return """
    .bottom-nav {
      position: fixed;
      left: 50%;
      bottom: calc(14px + env(safe-area-inset-bottom));
      z-index: 100;
      transform: translateX(-50%);
      width: min(640px, calc(100% - 28px));
      display: flex;
      align-items: flex-end;
      justify-content: space-around;
      gap: 4px;
      padding: 10px 14px 12px;
      background: var(--nav-bg);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--nav-border);
      border-radius: 28px;
      box-shadow: var(--nav-shadow);
    }
    .bottom-nav-item {
      position: relative;
      flex: 1;
      max-width: 76px;
      min-height: 56px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 6px;
      padding: 8px 4px;
      border: 0;
      border-radius: 16px;
      background: transparent;
      color: var(--muted);
      text-decoration: none;
      font: inherit;
      font-size: 0.68rem;
      font-weight: 600;
      letter-spacing: 0.01em;
      line-height: 1.35;
      cursor: pointer;
      list-style: none;
    }
    .bottom-nav-item::-webkit-details-marker { display: none; }
    .bottom-nav-item .nav-icon {
      font-size: 1.28rem;
      line-height: 1;
    }
    .bottom-nav-item.active,
    .bottom-nav-item[aria-current="page"] {
      color: var(--charcoal);
      background: var(--accent-soft);
    }
    .bottom-nav-add {
      flex: 0 0 auto;
      width: 56px;
      height: 56px;
      margin-top: -22px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      background: var(--charcoal);
      color: var(--paper);
      text-decoration: none;
      box-shadow: var(--nav-add-shadow);
    }
    .bottom-nav-add .nav-icon {
      font-size: 1.65rem;
      line-height: 1;
      font-weight: 300;
    }
    .bottom-nav-add.active {
      outline: 3px solid rgba(255, 201, 60, 0.45);
    }
    .nav-badge {
      position: absolute;
      top: 4px;
      right: calc(50% - 22px);
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      border-radius: 999px;
      background: var(--charcoal);
      color: var(--on-accent);
      font-size: 0.62rem;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    .bottom-nav-more { position: relative; flex: 1; max-width: 76px; }
    .bottom-nav-more > summary { width: 100%; }
    .bottom-nav-sheet {
      position: absolute;
      right: 0;
      bottom: calc(100% + 10px);
      min-width: 196px;
      padding: 8px;
      border: 1px solid var(--border);
      border-radius: var(--radius-2xl);
      background: var(--card);
      box-shadow: var(--shadow-lg);
    }
    .bottom-nav-sheet a,
    .bottom-nav-sheet button {
      width: 100%;
      min-height: 44px;
      display: flex;
      align-items: center;
      padding: 0 14px;
      border: 0;
      border-radius: 12px;
      background: transparent;
      color: var(--ink);
      text-decoration: none;
      font: inherit;
      font-size: 0.92rem;
      font-weight: 600;
      cursor: pointer;
    }
    .bottom-nav-sheet a:hover,
    .bottom-nav-sheet button:hover {
      background: var(--accent-soft);
    }
    """


def _mobile_shell_css() -> str:
    return f"""
    {_mobile_design_tokens()}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--paper);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 1rem;
      line-height: var(--line-body);
      -webkit-font-smoothing: antialiased;
    }}
    main {{
      width: min(720px, 100%);
      margin: 0 auto;
      padding: max(24px, env(safe-area-inset-top)) 20px var(--nav-offset);
    }}
    h1, h2, h3 {{
      color: var(--charcoal);
      line-height: 1.35;
      letter-spacing: -0.02em;
    }}
    .detail-back {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      margin-bottom: 20px;
      color: var(--muted);
      text-decoration: none;
      font-size: 0.92rem;
      font-weight: 600;
      line-height: var(--line-body);
    }}
    .detail-back:hover {{ color: var(--charcoal); }}
    .surface-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius-2xl);
      padding: 28px 24px;
      margin-bottom: 24px;
      box-shadow: var(--shadow);
    }}
    .page-heading {{
      margin-bottom: 32px;
      padding: 4px 2px 0;
    }}
    .page-heading .brand {{
      margin: 0 0 10px;
      font-size: clamp(1.85rem, 7vw, 2.45rem);
      font-weight: 700;
      color: var(--charcoal);
      line-height: 1.2;
    }}
    .page-heading .subtitle,
    .dashboard-subtitle {{
      margin: 0;
      color: var(--muted);
      font-size: 1.02rem;
      line-height: var(--line-relaxed);
    }}
    {_bottom_nav_css()}
    .fragment-poll-timeout {{
      display:grid;
      gap:12px;
      margin-top:16px;
      color:var(--ink);
      font-size:.95rem;
      line-height:var(--line-relaxed);
    }}
    .fragment-poll-timeout-actions {{
      display:flex;
      flex-wrap:wrap;
      gap:10px;
      align-items:center;
    }}
    .fragment-poll-timeout-actions button {{
      min-height:0;
      padding:10px 14px;
      border-radius:999px;
      border:1px solid var(--border);
      background:var(--surface);
      color:var(--charcoal);
      font:inherit;
      font-weight:600;
      cursor:pointer;
    }}
    .fragment-poll-timeout-actions button.primary {{
      background:var(--charcoal);
      border-color:var(--charcoal);
      color:var(--paper);
    }}
    .fragment-poll-timeout-actions button.link {{
      border:0;
      background:transparent;
      color:var(--muted);
      text-decoration:underline;
      padding:10px 0;
    }}
    """


def _bottom_nav_html(*, active: str = "home", review_count: int = 0) -> str:
    def item(href: str, label: str, icon: str, key: str, badge: str = "") -> str:
        is_active = active == key
        current = ' aria-current="page"' if is_active else ""
        cls = "bottom-nav-item active" if is_active else "bottom-nav-item"
        badge_html = f'<span class="nav-badge">{html.escape(badge)}</span>' if badge else ""
        return (
            f'<a class="{cls}" href="{href}"{current}>'
            f'<span class="nav-icon" aria-hidden="true">{icon}</span>'
            f'<span class="nav-label">{html.escape(label)}</span>'
            f"{badge_html}"
            f"</a>"
        )

    more_active = active in {"journal", "patterns", "more", "about"}
    more_cls = "bottom-nav-item active" if more_active else "bottom-nav-item"
    reviews_badge = str(review_count) if review_count else ""
    add_cls = "bottom-nav-add active" if active == "new" else "bottom-nav-add"

    return f"""
  <nav class="bottom-nav" aria-label="Primary">
    {item("/", "Home", "⌂", "home")}
    {item("/projects", "Projects", "▦", "projects")}
    <a class="{add_cls}" href="/tasks/new" aria-label="New task"{(' aria-current="page"' if active == 'new' else '')}>
      <span class="nav-icon" aria-hidden="true">+</span>
    </a>
    {item("/reviews", "Reviews", "◎", "reviews", reviews_badge)}
    <details class="bottom-nav-more" id="bottom-nav-more">
      <summary class="{more_cls}" aria-label="More">
        <span class="nav-icon" aria-hidden="true">⋯</span>
        <span class="nav-label">More</span>
      </summary>
      <div class="bottom-nav-sheet">
        <button type="button" data-theme-toggle>Appearance: System</button>
        <a href="/about">About</a>
        <a href="/work-patterns">Work Patterns</a>
        <a href="/journal">Journal</a>
        <form method="post" action="/logout"><button type="submit">Sign Out</button></form>
      </div>
    </details>
  </nav>
  <script>
  (() => {{
    const more = document.getElementById("bottom-nav-more");
    if (!more) return;
    document.addEventListener("click", (event) => {{
      if (more.open && !more.contains(event.target)) more.open = false;
    }});
    document.addEventListener("keydown", (event) => {{
      if (event.key === "Escape" && more.open) {{
        more.open = false;
        const trigger = more.querySelector("summary");
        if (trigger) trigger.focus();
      }}
    }});
  }})();
  </script>
  {_theme_toggle_script()}
"""


def _login_page(next_url: str = "/", error: str = "") -> str:
    safe_next = html.escape(_safe_login_next(next_url), quote=True)
    error_html = (
        f'<p style="color:#a33">{html.escape(error)}</p>'
        if error else ""
    )
    return f'''<!doctype html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
{_theme_head_extras()}
<title>Sign in · AIOS</title>
<style>
{_mobile_shell_css()}
body{{display:grid;place-items:center;min-height:100dvh}}
main{{width:min(420px,100%);padding:24px 20px var(--nav-offset)}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-2xl);padding:28px 24px;box-shadow:var(--shadow)}}
input,button{{width:100%;box-sizing:border-box;min-height:48px;margin-top:10px;padding:12px 14px;font:inherit;line-height:var(--line-body)}}
input{{border:1px solid var(--border);border-radius:var(--radius-2xl);background:var(--highlight);color:var(--ink)}}
button{{background:var(--charcoal);color:var(--paper);border:0;border-radius:var(--radius-2xl);font-weight:700;margin-top:16px}}
label{{display:block;margin-top:16px;font-weight:600;color:var(--charcoal);line-height:var(--line-body)}}
h1{{color:var(--charcoal);margin:0 0 12px;line-height:1.3}}
p{{color:var(--muted);line-height:var(--line-relaxed);margin:0 0 8px}}
</style></head><body><main><section class="card">
<h1>AIOS</h1><p>Sign in to continue.</p>{error_html}
<form method="post" action="/login">
<input type="hidden" name="next" value="{safe_next}">
<label>Username</label><input name="username" autocomplete="username" required autofocus>
<label>Password</label><input name="password" type="password" autocomplete="current-password" required>
<button type="submit">Sign in</button>
</form></section></main></body></html>'''

def _check_basic_auth(request: Request) -> str:
    username = _decode_session(request.cookies.get(SESSION_COOKIE_NAME))
    if username:
        return username
    next_url = _safe_login_next(
        request.url.path + (f"?{request.url.query}" if request.url.query else "")
    )
    raise HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        headers={"Location": f"/login?next={quote_plus(next_url)}"},
    )

@app.get("/login", response_class=HTMLResponse)
def login_web(request: Request, next: str = "/"):
    username = _decode_session(request.cookies.get(SESSION_COOKIE_NAME))
    if username:
        return RedirectResponse(_safe_login_next(next), status_code=303)
    return HTMLResponse(_login_page(next))

@app.post("/login")
def login_submit_web(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str, Form()] = "/",
):
    expected_username = _env("AIOS_WEB_USERNAME")
    expected_password = _env("AIOS_WEB_PASSWORD")
    ok = (
        hmac.compare_digest(str(username).encode(), expected_username.encode())
        and hmac.compare_digest(str(password).encode(), expected_password.encode())
    )
    if not ok:
        return HTMLResponse(
            _login_page(next, "Invalid username or password."),
            status_code=401,
        )
    response = RedirectResponse(_safe_login_next(next), status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        _encode_session(expected_username),
        max_age=_session_days() * 86400,
        httponly=True,
        secure=_session_cookie_secure(),
        samesite="lax",
        path="/",
    )
    return response

@app.post("/logout")
def logout_web():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=_session_cookie_secure(),
        httponly=True,
        samesite="lax",
    )
    return response

def _api_url() -> str:
    return _env("AIOS_API_URL").rstrip("/")


def _identity_token(audience: str) -> str:
    cache_for = 3000.0
    now = time.time()
    cached = getattr(_identity_token, "_cache", None)
    if cached is None:
        cached = {}
        _identity_token._cache = cached  # type: ignore[attr-defined]
    entry = cached.get(audience)
    if entry and entry[1] > now:
        return entry[0]

    impersonate_service_account = (os.getenv("AIOS_LOCAL_IMPERSONATE_SERVICE_ACCOUNT") or "").strip()
    if impersonate_service_account:
        result = subprocess.run(
            [
                "gcloud", "auth", "print-identity-token",
                f"--impersonate-service-account={impersonate_service_account}",
                f"--audiences={audience}",
            ],
            check=True, capture_output=True, text=True,
        )
        token = result.stdout.strip()
        if not token:
            raise RuntimeError("gcloud returned an empty identity token")
    else:
        request = GoogleAuthRequest()
        token = id_token.fetch_id_token(
            request,
            audience,
        )

    cached[audience] = (token, now + cache_for)
    return token


def _fetch_focus() -> dict | None:
    api_url = _api_url()
    token = _identity_token(api_url)
    response = requests.get(f"{api_url}/focus", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if not response.ok:
        raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    value = (response.json() or {}).get("focus")
    return dict(value) if value else None


def _fetch_open_tasks(*, search: str = "", limit: int = 50) -> dict:
    api_url=_api_url(); token=_identity_token(api_url)
    response=requests.get(f"{api_url}/tasks", headers={"Authorization": f"Bearer {token}"}, params={"limit": limit, "search": search}, timeout=30)
    if not response.ok:
        raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    payload = response.json() or {}
    sections = dict(payload.get("sections") or {})
    sections["_completed_today_summary"] = str(payload.get("completed_today_summary") or "").strip()
    sections["_completed_today_summary_state"] = str(payload.get("completed_today_summary_state") or "empty")
    return sections


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


def _task_snooze_control_html(
    task_id: str,
    *,
    return_to: str = "",
    external_form_id: str = "",
    css_class: str = "task-snooze",
) -> str:
    """Render the shared icon-based snooze menu for an actionable task."""
    safe_id = html.escape(str(task_id), quote=True)
    safe_return = html.escape(str(return_to or ""), quote=True)
    safe_class = html.escape(css_class, quote=True)

    if external_form_id:
        form_id = html.escape(external_form_id, quote=True)
        preset_button = lambda value, label: (
            f'<button class="menu-button" type="submit" form="{form_id}" name="preset" value="{value}">{label}</button>'
        )
        custom_controls = (
            f'<div class="task-snooze-date">'
            f'<input type="date" name="custom_date" form="{form_id}" required>'
            f'<button class="menu-button" type="submit" form="{form_id}" name="preset" value="pick_date">Pick date</button>'
            f'</div>'
        )
    else:
        def preset_button(value: str, label: str) -> str:
            return (
                f'<form class="menu-form" method="post" action="/tasks/{safe_id}/snooze">'
                f'<input type="hidden" name="preset" value="{value}">'
                + (f'<input type="hidden" name="return_to" value="{safe_return}">' if safe_return else '')
                + f'<button class="menu-button" type="submit">{label}</button></form>'
            )
        custom_controls = (
            f'<form class="task-snooze-date menu-form" method="post" action="/tasks/{safe_id}/snooze">'
            f'<input type="hidden" name="preset" value="pick_date">'
            + (f'<input type="hidden" name="return_to" value="{safe_return}">' if safe_return else '')
            + '<input type="date" name="custom_date" required>'
            + '<button class="menu-button" type="submit">Pick date</button></form>'
        )

    return (
        f'<details class="{safe_class}">'
        '<summary class="snooze-icon-button" aria-label="Snooze task" title="Snooze task">'
        '<span aria-hidden="true">⏰</span></summary>'
        '<div class="task-snooze-menu">'
        + preset_button('later_today', 'Later today')
        + preset_button('tomorrow', 'Tomorrow')
        + preset_button('three_days', '3 days')
        + preset_button('one_week', '1 week')
        + custom_controls
        + '</div></details>'
    )


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


def _capture_to_aios(text: str, *, capture_interface: str = "cloud_run_web") -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)

    response = requests.post(
        f"{api_url}/inbox",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"text": text, "capture_interface": capture_interface},
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


def _capture_many(
    lines: list[str],
    *,
    capture_interface: str = "cloud_run_web",
) -> tuple[int, list[str]]:
    sent = 0
    failures: list[str] = []

    for line in lines:
        try:
            _capture_to_aios(line, capture_interface=capture_interface)
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


def _request_focus_context_help(task_id: str) -> dict:
    api_url = _api_url(); token = _identity_token(api_url)
    response = requests.post(f"{api_url}/tasks/{task_id}/focus-context/help", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if not response.ok: raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    return dict(response.json() or {})


def _answer_focus_context(task_id: str, answer: str) -> dict:
    api_url = _api_url(); token = _identity_token(api_url)
    response = requests.post(f"{api_url}/tasks/{task_id}/focus-context/answer", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"answer": answer}, timeout=30)
    if not response.ok: raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    return dict(response.json() or {})


def _save_focus_context(task_id: str, context: str) -> dict:
    api_url = _api_url(); token = _identity_token(api_url)
    response = requests.post(f"{api_url}/tasks/{task_id}/focus-context", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"context": context}, timeout=30)
    if not response.ok: raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    return dict(response.json() or {})


def _safe_return_to(value: str | None) -> str:
    """Allow only local AIOS paths as task-detail return targets."""
    target = str(value or "").strip()

    if not target.startswith("/") or target.startswith("//"):
        return "/"

    return target


def _with_fast_return_param(value: str | None) -> str:
    """Mark return targets that should render immediately and hydrate via polling."""
    target = _safe_return_to(value)
    if target.startswith("/projects/"):
        return target
    if "fast=1" in target:
        return target
    joiner = "&" if "?" in target else "?"
    return f"{target}{joiner}fast=1"


def _task_date_input_value(value: object) -> str:
    from aios.temporal import local_date_for_task_datetime

    local_date = local_date_for_task_datetime(value)
    return local_date.isoformat() if local_date else ""


def _task_datetime_local_input_value(value: object) -> str:
    from aios.temporal import local_timezone, task_datetime

    dt = task_datetime(value)
    if dt is None:
        return ""
    return dt.astimezone(local_timezone()).strftime("%Y-%m-%dT%H:%M")


def _task_edit_form_payload(
    *,
    title: str,
    context: str = "",
    due_at: str = "",
    defer_until: str = "",
    importance: str = "",
    urgency: str = "",
    effort: str = "",
    duration: str = "",
    is_just_do_it: str | None = None,
) -> dict:
    return {
        "title": title.strip(),
        "context": context.strip(),
        "due_at": due_at,
        "defer_until": defer_until,
        "importance": importance,
        "urgency": urgency,
        "effort": effort,
        "duration": duration,
        "is_just_do_it": is_just_do_it == "true",
    }


def _breakdown_list_editor_html(*, titles: list[str], form_action: str, return_to: str, submit_label: str, cancel_action: str | None = None) -> str:
    rows = []
    for title in titles:
        rows.append(
            '<div class="breakdown-row" draggable="true">'
            '<button class="breakdown-drag" type="button" title="Drag to reorder" aria-label="Drag to reorder">☷</button>'
            f'<input class="breakdown-title" type="text" value="{html.escape(str(title), quote=True)}" aria-label="Subtask title">'
            '<button class="breakdown-trash" type="button" title="Remove task" aria-label="Remove task">🗑</button>'
            '</div>'
        )
    rows_html = ''.join(rows)
    cancel_html = ''
    if cancel_action:
        cancel_html = f'<button class="secondary-button" type="submit" formaction="{cancel_action}" formnovalidate>Cancel</button>'
    return f'''
    <form method="post" action="{form_action}" class="breakdown-list-form" onsubmit="return syncBreakdownTitles(this)">
      <input type="hidden" name="return_to" value="{html.escape(return_to, quote=True)}">
      <input type="hidden" name="titles" value="">
      <div class="breakdown-list" data-breakdown-list>{rows_html}</div>
      <button class="breakdown-add" type="button" onclick="addBreakdownRow(this)">+ Add task</button>
      <div class="actions">
        <button class="primary-button" type="submit">{html.escape(submit_label)}</button>
        {cancel_html}
      </div>
    </form>
    '''


def _fragment_poll_script(
    *,
    enabled: bool,
    url: str,
    target_id: str,
    fingerprint: str,
    session_key: str,
    init_hook: str = "",
    initial_delay: int = 2000,
    max_attempts: int = 45,
) -> str:
    config = {
        "enabled": enabled,
        "url": url,
        "targetId": target_id,
        "initialFingerprint": fingerprint,
        "sessionKey": session_key,
        "initHook": init_hook or None,
        "initialDelay": initial_delay,
        "maxAttempts": max_attempts,
    }
    if not enabled:
        return (
            f"<script>window.__AIOS_FRAGMENT_POLL__ = {json.dumps({'enabled': False})};"
            f"sessionStorage.removeItem({json.dumps(session_key)});</script>"
        )
    return (
        f"<script>window.__AIOS_FRAGMENT_POLL__ = {json.dumps(config)};</script>"
        + _FRAGMENT_POLL_CLIENT_JS
    )


_FRAGMENT_POLL_CLIENT_JS = """
<script>
(() => {
  const cfg = window.__AIOS_FRAGMENT_POLL__;
  if (!cfg?.enabled) return;

  let fingerprint = cfg.initialFingerprint || null;
  let timer = null;
  let attempt = Number(sessionStorage.getItem(cfg.sessionKey) || "0");
  let delay = cfg.initialDelay || 2000;
  const maxDelay = 30000;
  const maxAttempts = cfg.maxAttempts || 45;

  const runInitHook = (root) => {
    const hook = cfg.initHook;
    if (!hook) return;
    const fn = window[hook];
    if (typeof fn === "function") fn(root);
  };

  const replaceTarget = (html) => {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = html.trim();
    const next = wrapper.firstElementChild;
    if (!next) return null;
    const existing = document.getElementById(cfg.targetId);
    if (existing) {
      existing.replaceWith(next);
    }
    runInitHook(next);
    return next;
  };

  const showPollTimeout = () => {
    const target = document.getElementById(cfg.targetId);
    if (!target) return;
    target.innerHTML =
      '<div class="fragment-poll-timeout">' +
      '<p>Still processing. The update may still be running in the background.</p>' +
      '<div class="fragment-poll-timeout-actions">' +
      '<button type="button" class="primary" data-fragment-poll-retry>Try again</button>' +
      '<button type="button" class="link" data-fragment-poll-reload>Refresh page</button>' +
      '</div></div>';
    target.querySelector("[data-fragment-poll-retry]")?.addEventListener("click", () => {
      sessionStorage.removeItem(cfg.sessionKey);
      attempt = 0;
      delay = cfg.initialDelay || 2000;
      schedulePoll();
    });
    target.querySelector("[data-fragment-poll-reload]")?.addEventListener("click", () => {
      window.location.reload();
    });
  };

  const poll = async () => {
    if (attempt >= maxAttempts) {
      sessionStorage.removeItem(cfg.sessionKey);
      timer = null;
      showPollTimeout();
      return;
    }

    attempt += 1;
    sessionStorage.setItem(cfg.sessionKey, String(attempt));

    try {
      const response = await fetch(cfg.url, {
        headers: { "X-Requested-With": "fetch" },
      });
      if (!response.ok) throw new Error("Fragment poll failed");
      const data = await response.json();
      if (data.html && data.fingerprint !== fingerprint) {
        replaceTarget(data.html);
        fingerprint = data.fingerprint;
      }
      if (!data.pending) {
        sessionStorage.removeItem(cfg.sessionKey);
        timer = null;
        return;
      }
    } catch (_error) {
      // Keep polling on transient failures.
    }

    delay = Math.min(Math.round(delay * 1.6), maxDelay);
    timer = window.setTimeout(poll, delay);
  };

  const schedulePoll = () => {
    if (timer) window.clearTimeout(timer);
    timer = window.setTimeout(poll, delay);
  };

  schedulePoll();
})();
</script>
"""


def _breakdown_panel_fingerprint(task: dict) -> str:
    breakdown_state = str(task.get("breakdown_state") or "").strip()
    raw_proposal = task.get("breakdown_proposal") or []
    proposal_titles = [
        str(item).strip()
        for item in raw_proposal
        if str(item).strip()
    ] if isinstance(raw_proposal, list) else []
    children = list(task.get("breakdown_children") or [])
    parts = [
        breakdown_state,
        str(len(proposal_titles)),
        "|".join(proposal_titles),
        str(bool(task.get("has_breakdown_children"))),
        str(task.get("breakdown_request_context") or "")[:120],
        str(len(children)),
    ]
    for child in children:
        parts.extend(
            [
                str(child.get("id") or ""),
                str(child.get("title") or ""),
                "1" if child.get("is_done") else "0",
            ]
        )
    return "|".join(parts)


def _breakdown_panel_body(task: dict, *, return_to: str) -> str:
    task_id = html.escape(str(task.get("id") or ""))
    safe_return_to = html.escape(_safe_return_to(return_to), quote=True)
    breakdown_state = str(task.get("breakdown_state") or "").strip()
    has_breakdown_children = bool(task.get("has_breakdown_children"))
    breakdown_context = html.escape(str(task.get("breakdown_request_context") or ""))
    raw_proposal = task.get("breakdown_proposal") or []
    proposal_titles = [
        str(item).strip() for item in raw_proposal
        if str(item).strip()
    ] if isinstance(raw_proposal, list) else []

    if breakdown_state == "pending":
        return """
        <p class="readonly-note">AIOS is proposing the smallest useful breakdown using your guidance. Nothing will be created until you accept it.</p>
        <div class="breakdown-pending"><span class="mini-spinner"></span> Building proposed breakdown…</div>
        """
    if breakdown_state == "proposed" and proposal_titles:
        return f"""
        <p class="readonly-note">Review the proposed breakdown below. Drag to reorder, edit task names, remove tasks, or add a missing task before accepting.</p>
        {_breakdown_list_editor_html(titles=proposal_titles, form_action=f"/tasks/{task_id}/breakdown/accept", return_to=_safe_return_to(return_to), submit_label="Accept Breakdown", cancel_action=f"/tasks/{task_id}/breakdown/cancel")}
        """
    if breakdown_state == "accepted" or has_breakdown_children:
        children = list(task.get("breakdown_children") or [])
        completed_children = [c for c in children if c.get("is_done")]
        open_children = [c for c in children if not c.get("is_done") and c.get("is_open", True)]
        completed_html = ""
        if completed_children:
            items = "".join(
                f"<li>{html.escape(str(c.get('title') or ''))} <span class='optional'>(completed)</span></li>"
                for c in completed_children
            )
            completed_html = (
                f"<p class='readonly-note'>Completed subtasks are preserved as history and are not removed by this editor.</p><ul>{items}</ul>"
            )
        return f"""
        <p class="readonly-note">Edit the open breakdown below. Drag to reorder, edit task names, remove tasks, or add a missing task.</p>
        {completed_html}
        {_breakdown_list_editor_html(titles=[str(c.get("title") or "").strip() for c in open_children], form_action=f"/tasks/{task_id}/breakdown/edit", return_to=_safe_return_to(return_to), submit_label="Save Breakdown")}
        """

    state_note = ""
    if breakdown_state == "no_proposal":
        state_note = '<div class="notice">AIOS did not find a useful breakdown. Add guidance and try again if you want.</div>'
    elif breakdown_state == "failed":
        state_note = '<div class="notice error">AIOS could not generate a breakdown. You can try again with more guidance.</div>'
    return f"""
        {state_note}
        <p class="readonly-note">Use this when the task would be easier to execute as a small set of meaningful steps. AIOS will propose first; nothing is created automatically.</p>
        <form method="post" action="/tasks/{task_id}/breakdown/request">
          <input type="hidden" name="return_to" value="{safe_return_to}">
          <label>Anything AIOS should know? <span class="optional">Optional</span>
            <textarea class="breakdown-editor" name="context" rows="3" placeholder="e.g. I already bought the materials; focus on installation.">{breakdown_context}</textarea>
          </label>
          <div class="actions"><button class="secondary-button" type="submit">Break Down Task</button></div>
        </form>
        """


def _breakdown_panel_view(task: dict, *, return_to: str = "/") -> dict[str, object]:
    body = _breakdown_panel_body(task, return_to=return_to)
    pending = str(task.get("breakdown_state") or "").strip() == "pending"
    return {
        "html": f'<div id="breakdown-panel">{body}</div>',
        "fingerprint": _breakdown_panel_fingerprint(task),
        "pending": pending,
    }


def _task_detail_page(
    task: dict,
    message: str = "",
    error: str = "",
    return_to: str = "/",
) -> str:
    task_id = html.escape(str(task.get("id") or ""))
    title = html.escape(str(task.get("title") or ""))
    task_context = html.escape(str(task.get("context") or ""))
    due_at = html.escape(_task_date_input_value(task.get("due_at")))
    defer_until = html.escape(_task_datetime_local_input_value(task.get("defer_until")))
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

    breakdown_view = _breakdown_panel_view(task, return_to=return_to)
    breakdown_body = str(breakdown_view["html"])
    raw_task_id = str(task.get("id") or "")
    breakdown_poll_script = _fragment_poll_script(
        enabled=bool(breakdown_view["pending"]),
        url=f"/api/tasks/{quote_plus(raw_task_id)}/breakdown-panel?return_to={quote_plus(_safe_return_to(return_to))}",
        target_id="breakdown-panel",
        fingerprint=str(breakdown_view["fingerprint"]),
        session_key="aios-breakdown-panel-refresh-count",
        init_hook="aiosInitBreakdownPanel",
        initial_delay=2500,
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
{_theme_head_extras()}
<title>AIOS Task</title>
<style>
{_mobile_shell_css()}
.layout {{
  display:grid;
  grid-template-columns:minmax(0,1.35fr) minmax(300px,.85fr);
  gap:24px;
  margin-top:8px;
  align-items:start;
}}
.card {{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:var(--radius-2xl);
  padding:28px 24px;
  box-shadow:var(--shadow);
}}
.card-title {{
  margin:0 0 22px;
  color:var(--charcoal);
  font-size:1.12rem;
  font-weight:700;
  line-height:var(--line-body);
}}
.form-grid {{
  display:grid;
  grid-template-columns:1fr;
  gap:20px;
}}
.form-grid label {{ min-width:0; }}
.full {{ grid-column:1/-1; }}
.datetime-field {{
  display:grid;
  grid-template-columns:minmax(0,1fr) auto;
  gap:8px;
  align-items:center;
}}
.field-clear {{
  flex:0 0 auto;
  min-height:40px;
  border:1px solid var(--border);
  border-radius:999px;
  padding:0 12px;
  background:var(--card);
  color:var(--muted);
  font:inherit;
  font-size:.82rem;
  font-weight:600;
  cursor:pointer;
  white-space:nowrap;
}}
.field-clear.icon {{
  width:40px;
  min-width:40px;
  padding:0;
  font-size:1.25rem;
  line-height:1;
}}
.field-clear:hover {{ color:var(--charcoal); border-color:var(--charcoal); }}
label {{
  display:grid;
  gap:10px;
  color:var(--ink);
  font-size:.92rem;
  font-weight:600;
  line-height:var(--line-body);
}}
input[type="text"],
input[type="date"],
input[type="datetime-local"],
textarea {{
  width:100%;
  max-width:100%;
  box-sizing:border-box;
  min-width:0;
  min-height:48px;
  border:1px solid var(--border);
  border-radius:var(--radius-2xl);
  padding:0 16px;
  background:var(--highlight);
  color:var(--ink);
  font:inherit;
  font-weight:500;
  line-height:var(--line-body);
  outline:none;
  overflow:hidden;
  text-overflow:ellipsis;
}}
input[type="date"],
input[type="datetime-local"] {{
  padding:0 12px;
  font-size:1rem;
}}
@media (max-width:640px) {{
  .datetime-field {{
    grid-template-columns:minmax(0,1fr) 40px;
  }}
  input[type="date"],
  input[type="datetime-local"] {{
    font-size:16px;
  }}
}}
textarea {{
  min-height:96px;
  padding:14px 16px;
  resize:vertical;
}}
input:focus, textarea:focus {{
  border-color:var(--focus-ring);
  box-shadow:0 0 0 3px var(--focus-ring-shadow);
}}
.checkbox-row {{
  display:flex;
  align-items:center;
  gap:12px;
  min-height:48px;
  padding:4px 0;
  line-height:var(--line-relaxed);
}}
.checkbox-row input {{
  width:20px;
  height:20px;
  accent-color:var(--charcoal);
}}
.actions {{
  display:flex;
  gap:12px;
  align-items:center;
  margin-top:24px;
  flex-wrap:wrap;
}}
.primary-button {{
  min-height:48px;
  border:0;
  border-radius:var(--radius-2xl);
  padding:0 20px;
  background:var(--charcoal);
  color:var(--paper);
  font:inherit;
  font-weight:700;
  cursor:pointer;
}}
.secondary-button {{
  min-height:48px; border:1px solid var(--border); border-radius:var(--radius-2xl);
  padding:0 18px; background:var(--card); color:var(--charcoal); font:inherit; font-weight:700; cursor:pointer;
}}
.breakdown-editor {{ width:100%; margin-top:10px; min-height:96px; resize:vertical; }}
.breakdown-list {{ display:grid; gap:12px; margin-top:16px; }}
.breakdown-row {{ display:grid; grid-template-columns:42px minmax(0,1fr) 46px; gap:10px; align-items:center; padding:12px; border:1px solid var(--border); border-radius:var(--radius-2xl); background:var(--card); box-shadow:var(--shadow); }}
.breakdown-row.dragging {{ opacity:.45; }}
.breakdown-drag, .breakdown-trash, .breakdown-add {{ border:1px solid var(--border); background:var(--card); color:var(--charcoal); font:inherit; font-weight:700; cursor:pointer; border-radius:12px; }}
.breakdown-drag {{ height:42px; cursor:grab; font-size:22px; line-height:1; }}
.breakdown-drag:active {{ cursor:grabbing; }}
.breakdown-trash {{ height:42px; font-size:18px; }}
.breakdown-add {{ min-height:44px; padding:0 16px; margin-top:14px; }}
.breakdown-title {{ width:100%; min-height:44px; }}
@media (max-width:640px) {{ .breakdown-row {{ grid-template-columns:38px minmax(0,1fr) 42px; padding:10px; }} }}
.optional {{ color:var(--muted); font-weight:500; }}
.breakdown-pending {{ display:flex; align-items:center; gap:12px; font-weight:700; color:var(--charcoal); line-height:var(--line-relaxed); }}
.fragment-poll-timeout {{ display:grid; gap:12px; margin-top:16px; color:var(--ink); font-size:.95rem; line-height:var(--line-relaxed); }}
.fragment-poll-timeout-actions {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; }}
.fragment-poll-timeout-actions button {{ min-height:0; padding:10px 14px; border-radius:999px; border:1px solid var(--border); background:var(--surface); color:var(--charcoal); font:inherit; font-weight:600; cursor:pointer; }}
.fragment-poll-timeout-actions button.primary {{ background:var(--charcoal); border-color:var(--charcoal); color:var(--paper); }}
.fragment-poll-timeout-actions button.link {{ border:0; background:transparent; color:var(--muted); text-decoration:underline; padding:10px 0; }}
.mini-spinner {{ width:18px; height:18px; border:3px solid var(--border); border-top-color:var(--charcoal); border-radius:50%; animation:spin .8s linear infinite; }}
@keyframes spin {{ to {{ transform:rotate(360deg); }} }}
.secondary-link {{
  min-height:48px;
  display:inline-flex;
  align-items:center;
  padding:0 16px;
  border:1px solid var(--border);
  border-radius:var(--radius-2xl);
  color:var(--charcoal);
  text-decoration:none;
  font-weight:600;
  background:var(--card);
}}
.notice {{
  margin:0 0 24px;
  padding:16px 18px;
  border-radius:var(--radius-2xl);
  font-weight:600;
  line-height:var(--line-relaxed);
  box-shadow:var(--shadow);
}}
.success {{ background:var(--success); color:var(--charcoal); }}
.error {{ background:var(--error); color:var(--charcoal); }}
.meta-list {{ display:grid; gap:0; }}
.meta-row {{
  display:grid;
  grid-template-columns:1fr auto;
  gap:20px;
  align-items:center;
  padding:16px 0;
  border-bottom:1px solid var(--border);
  line-height:var(--line-body);
}}
.meta-row:last-child {{ border-bottom:0; }}
.meta-label {{
  color:var(--muted);
  font-size:.86rem;
  font-weight:600;
}}
.meta-value {{
  color:var(--ink);
  font-weight:700;
  text-align:right;
  overflow-wrap:anywhere;
}}
.project-value {{
  max-width:260px;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:.84rem;
  font-weight:600;
}}
.readonly-note {{
  margin:-4px 0 18px;
  color:var(--muted);
  font-size:.9rem;
  line-height:var(--line-relaxed);
}}
@media (max-width:960px) {{
  .layout {{ grid-template-columns:1fr; }}
  .card {{ padding:22px 20px; }}
}}
</style>
</head>
<body>
<main>
  <a class="detail-back" href="{return_to}">← Back</a>
  <div class="page-heading">
    <h1 class="brand">Edit Task</h1>
    <p class="subtitle">Update task details while keeping AIOS guidance read-only.</p>
  </div>

  {notice}

  <div class="layout">
    <form method="post" action="/tasks/{task_id}/edit" id="taskEditForm" data-async-save="{WEB_TASK_DETAIL_OPTIMISTIC_SAVE_VERSION}">
      <input type="hidden" name="return_to" value="{return_to}">
      <section class="card">
        <h2 class="card-title">Task Details</h2>

        <div class="form-grid">
          <label class="full">
            Task
            <input type="text" name="title" value="{title}" required>
          </label>

          <label class="full">
            Task context <span class="optional">Optional</span>
            <textarea name="context" rows="4" placeholder="Supporting detail, constraints, or useful context that does not belong in the task title.">{task_context}</textarea>
          </label>

          <label class="full">
            Due date
            <span class="datetime-field">
              <input type="date" name="due_at" value="{due_at}">
              <button type="button" class="field-clear icon" data-clear-for="due_at" aria-label="Clear due date">×</button>
            </span>
          </label>

          <label class="full">
            Defer until
            <span class="datetime-field">
              <input type="datetime-local" name="defer_until" value="{defer_until}">
              <button type="button" class="field-clear icon" data-clear-for="defer_until" aria-label="Clear defer until">×</button>
            </span>
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
<script>
(() => {{
  const form = document.getElementById("taskEditForm");
  if (!form) return;

  form.addEventListener("submit", (event) => {{
    event.preventDefault();
    if (form.dataset.saving === "1") return;
    form.dataset.saving = "1";

    const returnTo = form.querySelector('input[name="return_to"]')?.value || "/";
    const body = new FormData(form);

    try {{
      fetch(form.action, {{
        method: "POST",
        body,
        credentials: "same-origin",
        keepalive: true,
      }}).catch(() => {{}});
    }} catch (_error) {{}}

    let returned = false;
    try {{
      const targetPath = new URL(returnTo, window.location.origin).pathname;
      const referrerPath = document.referrer
        ? new URL(document.referrer, window.location.origin).pathname
        : "";
      if (referrerPath && referrerPath === targetPath && window.history.length > 1) {{
        window.history.back();
        returned = true;
      }}
    }} catch (_error) {{}}

    if (!returned) {{
      let fastReturn = returnTo;
      try {{
        const url = new URL(returnTo, window.location.origin);
        if (!url.pathname.startsWith("/projects/")) {{
          url.searchParams.set("fast", "1");
        }}
        fastReturn = url.pathname + url.search + url.hash;
      }} catch (_error) {{}}
      window.location.assign(fastReturn);
    }}
  }});
}})();
</script>

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

  <section class="card" id="breakdown" style="margin-top:24px;">
    <h2 class="card-title">Breakdown</h2>
    {breakdown_body}
  </section>
</main>
{_bottom_nav_html(active="home")}
<script>
function breakdownRow(title) {{
  const row = document.createElement('div'); row.className='breakdown-row'; row.draggable=true;
  row.innerHTML='<button class="breakdown-drag" type="button" title="Drag to reorder" aria-label="Drag to reorder">☷</button><input class="breakdown-title" type="text" aria-label="Subtask title"><button class="breakdown-trash" type="button" title="Remove task" aria-label="Remove task">🗑</button>';
  row.querySelector('.breakdown-title').value=title||''; wireBreakdownRow(row); return row;
}}
function wireBreakdownRow(row) {{ const trash=row.querySelector('.breakdown-trash'); if(trash) trash.onclick=function(){{row.remove();}}; row.addEventListener('dragstart',function(e){{row.classList.add('dragging');e.dataTransfer.effectAllowed='move';}}); row.addEventListener('dragend',function(){{row.classList.remove('dragging');}}); }}
function addBreakdownRow(button) {{ const form=button.closest('form'), list=form.querySelector('[data-breakdown-list]'), row=breakdownRow(''); list.appendChild(row); row.querySelector('.breakdown-title').focus(); }}
function syncBreakdownTitles(form) {{ const titles=Array.from(form.querySelectorAll('.breakdown-title')).map(i=>i.value.trim()).filter(Boolean); form.querySelector('input[name="titles"]').value=titles.join('\\n'); return true; }}
window.aiosInitBreakdownPanel=function(root){{ const scope=root||document; scope.querySelectorAll('.breakdown-row').forEach(wireBreakdownRow); scope.querySelectorAll('[data-breakdown-list]').forEach(function(list){{ if(list.dataset.aiosBreakdownBound==='1')return; list.dataset.aiosBreakdownBound='1'; list.addEventListener('dragover',function(e){{ e.preventDefault(); const dragging=list.querySelector('.dragging'); if(!dragging)return; const candidates=Array.from(list.querySelectorAll('.breakdown-row:not(.dragging)')); const after=candidates.reduce(function(best,child){{const box=child.getBoundingClientRect(),offset=e.clientY-box.top-box.height/2; return offset<0&&offset>best.offset?{{offset:offset,element:child}}:best;}},{{offset:Number.NEGATIVE_INFINITY,element:null}}).element; if(after)list.insertBefore(dragging,after);else list.appendChild(dragging); }}); }}); }};
function wireProjectTaskRow(row) {{ const title=row.querySelector('.project-editor-title'); if(title){{ const remember=function(){{row.dataset.editedTitle=title.value;}}; title.addEventListener('input',remember); title.addEventListener('change',remember); remember(); }} const trash=row.querySelector('.project-editor-trash'); if(trash) trash.onclick=function(){{row.remove();}}; row.addEventListener('dragstart',function(e){{row.classList.add('dragging');e.dataTransfer.effectAllowed='move';}}); row.addEventListener('dragend',function(){{row.classList.remove('dragging');}}); }}
function projectTaskRow(title) {{ const row=document.createElement('div'); row.className='project-editor-row'; row.draggable=true; row.dataset.taskId=''; row.innerHTML='<button class="project-drag" type="button" title="Drag to reorder" aria-label="Drag to reorder">☷</button><span></span><div class="project-editor-main"><input type="hidden" name="task_id" value=""><input class="project-editor-title" name="task_title" type="text" aria-label="Task title"><div class="task-meta">New task</div></div><span></span><button class="project-editor-trash" type="button" title="Remove task" aria-label="Remove task">🗑</button>'; row.querySelector('.project-editor-title').value=title||''; wireProjectTaskRow(row); return row; }}
function addProjectTaskRow(button) {{ const form=button.closest('form'),list=form.querySelector('[data-project-task-list]'); const empty=list.querySelector('.project-empty'); if(empty) empty.remove(); const row=projectTaskRow(''); list.appendChild(row); row.querySelector('.project-editor-title').focus(); }}
function syncProjectTasks(form) {{ const tasks=Array.from(form.querySelectorAll('.project-editor-row')).map(function(row){{ const input=row.querySelector('.project-editor-title'); const liveTitle=input?input.value:String(row.dataset.editedTitle||''); row.dataset.editedTitle=liveTitle; return {{id:row.dataset.taskId||null,title:liveTitle.trim()}};}}).filter(t=>t.title); form.querySelector('input[name="tasks_json"]').value=JSON.stringify(tasks); return true; }}

document.addEventListener('DOMContentLoaded',function(){{ window.aiosInitBreakdownPanel(document.getElementById('breakdown-panel')); document.querySelectorAll('.project-editor-row').forEach(wireProjectTaskRow); document.querySelectorAll('[data-project-task-list]').forEach(function(list){{ list.addEventListener('dragover',function(e){{e.preventDefault(); const dragging=list.querySelector('.dragging'); if(!dragging)return; const candidates=Array.from(list.querySelectorAll('.project-editor-row:not(.dragging)')); const after=candidates.reduce(function(best,child){{const box=child.getBoundingClientRect(),offset=e.clientY-box.top-box.height/2; return offset<0&&offset>best.offset?{{offset:offset,element:child}}:best;}},{{offset:Number.NEGATIVE_INFINITY,element:null}}).element; if(after)list.insertBefore(dragging,after);else list.appendChild(dragging);}});}}); }});
</script>
{breakdown_poll_script}
<script>
(() => {{
  document.querySelectorAll(".field-clear").forEach((button) => {{
    button.addEventListener("click", () => {{
      const name = button.dataset.clearFor;
      if (!name) return;
      const input = document.querySelector(`#taskEditForm [name="${{name}}"]`);
      if (input) input.value = "";
    }});
  }});
}})();
</script>
</body>
</html>"""


def _save_task_detail_background(task_id: str, payload: dict) -> None:
    try:
        _update_task_detail(task_id, payload)
    except Exception as exc:
        print(f"[Task Edit Background] Save failed for {task_id}:", exc)


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


def _update_project_tasks(project_id: str, tasks: list[dict]) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)
    response = requests.put(
        f"{api_url}/projects/{project_id}/tasks",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"tasks": tasks},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    return dict(response.json() or {})


def _work_patterns_api(method: str, path: str, payload: dict | None = None) -> dict:
    api_url=_api_url(); token=_identity_token(api_url)
    response=requests.request(method,f"{api_url}{path}",headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},json=payload,timeout=30)
    if not response.ok: raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    return dict(response.json() or {})

def _fetch_work_patterns() -> list[dict]: return list(_work_patterns_api("GET","/work-patterns").get("patterns") or [])
def _fetch_work_pattern(pattern_id: str) -> dict: return dict(_work_patterns_api("GET",f"/work-patterns/{pattern_id}").get("pattern") or {})

def _pattern_rows(steps: list[dict]) -> str:
    return ''.join('<div class="pattern-row" draggable="true"><button class="drag" type="button">☷</button><div><input name="step_title" required value="'+html.escape(str(s.get("title") or ""),quote=True)+'" placeholder="Task title"><input name="step_context" value="'+html.escape(str(s.get("context") or ""),quote=True)+'" placeholder="Optional task context"></div><button class="trash" type="button">🗑</button></div>' for s in steps)

def _pattern_shell(title: str, body: str, *, nav_active: str = "more") -> str:
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">{_theme_head_extras()}<title>{html.escape(title)} · AIOS</title><style>{_mobile_shell_css()}
.card,.pattern-row{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-2xl);box-shadow:var(--shadow)}}
.card{{padding:24px 22px;margin:0 0 20px;line-height:var(--line-relaxed)}}
.pattern-row{{display:grid;grid-template-columns:40px 1fr 44px;gap:10px;padding:12px;margin:10px 0}}
.pattern-row>div{{display:grid;gap:8px}}
input,textarea{{width:100%;box-sizing:border-box;padding:12px 14px;border:1px solid var(--border);border-radius:var(--radius-2xl);font:inherit;background:var(--highlight);color:var(--ink);line-height:var(--line-body)}}
textarea{{min-height:96px}}
button,.button{{border:1px solid var(--border);background:var(--card);color:var(--charcoal);border-radius:var(--radius-2xl);padding:10px 14px;font:inherit;font-weight:700;cursor:pointer;text-decoration:none;line-height:var(--line-body)}}
.primary{{background:var(--charcoal);color:var(--paper);border:0}}
.actions{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:18px}}
.drag{{cursor:grab;padding:0;font-size:20px;border:0;background:transparent}}
.trash{{padding:0;border:0;background:transparent}}
.muted{{color:var(--muted)}}
.pattern-card{{display:flex;justify-content:space-between;gap:14px;align-items:center}}
.pattern-card h1,.pattern-card h2{{margin:0;color:var(--charcoal);font-size:1.05rem;line-height:var(--line-relaxed)}}
.pattern-card p{{margin:6px 0;line-height:var(--line-relaxed)}}
.dragging{{opacity:.45}}
.pattern-card .actions{{margin-top:0}}
.pattern-choice{{text-decoration:none;color:inherit}}
.pattern-choice:hover{{box-shadow:var(--shadow-lg)}}
@media(max-width:640px){{.pattern-card{{align-items:stretch;flex-direction:column}}.pattern-card .actions{{margin-top:10px}}}}
</style></head><body><main>{body}</main>{_bottom_nav_html(active=nav_active)}</body></html>'''

def _pattern_editor(pattern: dict | None = None) -> str:
    p=dict(pattern or {}); pid=str(p.get("id") or ""); steps=list(p.get("steps") or []) or [{"title":"","context":""}]; action=f"/work-patterns/{pid}" if pid else "/work-patterns"
    body=f'''<a class="detail-back" href="/work-patterns">← Work Patterns</a><div class="page-heading"><h1 class="brand">{'Edit' if pid else 'New'} Work Pattern</h1></div><section class="surface-card"><form method="post" action="{action}"><label>Name</label><input name="name" required value="{html.escape(str(p.get('name') or ''),quote=True)}"><p><label>Context <span class="muted">(optional)</span></label></p><textarea name="context">{html.escape(str(p.get('context') or ''))}</textarea><h2>Steps</h2><div data-list>{_pattern_rows(steps)}</div><button type="button" onclick="addRow()">+ Add step</button><div class="actions"><button class="primary" type="submit">Save</button><a class="button" href="/work-patterns">Done</a></div></form></section>'''
    return _pattern_shell("Work Pattern",body+_pattern_js())

def _pattern_js() -> str:
    return '''<script>function wire(r){r.querySelector('.trash').onclick=()=>r.remove();r.addEventListener('dragstart',()=>r.classList.add('dragging'));r.addEventListener('dragend',()=>r.classList.remove('dragging'));}function addRow(){const l=document.querySelector('[data-list]'),r=document.createElement('div');r.className='pattern-row';r.draggable=true;r.innerHTML='<button class="drag" type="button">☷</button><div><input name="step_title" required placeholder="Task title"><input name="step_context" placeholder="Optional task context"></div><button class="trash" type="button">🗑</button>';l.appendChild(r);wire(r);r.querySelector('input').focus();}document.querySelectorAll('.pattern-row').forEach(wire);document.querySelector('[data-list]')?.addEventListener('dragover',e=>{e.preventDefault();const l=e.currentTarget,d=l.querySelector('.dragging');if(!d)return;const a=[...l.querySelectorAll('.pattern-row:not(.dragging)')].find(x=>e.clientY<x.getBoundingClientRect().top+x.offsetHeight/2);a?l.insertBefore(d,a):l.appendChild(d);});</script>'''

def _patterns_library(patterns: list[dict]) -> str:
    cards=''.join(f'''<div class="card pattern-card"><div><h2>{html.escape(str(p.get('name') or 'Untitled Pattern'))}</h2><p class="muted">{html.escape(str(p.get('context') or ''))}</p><span class="muted">{int(p.get('step_count') or 0)} steps</span></div><div class="actions"><a href="/work-patterns/{p.get('id')}">Edit</a><form method="post" action="/work-patterns/{p.get('id')}/duplicate"><button>Duplicate</button></form><form method="post" action="/work-patterns/{p.get('id')}/delete"><button>Delete</button></form></div></div>''' for p in patterns) or '<div class="card">No work patterns yet.</div>'
    return _pattern_shell("Work Patterns",f'<div class="page-heading"><h1 class="brand">Work Patterns</h1><p class="subtitle">Reusable ordered sets of work.</p></div><div class="card pattern-card"><div><p class="muted">Create reusable task sequences for projects.</p></div><a class="button primary" href="/work-patterns/new">+ New Pattern</a></div>{cards}')

@app.get("/work-patterns")
def work_patterns_web(_user: Annotated[str, Depends(_check_basic_auth)]): return HTMLResponse(_patterns_library(_fetch_work_patterns()))
@app.get("/work-patterns/new")
def new_work_pattern_web(_user: Annotated[str, Depends(_check_basic_auth)]): return HTMLResponse(_pattern_editor())
@app.get("/work-patterns/{pattern_id}")
def edit_work_pattern_web(
    pattern_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    saved: str = "",
):
    page = _pattern_editor(_fetch_work_pattern(pattern_id))
    if saved == "1":
        page = page.replace(
            "<h1>Edit Work Pattern</h1>",
            '<div class="muted" style="margin-top:8px">Saved</div><h1>Edit Work Pattern</h1>',
            1,
        )
    return HTMLResponse(page)
@app.post("/work-patterns")
def create_work_pattern_web(_user: Annotated[str, Depends(_check_basic_auth)],name: Annotated[str,Form()],context: Annotated[str,Form()]="",step_title: Annotated[list[str]|None,Form()]=None,step_context: Annotated[list[str]|None,Form()]=None):
    titles=list(step_title or []); contexts=list(step_context or [])+[""]*len(titles); _work_patterns_api("POST","/work-patterns",{"name":name,"context":context,"steps":[{"title":t,"context":c} for t,c in zip(titles,contexts) if t.strip()]}); return RedirectResponse("/work-patterns",303)
@app.post("/work-patterns/{pattern_id}")
def update_work_pattern_web(pattern_id: str,_user: Annotated[str, Depends(_check_basic_auth)],name: Annotated[str,Form()],context: Annotated[str,Form()]="",step_title: Annotated[list[str]|None,Form()]=None,step_context: Annotated[list[str]|None,Form()]=None):
    titles=list(step_title or [])
    contexts=list(step_context or [])+[""]*len(titles)
    _work_patterns_api(
        "PUT",
        f"/work-patterns/{pattern_id}",
        {"name":name,"context":context,"steps":[{"title":t,"context":c} for t,c in zip(titles,contexts) if t.strip()]},
    )
    return RedirectResponse(f"/work-patterns/{pattern_id}?saved=1",303)
@app.post("/work-patterns/{pattern_id}/duplicate")
def duplicate_work_pattern_web(pattern_id: str,_user: Annotated[str, Depends(_check_basic_auth)]): _work_patterns_api("POST",f"/work-patterns/{pattern_id}/duplicate",{}); return RedirectResponse("/work-patterns",303)
@app.post("/work-patterns/{pattern_id}/delete")
def delete_work_pattern_web(pattern_id: str,_user: Annotated[str, Depends(_check_basic_auth)]): _work_patterns_api("DELETE",f"/work-patterns/{pattern_id}"); return RedirectResponse("/work-patterns",303)
@app.get("/projects/{project_id}/work-patterns")
def choose_project_pattern_web(project_id: str,_user: Annotated[str, Depends(_check_basic_auth)]):
    cards=''.join(f'<a class="card pattern-card pattern-choice" href="/projects/{project_id}/work-patterns/{p.get("id")}/use"><strong>{html.escape(str(p.get("name") or "Untitled Pattern"))}</strong><span>{int(p.get("step_count") or 0)} steps</span></a>' for p in _fetch_work_patterns()) or '<div class="card">No patterns yet. <a href="/work-patterns/new">Create one.</a></div>'; return HTMLResponse(_pattern_shell("Use Work Pattern",f'<a href="/projects/{project_id}">← Project</a><h1>Use Work Pattern</h1><p>Choose a starting pattern. You can edit every task before creating anything.</p>{cards}'))
@app.get("/projects/{project_id}/work-patterns/{pattern_id}/use")
def use_project_pattern_web(project_id: str,pattern_id: str,_user: Annotated[str, Depends(_check_basic_auth)]):
    p=_fetch_work_pattern(pattern_id); body=f'<a href="/projects/{project_id}/work-patterns">← Choose Pattern</a><h1>{html.escape(str(p.get("name") or "Work Pattern"))}</h1><p>Review, edit, reorder, remove, or add tasks. Nothing is created until you accept.</p><form method="post" action="/projects/{project_id}/work-patterns/{pattern_id}/instantiate"><div data-list>{_pattern_rows(list(p.get("steps") or []))}</div><button type="button" onclick="addRow()">+ Add task</button><div class="actions"><button class="primary">Create Project Tasks</button><a href="/projects/{project_id}">Cancel</a></div></form>'; return HTMLResponse(_pattern_shell("Use Work Pattern",body+_pattern_js()))
@app.post("/projects/{project_id}/work-patterns/{pattern_id}/instantiate")
def instantiate_project_pattern_web(project_id: str,pattern_id: str,_user: Annotated[str, Depends(_check_basic_auth)],step_title: Annotated[list[str]|None,Form()]=None,step_context: Annotated[list[str]|None,Form()]=None):
    titles=list(step_title or []); contexts=list(step_context or [])+[""]*len(titles); _work_patterns_api("POST",f"/projects/{project_id}/work-patterns/{pattern_id}/instantiate",{"steps":[{"title":t,"context":c} for t,c in zip(titles,contexts) if t.strip()]}); return RedirectResponse(f"/projects/{project_id}#project-tasks",303)


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
{_theme_head_extras()}
<title>AIOS Projects</title>
<style>
{_mobile_shell_css()}
.notice {{ padding:16px 18px; border-radius:var(--radius-2xl); margin-bottom:20px; line-height:var(--line-relaxed); box-shadow:var(--shadow); }}
.error {{ background:var(--error); }}
.section {{ margin-top:28px; }}
.section:first-of-type {{ margin-top:0; }}
.section h2 {{
  margin:0 0 14px; color:var(--charcoal); font-size:1.1rem; font-weight:700;
}}
.section-note {{
  margin:-2px 0 16px; color:var(--muted); font-size:.94rem; line-height:var(--line-relaxed);
}}
.project-list {{ display:grid; gap:14px; }}
.project-card {{
  display:flex; align-items:center; justify-content:space-between;
  gap:20px; padding:20px 22px; background:var(--card);
  border:1px solid var(--border); border-radius:var(--radius-2xl);
  color:inherit; text-decoration:none; box-shadow:var(--shadow);
  line-height:var(--line-relaxed);
}}
.project-card:hover {{
  box-shadow:var(--shadow-lg);
}}
.project-card-wrap {{ display:grid; gap:10px; }}
.project-activate-form {{ display:flex; justify-content:flex-end; margin:0 4px 0 0; }}
.project-activate {{
  border:1px solid var(--charcoal); border-radius:12px; padding:8px 14px;
  background:var(--card); color:var(--charcoal); font:inherit;
  font-size:.86rem; font-weight:700; cursor:pointer;
}}
.possible-match {{
  margin-top:14px; padding:14px 16px; border:1px solid var(--border);
  border-radius:12px; background:var(--highlight);
}}
.possible-match-label {{ color:var(--muted); font-size:.8rem; font-weight:700; }}
.possible-match-name {{ margin-top:6px; color:var(--ink); font-size:.92rem; font-weight:600; line-height:var(--line-relaxed); }}
.possible-match-actions {{ display:flex; gap:10px; margin-top:12px; flex-wrap:wrap; }}
.possible-match-actions form {{ margin:0; }}
.possible-match-use, .possible-match-keep {{
  border-radius:10px; padding:8px 12px; font:inherit; font-size:.84rem; font-weight:700; cursor:pointer;
}}
.possible-match-use {{ border:1px solid var(--charcoal); background:var(--charcoal); color:var(--paper); }}
.possible-match-keep {{ border:1px solid var(--border); background:var(--card); color:var(--charcoal); }}
.review-card {{ background:var(--highlight); }}
.project-card h2 {{ margin:0; color:var(--charcoal); font-size:1.05rem; font-weight:700; line-height:var(--line-relaxed); }}
.project-status {{ display:inline-block; margin-top:8px; color:var(--muted); font-size:.86rem; }}
.review-reasons {{ margin:12px 0 0; padding-left:18px; color:var(--muted); font-size:.9rem; line-height:var(--line-relaxed); }}
.project-count {{ flex:0 0 auto; display:grid; text-align:right; }}
.project-count strong {{ color:var(--charcoal); font-size:1.35rem; line-height:1; }}
.project-count span {{ color:var(--muted); font-size:.8rem; margin-top:6px; }}
.empty-state {{
  padding:28px 24px; color:var(--muted); background:var(--card);
  border:1px solid var(--border); border-radius:var(--radius-2xl);
  box-shadow:var(--shadow); line-height:var(--line-relaxed);
}}
</style>
</head>
<body>
<main>
  <div class="page-heading">
    <h1 class="brand">Projects</h1>
    <p class="subtitle">Projects with unfinished work.</p>
  </div>

  {notice}

  <section class="surface-card section">
    <h2>Suggested Projects</h2>
    <p class="section-note">
      AIOS found these projects, but they are not active until you choose to activate them.
    </p>
    <div class="project-list">{suggested_cards}</div>
  </section>

  <section class="surface-card section">
    <h2>Needs Review</h2>
    <p class="section-note">
      Projects where AIOS sees a mismatch between project state and current work.
    </p>
    <div class="project-list">{review_cards}</div>
  </section>

  <section class="surface-card section">
    <h2>Active Projects</h2>
    <div class="project-list">{active_cards}</div>
  </section>
</main>
{_bottom_nav_html(active="projects")}
</body>
</html>"""


def _project_work_results_fingerprint(
    payload: dict,
    *,
    refresh_proposal: bool = False,
) -> str:
    project = dict(payload.get("project") or {})
    work_proposals = list(payload.get("work_proposals") or [])
    work_generation_state = str(project.get("work_generation_state") or "").strip().lower()
    parts = [
        "1" if refresh_proposal else "0",
        work_generation_state,
        str(len(work_proposals)),
        str(project.get("work_generation_question") or "")[:120],
        str(project.get("work_generation_context_update") or "")[:120],
    ]
    for proposal in work_proposals:
        parts.extend(
            [
                str(proposal.get("id") or ""),
                str(proposal.get("title") or ""),
            ]
        )
    return "|".join(parts)


def _project_work_results_body(
    payload: dict,
    *,
    refresh_proposal: bool = False,
) -> tuple[str, bool]:
    project = dict(payload.get("project") or {})
    work_proposals = list(payload.get("work_proposals") or [])
    project_id = html.escape(str(project.get("id") or ""))
    work_generation_state = str(
        project.get("work_generation_state") or ""
    ).strip().lower()
    work_generation_question = str(project.get("work_generation_question") or "").strip()
    work_generation_context_update = str(project.get("work_generation_context_update") or "").strip()

    proposal_rows = ""
    for proposal in work_proposals:
        proposal_id = html.escape(str(proposal.get("id") or ""))
        proposal_title = html.escape(str(proposal.get("title") or "Untitled proposal"))
        proposal_rows += (
            '<div class="proposal-row">'
            '<div class="proposal-section">'
            '<div class="proposal-section-label">Suggested task</div>'
            f'<form class="proposal-accept-form" method="post" '
            f'action="/projects/{project_id}/work-proposals/{proposal_id}/accept">'
            f'<textarea class="proposal-title-input" name="title" maxlength="75" required>'
            f'{proposal_title}</textarea>'
            '<div class="proposal-primary-actions">'
            '<span class="proposal-edit-note">Edit the task if needed before accepting.</span>'
            '<button class="proposal-accept" type="submit">Accept</button>'
            '</div></form></div>'
            '<div class="proposal-divider"></div>'
            '<div class="proposal-section">'
            '<div class="proposal-section-label">Not quite right?</div>'
            '<div class="proposal-help">Tell AIOS exactly what should change. '
            'Your correction will guide the next proposal.</div>'
            f'<form class="proposal-retry-form" method="post" '
            f'action="/projects/{project_id}/work-proposals/{proposal_id}/retry">'
            '<textarea name="feedback" required placeholder="What should AIOS change?"></textarea>'
            '<div class="proposal-action-row">'
            '<button class="proposal-retry" type="submit">Try Again</button></form>'
            f'<form method="post" action="/projects/{project_id}/work-proposals/{proposal_id}/dismiss">'
            '<button class="proposal-dismiss" type="submit">Dismiss</button></form>'
            '</div></div></div>'
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
        '<div><strong>Looking for missing project work…</strong>'
        '<div class="proposal-pending-note">'
        'AIOS is reviewing the project outcome, context, open work, and completed work.'
        '</div></div></div></section>'
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
            generation_result_html = (
                '<section class="proposal-card"><h2>Suggested project work</h2>'
                '<p class="proposal-note">AIOS is turning your answer into reusable project context…</p>'
                '</section>'
            )
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
                '<section class="proposal-card"><h2>Suggested project work</h2>'
                '<p class="proposal-note" style="margin-bottom:0">'
                '<strong>No missing project work found.</strong><br>'
                'AIOS did not identify additional actionable work beyond what is already planned or completed.'
                '</p></section>'
            )
        elif work_generation_state == "failed":
            generation_result_html = (
                '<section class="proposal-card"><h2>Suggested project work</h2>'
                '<p class="proposal-note" style="margin-bottom:0">'
                '<strong>Project work could not be generated.</strong><br>'
                'Check that the project has a clear outcome, then try again.'
                '</p></section>'
            )

    proposal_section = ""
    if proposal_rows and not proposal_pending:
        proposal_section = (
            '<section class="proposal-card">'
            '<h2>Proposed project work</h2>'
            '<p class="proposal-note">'
            'AIOS found grounded work that could move this project forward. '
            'Review it before creating a real task.'
            '</p>'
            + proposal_rows
            + '</section>'
        )

    body = proposal_section + pending_html + generation_result_html
    return body, proposal_pending


def _project_work_results_view(
    payload: dict,
    *,
    refresh_proposal: bool = False,
) -> dict[str, object]:
    body, pending = _project_work_results_body(payload, refresh_proposal=refresh_proposal)
    return {
        "html": f'<div id="project-work-results-panel">{body}</div>',
        "fingerprint": _project_work_results_fingerprint(
            payload,
            refresh_proposal=refresh_proposal,
        ),
        "pending": pending,
    }


def _project_detail_page(
    payload: dict,
    *,
    refresh_proposal: bool = False,
) -> str:
    project = dict(payload.get("project") or {})
    tasks = list(payload.get("tasks") or [])

    name = html.escape(str(project.get("name") or "Untitled Project"))
    project_id = html.escape(str(project.get("id") or ""))
    outcome = html.escape(str(project.get("outcome") or ""))
    context = html.escape(str(project.get("context") or ""))
    count = int(project.get("open_task_count") or 0)
    status = str(project.get("status") or "").strip()

    task_rows = ""
    completion_forms = ""
    for task in tasks:
        raw_task_id = str(task.get("id") or "")
        task_id = html.escape(raw_task_id)
        title = html.escape(str(task.get("title") or "Untitled task"), quote=True)
        score = task.get("execution_score")
        rank = task.get("execution_rank")
        due = str(task.get("due_at") or "").strip()
        importance = str(task.get("importance") or "").strip()
        meta = []
        if rank is not None: meta.append(f"Rank {html.escape(str(rank))}")
        if score is not None: meta.append(f"Score {html.escape(str(score))}")
        if importance: meta.append(html.escape(importance))
        if due: meta.append("Due " + html.escape(due[:10]))
        if task.get("best_next_action"): meta.append("Best Next Action")
        if task.get("is_quick_win"): meta.append("Quick Win")
        if task.get("is_just_do_it"): meta.append("Just Do It")
        project_return = f"/projects/{project_id}#project-tasks"
        form_id = f"project-complete-{task_id}"
        snooze_form_id = f"project-snooze-{task_id}"
        completion_forms += (
            f'<form id="{form_id}" method="post" action="/tasks/{task_id}/complete">'
            f'<input type="hidden" name="return_to" value="{project_return}"></form>'
            f'<form id="{snooze_form_id}" method="post" action="/tasks/{task_id}/snooze">'
            f'<input type="hidden" name="return_to" value="{project_return}"></form>'
        )
        task_rows += (
            f'<div class="project-editor-row" draggable="true" data-task-id="{task_id}">'
            '<button class="project-drag" type="button" title="Drag to reorder" aria-label="Drag to reorder">☷</button>'
            f'<button class="complete-checkbox" type="submit" form="{form_id}" aria-label="Mark task done" title="Mark done"><span aria-hidden="true"></span></button>'
            '<div class="project-editor-main">'
            f'<input type="hidden" name="task_id" value="{task_id}">'
            f'<input class="project-editor-title" name="task_title" type="text" value="{title}" aria-label="Task title">'
            f'<div class="task-meta">{" · ".join(meta)}</div>'
            '</div>'
            f'<a class="project-task-open" href="/tasks/{task_id}?return_to={project_return}" title="Open task">Details</a>'
            + _task_snooze_control_html(
                raw_task_id,
                return_to=project_return,
                external_form_id=snooze_form_id,
                css_class="project-task-snooze",
            )
            + '<button class="project-editor-trash" type="button" title="Remove task" aria-label="Remove task">🗑</button>'
            '</div>'
        )

    if not task_rows:
        task_rows = '<div class="empty-state project-empty">No open tasks in this project.</div>'

    status_html = (
        f'<span class="status">{html.escape(status)}</span>'
        if status else ""
    )

    work_results_view = _project_work_results_view(
        payload,
        refresh_proposal=refresh_proposal,
    )
    work_results_body = str(work_results_view["html"])
    work_results_poll_script = _fragment_poll_script(
        enabled=bool(work_results_view["pending"]),
        url=f"/api/projects/{project_id}/work-results?refresh_proposal={'1' if refresh_proposal else '0'}",
        target_id="project-work-results-panel",
        fingerprint=str(work_results_view["fingerprint"]),
        session_key="aios-project-work-results-refresh-count",
        initial_delay=2000,
    )

    scroll_proposal_script = ""
    if refresh_proposal:
        scroll_proposal_script = """
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
{_theme_head_extras()}
<title>{name} · AIOS</title>
<style>
{_mobile_shell_css()}
.header {{ margin:0 0 8px; }}
.summary {{
  display:flex; align-items:center; gap:12px;
  margin-top:10px; color:var(--muted); font-size:.94rem; line-height:var(--line-relaxed);
}}
.status {{
  padding:4px 10px; background:var(--card); border:1px solid var(--border);
  border-radius:999px; font-size:.8rem;
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
.project-task-editor {{ margin-top:24px; }}
.project-editor-list {{ display:flex; flex-direction:column; gap:10px; }}
.project-editor-row {{ display:grid; grid-template-columns:38px 44px minmax(0,1fr) auto 44px 44px; gap:10px; align-items:center; padding:12px 0; border-bottom:1px solid var(--border); }}
.project-editor-row.dragging {{ opacity:.45; }}
.project-drag {{ border:0; background:transparent; cursor:grab; font-size:24px; color:var(--muted); }}
.project-editor-title {{ width:100%; box-sizing:border-box; font:inherit; font-weight:700; color:var(--ink); border:1px solid transparent; border-radius:8px; padding:8px; background:transparent; }}
.project-editor-title:focus {{ border-color:var(--border); background:var(--surface); outline:none; }}
.project-editor-trash {{ border:0; background:transparent; cursor:pointer; font-size:20px; }}
.project-task-open {{ font-weight:700; white-space:nowrap; }}
.project-editor-actions {{ display:flex; justify-content:space-between; align-items:center; gap:12px; margin-top:16px; flex-wrap:wrap; }}
.project-add-task {{ background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:11px 16px; font-weight:700; cursor:pointer; }}

.project-task-main {{ min-width:0; }}
.project-task-link {{ color:inherit; text-decoration:none; }}
.project-task-link:hover {{ text-decoration:underline; }}
.complete-form, .delete-form {{ display:flex; margin:0; align-items:center; justify-content:center; }}
.complete-checkbox, .trash-button {{ width:44px; height:44px; min-height:44px; padding:0; border:0; border-radius:10px; background:transparent; display:flex; align-items:center; justify-content:center; cursor:pointer; }}
.complete-checkbox span {{ width:20px; height:20px; border:2px solid var(--muted); border-radius:6px; display:block; }}
.complete-checkbox:hover, .complete-checkbox:focus-visible, .trash-button:hover, .trash-button:focus-visible {{ background:var(--button-hover); }}
.trash-button {{ font-size:1.08rem; opacity:.72; }}
.task-snooze, .project-task-snooze {{ position:relative; }}
.snooze-icon-button {{ list-style:none; width:44px; height:44px; border-radius:10px; display:flex; align-items:center; justify-content:center; cursor:pointer; font-size:1rem; opacity:.72; }}
.snooze-icon-button::-webkit-details-marker {{ display:none; }}
.snooze-icon-button:hover, .snooze-icon-button:focus-visible {{ opacity:1; background:var(--button-hover); }}
.task-snooze-menu {{ position:absolute; z-index:30; top:42px; left:0; right:auto; width:min(260px, calc(100vw - 24px)); padding:8px; border:1px solid var(--border); border-radius:12px; background:var(--card); box-shadow:var(--shadow-lg); }}
.task-snooze-menu form {{ display:block; margin:0; }}
.task-snooze-menu button {{ width:100%; border:0; border-radius:8px; background:transparent; color:var(--ink); font:inherit; font-size:.86rem; font-weight:700; text-align:left; cursor:pointer; padding:9px 10px; }}
.task-snooze-menu button:hover {{ background:var(--menu-hover); }}
.task-snooze-date {{ display:grid !important; grid-template-columns:minmax(145px,1fr) auto; gap:8px !important; padding:8px 4px 4px; }}
.task-snooze-date input[type="date"] {{ width:100%; min-width:145px; border:1px solid var(--border); border-radius:8px; padding:7px 9px; font:inherit; font-size:.8rem; }}
.task-snooze-date button {{ width:auto; white-space:nowrap; }}
.task-row:last-child {{ border-bottom:0; }}
.task-row:hover {{ background:var(--row-hover); }}
.task-title {{ font-weight:700; }}
.task-parent-meta {{ margin-top:5px; color:var(--muted); font-size:.8rem; line-height:1.35; }}
.task-parent-meta a {{ color:inherit; text-decoration:underline; font-weight:inherit; }}
.task-meta {{
  margin-top:5px; color:var(--muted); font-size:.8rem; line-height:1.35;
}}
.completed-task-icon {{ width:44px; min-width:44px; text-align:center; color:var(--muted); font-size:1.05rem; font-weight:700; }}
.completed-task-spacer {{ width:44px; min-width:44px; }}
.chevron {{ color:var(--muted); font-size:1.6rem; }}
.empty-state {{ padding:24px; color:var(--muted); }}
.context-card, .proposal-card, .project-task-editor {{
  margin:0 0 24px; padding:28px 24px;
  background:var(--card); border:1px solid var(--border);
  border-radius:var(--radius-2xl); box-shadow:var(--shadow);
}}
.context-card h2 {{
  margin:0 0 6px; color:var(--charcoal); font-size:1rem;
}}
.context-note {{
  margin:0 0 12px; color:var(--muted);
  font-size:.84rem; line-height:1.4;
}}
.context-card textarea {{
  width:100%; min-height:130px; resize:vertical;
  padding:12px 13px; border:1px solid var(--border);
  border-radius:10px; font:inherit; line-height:1.45;
  color:var(--ink); background:var(--surface);
}}
.context-actions {{
  display:flex; justify-content:flex-end;
  margin-top:10px;
}}
.context-save {{
  border:0; border-radius:10px;
  padding:9px 14px; background:var(--charcoal); color:var(--on-accent);
  font:inherit; font-weight:750; cursor:pointer;
}}
.context-save:hover {{ opacity:.92; }}

.proposal-card h2 {{
  margin:0 0 6px;
  color:var(--charcoal);
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
  color:var(--charcoal);
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
  background:var(--surface);
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
  background:var(--charcoal);
  color:white;
}}

.proposal-retry {{
  border:1px solid var(--charcoal);
  background:var(--surface);
  color:var(--charcoal);
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
  border-top-color:var(--charcoal);
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
  <a class="detail-back" href="/projects">← Projects</a>
  <div class="page-heading header">
    <h1 class="brand">{name}</h1>
    <div class="summary">
      <span>{count} open task{"s" if count != 1 else ""}</span>
      {status_html}
    </div>
  </div>

  <section class="surface-card context-card">
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
  {work_results_body}
  </div>

  <section class="proposal-card" id="work-patterns"><h2>Work Patterns</h2><p class="proposal-note">Reuse a saved set of tasks, review the steps, then add them to this project.</p><div class="context-actions"><a class="context-save" style="text-decoration:none" href="/projects/{project_id}/work-patterns">Use Work Pattern</a> <a class="secondary-link" href="/work-patterns">Manage Patterns</a></div></section>

  <section class="project-task-editor" id="project-tasks">
    <h2>Project tasks</h2>
    <p class="proposal-note">Drag to set the project sequence, edit titles inline, remove tasks, or add work. Completion remains immediate; structural changes are saved together.</p>
    {completion_forms}
    <form method="post" action="/projects/{project_id}/tasks">
      <div class="project-editor-list" data-project-task-list>{task_rows}</div>
      <div class="project-editor-actions">
        <button class="project-add-task" type="button" onclick="addProjectTaskRow(this)">+ Add task</button>
        <button class="context-save" type="submit">Save Project Tasks</button>
      </div>
    </form>
  </section>
</main>
{_bottom_nav_html(active="projects")}
<script>
function wireProjectTaskRow(row) {{ const title=row.querySelector('.project-editor-title'); if(title){{ const remember=function(){{row.dataset.editedTitle=title.value;}}; title.addEventListener('input',remember); title.addEventListener('change',remember); remember(); }} const trash=row.querySelector('.project-editor-trash'); if(trash) trash.onclick=function(){{row.remove();}}; row.addEventListener('dragstart',function(e){{row.classList.add('dragging');e.dataTransfer.effectAllowed='move';}}); row.addEventListener('dragend',function(){{row.classList.remove('dragging');}}); }}
function projectTaskRow(title) {{ const row=document.createElement('div'); row.className='project-editor-row'; row.draggable=true; row.dataset.taskId=''; row.innerHTML='<button class="project-drag" type="button" title="Drag to reorder" aria-label="Drag to reorder">☷</button><span></span><div class="project-editor-main"><input type="hidden" name="task_id" value=""><input class="project-editor-title" name="task_title" type="text" aria-label="Task title"><div class="task-meta">New task</div></div><span></span><button class="project-editor-trash" type="button" title="Remove task" aria-label="Remove task">🗑</button>'; row.querySelector('.project-editor-title').value=title||''; wireProjectTaskRow(row); return row; }}
function addProjectTaskRow(button) {{ const form=button.closest('form'),list=form.querySelector('[data-project-task-list]'); const empty=list.querySelector('.project-empty'); if(empty) empty.remove(); const row=projectTaskRow(''); list.appendChild(row); row.querySelector('.project-editor-title').focus(); }}
function syncProjectTasks(form) {{ const tasks=Array.from(form.querySelectorAll('.project-editor-row')).map(function(row){{ const input=row.querySelector('.project-editor-title'); const liveTitle=input?input.value:String(row.dataset.editedTitle||''); row.dataset.editedTitle=liveTitle; return {{id:row.dataset.taskId||null,title:liveTitle.trim()}};}}).filter(t=>t.title); form.querySelector('input[name="tasks_json"]').value=JSON.stringify(tasks); return true; }}
document.addEventListener('DOMContentLoaded',function(){{ document.querySelectorAll('.project-editor-row').forEach(wireProjectTaskRow); document.querySelectorAll('[data-project-task-list]').forEach(function(list){{ list.addEventListener('dragover',function(e){{e.preventDefault(); const dragging=list.querySelector('.dragging'); if(!dragging)return; const candidates=Array.from(list.querySelectorAll('.project-editor-row:not(.dragging)')); const after=candidates.reduce(function(best,child){{const box=child.getBoundingClientRect(),offset=e.clientY-box.top-box.height/2; return offset<0&&offset>best.offset?{{offset:offset,element:child}}:best;}},{{offset:Number.NEGATIVE_INFINITY,element:null}}).element; if(after)list.insertBefore(dragging,after);else list.appendChild(dragging);}});}}); }});
</script>
{work_results_poll_script}
{scroll_proposal_script}
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
{_theme_head_extras()}
<title>AIOS New Task Review</title>
<style>
{_mobile_shell_css()}
.card {{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-2xl);padding:28px 24px;margin-top:8px;box-shadow:var(--shadow);line-height:var(--line-relaxed);}}
.label {{color:var(--muted);font-size:.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.03em;margin-top:18px;}}
.label:first-child {{margin-top:0;}}
.value {{margin-top:8px;font-size:1rem;line-height:var(--line-relaxed);}}
.title {{font-size:1.18rem;font-weight:700;color:var(--charcoal);}}
.muted {{color:var(--muted);font-size:.88rem;}}
</style>
</head>
<body>
<main>
  <a class="detail-back" href="/reviews">← Review</a>
  <div class="page-heading">
    <h1 class="brand">New task</h1>
    <p class="subtitle">This task has not been created yet. AIOS is holding it for your duplicate decision.</p>
  </div>
  <section class="card">
    <div class="label">Proposed task</div>
    <div class="value title">{title}</div>
    <div class="label">Original Brain Dump</div>
    <div class="value">{original}</div>
    {comparison_html}
    {reason_html}
  </section>
</main>
{_bottom_nav_html(active="reviews")}
</body>
</html>'''


def _reviews_list_fingerprint(reviews: list[dict]) -> str:
    parts: list[str] = []
    for review in reviews:
        if review.get("state") == "resolved":
            continue
        payload = dict(review.get("payload") or {})
        parts.extend(
            [
                str(review.get("id") or ""),
                str(review.get("review_type") or ""),
                str(review.get("state") or ""),
                str(payload.get("requested_action") or ""),
                str(review.get("subject_text") or "")[:80],
                str(payload.get("candidate_task_title") or "")[:80],
                str(payload.get("proposed_text") or "")[:80],
                str(payload.get("question") or "")[:80],
            ]
        )
    return "|".join(parts)


def _enrich_duplicate_reviews(reviews: list[dict]) -> None:
    for review in reviews:
        if review.get("review_type") != "possible_duplicate":
            continue

        payload = dict(review.get("payload") or {})
        candidate_id = str(payload.get("candidate_task_id") or "").strip()
        if not candidate_id:
            continue

        stored_title = str(payload.get("candidate_task_title") or "").strip()
        try:
            current_task = _fetch_task_detail(candidate_id)
            current_title = str(current_task.get("title") or "").strip()
            if not current_title:
                continue

            payload["candidate_task_changed"] = (
                bool(stored_title) and current_title != stored_title
            )
            payload["stored_candidate_task_title"] = stored_title
            payload["candidate_task_title"] = current_title

            source_task_id = str(payload.get("source_task_id") or "").strip()
            source_stored_title = str(payload.get("source_task_title") or "").strip()
            source_task_changed = False

            if source_task_id:
                try:
                    source_task = _fetch_task_detail(source_task_id)
                    source_current_title = str(source_task.get("title") or "").strip()
                    if source_current_title:
                        source_task_changed = (
                            bool(source_stored_title)
                            and source_current_title != source_stored_title
                        )
                        payload["current_source_task_title"] = source_current_title
                except Exception as exc:
                    print("[Review] Source task refresh failed:", source_task_id, exc)

            payload["source_task_changed"] = source_task_changed
            review["payload"] = payload
        except Exception as exc:
            print("[Review] Candidate task refresh failed:", candidate_id, exc)


def _build_review_cards(reviews: list[dict]) -> dict[str, object]:
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

    pending = bool(
        reevaluation_pending
        or duplicate_creation_pending
        or clarification_processing_pending
    )
    return {
        "html": f'<div id="review-list-panel">{cards}</div>',
        "fingerprint": _reviews_list_fingerprint(reviews),
        "pending": pending,
    }


def _reviews_page(
    reviews: list[dict],
    *,
    notices: list[dict] | None = None,
    error: str = "",
) -> str:
    notices = notices or []
    list_view = _build_review_cards(reviews)
    cards_html = str(list_view["html"])
    review_poll_script = _fragment_poll_script(
        enabled=bool(list_view["pending"]),
        url="/api/reviews/list",
        target_id="review-list-panel",
        fingerprint=str(list_view["fingerprint"]),
        session_key="aios-review-processing-refresh-count",
        initial_delay=2000,
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

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1, viewport-fit=cover">
{_theme_head_extras()}
<title>AIOS Review</title>
<style>
{_mobile_shell_css()}
.notice {{
  margin:0 0 20px;
  padding:16px 18px;
  background:var(--card);
  border:1px solid var(--border);
  border-radius:var(--radius-2xl);
  line-height:var(--line-relaxed);
  box-shadow:var(--shadow);
}}
.auto-merge-notice {{
  display:none;
  background:var(--card);
  border:1px solid var(--border);
  border-left:4px solid var(--charcoal);
  border-radius:var(--radius-2xl);
  padding:18px 20px;
  margin:0 0 20px;
  line-height:var(--line-relaxed);
  box-shadow:var(--shadow);
}}
.auto-merge-notice strong {{
  color:var(--charcoal);
}}
.auto-merge-notice > strong {{
  display:block;
  margin-bottom:6px;
}}
.review-task-row {{
  display:flex;
  align-items:flex-start;
  justify-content:space-between;
  gap:14px;
  margin-bottom:8px;
}}
.review-task-row .review-task-link {{
  flex:1;
  font-size:1.05rem;
  line-height:var(--line-relaxed);
}}
.review-delete-button {{
  width:44px;
  height:44px;
  flex:0 0 44px;
  padding:0;
  border:0;
  border-radius:12px;
  background:transparent;
  cursor:pointer;
  font-size:1rem;
  opacity:.68;
}}
.review-delete-button:hover,
.review-delete-button:focus-visible {{
  opacity:1;
  background:var(--accent-soft);
}}
.clarification-edit {{
  width:100%;
  min-height:96px;
  margin:10px 0 6px;
  padding:14px 16px;
  border:1px solid var(--border);
  border-radius:var(--radius-2xl);
  background:var(--highlight);
  color:var(--ink);
  font:inherit;
  line-height:var(--line-relaxed);
  resize:vertical;
}}
.clarification-edit:focus {{
  outline:3px solid var(--focus-ring-shadow);
  border-color:var(--focus-ring);
}}
.review-card {{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:var(--radius-2xl);
  padding:24px 22px;
  margin-bottom:20px;
  box-shadow:var(--shadow);
}}
.review-label {{
  color:var(--muted);
  font-size:.8rem;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:.04em;
  margin-bottom:18px;
}}
.review-section-label {{
  color:var(--muted);
  font-size:.82rem;
  font-weight:600;
  margin-top:12px;
  line-height:var(--line-body);
}}
.review-task,
.review-existing {{
  margin-top:6px;
  font-size:1rem;
  line-height:var(--line-relaxed);
}}
.review-existing {{
  display:flex;
  gap:10px;
  align-items:baseline;
  flex-wrap:wrap;
}}
.review-task-link {{
  color:var(--charcoal);
  text-decoration:none;
  font-weight:600;
}}
.review-task-link:hover {{
  text-decoration:underline;
}}
.review-score {{
  color:var(--muted);
  font-size:.84rem;
}}
.review-pending {{
  display:flex;
  gap:14px;
  align-items:center;
  padding:10px 0;
  line-height:var(--line-relaxed);
}}
.review-spinner {{
  width:20px;
  height:20px;
  flex:0 0 20px;
  border:3px solid var(--border);
  border-top-color:var(--charcoal);
  border-radius:50%;
  animation:review-spin .8s linear infinite;
}}
@keyframes review-spin {{
  to {{ transform:rotate(360deg); }}
}}
.review-stale-note {{
  color:var(--muted);
  font-size:.9rem;
  line-height:var(--line-relaxed);
  padding:10px 0;
}}
.review-actions {{
  display:flex;
  gap:10px;
  flex-wrap:wrap;
  margin-top:22px;
}}
.review-actions form {{
  margin:0;
}}
.review-primary,
.review-secondary {{
  border-radius:var(--radius-2xl);
  padding:10px 16px;
  font:inherit;
  font-weight:700;
  cursor:pointer;
  line-height:var(--line-body);
}}
.review-primary {{
  border:0;
  background:var(--charcoal);
  color:var(--paper);
}}
.review-secondary {{
  border:1px solid var(--border);
  background:var(--card);
  color:var(--charcoal);
}}
.empty-state {{
  padding:28px 24px;
  background:var(--card);
  border:1px solid var(--border);
  border-radius:var(--radius-2xl);
  color:var(--muted);
  line-height:var(--line-relaxed);
  box-shadow:var(--shadow);
}}
</style>
</head>
<body>
<main>
  <div class="page-heading">
    <h1 class="brand">Review</h1>
    <p class="subtitle">Resolve tasks that AIOS thinks may already exist.</p>
  </div>
  {notice}
  {auto_notice_html}
  <div class="review-list">{cards_html}</div>
</main>
{_bottom_nav_html(active="reviews")}
{review_poll_script}
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
{_theme_head_extras()}
<title>New Task · AIOS</title>
<style>
{_mobile_shell_css()}
.notice {{ padding:16px 18px; border-radius:var(--radius-2xl); margin-bottom:20px; line-height:var(--line-relaxed); box-shadow:var(--shadow); }}
.error {{ background:var(--error); }}
.card {{
  background:var(--card); border:1px solid var(--border);
  border-radius:var(--radius-2xl); padding:24px 22px;
  box-shadow:var(--shadow);
}}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
.full {{ grid-column:1/-1; }}
label {{
  display:grid; gap:8px; color:var(--ink); font-size:.92rem; font-weight:600; line-height:var(--line-body);
}}
input[type="text"], input[type="date"], select {{
  width:100%; min-height:48px; border:1px solid var(--border);
  border-radius:var(--radius-2xl); padding:0 16px; background:var(--highlight);
  color:var(--ink); font:inherit; line-height:var(--line-body);
}}
.checkbox-row {{
  display:flex; align-items:center; gap:12px; min-height:48px; line-height:var(--line-relaxed);
}}
.checkbox-row input {{ width:20px; height:20px; accent-color:var(--charcoal); }}
.actions {{ display:flex; gap:12px; margin-top:24px; }}
button {{
  min-height:48px; border:0; border-radius:var(--radius-2xl);
  padding:0 20px; background:var(--charcoal);
  color:var(--paper); font:inherit; font-weight:700; cursor:pointer;
}}
.cancel {{
  min-height:48px; display:inline-flex; align-items:center;
  padding:0 16px; border:1px solid var(--border); border-radius:var(--radius-2xl);
  color:var(--charcoal); text-decoration:none; font-weight:600; background:var(--card);
}}
@media (max-width:600px) {{
  .grid {{ grid-template-columns:1fr; }}
  .full {{ grid-column:auto; }}
}}
</style>
</head>
<body>
<main>
  <div class="page-heading">
    <h1 class="brand">New Task</h1>
    <p class="subtitle">Create a task directly when you already know what needs to be done.</p>
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
{_bottom_nav_html(active="new")}
</body>
</html>"""


def _focus_card_fingerprint(focus: dict | None, *, refresh_focus: bool) -> str:
    if not focus:
        return "pending-no-focus" if refresh_focus else "none"
    activation = dict(focus.get("activation") or {})
    parts = [
        str(focus.get("id") or ""),
        str(activation.get("id") or ""),
        str(activation.get("title") or ""),
        str(activation.get("activation_disposition") or ""),
        str(focus.get("focus_context_help_state") or ""),
        str(focus.get("focus_context_draft") or "")[:120],
        str(focus.get("focus_context_question") or "")[:120],
        str(focus.get("title") or ""),
        str(focus.get("starter_step") or ""),
        str(focus.get("starter_minutes") or ""),
        "refresh" if refresh_focus else "",
    ]
    return "|".join(parts)


def _focus_card_pending(focus: dict | None, *, refresh_focus: bool) -> bool:
    if not focus:
        return bool(refresh_focus)

    context_pending = str(focus.get("focus_context_help_state") or "") in {
        "pending",
        "answer_pending",
    }
    if context_pending:
        return True

    if not refresh_focus:
        return False

    activation = dict(focus.get("activation") or {})
    activation_id = str(activation.get("id") or "")
    if activation_id:
        return False

    # refresh_focus with a focus task but no activation child yet — keep
    # polling until the processor publishes a new Start Here step.
    return True


def _focus_card_view(
    focus: dict | None,
    *,
    refresh_focus: bool = False,
) -> dict[str, object]:
    activation = dict(focus.get("activation") or {}) if focus else {}
    activation_id = str(activation.get("id") or "")
    activation_history_exists = bool(
        focus.get("activation_history_exists")
        if focus
        else False
    )
    refresh_pending = bool(refresh_focus and not focus)
    focus_id = str(focus.get("id") or "") if focus else ""
    focus_card = ""

    focus_parent_meta = ""
    if focus:
        focus_parent_id = str(focus.get("parent_task_id") or "").strip()
        focus_parent_title = str(focus.get("parent_title") or "").strip()
        if focus_parent_id and focus_parent_title:
            focus_parent_meta = (
                '<div class="focus-parent-meta">Part of: '
                f'<a href="/tasks/{html.escape(focus_parent_id, quote=True)}">{html.escape(focus_parent_title)}</a>'
                '</div>'
            )

    if refresh_pending:
        focus_card = (
            '<section class="focus-card" id="focus-card">'
            '<div class="focus-label">⭐ Best Next Action</div>'
            '<div class="focus-pending"><span class="mini-spinner"></span> Updating your focus…</div>'
            '</section>'
        )

    if focus and not refresh_pending:
        safe_id = html.escape(focus_id)
        title = html.escape(str(focus.get("title") or "Untitled task"))
        focus_context = str(focus.get("context") or "").strip()
        focus_context_state = str(focus.get("focus_context_help_state") or "").strip()
        focus_context_draft = str(focus.get("focus_context_draft") or "").strip()
        focus_context_question = str(focus.get("focus_context_question") or "").strip()
        meta = []
        if focus.get("execution_rank") is not None:
            meta.append(f"Rank {html.escape(str(focus.get('execution_rank')))}")
        if focus.get("execution_score") is not None:
            meta.append(f"Score {html.escape(str(focus.get('execution_score')))}")
        if focus.get("importance"):
            meta.append(html.escape(str(focus.get("importance"))))

        activation_title = str(activation.get("title") or "").strip()
        activation_disposition = str(activation.get("activation_disposition") or "").strip()
        activation_not_useful = activation_disposition == "not_useful"
        activation_pending = bool(focus.get("activation_pending"))

        if activation_title:
            starter = activation_title
        elif activation_pending or activation_history_exists:
            starter = ""
        elif refresh_focus and not activation_id:
            starter = ""
        else:
            starter = str(focus.get("starter_step") or "").strip()

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

        focus_step_actions_html = (
            '<div class="focus-step-actions"><span class="focus-rejected-note">Marked not useful</span></div>'
            if activation_not_useful
            else ""
        )

        timebox_sub_html = (
            f'<div class="focus-start-sub-line focus-timebox-inline"><strong>Give it {html.escape(timebox_text)}</strong>'
            '<span> — only for this starting move.</span></div>'
        ) if timebox_text else ""

        starter_html = ""

        if activation_pending or (refresh_focus and not activation_id):
            starter_html = (
                '<div class="focus-start">'
                '<div class="focus-start-heading">Start here</div>'
                '<div class="task-title-row">'
                '<span class="task-check-placeholder" aria-hidden="true"></span>'
                '<div class="focus-pending">'
                '<span class="mini-spinner"></span> Finding your next step…'
                '</div></div></div>'
            )

        if starter:
            if activation_id:
                safe_activation_id = html.escape(activation_id)
                starter_html = (
                    '<div class="focus-start">'
                    '<div class="focus-start-heading">Start here</div>'
                    '<div class="task-title-row">'
                    f'<form class="complete-form focus-activation-complete" data-task-id="{safe_activation_id}" method="post" action="/tasks/{safe_activation_id}/complete">'
                    '<button class="complete-checkbox" type="submit" aria-label="Complete starting step" title="Complete starting step"><span aria-hidden="true"></span></button>'
                    '</form>'
                    f'<a class="task-link" href="/tasks/{safe_activation_id}">{html.escape(starter)}</a>'
                    '</div>'
                    '<div class="task-sub">'
                    + (
                        focus_step_actions_html
                        if activation_not_useful
                        else (
                            '<div class="focus-step-actions">'
                            f'<form class="focus-not-now-form" method="post" action="/tasks/{safe_activation_id}/not-now">'
                            '<button class="focus-not-now" type="submit">Not now</button></form>'
                            f'<form class="focus-not-useful-form" method="post" action="/tasks/{safe_activation_id}/not-useful">'
                            '<button class="focus-not-useful" type="submit">Not useful</button></form>'
                            '</div>'
                        )
                    )
                    + timebox_sub_html
                    + '</div></div>'
                )
            else:
                starter_html = (
                    '<div class="focus-start">'
                    '<div class="focus-start-heading">Start here</div>'
                    '<div class="task-title-row">'
                    '<span class="task-check-placeholder" aria-hidden="true"></span>'
                    f'<div class="task-link">{html.escape(starter)}</div>'
                    '</div>'
                    + (f'<div class="task-sub">{timebox_sub_html}</div>' if timebox_sub_html else '')
                    + '</div>'
                )

        context_value = (
            focus_context_draft
            if focus_context_state in {"ready", "answer_pending"}
            else focus_context
        )
        context_summary = "Edit context" if focus_context else "Add context"
        context_question_html = ""
        if focus_context_state == "ready" and focus_context_question:
            context_question_html = (
                '<div class="focus-context-question"><strong>One useful question:</strong> '
                + html.escape(focus_context_question)
                + '</div>'
                + f'<form class="focus-context-answer-form" method="post" action="/tasks/{safe_id}/focus-context/answer">'
                + '<label>Your answer<textarea class="focus-autoexpand focus-context-answer" name="answer" rows="2" required placeholder="Type your answer here…"></textarea></label>'
                + '<button class="focus-context-answer-button" type="submit">Use my answer</button></form>'
            )
        context_help_status = (
            '<div class="focus-context-pending"><span class="mini-spinner"></span> <span class="focus-context-processing"><span class="focus-context-spinner" aria-hidden="true"></span>Improving your context…</span></div>'
            if focus_context_state in {"pending", "answer_pending"}
            else ""
        )
        context_help_button = (
            ""
            if focus_context_state in {"pending", "answer_pending", "ready"}
            else f'<form method="post" action="/tasks/{safe_id}/focus-context/help"><button class="focus-context-help-button" type="submit">Help me improve this context</button></form>'
        )
        focus_context_html = (
            '<details class="focus-context-panel"'
            + (' open' if focus_context_state in {"pending", "answer_pending", "ready"} else '')
            + '>'
            + f'<summary>{context_summary}</summary><div class="focus-context-body">'
            + '<p>Tell AIOS what is already decided, what matters, or what would make the next step more relevant.</p>'
            + context_question_html
            + context_help_status
            + f'<form method="post" action="/tasks/{safe_id}/focus-context">'
            + f'<textarea name="context" rows="4" placeholder="What should AIOS know about this task?" class="focus-autoexpand">{html.escape(context_value)}</textarea>'
            + '<button class="focus-context-save" type="submit">Save context &amp; refresh Start Here</button></form>'
            + context_help_button
            + '</div></details>'
        )

        meta_html = ""
        if meta:
            meta_html = (
                '<div class="focus-meta">'
                + "".join(f'<span class="focus-meta-tag">{part}</span>' for part in meta)
                + "</div>"
            )

        focus_card = (
            f'<section class="focus-card surface-card" id="focus-card" data-task-id="{safe_id}">'
            '<div class="focus-label">⭐ Best Next Action</div>'
            '<div class="task-title-row focus-parent-title-row">'
            f'<form class="complete-form focus-parent-complete" data-task-id="{safe_id}" method="post" action="/tasks/{safe_id}/complete">'
            '<button class="complete-checkbox" type="submit" aria-label="Complete Best Next Action" title="Complete Best Next Action"><span aria-hidden="true"></span></button>'
            '</form>'
            f'<a class="task-link" href="/tasks/{safe_id}">{title}</a>'
            '</div>'
            '<div class="task-sub focus-parent-sub">'
            + focus_parent_meta
            + meta_html
            + '<div class="focus-action-bar">'
            + _task_snooze_control_html(
                focus_id,
                return_to="/?refresh_focus=1#focus-card",
                css_class="focus-snooze",
            )
            + f'<form class="delete-form focus-delete" method="post" action="/tasks/{safe_id}/delete" onsubmit="return confirm(&quot;Delete this task?&quot;);">'
            '<button class="trash-button" type="submit" aria-label="Delete task" title="Delete task"><span aria-hidden="true">🗑️</span></button></form>'
            + "</div></div>"
            + starter_html
            + focus_context_html
            + '</section>'
        )

    pending = _focus_card_pending(focus, refresh_focus=refresh_focus)
    return {
        "html": focus_card,
        "pending": pending,
        "focus_id": focus_id or None,
        "fingerprint": _focus_card_fingerprint(focus, refresh_focus=refresh_focus),
    }


def _tasks_section_specs(*, search: str = "") -> list[tuple[str, str]]:
    if search:
        return [(f'Search Results for “{search}”', "search_results")]
    return [
        ("Top 5", "top5"),
        ("Quick Wins", "quick_wins"),
        ("Today", "today"),
        ("Just Do It", "just_do_it"),
        ("Completed Today", "completed_today"),
    ]


def _tasks_sections_fingerprint(
    tasks: dict[str, list[dict]] | None,
    *,
    search: str = "",
    focus_id: str = "",
) -> str:
    tasks = tasks or {}
    parts = [search, focus_id]
    for _heading, key in _tasks_section_specs(search=search):
        section_tasks = list(tasks.get(key, []))
        if focus_id and key not in {"today", "search_results", "completed_today"}:
            section_tasks = [
                task
                for task in section_tasks
                if str(task.get("id") or "") != focus_id
            ]
        parts.extend([key, str(len(section_tasks))])
        for task in section_tasks:
            parts.extend(
                [
                    str(task.get("id") or ""),
                    str(task.get("title") or ""),
                    str(task.get("execution_rank") or ""),
                    str(task.get("execution_score") or ""),
                    str(task.get("effective_due_at") or task.get("due_at") or ""),
                    "1" if task.get("is_done") else "0",
                ]
            )
    parts.extend(
        [
            str(tasks.get("_completed_today_summary_state") or "empty"),
            str(tasks.get("_completed_today_summary") or "")[:200],
        ]
    )
    return "|".join(parts)


def _render_dashboard_task_row(
    task: dict,
    *,
    search: str = "",
    section_key: str = "",
) -> str:
    title = html.escape(
        str(task.get("title") or "Untitled task")
    )
    task_id = html.escape(str(task.get("id") or ""))
    due_at = str(task.get("effective_due_at") or task.get("due_at") or "").strip()
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

    parent_id = str(task.get("parent_task_id") or "").strip()
    parent_title = str(task.get("parent_title") or "").strip()
    parent_html = ""
    if parent_id and parent_title:
        parent_html = (
            '<div class="task-parent-meta">Part of: '
            f'<a href="/tasks/{html.escape(parent_id, quote=True)}">{html.escape(parent_title)}</a>'
            '</div>'
        )

    meta_html = ""
    if meta_parts:
        meta_html = (
            '<div class="task-meta">'
            + "".join(
                f'<span class="task-meta-tag">{part}</span>'
                for part in meta_parts
            )
            + "</div>"
        )

    if search:
        row_return_to = f"/?search={quote_plus(search)}#search-results"
    elif section_key:
        row_return_to = f"/#section-{quote_plus(section_key)}"
    else:
        row_return_to = "/"
    snooze_html = _task_snooze_control_html(
        str(task.get("id") or ""),
        return_to=row_return_to,
    )

    return (
        f'<article class="task-row" data-task-id="{task_id}">'
        '<div class="task-title-row">'
        + f'<form class="complete-form" data-task-id="{task_id}" method="post" action="/tasks/{task_id}/complete">'
        + '<button class="complete-checkbox" type="submit" aria-label="Mark task done" title="Mark done">'
        + '<span aria-hidden="true"></span></button></form>'
        + f'<a class="task-link" href="/tasks/{task_id}">{title}</a>'
        + '</div>'
        + '<div class="task-sub">'
        + parent_html
        + meta_html
        + '<div class="task-action-bar">'
        + snooze_html
        + f'<form class="delete-form" method="post" action="/tasks/{task_id}/delete" '
        + 'onsubmit="return confirm(&quot;Delete this task?&quot;);">'
        + '<button class="trash-button" type="submit" aria-label="Delete task" title="Delete task">'
        + '<span aria-hidden="true">🗑️</span></button></form>'
        + "</div></div></article>"
    )


def _render_dashboard_completed_task_row(task: dict) -> str:
    task_id = html.escape(str(task.get("id") or ""), quote=True)
    title = html.escape(str(task.get("title") or "Untitled"))
    parent_id = str(task.get("parent_task_id") or "").strip()
    parent_title = str(task.get("parent_title") or "").strip()
    parent_html = ""
    if parent_id and parent_title:
        parent_html = (
            '<div class="task-parent-meta">Part of: '
            f'<a href="/tasks/{html.escape(parent_id, quote=True)}">{html.escape(parent_title)}</a>'
            '</div>'
        )

    completed_meta = ""
    raw_completed = str(task.get("completed_at") or "").strip()
    if raw_completed:
        try:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            completed_dt = datetime.fromisoformat(raw_completed.replace("Z", "+00:00"))
            if completed_dt.tzinfo is not None:
                completed_dt = completed_dt.astimezone(ZoneInfo("America/Toronto"))
            completed_meta = completed_dt.strftime("Completed %-I:%M %p")
        except (TypeError, ValueError):
            completed_meta = "Completed today"
    if not completed_meta:
        completed_meta = "Completed today"

    return (
        '<article class="task-row completed-task-row">'
        '<div class="task-title-row">'
        '<div class="completed-task-icon" aria-hidden="true">✓</div>'
        f'<a class="task-link" href="/tasks/{task_id}">{title}</a>'
        '</div>'
        + '<div class="task-sub">'
        + parent_html
        + f'<div class="task-meta"><span class="task-meta-tag">{html.escape(completed_meta)}</span></div>'
        + "</div></article>"
    )


def _tasks_sections_view(
    tasks: dict[str, list[dict]] | None,
    *,
    search: str = "",
    focus_id: str = "",
) -> dict[str, object]:
    tasks = tasks or {}
    task_sections = ""

    for heading, key in _tasks_section_specs(search=search):
        section_tasks = list(tasks.get(key, []))
        # Rank 1 is presented separately as the Best Next Action. Today is
        # intentionally allowed to overlap because it is the complete calendar
        # view of tasks due today or overdue.
        if focus_id and key not in {"today", "search_results", "completed_today"}:
            section_tasks = [
                task
                for task in section_tasks
                if str(task.get("id") or "") != focus_id
            ]
        if not section_tasks:
            continue

        rows_html = "".join(
            _render_dashboard_completed_task_row(task)
            if key == "completed_today"
            else _render_dashboard_task_row(task, search=search, section_key=key)
            for task in section_tasks
        )

        search_open = ' open' if key == "search_results" else ''
        completed_summary_html = ""
        if key == "completed_today":
            completed_summary = str(tasks.get("_completed_today_summary") or "").strip()
            completed_summary_state = str(tasks.get("_completed_today_summary_state") or "empty")
            if completed_summary:
                completed_summary_html = (
                    '<div class="completed-today-summary">'
                    '<div class="completed-today-summary-label">Today\'s summary</div>'
                    f'<div class="completed-today-summary-text">{html.escape(completed_summary)}</div>'
                    '</div>'
                )
            elif completed_summary_state == "pending":
                completed_summary_html = (
                    '<div class="completed-today-summary pending">'
                    '<div class="completed-today-summary-label">Today\'s summary</div>'
                    '<div class="completed-today-summary-text">Updating the day\'s summary…</div>'
                    '</div>'
                )

        task_sections += (
            f'<details class="task-group" data-section="{html.escape(key)}"'
            + (f' id="search-results"' if key == "search_results" else f' id="section-{html.escape(key, quote=True)}"')
            + f'{search_open}>'
            f'<summary class="task-group-heading">'
            f'<span class="task-group-label">{html.escape(heading)}</span>'
            f'<span class="section-count">{len(section_tasks)}</span>'
            f'</summary>'
            + completed_summary_html
            + f'<div class="task-list">{rows_html}</div>'
            + "</details>"
        )

    if not task_sections:
        task_sections = (
            '<div class="empty-state">'
            'No matching tasks found.'
            '</div>'
        )

    wrapped = f'<div id="dashboard-task-groups">{task_sections}</div>'
    return {
        "html": wrapped,
        "fingerprint": _tasks_sections_fingerprint(
            tasks,
            search=search,
            focus_id=focus_id,
        ),
        "summary_pending": str(tasks.get("_completed_today_summary_state") or "empty") == "pending",
    }


def _page(
    *,
    message: str = "",
    error: str = "",
    tasks: dict[str, list[dict]] | None = None,
    search: str = "",
    focus: dict | None = None,
    refresh_focus: bool = False,
    review_count: int = 0,
    fast_shell: bool = False,
) -> str:
    tasks = tasks or {}
    focus_id = str(focus.get("id") or "") if focus else ""

    if fast_shell:
        task_sections = (
            '<div id="dashboard-task-groups">'
            '<div class="focus-pending"><span class="mini-spinner"></span> Loading tasks…</div>'
            '</div>'
        )
        initial_tasks_fingerprint = "fast-shell"
        tasks_view = {"summary_pending": False}
    else:
        tasks_view = _tasks_sections_view(tasks, search=search, focus_id=focus_id)
        task_sections = str(tasks_view["html"])
        initial_tasks_fingerprint = str(tasks_view["fingerprint"])

    focus_view = _focus_card_view(focus, refresh_focus=refresh_focus or fast_shell)
    focus_card = str(focus_view["html"])
    refresh_needed = bool(focus_view["pending"])
    initial_focus_fingerprint = str(focus_view["fingerprint"])

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

    focus_submit_feedback_script = """
<script>
function showFocusUpdating() {
  const card = document.querySelector('.focus-card');
  if (!card) return true;
  card.innerHTML = '<div class="focus-label">⭐ Best Next Action</div><div class="focus-pending"><span class="mini-spinner"></span> Updating your focus…</div>';
  return true;
}
</script>
"""

    focus_poll_config = {
        "enabled": refresh_needed or fast_shell,
        "refreshFocus": refresh_focus or fast_shell,
        "initialFocusId": focus_id or None,
        "initialFingerprint": initial_focus_fingerprint,
        "maxAttempts": 15,
    }
    focus_poll_script = (
        f"<script>window.__AIOS_FOCUS_POLL__ = {json.dumps(focus_poll_config)};</script>"
        if refresh_needed
        else '<script>window.__AIOS_FOCUS_POLL__ = {"enabled": false};sessionStorage.removeItem("aios-focus-activation-refresh-count");</script>'
    )
    dashboard_tasks_config = {
        "initialFingerprint": initial_tasks_fingerprint,
    }
    dashboard_tasks_script = (
        f"<script>window.__AIOS_DASHBOARD_TASKS__ = {json.dumps(dashboard_tasks_config)};</script>"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  {_theme_head_extras()}
  <meta name="application-name" content="AIOS">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="AIOS">
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" type="image/png" sizes="32x32" href="/pwa/icon-32.png">
  <link rel="apple-touch-icon" href="/pwa/icon-192.png">
  <title>AIOS</title>
  <style>
    {_mobile_shell_css()}
    .capture-heading {{
      display:flex;
      justify-content:space-between;
      align-items:flex-end;
      margin-bottom:14px;
    }}
    .capture-heading h2 {{
      margin:0;
      color:var(--charcoal);
      font-size:1.15rem;
      font-weight:700;
    }}
    .capture-heading p {{
      margin:6px 0 0;
      color:var(--muted);
      font-size:.92rem;
      line-height:var(--line-relaxed);
    }}
    .focus-card {{
      --task-check:20px;
      --task-check-gap:12px;
      margin:0 0 24px;
    }}
    .focus-card.surface-card {{
      background:var(--focus-bg);
      border-color:var(--focus-yellow);
      box-shadow:0 4px 24px var(--focus-card-glow), var(--shadow);
    }}
    .tasks-section {{
      --task-check:20px;
      --task-check-gap:12px;
      margin-top:0;
    }}
    .task-title-row {{
      display:flex;
      align-items:flex-start;
      gap:var(--task-check-gap);
      min-width:0;
    }}
    .task-title-row .complete-form,
    .task-title-row .focus-activation-complete {{
      display:flex;
      align-items:center;
      justify-content:center;
      flex:0 0 var(--task-check);
      width:var(--task-check);
      min-width:var(--task-check);
      margin:1px 0 0;
      padding:0;
    }}
    .task-check-placeholder {{
      flex:0 0 var(--task-check);
      width:var(--task-check);
      min-width:var(--task-check);
      height:var(--task-check);
    }}
    .task-title-row .complete-checkbox {{
      width:var(--task-check);
      height:var(--task-check);
      min-height:0;
      padding:0;
      flex-shrink:0;
    }}
    .task-title-row .complete-checkbox span {{
      width:var(--task-check);
      height:var(--task-check);
      border:1.5px solid var(--check-border);
      border-radius:50%;
      background:var(--surface);
      box-sizing:border-box;
      display:block;
    }}
    .task-title-row .complete-checkbox:hover span,
    .task-title-row .complete-checkbox:focus-visible span {{
      border-color:var(--check-border-hover);
      box-shadow:none;
    }}
    .task-title-row .complete-checkbox.is-completing span {{
      background:var(--navy);
      border-color:var(--navy);
    }}
    .task-title-row .complete-checkbox.is-completing span::after {{
      font-size:11px;
    }}
    .task-link {{
      flex:1;
      min-width:0;
      display:block;
      color:var(--ink);
      text-decoration:none;
      font-size:.9375rem;
      line-height:1.35;
      font-weight:400;
      text-wrap:pretty;
      overflow-wrap:anywhere;
    }}
    .task-link:hover {{ text-decoration:underline; }}
    .task-sub {{
      margin-top:4px;
      padding-left:calc(var(--task-check) + var(--task-check-gap));
      min-width:0;
    }}
    .task-sub-line + .task-sub-line,
    .focus-step-actions + .focus-timebox-inline {{
      margin-top:2px;
    }}
    .focus-pending {{ display:flex; align-items:center; gap:12px; color:var(--ink); font-size:.95rem; line-height:1.4; margin-top:0; }}
    .focus-pending .mini-spinner {{ display:inline-block; flex:0 0 auto; width:18px; height:18px; border:3px solid var(--border); border-top-color:var(--charcoal); border-radius:50%; animation:dashboard-spin .8s linear infinite; }}
    @keyframes dashboard-spin {{ to {{ transform:rotate(360deg); }} }}
    .focus-label {{
      margin-bottom:12px;
      color:var(--navy);
      font-size:.72rem;
      font-weight:700;
      letter-spacing:.06em;
      text-transform:uppercase;
    }}
    .focus-parent-meta {{ margin-top:0; color:var(--muted); font-size:.8125rem; line-height:1.4; overflow-wrap:anywhere; }}
    .focus-parent-meta + .focus-meta {{ margin-top:5px; }}
    .focus-parent-meta a {{ color:inherit; text-decoration:underline; font-weight:inherit; }}
    .focus-meta {{
      display:flex;
      flex-wrap:wrap;
      gap:5px;
      margin-top:0;
      min-width:0;
      max-width:100%;
    }}
    .focus-meta-tag {{
      display:inline-flex;
      align-items:center;
      max-width:100%;
      padding:3px 8px;
      border-radius:999px;
      background:var(--highlight);
      color:var(--muted);
      font-size:.6875rem;
      font-weight:600;
      line-height:1.2;
      overflow-wrap:anywhere;
    }}
    .focus-action-bar,
    .task-action-bar {{
      display:flex;
      flex-wrap:wrap;
      align-items:center;
      gap:0;
      margin:3px 0 0 -4px;
    }}
    .focus-card .trash-button,
    .focus-card .snooze-icon-button {{
      width:32px;
      height:32px;
      min-height:32px;
    }}
    .focus-snooze, .task-snooze, .project-task-snooze {{ position:relative; }}
    .complete-checkbox,
    .trash-button {{
      width:44px;
      height:44px;
      min-height:44px;
      padding:0;
      border:0;
      border-radius:12px;
      background:transparent;
      color:inherit;
      display:flex;
      align-items:center;
      justify-content:center;
      cursor:pointer;
      font-size:inherit;
      font-weight:inherit;
      line-height:1;
    }}
    .complete-checkbox span {{
      width:22px;
      height:22px;
      border:2px solid var(--navy);
      border-radius:7px;
      background:var(--surface);
      display:block;
    }}
    .complete-checkbox:hover span,
    .complete-checkbox:focus-visible span {{
      border-color:var(--navy);
      box-shadow:0 0 0 3px var(--check-glow);
    }}
    .complete-checkbox.is-completing span {{
      background:var(--navy);
      border-color:var(--navy);
      position:relative;
    }}
    .complete-checkbox.is-completing span::after {{
      content:"✓";
      position:absolute;
      inset:0;
      display:flex;
      align-items:center;
      justify-content:center;
      color:var(--paper);
      font-size:16px;
      font-weight:800;
      line-height:1;
    }}
    .trash-button {{ font-size:1.08rem; opacity:.72; }}
    .trash-button:hover, .trash-button:focus-visible {{ opacity:1; background:var(--accent-soft); }}
    .complete-form, .delete-form, .focus-not-now-form, .focus-not-useful-form {{
      display:flex;
      margin:0;
      gap:0;
    }}
    .snooze-icon-button {{
      list-style:none;
      width:44px;
      height:44px;
      min-height:44px;
      border:0;
      border-radius:12px;
      background:transparent;
      display:flex;
      align-items:center;
      justify-content:center;
      cursor:pointer;
      font-size:1rem;
      opacity:.72;
      padding:0;
      color:inherit;
      font-weight:inherit;
      line-height:1;
    }}
    .snooze-icon-button::-webkit-details-marker {{ display:none; }}
    .snooze-icon-button:hover, .snooze-icon-button:focus-visible {{ opacity:1; background:var(--accent-soft); }}
    .task-snooze-menu {{
      position:absolute;
      z-index:30;
      top:42px;
      left:0;
      right:auto;
      width:min(260px, calc(100vw - 24px));
      padding:10px;
      border:1px solid var(--border);
      border-radius:var(--radius-2xl);
      background:var(--card);
      box-shadow:var(--shadow-lg);
    }}
    .task-snooze-menu form {{ display:block; margin:0; }}
    .task-snooze-menu button {{ width:100%; min-height:0; border:0; border-radius:10px; background:transparent; color:var(--ink); font:inherit; font-size:.88rem; font-weight:600; text-align:left; cursor:pointer; padding:10px 12px; line-height:var(--line-body); }}
    .task-snooze-menu button:hover {{ background:var(--accent-soft); }}
    .task-snooze-date {{ display:grid !important; grid-template-columns:minmax(145px,1fr) auto; gap:8px !important; padding:8px 4px 4px; }}
    .task-snooze-date input[type="date"] {{ width:100%; min-width:145px; border:1px solid var(--border); border-radius:10px; padding:8px 10px; font:inherit; font-size:.84rem; }}
    .task-snooze-date button {{ width:auto; white-space:nowrap; }}
    .focus-start {{
      margin:20px 0 0;
      padding-top:18px;
      border-top:1px solid var(--border);
    }}
    .focus-start-heading {{
      margin:0 0 12px;
      color:var(--navy);
      font-size:1.35rem;
      font-weight:700;
      letter-spacing:-0.015em;
      line-height:1.15;
    }}
    .focus-timebox-inline {{
      font-size:.8125rem;
      line-height:1.35;
    }}
    .focus-timebox-inline strong {{ color:var(--muted); font-weight:500; }}
    .focus-timebox-inline span {{ color:var(--muted); font-weight:400; }}
    .focus-step-actions {{ display:flex; align-items:center; flex-wrap:wrap; gap:4px 12px; margin-top:0; }}
    .focus-not-now, .focus-not-useful {{
      border:0;
      background:transparent;
      color:var(--muted);
      font:inherit;
      font-size:.8125rem;
      font-weight:600;
      cursor:pointer;
      padding:4px 0;
      line-height:1.3;
      min-height:0;
    }}
    .focus-not-now:hover, .focus-not-useful:hover {{ color:var(--charcoal); text-decoration:underline; }}
    .focus-timebox {{
      margin:8px 0 0 calc(var(--focus-check-col) + var(--focus-check-gap));
      font-size:.8125rem;
      line-height:1.4;
    }}
    .focus-timebox strong {{ color:var(--charcoal); font-weight:650; }}
    .focus-timebox span {{ color:var(--muted); font-weight:500; }}
    .focus-context-panel {{
      margin:14px 0 0;
      padding-top:12px;
      padding-left:calc(var(--task-check) + var(--task-check-gap));
      border-top:1px solid var(--border);
    }}
    .focus-context-panel > summary {{
      color:var(--charcoal);
      font-size:.8125rem;
      font-weight:650;
      cursor:pointer;
      width:max-content;
    }}
    .focus-context-body {{ margin-top:12px; max-width:720px; }}
    .focus-context-body p {{ margin:0 0 12px; color:var(--muted); font-size:.9rem; line-height:var(--line-relaxed); }}
    .focus-context-question {{ margin:0 0 12px; padding:12px 14px; border-radius:12px; background:var(--highlight); color:var(--ink); font-size:.9rem; line-height:var(--line-relaxed); }}
    .focus-context-body textarea {{ width:100%; resize:vertical; border:1px solid var(--border); border-radius:12px; padding:12px 14px; font:inherit; font-size:.95rem; line-height:var(--line-relaxed); background:var(--card); }}
    .focus-context-save, .focus-context-help-button, .focus-context-answer-button {{ margin-top:10px; min-height:42px; border:0; border-radius:12px; padding:0 14px; font:inherit; font-size:.88rem; font-weight:700; cursor:pointer; }}
    .focus-context-save {{ background:var(--charcoal); color:var(--paper); }}
    .focus-context-help-button {{ background:transparent; color:var(--charcoal); padding-left:0; }}
    .focus-context-answer-form {{ margin:0 0 14px; }}
    .focus-context-answer-form label {{ color:var(--charcoal); font-size:.84rem; font-weight:700; }}
    .focus-context-answer-form textarea {{ display:block; margin-top:8px; min-height:80px; }}
    .focus-context-answer-button {{ width:max-content; background:var(--card); color:var(--charcoal); border:1px solid var(--border); }}
    .focus-context-answer {{ font-weight:400 !important; }}
    .focus-autoexpand {{ overflow-y:hidden; resize:vertical; }}
    .focus-context-processing {{ display:inline-flex; align-items:center; gap:.55rem; }}
    .focus-context-spinner {{ width:1rem; height:1rem; border:2px solid currentColor; border-right-color:transparent; border-radius:50%; display:inline-block; animation:focus-context-spin .8s linear infinite; flex:0 0 auto; }}
    @keyframes focus-context-spin {{ to {{ transform:rotate(360deg); }} }}
    .focus-context-pending {{ display:flex; align-items:center; gap:8px; margin:10px 0; color:var(--muted); font-size:.8125rem; line-height:1.4; }}
    .focus-rejected-note {{ color:var(--muted); font-weight:650; font-size:.8125rem; white-space:nowrap; }}
    form:not(.complete-form):not(.delete-form):not(.focus-not-now-form):not(.focus-not-useful-form):not(.menu-form) {{
      display:grid;
      gap:16px;
    }}
    textarea {{
      width:100%;
      min-height:150px;
      max-height:280px;
      resize:vertical;
      border:1px solid var(--border);
      border-radius:var(--radius-2xl);
      padding:20px;
      background:var(--highlight);
      color:var(--ink);
      font:inherit;
      font-size:1.05rem;
      line-height:var(--line-relaxed);
      box-shadow:inset 0 1px 2px rgba(26,26,26,.03);
    }}
    textarea:focus {{ outline:3px solid var(--focus-ring-shadow); border-color:var(--focus-ring); }}
    button:not(.complete-checkbox):not(.trash-button):not(.snooze-icon-button):not(.focus-not-now):not(.focus-not-useful):not(.focus-context-help-button):not(.focus-context-answer-button):not(.menu-button):not(.toolbar-button) {{
      min-height:54px;
      border:0;
      border-radius:var(--radius-2xl);
      background:var(--charcoal);
      color:var(--paper);
      font:inherit;
      font-weight:700;
      font-size:1.02rem;
      cursor:pointer;
      line-height:1.2;
    }}
    .menu-form {{
      display:block;
      margin:0;
    }}
    .menu-button,
    .task-snooze-menu .menu-button,
    .task-snooze-date .menu-button {{
      width:100%;
      min-height:0;
      border:0;
      border-radius:10px;
      background:transparent;
      color:var(--ink);
      font:inherit;
      font-size:.86rem;
      font-weight:600;
      text-align:left;
      cursor:pointer;
      padding:10px 12px;
      line-height:var(--line-body);
    }}
    .menu-button:hover {{
      background:var(--accent-soft);
    }}
    .task-snooze-date .menu-button {{
      width:auto;
      white-space:nowrap;
    }}
    button:disabled {{ opacity:.65; cursor:wait; }}
    .optimistic-toast {{
      position:fixed; left:50%; bottom:calc(var(--nav-offset) + 8px); z-index:80;
      transform:translateX(-50%);
      display:flex; align-items:center; gap:14px;
      min-width:260px; max-width:min(520px,calc(100vw - 28px));
      padding:14px 16px; border-radius:var(--radius-2xl);
      background:var(--charcoal); color:var(--paper);
      box-shadow:var(--shadow-lg);
      font-size:.92rem; font-weight:600; line-height:var(--line-body);
    }}
    .optimistic-toast button {{
      margin-left:auto; border:0; background:transparent; color:var(--paper);
      font:inherit; font-weight:700; text-decoration:underline; cursor:pointer; min-height:0;
    }}
    .optimistic-toast.error {{ background:var(--toast-error); }}
    .focus-poll-timeout {{
      display:grid;
      gap:12px;
      margin-top:4px;
      color:var(--ink);
      font-size:.95rem;
      line-height:var(--line-relaxed);
    }}
    .focus-poll-timeout-actions {{
      display:flex;
      flex-wrap:wrap;
      gap:10px;
      align-items:center;
    }}
    .focus-poll-timeout-actions button {{
      min-height:0;
      padding:10px 14px;
      border-radius:999px;
      border:1px solid var(--border);
      background:var(--surface);
      color:var(--charcoal);
      font:inherit;
      font-weight:600;
      cursor:pointer;
    }}
    .focus-poll-timeout-actions button.primary {{
      background:var(--charcoal);
      border-color:var(--charcoal);
      color:var(--paper);
    }}
    .focus-poll-timeout-actions button.link {{
      border:0;
      background:transparent;
      color:var(--muted);
      text-decoration:underline;
      padding:10px 0;
    }}
    .optimistic-hidden {{ display:none !important; }}
    .notice {{
      margin:0 0 20px;
      padding:16px 18px;
      border-radius:var(--radius-2xl);
      line-height:var(--line-relaxed);
      box-shadow:var(--shadow);
    }}
    .success {{ background:var(--success); color:var(--charcoal); }}
    .error {{ background:var(--error); color:var(--charcoal); }}
    .hint {{
      color:var(--muted);
      font-size:.92rem;
      text-align:center;
      line-height:var(--line-relaxed);
      margin:14px 0 0;
    }}

    .tasks-heading {{ margin:0; font-size:1.2rem; color:var(--charcoal); font-weight:700; line-height:1.3; }}
    .task-group {{ margin-top:0; }}
    .task-list {{ display:grid; gap:0; }}
    .task-search {{
      display:grid;
      grid-template-columns:minmax(0,1fr) auto;
      gap:10px;
      margin-bottom:22px;
    }}
    .task-search input {{
      min-width:0;
      min-height:46px;
      border:1px solid var(--border);
      border-radius:var(--radius-2xl);
      padding:0 16px;
      background:var(--highlight);
      color:var(--ink);
      font:inherit;
      line-height:var(--line-body);
    }}
    .task-search button {{
      min-height:46px;
      padding:0 18px;
      border-radius:var(--radius-2xl);
      font-size:.92rem;
      white-space:nowrap;
    }}
    .task-search .search-clear {{
      grid-column:1/-1;
      min-height:40px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border:1px solid var(--border);
      border-radius:var(--radius-2xl);
      background:var(--card);
      color:var(--charcoal);
      text-decoration:none;
      font-size:.88rem;
      font-weight:600;
    }}
    .task-row {{
      display:block;
      padding:14px 0;
      border-bottom:1px solid var(--border);
      min-width:0;
    }}
    .task-row:last-child {{ border-bottom:0; }}
    .task-sub .task-meta {{ margin-top:0; }}
    .task-parent-meta + .task-meta {{ margin-top:6px; }}
    .task-meta {{
      display:flex;
      flex-wrap:wrap;
      gap:6px;
      margin-top:0;
      min-width:0;
      max-width:100%;
    }}
    .task-meta-tag {{
      display:inline-flex;
      align-items:center;
      max-width:100%;
      padding:4px 9px;
      border-radius:999px;
      background:var(--highlight);
      color:var(--muted);
      font-size:.72rem;
      font-weight:600;
      line-height:1.25;
      letter-spacing:.01em;
      overflow-wrap:anywhere;
    }}
    .task-parent-meta {{
      margin-top:0;
      color:var(--muted);
      font-size:.82rem;
      line-height:var(--line-relaxed);
      overflow-wrap:anywhere;
    }}
    .task-parent-meta a {{ color:inherit; text-decoration:underline; font-weight:inherit; }}
    .task-action-bar .trash-button {{ font-size:1rem; opacity:.62; }}
    .task-action-bar .trash-button,
    .task-action-bar .snooze-icon-button {{
      width:32px;
      height:32px;
      min-height:32px;
      padding:0;
      border:0;
      border-radius:10px;
      background:transparent;
      display:flex;
      align-items:center;
      justify-content:center;
      cursor:pointer;
    }}
    .task-action-bar .trash-button:hover,
    .task-action-bar .trash-button:focus-visible {{ opacity:1; background:var(--accent-soft); }}
    .tasks-toolbar {{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      margin-bottom:20px;
    }}
    .section-toggle-controls {{ display:flex; gap:6px; flex-shrink:0; }}
    .section-toggle-controls button {{
      min-height:32px;
      width:auto;
      padding:0 11px;
      border:1px solid var(--border);
      border-radius:999px;
      background:var(--card);
      color:var(--muted);
      font:inherit;
      font-size:.74rem;
      font-weight:600;
      cursor:pointer;
      line-height:1.2;
    }}
    .section-toggle-controls button:hover {{
      color:var(--charcoal);
      background:var(--accent-soft);
    }}
    details.task-group {{ margin-top:24px; padding-top:24px; border-top:1px solid var(--border); }}
    details.task-group:first-of-type {{ margin-top:0; padding-top:0; border-top:0; }}
    details.task-group > summary {{ list-style:none; cursor:pointer; user-select:none; }}
    details.task-group > summary::-webkit-details-marker {{ display:none; }}
    details.task-group > summary.task-group-heading {{
      display:grid;
      grid-template-columns:minmax(0,1fr) 2rem 1rem;
      align-items:center;
      column-gap:12px;
      padding:0 0 14px;
      margin:0;
      color:var(--charcoal);
      font-size:.78rem;
      font-weight:700;
      letter-spacing:.06em;
      text-transform:uppercase;
      border-bottom:1px solid var(--border);
    }}
    .task-group-label {{
      min-width:0;
    }}
    details.task-group > summary.task-group-heading::after {{
      content:"▾";
      grid-column:3;
      justify-self:end;
      color:var(--muted);
      font-size:.85rem;
    }}
    details.task-group:not([open]) > summary.task-group-heading::after {{ content:"▸"; }}
    .section-count {{
      grid-column:2;
      justify-self:center;
      min-width:24px;
      height:24px;
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border-radius:999px;
      background:var(--accent-soft);
      color:var(--charcoal);
      font-size:.72rem;
      font-weight:700;
      letter-spacing:0;
      text-transform:none;
    }}
    .task-action-bar .snooze-icon-button {{ list-style:none; font-size:.95rem; opacity:.62; }}
    .task-action-bar .snooze-icon-button::-webkit-details-marker {{ display:none; }}
    .task-action-bar .snooze-icon-button:hover,
    .task-action-bar .snooze-icon-button:focus-visible {{ opacity:1; background:var(--accent-soft); }}
    .task-action-bar .task-snooze {{ position:relative; }}
    .task-action-bar .task-snooze-menu {{
      position:absolute;
      z-index:30;
      top:38px;
      left:0;
      right:auto;
      width:min(240px, calc(100vw - 24px));
      padding:8px;
      border:1px solid var(--border);
      border-radius:var(--radius-2xl);
      background:var(--card);
      box-shadow:var(--shadow-lg);
    }}
    .task-snooze-menu form {{ display:block; margin:0; }}
    .task-snooze-menu button {{
      width:100%;
      min-height:0;
      border:0;
      border-radius:10px;
      background:transparent;
      color:var(--ink);
      font:inherit;
      font-size:.86rem;
      font-weight:600;
      text-align:left;
      cursor:pointer;
      padding:10px 12px;
      line-height:var(--line-body);
    }}
    .task-snooze-menu button:hover {{ background:var(--accent-soft); }}
    .task-snooze-date {{
      display:grid !important;
      grid-template-columns:minmax(130px,1fr) auto;
      gap:8px !important;
      padding:8px 4px 4px;
    }}
    .task-snooze-date input[type="date"] {{
      width:100%;
      min-width:0;
      border:1px solid var(--border);
      border-radius:10px;
      padding:8px 10px;
      font:inherit;
      font-size:.82rem;
    }}
    .task-snooze-date button {{ width:auto; white-space:nowrap; }}
    .completed-task-icon {{
      flex:0 0 var(--task-check);
      width:var(--task-check);
      min-width:var(--task-check);
      height:var(--task-check);
      margin:1px 0 0;
      display:flex;
      align-items:center;
      justify-content:center;
      border-radius:50%;
      background:rgba(38, 65, 85, 0.12);
      color:var(--muted);
      font-size:11px;
      font-weight:700;
    }}
    .completed-task-row .task-link {{
      color:var(--muted);
    }}
    @media (max-width:560px) {{
      main {{ padding-left:16px; padding-right:16px; }}
      .surface-card {{ padding:20px 18px; }}
      .focus-card {{ padding:20px 18px; }}
      .task-search {{ grid-template-columns:1fr; }}
      .task-search button {{ width:100%; }}
    }}
    .empty-state {{ padding:24px 0; color:var(--muted); line-height:var(--line-relaxed); }}
    .completed-today-summary {{ margin:0 0 14px; padding:14px 16px; border:1px solid var(--border); border-radius:12px; background:var(--highlight); }}
    .completed-today-summary-label {{ font-size:.76rem; font-weight:700; letter-spacing:.03em; text-transform:uppercase; color:var(--muted); margin-bottom:6px; }}
    .completed-today-summary-text {{ font-size:.94rem; line-height:var(--line-relaxed); color:var(--ink); }}
    .completed-today-summary.pending .completed-today-summary-text {{ color:var(--muted); font-style:italic; }}
  </style>
</head>
<body>
  <main>
    <div class="page-heading">
      <h1 class="brand">Dashboard</h1>
      <p class="dashboard-subtitle">Capture, prioritize, and act.</p>
    </div>
    {notice}
    {focus_card}
    <section class="surface-card">
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
    </section>
    <section class="surface-card tasks-section">
      <div class="tasks-toolbar">
        <h2 class="tasks-heading">Tasks</h2>
        <div class="section-toggle-controls">
          <button type="button" class="toolbar-button" id="expandAllSections">Expand all</button>
          <button type="button" class="toolbar-button" id="collapseAllSections">Collapse all</button>
        </div>
      </div>
      <form class="task-search" method="get" action="/">
        <input name="search" value="{html.escape(search)}" placeholder="Search open tasks" aria-label="Search open tasks">
        <button type="submit">Search</button>
        {('<a class="search-clear" href="/">Clear search</a>' if search else '')}
      </form>
      {task_sections}
    </section>
  </main>
  {_bottom_nav_html(active="home", review_count=review_count)}
  <script>
    (() => {{
      function resizeFocusTextarea(el) {{
        if (!el || !el.classList.contains("focus-autoexpand")) return;
        el.style.height = "auto";
        const lineHeight = parseFloat(window.getComputedStyle(el).lineHeight) || 24;
        const maxHeight = lineHeight * 10 + 28;
        el.style.height = Math.min(el.scrollHeight, maxHeight) + "px";
        el.style.overflowY = el.scrollHeight > maxHeight ? "auto" : "hidden";
      }}

      document.querySelectorAll("textarea.focus-autoexpand").forEach((el) => {{
        resizeFocusTextarea(el);
        el.addEventListener("input", () => resizeFocusTextarea(el));
      }});

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

      let optimisticCompletion = null;

      const clearOptimisticTimer = () => {{
        if (!optimisticCompletion?.timer) return;
        window.clearTimeout(optimisticCompletion.timer);
        optimisticCompletion.timer = null;
      }};

      const removeOptimisticToast = () => {{
        document.getElementById("optimisticCompleteToast")?.remove();
      }};

      const restoreOptimisticNodes = (state) => {{
        (state?.hiddenNodes || []).forEach((node) => {{
          node.classList.remove("optimistic-hidden");
        }});
        if (state?.focusCard && state.focusHtml !== null) {{
          state.focusCard.innerHTML = state.focusHtml;
          initFocusCard(state.focusCard);
        }}
        (state?.hiddenNodes || []).forEach((node) => {{
          node.querySelectorAll(".complete-checkbox").forEach((button) => {{
            button.dataset.submitting = "0";
          }});
        }});
      }};

      const showOptimisticErrorToast = (message, onRetry) => {{
        removeOptimisticToast();
        const toast = document.createElement("div");
        toast.id = "optimisticCompleteToast";
        toast.className = "optimistic-toast error";
        if (onRetry) {{
          toast.innerHTML = `<span>${{message}}</span><button type="button">Try again</button>`;
          toast.querySelector("button")?.addEventListener("click", () => {{
            removeOptimisticToast();
            onRetry();
          }});
        }} else {{
          toast.textContent = message;
        }}
        document.body.appendChild(toast);
        window.setTimeout(removeOptimisticToast, 5000);
      }};

      const syncDashboardFragments = async ({{ refreshFocus = false }} = {{}}) => {{
        const focusUrl = new URL("/api/focus-card", window.location.origin);
        if (refreshFocus) {{
          focusUrl.searchParams.set("refresh_focus", "1");
        }}
        const [focusResponse, tasksData] = await Promise.all([
          fetch(focusUrl.toString(), {{
            headers: {{ "X-Requested-With": "fetch" }},
          }}),
          fetchDashboardTasks(),
        ]);
        if (!focusResponse.ok) throw new Error("Focus sync failed");
        const focusData = await focusResponse.json();
        if (focusData.html) {{
          replaceFocusCard(focusData.html);
          focusPollFingerprint = focusData.fingerprint;
        }}
        applyTasksPollData(tasksData);
        return {{ focusData, tasksData }};
      }};

      const showOptimisticToast = (state, message = "Task completed") => {{
        removeOptimisticToast();
        const toast = document.createElement("div");
        toast.id = "optimisticCompleteToast";
        toast.className = "optimistic-toast";
        toast.innerHTML = '<span>' + message + '</span><button type="button">Undo</button>';
        document.body.appendChild(toast);

        toast.querySelector("button")?.addEventListener("click", async () => {{
          if (!optimisticCompletion || optimisticCompletion.taskId !== state.taskId) return;

          const undoRequest = async () => {{
            clearOptimisticTimer();
            restoreOptimisticNodes(state);
            removeOptimisticToast();
            optimisticCompletion = null;

            try {{
              const response = await fetch(`/tasks/${{encodeURIComponent(state.taskId)}}/undo-complete-optimistic`, {{
                method: "POST",
                headers: {{ "X-Requested-With": "fetch" }},
              }});
              if (!response.ok) throw new Error("Undo failed");
              await syncDashboardFragments({{
                refreshFocus: Boolean(state.affectsFocus),
              }});
            }} catch (_error) {{
              state.hiddenNodes.forEach((node) => {{
                node.classList.add("optimistic-hidden");
              }});
              if (state.focusCard && state.focusHtml !== null) {{
                state.focusCard.innerHTML = state.focusHtml;
                initFocusCard(state.focusCard);
              }}
              optimisticCompletion = state;
              showOptimisticErrorToast("Undo could not be saved.", undoRequest);
            }}
          }};

          await undoRequest();
        }});
      }};

      const finishOptimisticWindow = (state) => {{
        removeOptimisticToast();
        optimisticCompletion = null;
        if (state.affectsFocus) {{
          startFocusPolling({{ refreshFocus: true }});
        }} else {{
          refreshTaskGroupsOnce();
        }}
      }};

      const bindCompleteForm = (form) => {{
        if (form.dataset.aiosCompleteBound === "1") return;
        form.dataset.aiosCompleteBound = "1";
        const button = form.querySelector(".complete-checkbox");
        const taskId = form.dataset.taskId || form.action.split("/tasks/")[1]?.split("/")[0] || "";
        if (!button || !taskId) return;

        form.addEventListener("submit", async (event) => {{
          event.preventDefault();
          if (button.dataset.submitting === "1") return;
          button.dataset.submitting = "1";

          if (optimisticCompletion) {{
            clearOptimisticTimer();
            finishOptimisticWindow(optimisticCompletion);
          }}

          const focusCard = form.closest(".focus-card");
          const isFocusParent = form.classList.contains("focus-parent-complete");
          const isFocusActivation = form.classList.contains("focus-activation-complete");
          const hiddenNodes = Array.from(
            document.querySelectorAll(`.task-row[data-task-id="${{CSS.escape(taskId)}}"]`)
          );

          const state = {{
            taskId,
            hiddenNodes,
            focusCard,
            focusHtml: focusCard ? focusCard.innerHTML : null,
            affectsFocus: Boolean(isFocusParent || isFocusActivation),
            timer: null,
          }};

          hiddenNodes.forEach((node) => node.classList.add("optimistic-hidden"));

          if (isFocusParent && focusCard) {{
            focusCard.innerHTML =
              '<div class="focus-label">⭐ Best Next Action</div>' +
              '<div class="focus-pending"><span class="mini-spinner"></span> Finding your next focus…</div>';
          }} else if (isFocusActivation && focusCard) {{
            const start = focusCard.querySelector(".focus-start");
            if (start) {{
              start.innerHTML =
                '<div class="focus-start-heading">Start here</div>' +
                '<div class="task-title-row">' +
                '<span class="task-check-placeholder" aria-hidden="true"></span>' +
                '<div class="focus-pending"><span class="mini-spinner"></span> Finding your next step…</div>' +
                '</div>';
            }}
          }}

          optimisticCompletion = state;
          showOptimisticToast(state);

          try {{
            const response = await fetch(`/tasks/${{encodeURIComponent(taskId)}}/complete-optimistic`, {{
              method: "POST",
              headers: {{ "X-Requested-With": "fetch" }},
            }});
            if (!response.ok) throw new Error("Completion failed");
            state.timer = window.setTimeout(() => finishOptimisticWindow(state), 8000);
          }} catch (_error) {{
            clearOptimisticTimer();
            restoreOptimisticNodes(state);
            removeOptimisticToast();
            optimisticCompletion = null;
            button.dataset.submitting = "0";

            const failed = document.createElement("div");
            failed.id = "optimisticCompleteToast";
            failed.className = "optimistic-toast error";
            failed.textContent = "Task could not be completed.";
            document.body.appendChild(failed);
            window.setTimeout(removeOptimisticToast, 3000);
          }}
        }});
      }};

      document.querySelectorAll(".complete-form").forEach(bindCompleteForm);

      const bindDeleteForm = (form) => {{
        if (form.dataset.aiosDeleteBound === "1") return;
        form.dataset.aiosDeleteBound = "1";
        form.addEventListener("submit", () => {{
          if (form.closest(".focus-card")) {{
            sessionStorage.removeItem(scrollKey);
          }} else {{
            saveScroll();
          }}
        }});
      }};

      document.querySelectorAll(".delete-form").forEach(bindDeleteForm);

      const bindSnoozeForm = (form) => {{
        if (form.dataset.aiosSnoozeBound === "1") return;
        form.dataset.aiosSnoozeBound = "1";
        form.addEventListener("submit", async (event) => {{
          event.preventDefault();

          const submitter = event.submitter;
          if (submitter?.dataset.submitting === "1") return;
          if (submitter) submitter.dataset.submitting = "1";

          const details = form.closest("details");
          const taskId =
            details?.closest("[data-task-id]")?.dataset.taskId ||
            form.action.split("/tasks/")[1]?.split("/")[0] ||
            "";

          if (!taskId) {{
            form.submit();
            return;
          }}

          const formData = new FormData(form);
          if (submitter?.name) {{
            formData.set(submitter.name, submitter.value);
          }}

          const hiddenNodes = Array.from(
            document.querySelectorAll(
              `.task-row[data-task-id="${{CSS.escape(taskId)}}"]`
            )
          );

          const projectRow = details?.closest(".project-editor-row");
          if (projectRow && !hiddenNodes.includes(projectRow)) {{
            hiddenNodes.push(projectRow);
          }}

          const focusCard = details?.closest(".focus-card");
          const focusHtml = focusCard ? focusCard.innerHTML : null;

          hiddenNodes.forEach((node) => {{
            node.classList.add("optimistic-hidden");
          }});

          if (focusCard) {{
            focusCard.innerHTML =
              '<div class="focus-label">⭐ Best Next Action</div>' +
              '<div class="focus-pending"><span class="mini-spinner"></span> Finding your next focus…</div>';
          }}

          if (details) details.open = false;

          try {{
            const response = await fetch(
              `/tasks/${{encodeURIComponent(taskId)}}/snooze-optimistic`,
              {{
                method: "POST",
                headers: {{ "X-Requested-With": "fetch" }},
                body: formData,
              }}
            );

            if (!response.ok) throw new Error("Snooze failed");

            if (focusCard) {{
              startFocusPolling({{
                refreshFocus: false,
                previousFocusId: taskId,
                waitForFocusChange: true,
              }});
            }} else {{
              window.setTimeout(() => refreshTaskGroupsOnce(), 1500);
            }}
          }} catch (_error) {{
            hiddenNodes.forEach((node) => {{
              node.classList.remove("optimistic-hidden");
            }});

            if (focusCard && focusHtml !== null) {{
              focusCard.innerHTML = focusHtml;
              initFocusCard(focusCard);
            }}

            if (submitter) submitter.dataset.submitting = "0";

            removeOptimisticToast();

            const failed = document.createElement("div");
            failed.id = "optimisticCompleteToast";
            failed.className = "optimistic-toast error";
            failed.textContent = "Task could not be snoozed.";
            document.body.appendChild(failed);

            window.setTimeout(removeOptimisticToast, 3000);
          }}
        }});
      }};

      document.querySelectorAll(".task-snooze-menu form").forEach(bindSnoozeForm);

      const allSnoozeMenus = () =>
        Array.from(document.querySelectorAll("details.task-snooze, details.project-task-snooze, details.focus-snooze"));

      const positionSnoozeMenu = (menu) => {{
        const panel = menu.querySelector(".task-snooze-menu");
        if (!panel) return;
        panel.style.left = "0";
        panel.style.right = "auto";
        const margin = 12;
        const panelRect = panel.getBoundingClientRect();
        if (panelRect.right > window.innerWidth - margin) {{
          panel.style.left = `${{window.innerWidth - margin - panelRect.right}}px`;
        }}
        const nextRect = panel.getBoundingClientRect();
        if (nextRect.left < margin) {{
          panel.style.left = `${{margin - menu.getBoundingClientRect().left}}px`;
        }}
      }};

      const bindSnoozeMenu = (menu) => {{
        if (menu.dataset.aiosSnoozeMenuBound === "1") return;
        menu.dataset.aiosSnoozeMenuBound = "1";
        menu.addEventListener("toggle", () => {{
          if (!menu.open) return;
          allSnoozeMenus().forEach((other) => {{
            if (other !== menu) other.open = false;
          }});
          positionSnoozeMenu(menu);
        }});
      }};

      const initFocusTextareas = (root) => {{
        (root || document).querySelectorAll("textarea.focus-autoexpand").forEach((el) => {{
          if (el.dataset.aiosTextareaBound === "1") return;
          el.dataset.aiosTextareaBound = "1";
          resizeFocusTextarea(el);
          el.addEventListener("input", () => resizeFocusTextarea(el));
        }});
      }};

      const initFocusCard = (root) => {{
        const card = root || document.getElementById("focus-card");
        if (!card) return;
        card.querySelectorAll(".complete-form").forEach(bindCompleteForm);
        card.querySelectorAll(".delete-form").forEach(bindDeleteForm);
        card.querySelectorAll(".task-snooze-menu form").forEach(bindSnoozeForm);
        card.querySelectorAll("details.task-snooze, details.focus-snooze").forEach(bindSnoozeMenu);
        initFocusTextareas(card);
      }};

      const replaceFocusCard = (html) => {{
        const wrapper = document.createElement("div");
        wrapper.innerHTML = html.trim();
        const next = wrapper.firstElementChild;
        if (!next) return null;
        const existing = document.getElementById("focus-card");
        if (existing) {{
          existing.replaceWith(next);
        }} else {{
          const anchor = document.querySelector(".tasks-section");
          if (anchor) {{
            anchor.parentElement?.insertBefore(next, anchor);
          }} else {{
            document.querySelector("main")?.appendChild(next);
          }}
        }}
        initFocusCard(next);
        return next;
      }};

      const initTaskList = (root) => {{
        const scope = root || document.getElementById("dashboard-task-groups") || document;
        scope.querySelectorAll(".complete-form").forEach(bindCompleteForm);
        scope.querySelectorAll(".delete-form").forEach(bindDeleteForm);
        scope.querySelectorAll(".task-snooze-menu form").forEach(bindSnoozeForm);
        scope.querySelectorAll("details.task-snooze").forEach(bindSnoozeMenu);
        restoreSectionState();
      }};

      const replaceTaskGroups = (html) => {{
        const wrapper = document.createElement("div");
        wrapper.innerHTML = html.trim();
        const next = wrapper.firstElementChild;
        if (!next) return null;
        const existing = document.getElementById("dashboard-task-groups");
        if (existing) {{
          existing.replaceWith(next);
        }} else {{
          document.querySelector(".tasks-section")?.appendChild(next);
        }}
        initTaskList(next);
        return next;
      }};

      const fetchDashboardTasks = async () => {{
        const url = new URL("/api/dashboard-tasks", window.location.origin);
        const searchInput = document.querySelector('.task-search input[name="search"]');
        const searchValue = searchInput?.value?.trim();
        if (searchValue) {{
          url.searchParams.set("search", searchValue);
        }}
        const response = await fetch(url.toString(), {{
          headers: {{ "X-Requested-With": "fetch" }},
        }});
        if (!response.ok) throw new Error("Tasks poll failed");
        return response.json();
      }};

      const applyTasksPollData = (data) => {{
        if (!data?.html) return false;
        if (data.fingerprint === tasksPollFingerprint) return false;
        replaceTaskGroups(data.html);
        tasksPollFingerprint = data.fingerprint;
        return true;
      }};

      const refreshTaskGroupsOnce = async () => {{
        try {{
          const tasksData = await fetchDashboardTasks();
          applyTasksPollData(tasksData);
        }} catch (_error) {{
          // Best-effort sync for list-only changes.
        }}
      }};

      const cleanFocusPollUrl = () => {{
        const url = new URL(window.location.href);
        url.searchParams.delete("refresh_focus");
        url.searchParams.delete("message");
        const next = url.pathname + (url.search ? url.search : "") + "#focus-card";
        window.history.replaceState(null, "", next);
      }};

      let focusPollTimer = null;
      let focusPollFingerprint = window.__AIOS_FOCUS_POLL__?.initialFingerprint || null;
      let tasksPollFingerprint = window.__AIOS_DASHBOARD_TASKS__?.initialFingerprint || null;
      let lastFocusPollOverrides = null;

      const showFocusPollTimeout = (retryConfig) => {{
        const card = document.getElementById("focus-card");
        if (!card) return;
        card.innerHTML =
          '<div class="focus-label">⭐ Best Next Action</div>' +
          '<div class="focus-poll-timeout">' +
          '<p>Still updating your focus. The change may still be processing in the background.</p>' +
          '<div class="focus-poll-timeout-actions">' +
          '<button type="button" class="primary" data-focus-poll-retry>Try again</button>' +
          '<button type="button" class="link" data-focus-poll-reload>Refresh page</button>' +
          '</div></div>';
        card.querySelector("[data-focus-poll-retry]")?.addEventListener("click", () => {{
          sessionStorage.removeItem("aios-focus-activation-refresh-count");
          startFocusPolling(retryConfig || lastFocusPollOverrides || {{ waitForFocusChange: true }});
        }});
        card.querySelector("[data-focus-poll-reload]")?.addEventListener("click", () => {{
          window.location.reload();
        }});
      }};

      const startFocusPolling = (overrides = {{}}) => {{
        const card = document.getElementById("focus-card");
        const base = window.__AIOS_FOCUS_POLL__ || {{ enabled: false }};
        const config = {{
          ...base,
          ...overrides,
          enabled: true,
          initialFocusId:
            overrides.initialFocusId
            ?? base.initialFocusId
            ?? card?.dataset.taskId
            ?? null,
          previousFocusId:
            overrides.previousFocusId
            ?? base.previousFocusId
            ?? null,
          waitForFocusChange: Boolean(
            overrides.waitForFocusChange ?? base.waitForFocusChange
          ),
          refreshFocus: overrides.refreshFocus ?? base.refreshFocus ?? true,
          maxAttempts: overrides.maxAttempts || base.maxAttempts || 15,
        }};
        lastFocusPollOverrides = {{ ...config }};
        if (focusPollTimer) {{
          window.clearTimeout(focusPollTimer);
          focusPollTimer = null;
        }}

        const key = "aios-focus-activation-refresh-count";
        let attempt = Number(sessionStorage.getItem(key) || "0");
        let delay = config.waitForFocusChange ? 800 : 2000;
        const maxDelay = 30000;

        const poll = async () => {{
          if (attempt >= config.maxAttempts) {{
            sessionStorage.removeItem(key);
            cleanFocusPollUrl();
            focusPollTimer = null;
            if (config.waitForFocusChange) {{
              showFocusPollTimeout(config);
            }}
            return;
          }}

          attempt += 1;
          sessionStorage.setItem(key, String(attempt));

          const focusUrl = new URL("/api/focus-card", window.location.origin);
          if (config.refreshFocus) {{
            focusUrl.searchParams.set("refresh_focus", "1");
          }}

          try {{
            const [focusResponse, tasksData] = await Promise.all([
              fetch(focusUrl.toString(), {{
                headers: {{ "X-Requested-With": "fetch" }},
              }}),
              fetchDashboardTasks(),
            ]);
            if (!focusResponse.ok) throw new Error("Focus poll failed");
            const data = await focusResponse.json();
            applyTasksPollData(tasksData);

            const focusChanged = Boolean(
              config.waitForFocusChange
              && config.previousFocusId
              && data.focus_id
              && data.focus_id !== config.previousFocusId
            );

            if (
              !focusChanged
              && config.initialFocusId
              && data.focus_id
              && data.focus_id !== config.initialFocusId
            ) {{
              sessionStorage.removeItem(key);
              cleanFocusPollUrl();
              focusPollTimer = null;
              if (data.html) {{
                replaceFocusCard(data.html);
                focusPollFingerprint = data.fingerprint;
              }}
              applyTasksPollData(tasksData);
              return;
            }}

            if (data.html && (data.fingerprint !== focusPollFingerprint || focusChanged)) {{
              replaceFocusCard(data.html);
              focusPollFingerprint = data.fingerprint;
            }}

            const waitingForFocusChange = Boolean(
              config.waitForFocusChange
              && config.previousFocusId
              && (!data.focus_id || data.focus_id === config.previousFocusId)
            );

            const tasksPending = Boolean(tasksData?.summary_pending);

            if (!data.pending && !waitingForFocusChange && !tasksPending) {{
              sessionStorage.removeItem(key);
              cleanFocusPollUrl();
              focusPollTimer = null;
              applyTasksPollData(tasksData);
              return;
            }}
          }} catch (_error) {{
            // Keep polling on transient failures.
          }}

          delay = Math.min(Math.round(delay * 1.6), maxDelay);
          focusPollTimer = window.setTimeout(poll, delay);
        }};

        focusPollTimer = window.setTimeout(poll, delay);
      }};

      allSnoozeMenus().forEach(bindSnoozeMenu);

      document.addEventListener("click", (event) => {{
        allSnoozeMenus().forEach((menu) => {{
          if (menu.open && !menu.contains(event.target)) menu.open = false;
        }});
      }});

      document.addEventListener("keydown", (event) => {{
        if (event.key !== "Escape") return;
        allSnoozeMenus().forEach((menu) => {{
          if (!menu.open) return;
          menu.open = false;
          const trigger = menu.querySelector("summary");
          if (trigger) trigger.focus();
        }});
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

      if (window.__AIOS_FOCUS_POLL__?.enabled) {{
        startFocusPolling(window.__AIOS_FOCUS_POLL__);
      }}

      if (new URL(window.location.href).searchParams.get("fast") === "1") {{
        syncDashboardFragments({{ refreshFocus: true }}).finally(() => {{
          const url = new URL(window.location.href);
          url.searchParams.delete("fast");
          const next = url.pathname + (url.search ? url.search : "") + url.hash;
          window.history.replaceState(null, "", next);
        }});
      }}
    }})();
  </script>
{focus_submit_feedback_script}
{focus_poll_script}
{dashboard_tasks_script}
<script>
if ("serviceWorker" in navigator) {{
  window.addEventListener("load", () => {{
    navigator.serviceWorker.register("/service-worker.js", {{ scope: "/" }}).catch(() => {{}});
  }});
}}
</script>


</body>
</html>"""


_MAIN_PWA_MANIFEST = r'''{
  "id": "/", "name": "AIOS", "short_name": "AIOS",
  "description": "AIOS personal task assistant",
  "start_url": "/", "scope": "/", "display": "standalone",
  "background_color": "#F7F6F1", "theme_color": "#264155",
  "icons": [
    {"src":"/pwa/icon-192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},
    {"src":"/pwa/icon-512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}
  ]
}'''

_MAIN_SERVICE_WORKER = r'''const CACHE="aios-main-shell-v1";
const STATIC=["/manifest.webmanifest","/pwa/icon-32.png","/pwa/icon-192.png","/pwa/icon-512.png"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(STATIC)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith("aios-main-shell-")&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener("fetch",e=>{
  const r=e.request;if(r.method!=="GET")return;const u=new URL(r.url);if(u.origin!==self.location.origin)return;
  if(u.pathname==="/capture"||u.pathname.startsWith("/capture/"))return;
  // Dynamic/authenticated AIOS HTML and data stay network-authoritative in V1.
  if(!STATIC.includes(u.pathname))return;
  e.respondWith(caches.match(r).then(c=>c||fetch(r)));
});'''

_CAPTURE_PWA_MANIFEST = '''{
  "name": "Brain Dump",
  "short_name": "Brain Dump",
  "description": "Fast brain dump capture",
  "start_url": "/capture",
  "scope": "/capture",
  "display": "standalone",
  "background_color": "#F7F6F1",
  "theme_color": "#264155",
  "icons": [
    {"src": "/capture/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/capture/icon-512.png", "sizes": "512x512", "type": "image/png"}
  ]
}'''

_CAPTURE_SERVICE_WORKER = '''const CACHE="aios-capture-v1";const SHELL=["/capture","/capture/manifest.webmanifest"];self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));self.skipWaiting()});self.addEventListener("activate",e=>e.waitUntil(self.clients.claim()));self.addEventListener("fetch",e=>{if(e.request.method!=="GET")return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)))})'''

def _capture_pwa_page() -> str:
    return (
        r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
"""
        + _theme_head_extras()
        + r"""
<link rel="manifest" href="/capture/manifest.webmanifest">
<link rel="icon" type="image/png" sizes="32x32" href="/capture/favicon.png">
<link rel="apple-touch-icon" href="/capture/icon-192.png">
<title>Brain Dump</title>
<style>
"""
        + _mobile_design_tokens()
        + r"""
*{box-sizing:border-box}
html,body{
  margin:0;
  padding:0;
  width:100%;
  height:100dvh;
  min-height:0;
  overflow:hidden;
}
body{
  background:var(--paper);
  color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
}
.app-wrapper{
  width:100%;
  height:100%;
  min-height:0;
  padding:12px;
  display:flex;
  flex-direction:column;
}
.capture-card{
  width:100%;
  max-width:none;
  height:100%;
  min-height:0;
  margin:0;
  padding:16px;
  display:flex;
  flex-direction:column;
  container-type:inline-size;
  background:var(--card);
  border:1px solid var(--border);
  border-radius:16px;
  box-shadow:var(--shadow);
}
.card-header{
  flex:0 0 auto;
  margin-bottom:10px;
}
.card-title{
  margin:0;
  color:var(--charcoal);
  font-size:1.45rem;
  font-weight:750;
}
.sub{display:none}
.capture-form{
  flex:1 1 auto;
  min-height:0;
  display:flex;
  flex-direction:column;
}
.input-area{
  flex:1 1 auto;
  min-height:0;
  display:flex;
  flex-direction:column;
}
textarea{
  width:100%;
  height:100%;
  min-height:0;
  resize:none;
  border:1px solid var(--border);
  border-radius:13px;
  background:transparent;
  color:var(--ink);
  padding:12px;
  font:inherit;
  font-size:clamp(14px,3.5cqw,24px);
  line-height:1.5;
}
textarea:focus{
  outline:2px solid var(--focus-ring);
  outline-offset:0;
}
.card-footer{
  flex:0 0 auto;
  display:flex;
  align-items:center;
  gap:10px;
  margin-top:10px;
  flex-wrap:wrap;
}
button{
  border:0;
  border-radius:11px;
  background:var(--charcoal);
  color:var(--on-accent);
  font:inherit;
  font-weight:750;
  padding:9px 16px;
  min-height:40px;
  cursor:pointer;
}
.theme-toggle{
  border:1px solid var(--border);
  background:transparent;
  color:var(--muted);
  font-size:.82rem;
  font-weight:600;
}
button:disabled{opacity:.55}
.status{
  min-height:1.3em;
  color:var(--muted);
  font-size:.92rem;
}
.status.ok{color:var(--ok)}
.hint{
  margin:0;
  color:var(--muted);
  font-size:.8rem;
  white-space:nowrap;
}
@media(max-width:520px){
  .app-wrapper{padding:12px}
  .capture-card{padding:18px}
  .sub{
    display:block;
    color:var(--muted);
    margin:4px 0 12px;
  }
  .card-header{margin-bottom:0}
  .card-footer{
    align-items:stretch;
    flex-direction:column;
  }
  button{
    width:100%;
    padding:13px;
  }
  .hint{display:none}
  .status{text-align:center}
}
</style>
</head>
<body>
<div class="app-wrapper">
  <section class="capture-card">
    <div class="card-header">
      <h1 class="card-title">Brain Dump</h1>
      <p class="sub">What’s on your mind?</p>
    </div>

    <form id="captureForm" class="capture-form">
      <div class="input-area">
        <textarea id="captureText" maxlength="10000" autofocus placeholder="• What do you need to remember or act on?"></textarea>
      </div>

      <div class="card-footer">
        <button id="captureButton" type="submit">Capture</button>
        <button type="button" class="theme-toggle" data-theme-toggle>Appearance: System</button>
        <div class="hint">⌘/Ctrl + Enter</div>
        <div id="status" class="status" role="status" aria-live="polite"></div>
      </div>
    </form>
  </section>
</div>

<script>
const key="aios-capture-draft-v1";
const box=document.getElementById("captureText");
const form=document.getElementById("captureForm");
const button=document.getElementById("captureButton");
const status=document.getElementById("status");

function normalizeBullets(value){
  return value.split("\n").map(line=>{
    if(!line.trim()) return line;
    return /^\s*[•*-]\s+/.test(line)
      ? line.replace(/^\s*[•*-]\s+/, "• ")
      : "• "+line;
  }).join("\n");
}

const savedDraft=localStorage.getItem(key)||"";
box.value=savedDraft ? normalizeBullets(savedDraft) : "• ";

box.addEventListener("input",()=>{
  localStorage.setItem(key,box.value);
});

box.addEventListener("keydown",e=>{
  if(e.key==="Enter"&&(e.metaKey||e.ctrlKey)){
    e.preventDefault();
    form.requestSubmit();
    return;
  }

  if(e.key==="Enter"){
    e.preventDefault();
    const start=box.selectionStart;
    const end=box.selectionEnd;
    const before=box.value.slice(0,start);
    const after=box.value.slice(end);
    const insert="\n• ";
    box.value=before+insert+after;
    box.selectionStart=box.selectionEnd=start+insert.length;
    localStorage.setItem(key,box.value);
  }
});

form.addEventListener("submit",async e=>{
  e.preventDefault();

  const text=box.value
    .split("\n")
    .map(line=>line.replace(/^\s*•\s*/, ""))
    .join("\n")
    .trim();

  if(!text){
    status.textContent="Enter something first.";
    box.focus();
    return;
  }

  button.disabled=true;
  status.textContent="Adding…";

  try{
    const r=await fetch("/capture/submit",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({text})
    });

    if(!r.ok) throw new Error();

    localStorage.removeItem(key);
    box.value="• ";
    status.textContent="✓ Added to AIOS";
    status.className="status ok";
    box.focus();

    setTimeout(()=>{
      status.textContent="";
      status.className="status";
    },2200);

  }catch(err){
    status.textContent="Couldn’t add it. Your text is saved here—try again.";
    localStorage.setItem(key,box.value);
  }finally{
    button.disabled=false;
  }
});

if("serviceWorker" in navigator){
  window.addEventListener("load",()=>{
    navigator.serviceWorker.register("/capture/service-worker.js");
  });
}
</script>
"""
        + _theme_toggle_script()
        + """
</body>
</html>"""
    )


@app.get('/manifest.webmanifest')
def main_pwa_manifest():
    from fastapi.responses import Response
    return Response(_MAIN_PWA_MANIFEST, media_type='application/manifest+json', headers={'Cache-Control':'no-cache'})

@app.get('/service-worker.js')
def main_pwa_service_worker():
    from fastapi.responses import Response
    return Response(_MAIN_SERVICE_WORKER, media_type='application/javascript', headers={'Cache-Control':'no-cache','Service-Worker-Allowed':'/'})

@app.get('/pwa/icon-32.png')
def main_pwa_icon_32():
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name('static')/'aios-32.png', media_type='image/png')

@app.get('/pwa/icon-192.png')
def main_pwa_icon_192():
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name('static')/'aios-192.png', media_type='image/png')

@app.get('/pwa/icon-512.png')
def main_pwa_icon_512():
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name('static')/'aios-512.png', media_type='image/png')


@app.get('/capture', response_class=HTMLResponse)
def capture_pwa(_user: Annotated[str, Depends(_check_basic_auth)]) -> HTMLResponse:
    return HTMLResponse(_capture_pwa_page())

@app.get('/capture/favicon.png')
def capture_favicon():
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name("static") / "brain-dump-32.png", media_type="image/png")


@app.get('/capture/icon-192.png')
def capture_icon_192():
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name("static") / "brain-dump-192.png", media_type="image/png")


@app.get('/capture/icon-512.png')
def capture_icon_512():
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).with_name("static") / "brain-dump-512.png", media_type="image/png")


@app.get('/capture/manifest.webmanifest')
def capture_manifest():
    from fastapi.responses import Response
    return Response(_CAPTURE_PWA_MANIFEST, media_type='application/manifest+json')

@app.get('/capture/service-worker.js')
def capture_service_worker():
    from fastapi.responses import Response
    return Response(_CAPTURE_SERVICE_WORKER, media_type='application/javascript')

@app.post('/capture/submit')
async def capture_pwa_submit(request: Request, _user: Annotated[str, Depends(_check_basic_auth)]):
    payload = await request.json()
    text = str(payload.get('text') or '').strip()
    lines = _split_brain_dump(text)
    if not lines:
        raise HTTPException(status_code=400, detail='Please enter something.')

    sent, failures = _capture_many(lines, capture_interface='capture_pwa_v1')
    if failures:
        if sent == 0:
            raise HTTPException(status_code=502, detail='AIOS could not accept the capture.')
        raise HTTPException(
            status_code=502,
            detail=f'{sent} item(s) sent, {len(failures)} failed. Your text is still saved here—retry the failed lines.',
        )

    return {'ok': True, 'sent': sent}

@app.get("/health")
def health() -> dict:
    payload = _web_about_payload()
    return {
        "status": payload["status"],
        "service": payload["service"],
        "version": payload["version"],
        "about_page": payload["about_page"],
    }


@app.get("/api/about")
def about_api(
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> JSONResponse:
    return JSONResponse(_web_about_payload())


@app.get("/about", response_class=HTMLResponse)
def about_web(
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> HTMLResponse:
    return HTMLResponse(_about_page(_web_about_payload()))


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> HTMLResponse:
    message=request.query_params.get("message", "")
    error=request.query_params.get("error", "")
    search=request.query_params.get("search", "").strip()
    fast_shell = request.query_params.get("fast") == "1"
    if fast_shell:
        tasks = {}
        focus = None
        review_count = 0
        refresh_focus = True
    else:
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
            tasks=tasks if not fast_shell else {},
            search=search,
            focus=focus if not fast_shell else None,
            refresh_focus=refresh_focus,
            review_count=review_count,
            fast_shell=fast_shell,
        )
    )


@app.get("/api/focus-card")
def focus_card_api(
    request: Request,
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> JSONResponse:
    refresh_focus = request.query_params.get("refresh_focus") == "1"
    try:
        focus = _fetch_focus()
    except Exception as exc:
        return JSONResponse(
            {"error": str(exc), "pending": True},
            status_code=503,
        )
    return JSONResponse(_focus_card_view(focus, refresh_focus=refresh_focus))


@app.get("/api/dashboard-tasks")
def dashboard_tasks_api(
    request: Request,
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> JSONResponse:
    search = request.query_params.get("search", "").strip()
    try:
        tasks = _fetch_open_tasks(search=search, limit=50)
    except Exception as exc:
        return JSONResponse(
            {"error": str(exc), "pending": True},
            status_code=503,
        )
    try:
        focus = _fetch_focus()
    except Exception:
        focus = None
    focus_id = str(focus.get("id") or "") if focus else ""
    view = _tasks_sections_view(tasks, search=search, focus_id=focus_id)
    return JSONResponse(
        {
            "html": view["html"],
            "fingerprint": view["fingerprint"],
            "focus_id": focus_id or None,
            "summary_pending": view["summary_pending"],
        }
    )


@app.get("/api/tasks/{task_id}/breakdown-panel")
def breakdown_panel_api(
    task_id: str,
    request: Request,
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> JSONResponse:
    return_to = request.query_params.get("return_to", "/")
    try:
        task = _fetch_task_detail(task_id)
    except Exception as exc:
        return JSONResponse(
            {"error": str(exc), "pending": True},
            status_code=503,
        )
    return JSONResponse(_breakdown_panel_view(task, return_to=return_to))


@app.get("/api/projects/{project_id}/work-results")
def project_work_results_api(
    project_id: str,
    request: Request,
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> JSONResponse:
    refresh_proposal = request.query_params.get("refresh_proposal") == "1"
    try:
        payload = _fetch_project_detail(project_id)
    except Exception as exc:
        return JSONResponse(
            {"error": str(exc), "pending": True},
            status_code=503,
        )
    return JSONResponse(
        _project_work_results_view(payload, refresh_proposal=refresh_proposal)
    )


@app.get("/api/reviews/list")
def reviews_list_api(
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> JSONResponse:
    try:
        reviews = _fetch_reviews()
    except Exception as exc:
        return JSONResponse(
            {"error": str(exc), "pending": True},
            status_code=503,
        )
    _enrich_duplicate_reviews(reviews)
    return JSONResponse(_build_review_cards(reviews))





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
    context: Annotated[str, Form()] = "",
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
        "context": context.strip(),
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

        _enrich_duplicate_reviews(reviews)

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



@app.post("/projects/{project_id}/tasks")
def update_project_tasks_web(
    project_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    task_id: Annotated[list[str] | None, Form()] = None,
    task_title: Annotated[list[str] | None, Form()] = None,
):
    try:
        ids = list(task_id or [])
        titles = list(task_title or [])
        if len(ids) != len(titles):
            raise ValueError("Invalid project task list")
        tasks = [
            {"id": (raw_id.strip() or None), "title": raw_title.strip()}
            for raw_id, raw_title in zip(ids, titles)
            if raw_title.strip()
        ]
        _update_project_tasks(project_id, tasks)
        return RedirectResponse(url=f"/projects/{project_id}?message=Project+tasks+saved.#project-tasks", status_code=303)
    except Exception as exc:
        print("[Project Tasks] Update failed:", exc)
        return RedirectResponse(url=f"/projects/{project_id}?error=Project+tasks+could+not+be+saved.#project-tasks", status_code=303)

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
    except Exception as exc:
        return RedirectResponse(
            url="/projects?error=Project+detail+could+not+be+rendered.",
            status_code=303,
        )


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
            ),
            headers={"Cache-Control": "no-store"},
        )
    except Exception as exc:
        print("[Task Detail] Render failed:", exc)
        return RedirectResponse(
            url="/?error=Task+could+not+be+loaded.",
            status_code=303,
        )


@app.post("/tasks/{task_id}/focus-context/help")
def focus_context_help_web(task_id: str, _user: Annotated[str, Depends(_check_basic_auth)]):
    try:
        _request_focus_context_help(task_id)
        return RedirectResponse(url="/?refresh_focus=1#focus-card", status_code=303)
    except Exception as exc:
        print("[Focus Context] Help request failed:", exc)
        return RedirectResponse(url="/?error=Context+help+could+not+be+requested.#focus-card", status_code=303)


@app.post("/tasks/{task_id}/focus-context/answer")
def focus_context_answer_web(task_id: str, _user: Annotated[str, Depends(_check_basic_auth)], answer: Annotated[str, Form()] = ""):
    try:
        _answer_focus_context(task_id, answer.strip())
        return RedirectResponse(url="/?refresh_focus=1#focus-card", status_code=303)
    except Exception as exc:
        print("[Focus Context] Answer failed:", exc)
        return RedirectResponse(url="/?error=Context+answer+could+not+be+used.#focus-card", status_code=303)


@app.post("/tasks/{task_id}/focus-context")
def focus_context_save_web(task_id: str, _user: Annotated[str, Depends(_check_basic_auth)], context: Annotated[str, Form()] = ""):
    try:
        _save_focus_context(task_id, context.strip())
        return RedirectResponse(url="/?message=Context+saved.&refresh_focus=1#focus-card", status_code=303)
    except Exception as exc:
        print("[Focus Context] Save failed:", exc)
        return RedirectResponse(url="/?error=Context+could+not+be+saved.#focus-card", status_code=303)


@app.post("/tasks/{task_id}/edit")
def edit_task_web(
    task_id: str,
    background_tasks: BackgroundTasks,
    _user: Annotated[str, Depends(_check_basic_auth)],
    title: Annotated[str, Form()],
    context: Annotated[str, Form()] = "",
    due_at: Annotated[str, Form()] = "",
    defer_until: Annotated[str, Form()] = "",
    importance: Annotated[str, Form()] = "",
    urgency: Annotated[str, Form()] = "",
    effort: Annotated[str, Form()] = "",
    duration: Annotated[str, Form()] = "",
    is_just_do_it: Annotated[str | None, Form()] = None,
    return_to: Annotated[str, Form()] = "/",
):
    payload = _task_edit_form_payload(
        title=title,
        context=context,
        due_at=due_at,
        defer_until=defer_until,
        importance=importance,
        urgency=urgency,
        effort=effort,
        duration=duration,
        is_just_do_it=is_just_do_it,
    )
    background_tasks.add_task(_save_task_detail_background, task_id, payload)
    return RedirectResponse(
        url=_with_fast_return_param(return_to),
        status_code=303,
    )


@app.post("/tasks/{task_id}/edit-optimistic")
def edit_task_optimistic_web(
    task_id: str,
    background_tasks: BackgroundTasks,
    _user: Annotated[str, Depends(_check_basic_auth)],
    title: Annotated[str, Form()],
    context: Annotated[str, Form()] = "",
    due_at: Annotated[str, Form()] = "",
    defer_until: Annotated[str, Form()] = "",
    importance: Annotated[str, Form()] = "",
    urgency: Annotated[str, Form()] = "",
    effort: Annotated[str, Form()] = "",
    duration: Annotated[str, Form()] = "",
    is_just_do_it: Annotated[str | None, Form()] = None,
) -> JSONResponse:
    payload = _task_edit_form_payload(
        title=title,
        context=context,
        due_at=due_at,
        defer_until=defer_until,
        importance=importance,
        urgency=urgency,
        effort=effort,
        duration=duration,
        is_just_do_it=is_just_do_it,
    )
    background_tasks.add_task(_save_task_detail_background, task_id, payload)
    return JSONResponse({"ok": True, "accepted": True})


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


@app.post("/tasks/{task_id}/snooze-optimistic")
def snooze_task_optimistic_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    preset: Annotated[str, Form()] = "",
    custom_date: Annotated[str, Form()] = "",
) -> JSONResponse:
    try:
        result = _snooze_task(task_id, preset, custom_date)
        return JSONResponse({"ok": True, **result})
    except Exception as exc:
        print("[Optimistic Snooze] Save failed:", exc)
        return JSONResponse(
            {"ok": False, "detail": "Task could not be snoozed."},
            status_code=502,
        )


@app.post("/tasks/{task_id}/complete-optimistic")
def complete_task_optimistic_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> JSONResponse:
    try:
        result = _task_action(task_id, "complete")
        return JSONResponse({"ok": True, **result})
    except Exception as exc:
        print("[Optimistic Complete] Save failed:", exc)
        return JSONResponse(
            {"ok": False, "detail": "Task could not be completed."},
            status_code=502,
        )


@app.post("/tasks/{task_id}/undo-complete-optimistic")
def undo_complete_optimistic_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
) -> JSONResponse:
    try:
        result = _task_action(task_id, "undo-complete")
        return JSONResponse({"ok": True, **result})
    except Exception as exc:
        print("[Optimistic Complete] Undo failed:", exc)
        return JSONResponse(
            {"ok": False, "detail": "Completion could not be undone."},
            status_code=502,
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


@app.post("/tasks/{task_id}/not-useful")
def not_useful_task_web(task_id: str, _user: Annotated[str, Depends(_check_basic_auth)]) -> RedirectResponse:
    try:
        _task_action(task_id, "not-useful")
        return RedirectResponse(url="/?refresh_focus=1#focus-card", status_code=303)
    except Exception:
        return RedirectResponse(url="/?error=Starting+step+feedback+could+not+be+saved.", status_code=303)


@app.post("/tasks/{task_id}/snooze")
def snooze_task_web(
    task_id: str,
    _user: Annotated[str, Depends(_check_basic_auth)],
    preset: Annotated[str, Form()] = "",
    custom_date: Annotated[str, Form()] = "",
    return_to: Annotated[str, Form()] = "",
) -> RedirectResponse:
    target = _safe_return_to(return_to) if return_to else "/"
    try:
        _snooze_task(task_id, preset, custom_date)
        if target != "/":
            return RedirectResponse(url=target, status_code=303)
        return RedirectResponse(
            url="/?message=Task+snoozed.&refresh_focus=1",
            status_code=303,
        )
    except Exception:
        if target != "/":
            return RedirectResponse(url=target, status_code=303)
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

# === DAILY JOURNAL V1 ===
def _journal_api(method: str, path: str, payload: dict | None = None) -> dict:
    api_url = _api_url()
    token = _identity_token(api_url)
    response = requests.request(method, f"{api_url}{path}", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"AIOS API returned {response.status_code}: {response.text}")
    return response.json()


def _journal_today_iso() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    zone_name = os.getenv("AIOS_LOCAL_TIMEZONE", "America/Toronto").strip()
    try:
        zone = ZoneInfo(zone_name)
    except Exception:
        zone = ZoneInfo("America/Toronto")
    return datetime.now(zone).date().isoformat()


def _journal_page(journal_date: str, payload: dict) -> str:
    from datetime import date, datetime, timedelta
    from zoneinfo import ZoneInfo

    day = date.fromisoformat(journal_date)
    today = date.fromisoformat(_journal_today_iso())

    prev = (day - timedelta(days=1)).isoformat()
    nxt = (day + timedelta(days=1)).isoformat()

    heading = (
        "Today"
        if day == today
        else day.strftime("%A, %B %-d, %Y")
    )

    body = html.escape(
        str((payload.get("journal") or {}).get("body") or "")
    )

    completed = list(payload.get("completed_work") or [])

    completion_summary = str(
        payload.get("completion_summary") or ""
    ).strip()

    completion_summary_state = str(
        payload.get("completion_summary_state") or "empty"
    ).strip().lower()

    completed_count = int(
        payload.get("completed_count") or len(completed)
    )

    try:
        zone = ZoneInfo(
            os.getenv(
                "AIOS_LOCAL_TIMEZONE",
                "America/Toronto",
            ).strip()
        )
    except Exception:
        zone = ZoneInfo("America/Toronto")

    rows = []

    for task in completed:
        title = html.escape(
            str(task.get("title") or "Untitled")
        )

        project = html.escape(
            str(task.get("project_name") or "")
        )

        raw = str(task.get("completed_at") or "")
        when = "Completed"

        if raw:
            try:
                dt = datetime.fromisoformat(
                    raw.replace("Z", "+00:00")
                )
                if dt.tzinfo:
                    dt = dt.astimezone(zone)
                when = dt.strftime("%-I:%M %p")
            except (TypeError, ValueError):
                pass

        meta = (
            (
                f'<span class="project">{project}</span>'
                if project
                else ""
            )
            + f'<span>{html.escape(when)}</span>'
        )

        rows.append(
            '<li>'
            '<span class="check">✓</span>'
            '<div>'
            f'<strong>{title}</strong>'
            f'<div class="meta">{meta}</div>'
            '</div>'
            '</li>'
        )

    completed_html = (
        "<ul>" + "".join(rows) + "</ul>"
        if rows
        else '<p class="empty">No completed tasks recorded for this day.</p>'
    )

    if completion_summary:
        summary_html = (
            '<div class="summary-text">'
            f'{html.escape(completion_summary)}'
            '</div>'
        )
    elif completion_summary_state == "pending":
        summary_html = (
            '<div class="summary-text pending">'
            "Updating the day's summary…"
            '</div>'
        )
    else:
        summary_html = (
            '<div class="summary-text empty">'
            "No daily summary yet."
            '</div>'
        )

    detail_label = (
        f"Completed work · {completed_count}"
        if completed_count
        else "Completed work"
    )

    focus_label = (
        "Today's summary"
        if day == today
        else "Day's summary"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
{_theme_head_extras()}
<title>{html.escape(heading)} - Daily Journal</title>
<style>
{_mobile_shell_css()}
.journal-date-nav {{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  margin-bottom:24px;
}}
.journal-date-nav a {{
  color:var(--charcoal);
  text-decoration:none;
  border:1px solid var(--border);
  border-radius:var(--radius-2xl);
  padding:10px 14px;
  background:var(--card);
  font-weight:600;
  font-size:.9rem;
  box-shadow:var(--shadow);
  line-height:var(--line-body);
}}
.card {{
  background:var(--card);
  border:1px solid var(--border);
  border-radius:var(--radius-2xl);
  padding:28px 24px;
  margin-bottom:24px;
  box-shadow:var(--shadow);
}}
.summary-label {{
  color:var(--charcoal);
  font-size:.78rem;
  font-weight:700;
  text-transform:uppercase;
  letter-spacing:.05em;
  margin-bottom:10px;
}}
.summary-text {{
  font-size:1.05rem;
  line-height:var(--line-relaxed);
}}
.summary-text.pending,
.summary-text.empty {{
  color:var(--muted);
}}
.completed-details {{
  margin-top:20px;
  padding-top:16px;
  border-top:1px solid var(--border);
}}
.completed-details summary {{
  cursor:pointer;
  color:var(--charcoal);
  font-weight:700;
  list-style:none;
  line-height:var(--line-body);
}}
.completed-details summary::-webkit-details-marker {{ display:none; }}
.completed-details summary::before {{
  content:"▸";
  display:inline-block;
  margin-right:8px;
  transition:transform .12s ease;
}}
.completed-details[open] summary::before {{ transform:rotate(90deg); }}
ul {{ list-style:none; margin:12px 0 0; padding:0; }}
li {{
  display:grid;
  grid-template-columns:28px minmax(0,1fr);
  gap:12px;
  padding:14px 0;
  border-bottom:1px solid var(--border);
  line-height:var(--line-relaxed);
}}
li:last-child {{ border-bottom:0; }}
.check {{ color:var(--ok); font-weight:900; }}
.meta {{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  margin-top:6px;
  color:var(--muted);
  font-size:.86rem;
  line-height:var(--line-body);
}}
.project {{ color:var(--charcoal); font-weight:700; }}
.empty {{ color:var(--muted); line-height:var(--line-relaxed); }}
.card h2 {{
  margin:0 0 10px;
  color:var(--charcoal);
  font-size:1.2rem;
}}
.note {{
  margin:0 0 18px;
  color:var(--muted);
  line-height:var(--line-relaxed);
}}
textarea {{
  display:block;
  width:100%;
  min-height:260px;
  resize:vertical;
  border:1px solid var(--border);
  border-radius:var(--radius-2xl);
  padding:18px 20px;
  background:var(--highlight);
  color:var(--ink);
  font:inherit;
  font-size:1rem;
  line-height:var(--line-relaxed);
}}
textarea:focus {{
  outline:3px solid var(--focus-ring-shadow);
  border-color:var(--focus-ring);
}}
#saveStatus {{
  min-height:24px;
  margin-top:12px;
  color:var(--muted);
  font-size:.88rem;
  line-height:var(--line-body);
}}
#saveStatus.saved {{ color:var(--ok); }}
@media(max-width:560px) {{
  textarea {{ min-height:34dvh; }}
}}
</style>
</head>
<body>
<main>
  <div class="page-heading">
    <h1 class="brand">{html.escape(heading)}</h1>
    <p class="subtitle">Daily Journal</p>
  </div>
  <nav class="journal-date-nav" aria-label="Journal dates">
    <a href="/journal/{prev}" aria-label="Previous day">← Prev</a>
    <a href="/journal/{_journal_today_iso()}">Today</a>
    <a href="/journal/{nxt}" aria-label="Next day">Next →</a>
  </nav>

<section class="card">
  <div class="summary-label">{html.escape(focus_label)}</div>
  {summary_html}

  <details class="completed-details">
    <summary>{html.escape(detail_label)}</summary>
    {completed_html}
  </details>
</section>

<section class="card">
  <h2>Your journal</h2>
  <p class="note">Anything worth remembering about today?</p>
  <textarea
    id="journalBody"
    maxlength="50000"
    placeholder="Write anything you want to remember…"
  >{body}</textarea>
  <div id="saveStatus" role="status" aria-live="polite"></div>
</section>
</main>

<script>
(() => {{
  const body=document.getElementById("journalBody");
  const status=document.getElementById("saveStatus");

  let timer=null;
  let lastSaved=body.value;

  async function save(){{
    if(body.value===lastSaved)return;

    status.textContent="Saving…";
    status.className="";

    try{{
      const r=await fetch(
        "/journal/{journal_date}/save",
        {{
          method:"POST",
          headers:{{"Content-Type":"application/json"}},
          body:JSON.stringify({{body:body.value}})
        }}
      );

      if(!r.ok)throw new Error();

      lastSaved=body.value;
      status.textContent="Saved";
      status.className="saved";
    }}catch(_e){{
      status.textContent="Couldn’t save. Your text is still here.";
    }}
  }}

  body.addEventListener("input",()=>{{
    status.textContent="Unsaved";
    status.className="";
    clearTimeout(timer);
    timer=setTimeout(save,700);
  }});
}})();
</script>
{_bottom_nav_html(active="journal")}
</body>
</html>"""


@app.get("/journal")
def journal_today_web(_user: Annotated[str, Depends(_check_basic_auth)]):
    return RedirectResponse(f"/journal/{_journal_today_iso()}", status_code=303)


@app.get("/journal/{journal_date}")
def journal_day_web(journal_date: str, _user: Annotated[str, Depends(_check_basic_auth)]):
    from datetime import date
    try:
        date.fromisoformat(journal_date)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid journal date")
    try:
        payload = _journal_api("GET", f"/journal/{journal_date}")
    except Exception:
        payload = {
            "journal": {"journal_date": journal_date, "body": ""},
            "completion_summary": "",
            "completion_summary_state": "empty",
            "completed_count": 0,
            "completed_work": [],
        }
    return HTMLResponse(_journal_page(journal_date, payload))


@app.post("/journal/{journal_date}/save")
async def journal_save_web(journal_date: str, request: Request, _user: Annotated[str, Depends(_check_basic_auth)]):
    payload = await request.json()
    result = _journal_api("PUT", f"/journal/{journal_date}", {"body": str(payload.get("body") or "")})
    return {"saved": bool(result.get("saved"))}
# === END DAILY JOURNAL V1 ===
