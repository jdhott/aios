from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from aios.focus_activation import (
    complete_open_focus_activation_children,
    get_active_focus_activation,
    list_focus_activation_children,
    mark_focus_activation_not_now,
)
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os

from aios.api.config import (
    get_api_settings,
    validate_runtime_environment,
)

from aios.api.schemas import (
    HealthResponse,
    InboxCaptureRequest,
    InboxCaptureResponse,
    ReviewResponse,
    PossibleDuplicateResolutionRequest,
    ClarificationAwaitingAnswerRequest,
    ClarificationAnswerRequest,
    ClarificationPendingConfirmationRequest,
    ClarificationResolutionRequest,
)
from aios.ingestion.capture_metadata import parse_capture_metadata
from aios.services.review_service import ReviewService
from aios.storage.inbox_repository import InboxRepository
from aios.storage.supabase_store import SupabaseStore
from aios.project_work import create_supabase_project_task
from aios.project_work_proposals import (
    accept_project_work_proposal,
    dismiss_project_work_proposal,
    retry_project_work_proposal,
)
from aios.storage.project_lifecycle_writer import get_project_lifecycle_writer
from aios.text_utils import normalize
from aios.processing.trigger_coordinator import (
    ProcessingTriggerCoordinator,
)
from aios.processing.cloud_run_trigger import (
    CloudRunJobTrigger,
)


AIOS_API_VERSION = "cloud-run-api-v1-scaffold"
AIOS_API_SECURITY_VERSION = "cloud-run-api-v1.1-security"
AIOS_API_REVIEW_RESOLUTION_VERSION = "cloud-run-api-v1.2"
AIOS_REVIEW_LIFECYCLE_FIX_VERSION = "cloud-workflow-lifecycle-v1.1"
AIOS_CLOUD_PROCESSOR_TRIGGER_VERSION = "cloud-processor-trigger-v1"
AIOS_SCHEDULED_COMPAT_TRIGGER_VERSION = "scheduled-compat-trigger-v1"
AIOS_WEB_TASKS_API_VERSION = "web-tasks-v1-read-only"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    validate_runtime_environment()
    yield


app = FastAPI(
    title="AIOS API",
    version=AIOS_API_VERSION,
    description=(
        "App-facing HTTP boundary for AIOS. "
        "Supabase is authoritative; Notion is not required by these endpoints."
    ),
    lifespan=lifespan,
)


def _store() -> SupabaseStore:
    return SupabaseStore()


def _inbox_repository() -> InboxRepository:
    return InboxRepository(_store())


def _review_service() -> ReviewService:
    store = _store()
    return ReviewService(
        store=store,
        review_repository=None,
        inbox_repository=None,
    )


def _processor_trigger_enabled() -> bool:
    return (
        os.getenv("AIOS_PROCESSOR_TRIGGER_ENABLED", "false")
        .strip()
        .lower()
        in {"1", "true", "yes", "on"}
    )


def _request_processor_run() -> dict:
    if not _processor_trigger_enabled():
        return {
            "status": "disabled",
            "triggered": False,
        }

    store = _store()
    coordinator = ProcessingTriggerCoordinator(store)
    request = coordinator.request_processing()

    if not request.should_trigger:
        print(
            "[Processor Trigger] Processing requested; "
            "existing execution/trigger will handle it."
        )
        return {
            "status": "coalesced",
            "triggered": False,
            "running": request.running,
            "trigger_pending": request.trigger_pending,
        }

    try:
        operation = CloudRunJobTrigger().trigger()
        print(
            "[Processor Trigger] Cloud Run Job requested:",
            operation.get("name", "operation accepted"),
        )
        return {
            "status": "triggered",
            "triggered": True,
            "operation": operation.get("name"),
        }
    except Exception as exc:
        coordinator.release_trigger_claim()
        print(
            "[Processor Trigger] Trigger failed; processing remains requested:",
            exc,
        )
        return {
            "status": "failed",
            "triggered": False,
            "error": str(exc),
        }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
)
def health() -> HealthResponse:
    settings = get_api_settings()
    return HealthResponse(
        version=AIOS_API_VERSION,
        environment=settings.environment,
        auth_mode=settings.auth_mode,
    )


@app.post(
    "/inbox",
    response_model=InboxCaptureResponse,
    status_code=201,
    tags=["inbox"],
)
def capture_inbox(
    request: InboxCaptureRequest,
) -> InboxCaptureResponse:
    row = _inbox_repository().create_brain_dump_item(
        raw_text=request.text,
        notes=request.notes,
        parser=parse_capture_metadata,
        source_metadata={
            "capture_interface": "cloud_run_api_v1",
        },
    )

    # Triggering is best-effort only. The durable Supabase inbox row is
    # authoritative; a Cloud Run trigger failure must never lose capture.
    _request_processor_run()

    return InboxCaptureResponse(
        id=str(row["id"]),
        status=str(row.get("status") or "pending"),
        source=str(row.get("source") or "brain_dump"),
        text=str(row.get("text") or request.text),
        clean_text=row.get("clean_text"),
        due_date=(
            str(row["due_date"])
            if row.get("due_date") is not None
            else None
        ),
        project_hint=row.get("project_hint"),
        is_urgent=bool(row.get("is_urgent", False)),
        is_important=bool(row.get("is_important", False)),
        is_just_do_it=bool(row.get("is_just_do_it", False)),
    )


@app.get(
    "/reviews",
    response_model=list[ReviewResponse],
    tags=["reviews"],
)
def list_reviews() -> list[ReviewResponse]:
    reviews = _review_service().list_pending_reviews()

    return [
        ReviewResponse(**review.to_dict())
        for review in reviews
    ]


@app.get(
    "/reviews/notices/recent",
    tags=["reviews"],
)
def list_recent_review_notices() -> dict:
    notices = (
        _review_service()
        .list_recent_auto_merge_notices(
            limit=10,
        )
    )

    return {
        "notices": notices,
    }


@app.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def get_review(
    review_id: str,
) -> ReviewResponse:
    review = _review_service().get_review(review_id)

    if review is None:
        raise HTTPException(
            status_code=404,
            detail="Review not found",
        )

    return ReviewResponse(**review.to_dict())




AIOS_WEB_DASHBOARD_TODAY_VERSION = "v1.2-today-includes-overdue"
AIOS_WEB_DASHBOARD_POPULATION_VERSION = "v1.3-full-open-population"

AIOS_TASK_DETAIL_EDIT_VERSION = "task-detail-edit-v1"

@app.get("/tasks", tags=["tasks"])
def list_open_tasks_http(
    limit: int = 100,
    search: str = "",
) -> dict:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    # Retained for backward-compatible requests from the current web client.
    # Section sizes are governed below; source population is not truncated.
    _requested_limit = max(1, min(int(limit), 200))
    clean_search = (search or "").strip()

    query = (
        _store().client.table("tasks")
        .select(
            "id,title,status,due_at,project_id,importance,"
            "is_quick_win,is_just_do_it,created_at,updated_at"
        )
        .eq("is_open", True)
        .eq("is_done", False)
        .eq("is_archived", False)
    )

    if clean_search:
        query = query.ilike("title", f"%{clean_search}%")

    # Build dashboard sections from the complete open-task population.
    # Do not truncate candidates before section selection.
    rows = query.execute().data or []

    task_ids = [row.get("id") for row in rows if row.get("id")]
    state_by_task = {}

    if task_ids:
        state_rows = (
            _store().client.table("task_execution_state")
            .select(
                "task_id,execution_score,execution_rank,"
                "best_next_action,surfaced_quick_win"
            )
            .in_("task_id", task_ids)
            .execute()
            .data
            or []
        )
        state_by_task = {
            row.get("task_id"): row
            for row in state_rows
            if row.get("task_id")
        }

    for row in rows:
        state = state_by_task.get(row.get("id"), {})
        row["execution_score"] = state.get("execution_score")
        row["execution_rank"] = state.get("execution_rank")
        row["best_next_action"] = bool(
            state.get("best_next_action", False)
        )
        row["surfaced_quick_win"] = bool(
            state.get("surfaced_quick_win", False)
        )

    def score_key(row: dict):
        score = row.get("execution_score")
        rank = row.get("execution_rank")
        return (
            score is None,
            -(float(score) if score is not None else 0.0),
            rank is None,
            int(rank) if rank is not None else 999999,
            (row.get("title") or "").lower(),
        )

    importance_order = {
        "High Importance": 0,
        "Medium Importance": 1,
        "Low Importance": 2,
    }

    def quick_win_key(row: dict):
        return (
            importance_order.get(row.get("importance"), 99),
            *score_key(row),
        )

    toronto = ZoneInfo("America/Toronto")
    today = datetime.now(toronto).date()

    def due_today(row: dict) -> bool:
        raw = row.get("due_at")
        if not raw:
            return False
        try:
            dt = datetime.fromisoformat(
                str(raw).replace("Z", "+00:00")
            )
            if dt.tzinfo is None:
                return dt.date() <= today
            return dt.astimezone(toronto).date() <= today
        except (TypeError, ValueError):
            return str(raw)[:10] <= today.isoformat()

    used: set[str] = set()

    def take(candidates: list[dict], count: int | None = None):
        selected = []
        for row in candidates:
            task_id = row.get("id")
            if not task_id or task_id in used:
                continue
            selected.append(row)
            used.add(task_id)
            if count is not None and len(selected) >= count:
                break
        return selected

    top5 = take(sorted(rows, key=score_key), 5)

    quick_wins = take(
        sorted(
            [row for row in rows if bool(row.get("is_quick_win"))],
            key=quick_win_key,
        ),
        5,
    )

    today_items = take(
        sorted(
            [row for row in rows if due_today(row)],
            key=score_key,
        )
    )

    jdi_items = take(
        sorted(
            [row for row in rows if bool(row.get("is_just_do_it"))],
            key=score_key,
        )
    )

    return {
        "count": len(rows),
        "today": today.isoformat(),
        "precedence": [
            "top5",
            "quick_wins",
            "today",
            "just_do_it",
        ],
        "sections": {
            "top5": top5,
            "quick_wins": quick_wins,
            "today": today_items,
            "just_do_it": jdi_items,
        },
    }


@app.post("/tasks/{task_id}/complete", tags=["tasks"])
def complete_task_http(task_id: str) -> dict:
    store = _store()
    rows = (
        store.client.table("tasks")
        .select("id,is_archived")
        .eq("id", task_id)
        .limit(1)
        .execute().data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    if rows[0].get("is_archived"):
        raise HTTPException(status_code=409, detail="Task is archived")

    completed_at = datetime.now(timezone.utc).isoformat()
    (
        store.client.table("tasks")
        .update({
            "is_done": True,
            "is_open": False,
            "completed_at": completed_at,
            "updated_at": completed_at,
        })
        .eq("id", task_id)
        .execute()
    )

    completed_activation_children = complete_open_focus_activation_children(
        store,
        task_id,
        completed_at=completed_at,
    )

    try:
        _request_processor_run()
    except Exception:
        pass
    return {
        "id": task_id,
        "completed": True,
        "completed_activation_children": completed_activation_children,
    }


@app.post("/tasks/{task_id}/not-now", tags=["tasks"])
def not_now_task_http(task_id: str) -> dict:
    try:
        task = mark_focus_activation_not_now(
            _store(),
            task_id,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    try:
        _request_processor_run()
    except Exception:
        pass

    return {
        "id": task_id,
        "not_now": True,
        "task": task,
    }


@app.post("/tasks/{task_id}/delete", tags=["tasks"])
def delete_task_http(task_id: str) -> dict:
    rows=(_store().client.table("tasks").select("id").eq("id",task_id).limit(1).execute().data or [])
    if not rows: raise HTTPException(status_code=404, detail="Task not found")
    (_store().client.table("tasks").update({"is_archived":True,"is_open":False}).eq("id",task_id).execute())
    try: _request_processor_run()
    except Exception: pass
    return {"id":task_id,"deleted":True,"mode":"soft_archive"}



class ProjectOutcomeUpdate(BaseModel):
    outcome: str | None = None


class ProjectContextUpdate(BaseModel):
    context: str | None = None


class ProjectWorkAcceptRequest(BaseModel):
    title: str | None = None


class ProjectWorkRetryRequest(BaseModel):
    feedback: str


class TaskDetailUpdate(BaseModel):
    title: str | None = None
    due_at: str | None = None
    defer_until: str | None = None
    importance: str | None = None
    urgency: str | None = None
    effort: str | None = None
    duration: str | None = None
    is_just_do_it: bool | None = None


@app.get("/tasks/{task_id}", tags=["tasks"])
def get_task_detail_http(task_id: str) -> dict:
    rows = (
        _store().client.table("tasks")
        .select(
            "id,title,status,due_at,defer_until,importance,urgency,"
            "effort,duration,project_id,is_quick_win,is_just_do_it,"
            "is_open,is_done,is_archived,created_at,updated_at"
        )
        .eq("id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    task = dict(rows[0])

    state_rows = (
        _store().client.table("task_execution_state")
        .select(
            "execution_score,execution_rank,best_next_action,"
            "surfaced_quick_win,updated_at"
        )
        .eq("task_id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    state = state_rows[0] if state_rows else {}
    task["execution_score"] = state.get("execution_score")
    task["execution_rank"] = state.get("execution_rank")
    task["best_next_action"] = bool(state.get("best_next_action", False))
    task["surfaced_quick_win"] = bool(state.get("surfaced_quick_win", False))
    return {"task": task}


@app.patch("/tasks/{task_id}", tags=["tasks"])
def update_task_detail_http(task_id: str, update: TaskDetailUpdate) -> dict:
    rows = (
        _store().client.table("tasks")
        .select("id,is_done,is_archived")
        .eq("id", task_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    if rows[0].get("is_done") or rows[0].get("is_archived"):
        raise HTTPException(
            status_code=409,
            detail="Closed or archived tasks cannot be edited",
        )

    values = {}
    for field in (
        "title", "due_at", "defer_until", "importance",
        "urgency", "effort", "duration", "is_just_do_it",
    ):
        value = getattr(update, field)
        if value is not None:
            values[field] = value

    if "title" in values:
        values["title"] = str(values["title"]).strip()
        if not values["title"]:
            raise HTTPException(status_code=422, detail="Task title cannot be blank")

    for field in (
        "due_at", "defer_until", "importance",
        "urgency", "effort", "duration",
    ):
        if field in values and values[field] == "":
            values[field] = None

    if values:
        (
            _store().client.table("tasks")
            .update(values)
            .eq("id", task_id)
            .execute()
        )

    return get_task_detail_http(task_id)



AIOS_PROJECTS_WEB_VERSION = "projects-v1"


def _project_display_name(row: dict) -> str:
    for key in ("title", "name", "project_name"):
        value = row.get(key)
        if value:
            return str(value)
    return "Untitled Project"



def _project_review_reasons(
    project: dict,
    open_tasks: list[dict],
) -> list[str]:
    """Return conservative, read-only reasons a project needs review."""
    reasons: list[str] = []

    project_name = str(project.get("name") or "").strip()
    project_key = normalize(project_name)

    status = str(project.get("status") or "").strip().lower()
    inactive_statuses = {
        "completed",
        "done",
        "archived",
        "paused",
        "someday",
    }

    inactive = (
        status in inactive_statuses
        or project.get("is_active") is False
    )

    unresolved_proxy_tasks = [
        task
        for task in open_tasks
        if project_key
        and normalize(str(task.get("title") or "")) == project_key
        and task.get("task_role") != "project_anchor"
    ]

    executable_tasks = [
        task
        for task in open_tasks
        if task.get("task_role") != "project_anchor"
        and task.get("generated_source") != "focus_activation"
        and not task.get("is_just_do_it")
    ]

    # Someday + inactive is the normal staging state for an emerged
    # project awaiting an explicit activation decision.
    awaiting_activation = (
        status == "someday"
        and project.get("is_active") is False
    )

    if inactive and open_tasks and not awaiting_activation:
        reasons.append("inactive_with_open_work")

    if unresolved_proxy_tasks:
        reasons.append("project_proxy_task")

    if open_tasks and not executable_tasks:
        reasons.append("no_executable_tasks")

    return reasons


@app.get("/projects", tags=["projects"])
def list_projects_http() -> dict:
    projects = (
        _store().client.table("projects")
        .select("*")
        .execute()
        .data
        or []
    )

    open_tasks = (
        _store().client.table("tasks")
        .select(
            "id,title,project_id,is_open,is_done,is_archived,"
            "is_just_do_it,parent_task_id,generated_source,task_role"
        )
        .eq("is_open", True)
        .eq("is_done", False)
        .eq("is_archived", False)
        .execute()
        .data
        or []
    )

    counts = {}
    tasks_by_project: dict[str, list[dict]] = {}

    projects_by_id = {
        str(project.get("id") or ""): project
        for project in projects
        if project.get("id")
    }

    projects_by_id = {
        str(project.get("id") or ""): project
        for project in projects
        if project.get("id")
    }

    for task in open_tasks:
        project_id = task.get("project_id")
        if not project_id:
            continue

        counts[project_id] = counts.get(project_id, 0) + 1
        tasks_by_project.setdefault(project_id, []).append(
            dict(task)
        )

    active = []
    for project in projects:
        project_id = project.get("id")
        open_count = counts.get(project_id, 0)

        # Active projects remain visible even when execution has run dry.
        # This is when Project Work may have proposals or a waiting state.
        if open_count <= 0 and not project.get("is_active"):
            continue

        review_reasons = _project_review_reasons(
            project,
            tasks_by_project.get(project_id, []),
        )

        possible_existing_project_id = (
            project.get("possible_existing_project_id")
        )

        possible_existing_project = (
            projects_by_id.get(
                str(possible_existing_project_id or "")
            )
            if possible_existing_project_id
            else None
        )

        active.append({
            "id": project_id,
            "name": _project_display_name(project),
            "status": project.get("status"),
            "is_active": bool(project.get("is_active", False)),
            "open_task_count": open_count,
            "review_needed": bool(review_reasons),
            "review_reasons": review_reasons,
            "possible_existing_project_id": (
                possible_existing_project_id
            ),
            "possible_existing_project_name": (
                _project_display_name(possible_existing_project)
                if possible_existing_project
                else None
            ),
            "possible_existing_project_confidence": (
                project.get(
                    "possible_existing_project_confidence"
                )
            ),
        })

    active.sort(
        key=lambda row: (
            -int(row.get("open_task_count") or 0),
            str(row.get("name") or "").lower(),
        )
    )

    return {"count": len(active), "projects": active}




@app.post(
    "/projects/{project_id}/use-existing-project",
    tags=["projects"],
)
def use_existing_project_http(project_id: str) -> dict:
    store = _store()

    rows = (
        store.client
        .table("projects")
        .select(
            "id,name,status,is_active,"
            "possible_existing_project_id"
        )
        .eq("id", project_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Suggested project not found",
        )

    source_project = dict(rows[0])

    target_id = str(
        source_project.get("possible_existing_project_id")
        or ""
    ).strip()

    if not target_id:
        raise HTTPException(
            status_code=409,
            detail="No possible existing project is recorded",
        )

    target_rows = (
        store.client
        .table("projects")
        .select("id,name,status,is_active")
        .eq("id", target_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not target_rows:
        raise HTTPException(
            status_code=409,
            detail="Possible existing project no longer exists",
        )

    target = dict(target_rows[0])

    if not target.get("is_active"):
        raise HTTPException(
            status_code=409,
            detail="Possible existing project is no longer active",
        )

    target_name = str(target.get("name") or "").strip()

    task_rows = (
        store.client
        .table("tasks")
        .select("id,title,project_id")
        .eq("project_id", project_id)
        .execute()
        .data
        or []
    )

    moved = 0

    for task in task_rows:
        response = (
            store.client
            .table("tasks")
            .update({
                "project_id": target_id,
                "suggested_project": target_name,
            })
            .eq("id", task["id"])
            .eq("project_id", project_id)
            .execute()
        )

        if response.data or []:
            moved += 1

    (
        store.client
        .table("projects")
        .update({
            "status": "Archived",
            "is_active": False,
            "possible_existing_project_id": None,
            "possible_existing_project_confidence": None,
        })
        .eq("id", project_id)
        .execute()
    )

    return {
        "merged": True,
        "moved_tasks": moved,
        "target_project_id": target_id,
        "target_project_name": target_name,
    }


@app.post(
    "/projects/{project_id}/keep-separate",
    tags=["projects"],
)
def keep_project_separate_http(project_id: str) -> dict:
    response = (
        _store().client
        .table("projects")
        .update({
            "possible_existing_project_id": None,
            "possible_existing_project_confidence": None,
        })
        .eq("id", project_id)
        .execute()
    )

    if not (response.data or []):
        raise HTTPException(
            status_code=404,
            detail="Suggested project not found",
        )

    return {
        "kept_separate": True,
        "project": dict(response.data[0]),
    }


@app.post("/projects/{project_id}/activate", tags=["projects"])
def activate_project_http(project_id: str) -> dict:
    try:
        project = get_project_lifecycle_writer().update(
            project_ref_id=project_id,
            status="Active",
            is_active=True,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "project": project,
        "activated": True,
    }



@app.patch("/projects/{project_id}/outcome", tags=["projects"])
def update_project_outcome_http(
    project_id: str,
    update: ProjectOutcomeUpdate,
) -> dict:
    rows = (
        _store().client
        .table("projects")
        .select("id,name,outcome")
        .eq("id", project_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    outcome = str(update.outcome or "").strip() or None

    response = (
        _store().client
        .table("projects")
        .update({
            "outcome": outcome,
        })
        .eq("id", project_id)
        .execute()
    )

    updated = response.data or []

    if not updated:
        raise HTTPException(
            status_code=500,
            detail="Project outcome update returned no row",
        )

    return {
        "project": dict(updated[0]),
        "updated": True,
    }


@app.patch("/projects/{project_id}/context", tags=["projects"])
def update_project_context_http(
    project_id: str,
    update: ProjectContextUpdate,
) -> dict:
    rows = (
        _store().client
        .table("projects")
        .select("id,name,context")
        .eq("id", project_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    context = str(update.context or "").strip() or None

    response = (
        _store().client
        .table("projects")
        .update({
            "context": context,
        })
        .eq("id", project_id)
        .execute()
    )

    updated = response.data or []

    if not updated:
        raise HTTPException(
            status_code=500,
            detail="Project context update returned no row",
        )

    return {
        "project": dict(updated[0]),
        "updated": True,
    }



@app.post(
    "/projects/{project_id}/work-proposals/{proposal_id}/dismiss",
    tags=["projects"],
)
def dismiss_project_work_http(
    project_id: str,
    proposal_id: str,
) -> dict:
    try:
        proposal = dismiss_project_work_proposal(
            _store(),
            proposal_id,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    if str(proposal.get("project_id") or "") != project_id:
        raise HTTPException(
            status_code=409,
            detail="Proposal does not belong to this project",
        )

    return {
        "dismissed": True,
        "proposal": proposal,
    }


@app.post(
    "/projects/{project_id}/work-proposals/{proposal_id}/accept",
    tags=["projects"],
)
def accept_project_work_http(
    project_id: str,
    proposal_id: str,
    request: ProjectWorkAcceptRequest | None = None,
) -> dict:
    store = _store()

    rows = (
        store.client
        .table("project_work_proposals")
        .select("id,project_id,title,status")
        .eq("id", proposal_id)
        .eq("status", "proposed")
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Project-work proposal not found",
        )

    proposal = dict(rows[0])

    if str(proposal.get("project_id") or "") != project_id:
        raise HTTPException(
            status_code=409,
            detail="Proposal does not belong to this project",
        )

    accepted_title = str(
        request.title
        if request and request.title is not None
        else proposal.get("title") or ""
    ).strip()

    if not accepted_title:
        raise HTTPException(
            status_code=400,
            detail="Project task title is required",
        )

    task = create_supabase_project_task(
        store,
        title=accepted_title,
        project_id=project_id,
    )

    try:
        accepted = accept_project_work_proposal(
            store,
            proposal_id,
        )
    except Exception as exc:
        # Do not silently report success if proposal state failed to advance.
        # The task already exists, so surface the inconsistency for repair.
        raise HTTPException(
            status_code=500,
            detail=(
                "Task was created but proposal could not be marked accepted: "
                f"{exc}"
            ),
        ) from exc

    try:
        _request_processor_run()
    except Exception:
        pass

    return {
        "accepted": True,
        "proposal": accepted,
        "task": task,
    }



@app.post(
    "/projects/{project_id}/work-proposals/{proposal_id}/retry",
    tags=["projects"],
)
def retry_project_work_http(
    project_id: str,
    proposal_id: str,
    request: ProjectWorkRetryRequest,
) -> dict:
    store = _store()

    rows = (
        store.client
        .table("project_work_proposals")
        .select("id,project_id,title,status")
        .eq("id", proposal_id)
        .eq("status", "proposed")
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Project-work proposal not found",
        )

    proposal = dict(rows[0])

    if str(proposal.get("project_id") or "") != project_id:
        raise HTTPException(
            status_code=409,
            detail="Proposal does not belong to this project",
        )

    try:
        rejected = retry_project_work_proposal(
            store,
            proposal_id,
            feedback=request.feedback,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    try:
        _request_processor_run()
    except Exception:
        pass

    return {
        "retry_requested": True,
        "proposal": rejected,
    }


@app.get("/projects/{project_id}", tags=["projects"])
def get_project_detail_http(project_id: str) -> dict:
    project_rows = (
        _store().client.table("projects")
        .select("*")
        .eq("id", project_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not project_rows:
        raise HTTPException(status_code=404, detail="Project not found")

    project_row = project_rows[0]

    tasks = (
        _store().client.table("tasks")
        .select(
            "id,title,due_at,importance,is_quick_win,is_just_do_it,"
            "is_open,is_done,is_archived"
        )
        .eq("project_id", project_id)
        .eq("is_open", True)
        .eq("is_done", False)
        .eq("is_archived", False)
        .execute()
        .data
        or []
    )

    task_ids = [row.get("id") for row in tasks if row.get("id")]
    state_by_task = {}

    if task_ids:
        states = (
            _store().client.table("task_execution_state")
            .select(
                "task_id,execution_score,execution_rank,"
                "best_next_action,surfaced_quick_win"
            )
            .in_("task_id", task_ids)
            .execute()
            .data
            or []
        )
        state_by_task = {
            row.get("task_id"): row
            for row in states
            if row.get("task_id")
        }

    for task in tasks:
        state = state_by_task.get(task.get("id"), {})
        task["execution_score"] = state.get("execution_score")
        task["execution_rank"] = state.get("execution_rank")
        task["best_next_action"] = bool(state.get("best_next_action", False))
        task["surfaced_quick_win"] = bool(state.get("surfaced_quick_win", False))

    def sort_key(task: dict):
        rank = task.get("execution_rank")
        score = task.get("execution_score")
        return (
            rank is None,
            int(rank) if rank is not None else 999999,
            score is None,
            -(float(score) if score is not None else 0.0),
            str(task.get("title") or "").lower(),
        )

    tasks.sort(key=sort_key)

    proposals = (
        _store().client
        .table("project_work_proposals")
        .select(
            "id,project_id,title,status,"
            "created_at,updated_at,accepted_at,dismissed_at"
        )
        .eq("project_id", project_id)
        .eq("status", "proposed")
        .order("created_at")
        .execute()
        .data
        or []
    )

    return {
        "project": {
            "id": project_row.get("id"),
            "name": _project_display_name(project_row),
            "status": project_row.get("status"),
            "outcome": project_row.get("outcome"),
            "context": project_row.get("context"),
            "open_task_count": len(tasks),
        },
        "tasks": tasks,
        "work_proposals": [
            dict(row)
            for row in proposals
        ],
    }



AIOS_WEB_CREATE_TASK_VERSION = "create-task-v1"


class CreateTaskRequest(BaseModel):
    title: str
    due_at: str | None = None
    defer_until: str | None = None
    importance: str | None = None
    urgency: str | None = None
    effort: str | None = None
    duration: str | None = None
    is_just_do_it: bool = False
    project_id: str | None = None


@app.post("/tasks", tags=["tasks"], status_code=201)
def create_task_http(request: CreateTaskRequest) -> dict:
    title = str(request.title or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="Task title cannot be blank")

    values = {
        "title": title,
        "is_open": True,
        "is_done": False,
        "is_archived": False,
        "is_just_do_it": bool(request.is_just_do_it),
    }

    for field in (
        "due_at",
        "defer_until",
        "importance",
        "urgency",
        "effort",
        "duration",
        "project_id",
    ):
        value = getattr(request, field)
        if value not in (None, ""):
            values[field] = value

    result = (
        _store().client.table("tasks")
        .insert(values)
        .execute()
    )

    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=500, detail="Task could not be created")

    task = dict(rows[0])

    try:
        _request_processor_run()
    except Exception as exc:
        print(
            "[Task Create] Task created; processor trigger failed:",
            exc,
        )

    return {"task": task}


AIOS_DASHBOARD_FOCUS_API_VERSION = "dashboard-focus-v1"


@app.get("/focus", tags=["tasks"])
def get_dashboard_focus_http() -> dict:
    states = (_store().client.table("task_execution_state")
        .select("task_id,execution_score,execution_rank,best_next_action")
        .not_.is_("execution_rank", "null")
        .order("execution_rank")
        .limit(1).execute().data or [])
    if not states:
        return {"focus": None}
    state = dict(states[0])
    task_id = state.get("task_id")
    tasks = (_store().client.table("tasks")
        .select("id,title,status,due_at,defer_until,importance,urgency,effort,duration,project_id,is_quick_win,is_just_do_it,is_open,is_done,is_archived")
        .eq("id", task_id).eq("is_open", True).eq("is_done", False).eq("is_archived", False)
        .limit(1).execute().data or [])
    if not tasks:
        return {"focus": None}
    task = dict(tasks[0])
    task["execution_score"] = state.get("execution_score")
    task["execution_rank"] = state.get("execution_rank")
    task["best_next_action"] = bool(state.get("best_next_action", False))
    try:
        guidance_rows = (_store().client.table("task_focus_guidance")
            .select("starter_step,starter_minutes,source,updated_at")
            .eq("task_id", task_id).limit(1).execute().data or [])
    except Exception:
        guidance_rows = []
    guidance = dict(guidance_rows[0]) if guidance_rows else {}
    task["starter_step"] = guidance.get("starter_step")
    task["starter_minutes"] = guidance.get("starter_minutes")
    task["guidance_source"] = guidance.get("source")

    try:
        activation = get_active_focus_activation(
            _store(),
            task_id,
        )
        task["activation"] = activation

        if activation:
            task["activation_pending"] = False
        else:
            activation_history = list_focus_activation_children(
                _store(),
                task_id,
            )
            task["activation_pending"] = bool(
                activation_history
            )
    except Exception:
        task["activation"] = None
        task["activation_pending"] = False

    return {"focus": task}


@app.post(
    "/processing/request",
    status_code=202,
    tags=["processing"],
)
def request_processing_http() -> dict:
    # Request an AIOS processor run through the canonical coordinator.
    result = _request_processor_run()

    if result.get("status") == "disabled":
        raise HTTPException(
            status_code=503,
            detail="Processor triggering is disabled",
        )

    if result.get("status") == "failed":
        raise HTTPException(
            status_code=503,
            detail="Processor trigger failed; processing remains requested",
        )

    return {
        "accepted": True,
        **result,
    }

def _review_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        return HTTPException(status_code=404, detail=str(exc).strip("'"))
    return HTTPException(status_code=409, detail=str(exc))

def _mark_review_inbox_processed(review: ReviewResponse) -> None:
    if not review.inbox_item_id:
        return

    repo = _inbox_repository()

    review_row = repo.get_row(review.inbox_item_id)

    repo.mark_processed(review.inbox_item_id)

    if not review_row:
        return

    source_metadata = review_row.get("source_metadata") or {}

    if not bool(source_metadata.get("shadow")):
        return

    original_inbox_id = str(
        review_row.get("source_item_id") or ""
    ).strip()

    if not original_inbox_id:
        return

    if original_inbox_id == review.inbox_item_id:
        return

    original_row = repo.get_row(original_inbox_id)

    if original_row is None:
        return

    repo.mark_processed(original_inbox_id)

@app.post(
    "/reviews/{review_id}/possible-duplicate/reevaluate",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def request_possible_duplicate_reevaluation_http(
    review_id: str,
) -> ReviewResponse:
    try:
        updated = (
            _review_service()
            .request_possible_duplicate_reevaluation(
                review_id
            )
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc

    try:
        _request_processor_run()
    except Exception as exc:
        print(
            "[Possible Duplicate] "
            "Re-evaluation requested; processor trigger failed:",
            exc,
        )

    return ReviewResponse(**updated.to_dict())


@app.post(
    "/reviews/{review_id}/possible-duplicate/create-new",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def request_possible_duplicate_create_new_http(
    review_id: str,
) -> ReviewResponse:
    try:
        updated = (
            _review_service()
            .request_possible_duplicate_create_anyway(
                review_id
            )
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc

    try:
        _request_processor_run()
    except Exception as exc:
        print(
            "[Possible Duplicate] "
            "Create-new requested; processor trigger failed:",
            exc,
        )

    return ReviewResponse(**updated.to_dict())


@app.post(
    "/reviews/{review_id}/possible-duplicate",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def resolve_possible_duplicate_http(
    review_id: str,
    request: PossibleDuplicateResolutionRequest,
) -> ReviewResponse:
    if request.action not in {"link_existing", "create_anyway", "ignore"}:
        raise HTTPException(
            status_code=422,
            detail="Unsupported possible duplicate action",
        )

    if request.title_choice not in {None, "existing", "new"}:
        raise HTTPException(
            status_code=422,
            detail="Unsupported duplicate title choice",
        )

    if (
        request.action != "link_existing"
        and request.title_choice is not None
    ):
        raise HTTPException(
            status_code=422,
            detail="title_choice is only valid for link_existing",
        )

    candidate_task_title = request.candidate_task_title

    if request.action == "link_existing":
        candidate_task_id = str(
            request.candidate_task_id or ""
        ).strip()

        if not candidate_task_id:
            raise HTTPException(
                status_code=422,
                detail="candidate_task_id is required for link_existing",
            )

        task_rows = (
            _store().client
            .table("tasks")
            .select("id,title,is_done,is_archived")
            .eq("id", candidate_task_id)
            .limit(1)
            .execute()
            .data
            or []
        )

        if not task_rows:
            raise HTTPException(
                status_code=404,
                detail="Candidate task not found",
            )

        task_row = task_rows[0]

        if task_row.get("is_done") or task_row.get("is_archived"):
            raise HTTPException(
                status_code=409,
                detail="Closed or archived candidate task cannot be merged",
            )

        title_choice = request.title_choice or "existing"

        if title_choice == "new":
            review = _review_service().get_review(
                review_id
            )

            if review is None:
                raise HTTPException(
                    status_code=404,
                    detail="Review not found",
                )

            new_title = str(
                review.subject_text or ""
            ).strip()

            if not new_title:
                raise HTTPException(
                    status_code=409,
                    detail="New task wording is unavailable",
                )

            (
                _store().client
                .table("tasks")
                .update({"title": new_title})
                .eq("id", candidate_task_id)
                .execute()
            )

            candidate_task_title = new_title

        else:
            candidate_task_title = str(
                task_row.get("title") or ""
            ).strip()

    try:
        resolved = _review_service().resolve_possible_duplicate(
            review_id,
            action=request.action,
            candidate_task_id=request.candidate_task_id,
            candidate_task_title=candidate_task_title,
            created_task_ids=request.created_task_ids or None,
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc

    response = ReviewResponse(**resolved.to_dict())
    _mark_review_inbox_processed(response)
    return response

@app.post(
    "/reviews/{review_id}/clarification/delete-task",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def clarification_delete_task_http(
    review_id: str,
) -> ReviewResponse:
    try:
        resolved = (
            _review_service()
            .delete_review_task(
                review_id
            )
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc

    response = ReviewResponse(
        **resolved.to_dict()
    )
    _mark_review_inbox_processed(
        response
    )
    return response


@app.post(
    "/reviews/{review_id}/clarification/request-question",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def clarification_request_question_http(
    review_id: str,
) -> ReviewResponse:
    try:
        updated = (
            _review_service()
            .request_clarification_question(
                review_id
            )
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc

    try:
        _request_processor_run()
    except Exception as exc:
        print(
            "[Clarification] "
            "Question requested; processor trigger failed:",
            exc,
        )

    return ReviewResponse(**updated.to_dict())


@app.post(
    "/reviews/{review_id}/clarification/answer",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def clarification_answer_http(
    review_id: str,
    request: ClarificationAnswerRequest,
) -> ReviewResponse:
    try:
        updated = (
            _review_service()
            .submit_clarification_answer(
                review_id,
                answer=request.answer,
            )
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc

    try:
        _request_processor_run()
    except Exception as exc:
        print(
            "[Clarification] "
            "Answer submitted; processor trigger failed:",
            exc,
        )

    return ReviewResponse(**updated.to_dict())


@app.post(
    "/reviews/{review_id}/clarification/awaiting-answer",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def clarification_awaiting_answer_http(
    review_id: str,
    request: ClarificationAwaitingAnswerRequest,
) -> ReviewResponse:
    try:
        updated = _review_service().mark_clarification_awaiting_answer(
            review_id,
            question=request.question,
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc
    return ReviewResponse(**updated.to_dict())

@app.post(
    "/reviews/{review_id}/clarification/pending-confirmation",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def clarification_pending_confirmation_http(
    review_id: str,
    request: ClarificationPendingConfirmationRequest,
) -> ReviewResponse:
    try:
        updated = _review_service().mark_clarification_pending_confirmation(
            review_id,
            answer=request.answer,
            proposed_text=request.proposed_text,
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc
    return ReviewResponse(**updated.to_dict())

@app.post(
    "/reviews/{review_id}/clarification/resolve",
    response_model=ReviewResponse,
    tags=["reviews"],
)
def clarification_resolve_http(
    review_id: str,
    request: ClarificationResolutionRequest,
) -> ReviewResponse:
    try:
        resolved = _review_service().resolve_clarification(
            review_id,
            selected_text=request.selected_text,
            accepted_text=request.accepted_text,
        )
    except (KeyError, ValueError) as exc:
        raise _review_error(exc) from exc

    response = ReviewResponse(**resolved.to_dict())
    _mark_review_inbox_processed(response)
    return response
