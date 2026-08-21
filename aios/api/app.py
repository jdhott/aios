from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel
from aios.focus_activation import (
    FOCUS_ACTIVATION_SOURCE,
    complete_open_focus_activation_children,
    get_active_focus_activation,
    list_focus_activation_children,
    mark_focus_activation_not_now,
)
from aios.focus_activation_refresh import (
    FOCUS_ACTIVATION_REFRESH_VERSION,
    get_openai_client,
    refresh_focus_activation_for_parent,
)
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import os
import time

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
from aios.work_patterns import delete_work_pattern, duplicate_work_pattern, get_work_pattern, instantiate_pattern_for_project, list_work_patterns, save_work_pattern
from aios.storage.task_creation_writer import (
    create_supabase_children_for_existing_parent,
    edit_supabase_children_for_existing_parent,
)
from aios.project_work_proposals import (
    accept_project_work_proposal,
    dismiss_project_work_proposal,
    retry_project_work_proposal,
)
from aios.storage.project_lifecycle_writer import get_project_lifecycle_writer
from aios.text_utils import normalize
from aios.workspace import default_workspace_id
from aios.temporal import (
    is_future_task_datetime,
    local_now,
    local_timezone,
    serialize_task_datetime,
)
from aios.daily_completion_summary import completion_fingerprint
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
AIOS_FOCUS_ACTIVATION_REFRESH_VERSION = FOCUS_ACTIVATION_REFRESH_VERSION
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

def _completion_processor_delay_seconds() -> int:
    return int(os.getenv("AIOS_COMPLETION_PROCESSOR_DELAY_SECONDS", "5"))


def _refresh_focus_activation_after_action(
    parent_task_id: str,
    *,
    delay_seconds: int = 0,
    verify_task_id: str | None = None,
    verify_completed_at: str | None = None,
) -> None:
    """Generate the next Start Here step without waiting for a full processor run."""
    time.sleep(max(0, int(delay_seconds)))

    parent_id = str(parent_task_id or "").strip()
    if not parent_id:
        return

    try:
        store = _store()

        if verify_task_id and verify_completed_at:
            rows = (
                store.client.table("tasks")
                .select("id,is_done,is_open,completed_at,generated_source,parent_task_id")
                .eq("id", verify_task_id)
                .limit(1)
                .execute()
                .data
                or []
            )
            if not rows:
                return
            current = dict(rows[0])
            if (
                current.get("generated_source") != FOCUS_ACTIVATION_SOURCE
                or not current.get("is_done")
                or current.get("is_open")
                or str(current.get("completed_at") or "") != str(verify_completed_at)
                or str(current.get("parent_task_id") or "") != parent_id
            ):
                return

        client = get_openai_client()
        if client is None:
            print(
                "[Focus Activation Refresh] OPENAI_API_KEY not configured; "
                "falling back to processor."
            )
            _request_processor_run()
            return

        child = refresh_focus_activation_for_parent(
            store,
            client,
            parent_id,
        )
        if child:
            print(
                "[Focus Activation Refresh] Created or reused Start Here "
                f"{child.get('id')} for parent {parent_id}."
            )
        else:
            print(
                "[Focus Activation Refresh] No Start Here generated for "
                f"parent {parent_id}; processor may retry."
            )
            _request_processor_run()
    except Exception as exc:
        print(f"[Focus Activation Refresh] Fast refresh failed: {exc}")


def _request_processor_run_after_completion(
    task_id: str,
    completed_at: str,
    *,
    delay_seconds: int | None = None,
) -> None:
    """Debounce expensive reconciliation after an optimistic completion."""
    if delay_seconds is None:
        delay_seconds = _completion_processor_delay_seconds()
    time.sleep(max(0, int(delay_seconds)))
    try:
        rows = (
            _store().client.table("tasks")
            .select("id,is_done,is_open,completed_at")
            .eq("id", task_id)
            .limit(1)
            .execute().data or []
        )
        if not rows:
            return
        current = rows[0]
        if (
            current.get("is_done")
            and not current.get("is_open")
            and str(current.get("completed_at") or "") == str(completed_at)
        ):
            _request_processor_run()
    except Exception as exc:
        print(f"[Optimistic Complete] Deferred processor trigger failed: {exc}")

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
            "capture_interface": request.capture_interface or "cloud_run_api_v1",
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




def _is_future_defer_value(
    value: str | None,
    *,
    now: datetime | None = None,
    timezone_name: str = "America/Toronto",
) -> bool:
    try:
        return is_future_task_datetime(
            value,
            now=now,
            timezone_name=timezone_name,
        )
    except (TypeError, ValueError):
        return False


AIOS_WEB_DASHBOARD_TODAY_VERSION = "v1.3-today-importance-due-sort"
AIOS_WEB_DASHBOARD_POPULATION_VERSION = "v1.4-dashboard-semantics"

AIOS_TASK_DETAIL_EDIT_VERSION = "task-detail-edit-v1"


def _respect_breakdown_step_order(items: list[dict], *, skip_if_project_ordered: bool = False) -> list[dict]:
    """Keep each sibling breakdown together and ordered by step_order.

    The caller supplies items in the section's primary order (rank, due date,
    search title, etc.).  A sibling group is emitted at the position of its
    first member, preserving the section's broader semantics while respecting
    the local breakdown sequence.  Explicit project_order remains stronger
    than step_order when requested by the project-detail caller.
    """
    if len(items) < 2:
        return list(items)

    groups: dict[str, list[dict]] = {}
    for item in items:
        parent_id = str(item.get("parent_task_id") or "").strip()
        if parent_id:
            groups.setdefault(parent_id, []).append(item)

    ordered_groups: dict[str, list[dict]] = {}
    for parent_id, siblings in groups.items():
        if len(siblings) < 2:
            continue
        if skip_if_project_ordered and any(s.get("project_order") is not None for s in siblings):
            continue
        ordered_groups[parent_id] = sorted(
            siblings,
            key=lambda row: (
                row.get("step_order") is None,
                int(row.get("step_order")) if row.get("step_order") is not None else 999999,
                str(row.get("title") or "").lower(),
            ),
        )

    if not ordered_groups:
        return list(items)

    result: list[dict] = []
    emitted: set[str] = set()
    for item in items:
        parent_id = str(item.get("parent_task_id") or "").strip()
        sibling_group = ordered_groups.get(parent_id)
        if sibling_group is None:
            result.append(item)
            continue
        if parent_id in emitted:
            continue
        result.extend(sibling_group)
        emitted.add(parent_id)
    return result

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
            "id,title,status,due_at,defer_until,project_id,importance,parent_task_id,step_order,"
            "is_quick_win,is_just_do_it,created_at,updated_at,generated_source,task_role"
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

    # START HERE/focus-activation rows are implementation helpers for the
    # focus card, not independent work items. They must not leak into Today,
    # JDI, Quick Wins, Top 5, or general search results.
    rows = [
        row for row in rows
        if row.get("generated_source") != "focus_activation"
        and row.get("task_role") != "focus_activation"
    ]

    task_ids = [row.get("id") for row in rows if row.get("id")]

    # Child tasks lose important meaning when shown outside their hierarchy.
    # Enrich list payloads with the parent title for presentation only; the
    # child title itself remains unchanged.
    parent_ids = sorted({
        str(row.get("parent_task_id"))
        for row in rows
        if row.get("parent_task_id")
    })
    parent_title_by_id = {}
    if parent_ids:
        parent_rows = (
            _store().client.table("tasks")
            .select("id,title,due_at")
            .in_("id", parent_ids)
            .execute()
            .data
            or []
        )
        parent_meta_by_id = {
            str(parent.get("id")): {
                "title": str(parent.get("title") or "").strip(),
                "due_at": parent.get("due_at"),
            }
            for parent in parent_rows
            if parent.get("id")
        }
    else:
        parent_meta_by_id = {}

    for row in rows:
        parent_id = str(row.get("parent_task_id") or "").strip()
        if parent_id:
            parent_meta = parent_meta_by_id.get(parent_id) or {}
            row["parent_title"] = parent_meta.get("title") or None
            parent_due_at = parent_meta.get("due_at")
            if not row.get("due_at") and parent_due_at:
                row["effective_due_at"] = parent_due_at
                row["due_inherited_from_parent"] = True
            else:
                row["effective_due_at"] = row.get("due_at")
                row["due_inherited_from_parent"] = False
        else:
            row["effective_due_at"] = row.get("due_at")
            row["due_inherited_from_parent"] = False

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

    toronto = local_timezone()
    today = local_now().date()

    def due_today(row: dict) -> bool:
        raw = row.get("effective_due_at") or row.get("due_at")
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

    completed_today = []
    if not clean_search:
        # Completed Today is a progress view, not part of the actionable open-task
        # population. Use the user's local Toronto day boundaries and exclude
        # generated focus-activation helper children so the list reflects
        # meaningful user-facing accomplishments.
        local_start = datetime.combine(today, datetime.min.time(), tzinfo=toronto)
        local_end = local_start + timedelta(days=1)
        completed_rows = (
            _store().client.table("tasks")
            .select(
                "id,title,status,due_at,project_id,importance,parent_task_id,step_order,"
                "generated_source,task_role,completed_at"
            )
            .eq("is_done", True)
            .eq("is_archived", False)
            .gte("completed_at", local_start.astimezone(timezone.utc).isoformat())
            .lt("completed_at", local_end.astimezone(timezone.utc).isoformat())
            .order("completed_at", desc=True)
            .execute()
            .data
            or []
        )
        completed_today = [
            row for row in completed_rows
            if row.get("generated_source") != "focus_activation"
            and row.get("task_role") != "focus_activation"
        ]

        completed_parent_ids = sorted({
            str(row.get("parent_task_id"))
            for row in completed_today
            if row.get("parent_task_id")
        })
        if completed_parent_ids:
            completed_parent_rows = (
                _store().client.table("tasks")
                .select("id,title")
                .in_("id", completed_parent_ids)
                .execute()
                .data
                or []
            )
            completed_parent_titles = {
                str(parent.get("id")): str(parent.get("title") or "").strip()
                for parent in completed_parent_rows
                if parent.get("id")
            }
            for row in completed_today:
                parent_id = str(row.get("parent_task_id") or "").strip()
                if parent_id:
                    row["parent_title"] = completed_parent_titles.get(parent_id) or None

    # Search is a task lookup, not a dashboard-section filter. Return every
    # matching open task as one dedicated result set so ranking/section rules
    # cannot hide a valid title match.
    if clean_search:
        search_results = _respect_breakdown_step_order(sorted(
            rows,
            key=lambda row: (
                (row.get("title") or "").lower(),
                str(row.get("id") or ""),
            ),
        ))
        return {
            "count": len(search_results),
            "search": clean_search,
            "sections": {"search_results": search_results},
        }

    # Snoozed/deferred tasks remain searchable, but they should disappear from
    # the actionable dashboard lists until their defer window expires.
    actionable_rows = [
        row for row in rows
        if not _is_future_defer_value(row.get("defer_until"))
    ]

    # Dashboard sections are independent views, not mutually exclusive buckets.
    # Best Next Action (rank 1) is rendered separately by the focus card.
    # Top 5 means the next five ranked execution tasks: ranks 2 through 6.
    top5 = sorted(
        [
            row for row in actionable_rows
            if row.get("execution_rank") is not None
            and 2 <= int(row.get("execution_rank")) <= 6
        ],
        key=lambda row: int(row.get("execution_rank")),
    )

    # Today is a calendar view, not another ranking slice. Show every open
    # task due today or overdue, even when it also appears in another section.
    # Default order is user-facing priority first: Importance, then Due Date
    # ascending. Execution score remains only a deterministic tie-breaker.
    def today_sort_key(row: dict):
        raw_due = row.get("effective_due_at") or row.get("due_at")
        try:
            due_dt = datetime.fromisoformat(str(raw_due).replace("Z", "+00:00"))
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=toronto)
            else:
                due_dt = due_dt.astimezone(toronto)
            due_key = due_dt
        except (TypeError, ValueError):
            # due_today() already excludes missing due values. This fallback
            # keeps malformed legacy values stable without changing eligibility.
            due_key = datetime.max.replace(tzinfo=toronto)

        return (
            importance_order.get(row.get("importance"), 99),
            due_key,
            *score_key(row),
        )

    today_items = _respect_breakdown_step_order(sorted(
        [row for row in actionable_rows if due_today(row)],
        key=today_sort_key,
    ))

    # JDI is also an independent view: show every open JDI task even when it
    # appears in BNA, Top 5, or Today.
    jdi_items = _respect_breakdown_step_order(sorted(
        [row for row in actionable_rows if bool(row.get("is_just_do_it"))],
        key=score_key,
    ))

    # Quick Wins are the residual lightweight actions. They should never
    # duplicate a stronger dashboard signal: BNA, Top 5, Today, or JDI.
    stronger_ids = {str(row.get("id")) for row in top5 + today_items + jdi_items}
    quick_win_candidates = sorted(
        [
            row for row in actionable_rows
            if bool(row.get("is_quick_win"))
            and not bool(row.get("best_next_action"))
            and row.get("execution_rank") != 1
            and str(row.get("id")) not in stronger_ids
        ],
        key=quick_win_key,
    )
    quick_wins = _respect_breakdown_step_order(quick_win_candidates[:5])

    completed_today_summary = ""
    completed_today_summary_state = "empty"
    if len(completed_today) >= 2:
        completed_today_summary_state = "pending"
        try:
            fingerprint = completion_fingerprint(completed_today)
            summary_rows = (
                _store().client.table("daily_completion_summaries")
                .select("fingerprint,summary,completed_count")
                .eq("workspace_id", default_workspace_id())
                .eq("summary_date", today.isoformat())
                .limit(1)
                .execute().data
                or []
            )
            if summary_rows and str(summary_rows[0].get("fingerprint") or "") == fingerprint:
                completed_today_summary = str(summary_rows[0].get("summary") or "").strip()
                completed_today_summary_state = "ready" if completed_today_summary else "empty"
        except Exception as summary_exc:
            print(f"[Dashboard] Completed Today summary could not be loaded: {summary_exc}")

    return {
        "count": len(rows),
        "today": today.isoformat(),
        "completed_today_summary": completed_today_summary,
        "completed_today_summary_state": completed_today_summary_state,
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
            "completed_today": completed_today,
        },
    }


@app.post("/tasks/{task_id}/complete", tags=["tasks"])
def complete_task_http(task_id: str, background_tasks: BackgroundTasks) -> dict:
    store = _store()
    rows = (
        store.client.table("tasks")
        .select("id,is_archived,generated_source,parent_task_id")
        .eq("id", task_id)
        .limit(1)
        .execute().data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    if rows[0].get("is_archived"):
        raise HTTPException(status_code=409, detail="Task is archived")

    task = dict(rows[0])
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

    activation_parent_id = None
    if task.get("generated_source") == FOCUS_ACTIVATION_SOURCE:
        activation_parent_id = str(task.get("parent_task_id") or "").strip() or None

    if activation_parent_id:
        delay = _completion_processor_delay_seconds()
        background_tasks.add_task(
            _refresh_focus_activation_after_action,
            activation_parent_id,
            delay_seconds=delay,
            verify_task_id=task_id,
            verify_completed_at=completed_at,
        )

    background_tasks.add_task(
        _request_processor_run_after_completion,
        task_id,
        completed_at,
    )
    return {
        "id": task_id,
        "completed": True,
        "completed_at": completed_at,
        "completed_activation_children": completed_activation_children,
        "processor_deferred": True,
        "focus_activation_refresh_scheduled": bool(activation_parent_id),
    }


@app.post("/tasks/{task_id}/undo-complete", tags=["tasks"])
def undo_complete_task_http(task_id: str) -> dict:
    store = _store()
    rows = (
        store.client.table("tasks")
        .select("id,is_done,is_open,is_archived,completed_at")
        .eq("id", task_id)
        .limit(1)
        .execute().data or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    current = rows[0]
    if current.get("is_archived"):
        raise HTTPException(status_code=409, detail="Task is archived")

    completed_at = str(current.get("completed_at") or "").strip()
    if not current.get("is_done"):
        return {"id": task_id, "undone": True, "already_open": True}

    now = datetime.now(timezone.utc).isoformat()
    (
        store.client.table("tasks")
        .update({
            "is_done": False,
            "is_open": True,
            "completed_at": None,
            "updated_at": now,
        })
        .eq("id", task_id)
        .execute()
    )

    restored_activation_children = 0
    if completed_at:
        children = (
            store.client.table("tasks")
            .select("id")
            .eq("parent_task_id", task_id)
            .eq("generated_source", "focus_activation")
            .eq("is_done", True)
            .eq("is_open", False)
            .eq("completed_at", completed_at)
            .execute().data or []
        )
        for child in children:
            (
                store.client.table("tasks")
                .update({
                    "is_done": False,
                    "is_open": True,
                    "completed_at": None,
                    "updated_at": now,
                })
                .eq("id", child["id"])
                .execute()
            )
            restored_activation_children += 1

    return {
        "id": task_id,
        "undone": True,
        "restored_activation_children": restored_activation_children,
    }


@app.post("/tasks/{task_id}/not-now", tags=["tasks"])
def not_now_task_http(task_id: str, background_tasks: BackgroundTasks) -> dict:
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

    parent_id = str(task.get("parent_task_id") or "").strip()
    if parent_id:
        background_tasks.add_task(
            _refresh_focus_activation_after_action,
            parent_id,
        )

    return {
        "id": task_id,
        "not_now": True,
        "task": task,
        "focus_activation_refresh_scheduled": bool(parent_id),
    }


@app.post("/tasks/{task_id}/not-useful", tags=["tasks"])
def not_useful_task_http(task_id: str, background_tasks: BackgroundTasks) -> dict:
    store = _store()
    rows = (store.client.table("tasks").select("id,parent_task_id,generated_source,is_done,is_archived").eq("id", task_id).limit(1).execute().data or [])
    if not rows:
        raise HTTPException(status_code=404, detail="Starting step not found")
    task = rows[0]
    if task.get("generated_source") != "focus_activation" or task.get("is_done") or task.get("is_archived"):
        raise HTTPException(status_code=409, detail="Only an active Start Here step can be marked Not useful")
    parent_id = str(task.get("parent_task_id") or "").strip()
    if not parent_id:
        raise HTTPException(status_code=409, detail="Starting step has no parent task")
    now = datetime.now(timezone.utc).isoformat()
    # Keep the rejected Start Here open while coaching is active. This lets
    # the dashboard retain the exact suggestion the user said was not useful.
    store.client.table("tasks").update({
        "activation_disposition": "not_useful",
        "updated_at": now,
    }).eq("id", task_id).execute()
    store.client.table("tasks").update({
        "focus_context_help_state": "pending", "focus_context_draft": None,
        "focus_context_question": None, "focus_context_answer": None,
        "focus_context_help_updated_at": now, "updated_at": now,
    }).eq("id", parent_id).execute()
    background_tasks.add_task(_request_processor_run)
    return {"id": task_id, "not_useful": True, "parent_task_id": parent_id}


class TaskSnoozeRequest(BaseModel):
    preset: str
    custom_date: str | None = None


def _resolve_task_snooze_until(
    request: TaskSnoozeRequest,
    *,
    now: datetime | None = None,
) -> str:
    timezone_name = os.getenv("AIOS_LOCAL_TIMEZONE", "America/Toronto")
    local_tz = local_timezone(timezone_name)
    current = local_now(now=now, timezone_name=timezone_name)
    preset = str(request.preset or "").strip().lower()

    if preset == "one_hour":
        target = current + timedelta(hours=1)
        return serialize_task_datetime(target, timezone_name=timezone_name)

    if preset == "three_hours":
        target = current + timedelta(hours=3)
        return serialize_task_datetime(target, timezone_name=timezone_name)

    if preset == "tomorrow":
        target = datetime.combine(current.date() + timedelta(days=1), datetime.min.time(), tzinfo=local_tz)
        return serialize_task_datetime(target, timezone_name=timezone_name)
    if preset == "three_days":
        target = datetime.combine(current.date() + timedelta(days=3), datetime.min.time(), tzinfo=local_tz)
        return serialize_task_datetime(target, timezone_name=timezone_name)
    if preset == "one_week":
        target = datetime.combine(current.date() + timedelta(days=7), datetime.min.time(), tzinfo=local_tz)
        return serialize_task_datetime(target, timezone_name=timezone_name)
    if preset == "pick_date":
        custom = str(request.custom_date or "").strip()
        try:
            chosen = datetime.strptime(custom, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Choose a valid snooze date") from exc
        if chosen <= current.date():
            raise HTTPException(status_code=422, detail="Snooze date must be after today")
        target = datetime.combine(chosen, datetime.min.time(), tzinfo=local_tz)
        return serialize_task_datetime(target, timezone_name=timezone_name)

    raise HTTPException(status_code=422, detail="Unsupported snooze option")


@app.post("/tasks/{task_id}/snooze", tags=["tasks"])
def snooze_task_http(
    task_id: str,
    request: TaskSnoozeRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    store = _store()
    rows = (
        store.client.table("tasks")
        .select("id,is_open,is_done,is_archived,generated_source")
        .eq("id", task_id)
        .limit(1)
        .execute().data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")

    task = dict(rows[0])
    if task.get("is_done") or task.get("is_archived") or not task.get("is_open"):
        raise HTTPException(status_code=409, detail="Closed tasks cannot be snoozed")
    if task.get("generated_source") == "focus_activation":
        raise HTTPException(status_code=409, detail="Use the starting-step controls for this task")

    defer_until = _resolve_task_snooze_until(request)
    updated_at = datetime.now(timezone.utc).isoformat()
    result = (
        store.client.table("tasks")
        .update({"defer_until": defer_until, "updated_at": updated_at})
        .eq("id", task_id)
        .execute()
    )
    if not (result.data or []):
        raise HTTPException(status_code=500, detail="Task snooze could not be saved")

    background_tasks.add_task(_request_processor_run)
    return {"id": task_id, "snoozed": True, "defer_until": defer_until}


class FocusContextSaveRequest(BaseModel):
    context: str


class FocusContextAnswerRequest(BaseModel):
    answer: str


@app.post("/tasks/{task_id}/focus-context/help", tags=["tasks"])
def request_focus_context_help_http(task_id: str, background_tasks: BackgroundTasks) -> dict:
    rows = (_store().client.table("tasks").select("id,is_open,is_done,is_archived").eq("id", task_id).limit(1).execute().data or [])
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    task = rows[0]
    if not task.get("is_open") or task.get("is_done") or task.get("is_archived"):
        raise HTTPException(status_code=409, detail="Closed tasks cannot request context help")
    _store().client.table("tasks").update({
        "focus_context_help_state": "pending",
        "focus_context_draft": None,
        "focus_context_question": None,
        "focus_context_answer": None,
        "focus_context_help_updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", task_id).execute()
    background_tasks.add_task(_request_processor_run)
    return {"id": task_id, "focus_context_help_state": "pending"}


@app.post("/tasks/{task_id}/focus-context/answer", tags=["tasks"])
def answer_focus_context_http(task_id: str, request: FocusContextAnswerRequest, background_tasks: BackgroundTasks) -> dict:
    answer = str(request.answer or "").strip()
    if not answer:
        raise HTTPException(status_code=422, detail="Please answer the question")
    rows = (_store().client.table("tasks").select("id,is_open,is_done,is_archived,focus_context_help_state,focus_context_question").eq("id", task_id).limit(1).execute().data or [])
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    task = rows[0]
    if not task.get("is_open") or task.get("is_done") or task.get("is_archived"):
        raise HTTPException(status_code=409, detail="Closed tasks cannot update focus context")
    if str(task.get("focus_context_help_state") or "") != "ready" or not str(task.get("focus_context_question") or "").strip():
        raise HTTPException(status_code=409, detail="There is no context question awaiting an answer")
    now = datetime.now(timezone.utc).isoformat()
    _store().client.table("tasks").update({
        "focus_context_help_state": "answer_pending",
        "focus_context_answer": answer,
        "focus_context_help_updated_at": now,
        "updated_at": now,
    }).eq("id", task_id).execute()
    background_tasks.add_task(_request_processor_run)
    return {"id": task_id, "focus_context_help_state": "answer_pending"}


@app.post("/tasks/{task_id}/focus-context", tags=["tasks"])
def save_focus_context_http(task_id: str, request: FocusContextSaveRequest, background_tasks: BackgroundTasks) -> dict:
    rows = (_store().client.table("tasks").select("id,is_open,is_done,is_archived").eq("id", task_id).limit(1).execute().data or [])
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    task = rows[0]
    if not task.get("is_open") or task.get("is_done") or task.get("is_archived"):
        raise HTTPException(status_code=409, detail="Closed tasks cannot update focus context")
    context = str(request.context or "").strip() or None
    now = datetime.now(timezone.utc).isoformat()
    _store().client.table("tasks").update({
        "context": context,
        "focus_context_help_state": None,
        "focus_context_draft": None,
        "focus_context_question": None,
        "focus_context_answer": None,
        "focus_context_help_updated_at": now,
        "updated_at": now,
    }).eq("id", task_id).execute()
    # Commit point: only now retire the old Start Here. Preserve a
    # not_useful disposition so the next generator knows not to repeat it.
    (_store().client.table("tasks").update({
        "is_open": False,
        "updated_at": now,
    }).eq("parent_task_id", task_id)
      .eq("generated_source", "focus_activation")
      .eq("activation_disposition", "not_useful")
      .eq("is_open", True).eq("is_done", False).eq("is_archived", False)
      .execute())

    # Any other still-open generated activation is being replaced because the
    # durable context changed, not because the user explicitly rejected it.
    (_store().client.table("tasks").update({
        "is_open": False,
        "activation_disposition": "context_changed",
        "updated_at": now,
    }).eq("parent_task_id", task_id)
      .eq("generated_source", "focus_activation")
      .eq("is_open", True).eq("is_done", False).eq("is_archived", False)
      .execute())
    background_tasks.add_task(
        _refresh_focus_activation_after_action,
        task_id,
    )
    return {"id": task_id, "context": context, "regenerating_start_here": True}


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


class ProjectTaskListItem(BaseModel):
    id: str | None = None
    title: str


class ProjectTaskListUpdate(BaseModel):
    tasks: list[ProjectTaskListItem]


class WorkPatternStepRequest(BaseModel):
    title: str
    context: str | None = None

class WorkPatternSaveRequest(BaseModel):
    name: str
    context: str | None = None
    steps: list[WorkPatternStepRequest]

class WorkPatternInstantiateRequest(BaseModel):
    steps: list[WorkPatternStepRequest]


class ProjectWorkAcceptRequest(BaseModel):
    title: str | None = None


class ProjectWorkRetryRequest(BaseModel):
    feedback: str


class ManualBreakdownRequest(BaseModel):
    context: str | None = None


class ManualBreakdownAcceptRequest(BaseModel):
    titles: list[str]


class TaskDetailUpdate(BaseModel):
    title: str | None = None
    context: str | None = None
    due_at: str | None = None
    defer_until: str | None = None
    importance: str | None = None
    urgency: str | None = None
    effort: str | None = None
    duration: str | None = None
    is_just_do_it: bool | None = None


@app.post("/tasks/{task_id}/breakdown/request", tags=["tasks"])
def request_manual_breakdown_http(
    task_id: str,
    request: ManualBreakdownRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    store = _store()
    rows = (
        store.client.table("tasks")
        .select("id,is_open,is_done,is_archived")
        .eq("id", task_id)
        .limit(1)
        .execute().data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Task not found")
    task = rows[0]
    if task.get("is_done") or task.get("is_archived") or not task.get("is_open"):
        raise HTTPException(status_code=409, detail="Closed tasks cannot be broken down")

    child_rows = (
        store.client.table("tasks")
        .select("id,title,is_open,is_done,is_archived,step_order")
        .eq("parent_task_id", task_id)
        .eq("is_archived", False)
        .order("step_order")
        .execute().data
        or []
    )
    if child_rows:
        raise HTTPException(status_code=409, detail="Task already has breakdown children")

    now = datetime.now(timezone.utc).isoformat()
    (
        store.client.table("tasks")
        .update({
            "breakdown_state": "pending",
            "breakdown_request_context": str(request.context or "").strip() or None,
            "breakdown_proposal": None,
            "breakdown_requested_at": now,
            "breakdown_completed_at": None,
            "updated_at": now,
        })
        .eq("id", task_id)
        .execute()
    )
    background_tasks.add_task(_request_processor_run)
    return {"id": task_id, "breakdown_state": "pending"}


@app.post("/tasks/{task_id}/breakdown/accept", tags=["tasks"])
def accept_manual_breakdown_http(
    task_id: str,
    request: ManualBreakdownAcceptRequest,
) -> dict:
    titles = [str(item or "").strip() for item in request.titles if str(item or "").strip()]
    if len(titles) < 2:
        raise HTTPException(status_code=422, detail="Keep at least two breakdown tasks")
    if len(titles) > 5:
        raise HTTPException(status_code=422, detail="Breakdown supports at most five tasks")
    try:
        pages = create_supabase_children_for_existing_parent(
            parent_task_id=task_id,
            subtasks=titles,
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    now = datetime.now(timezone.utc).isoformat()
    (
        _store().client.table("tasks")
        .update({
            "breakdown_state": "accepted",
            "breakdown_proposal": None,
            "breakdown_completed_at": now,
            "updated_at": now,
        })
        .eq("id", task_id)
        .execute()
    )
    try:
        _request_processor_run()
    except Exception:
        pass
    return {"id": task_id, "accepted": True, "children_created": len(pages)}


@app.post("/tasks/{task_id}/breakdown/edit", tags=["tasks"])
def edit_existing_breakdown_http(task_id: str, request: ManualBreakdownAcceptRequest) -> dict:
    titles = [str(item or "").strip() for item in request.titles if str(item or "").strip()]
    try:
        edit_supabase_children_for_existing_parent(parent_task_id=task_id, subtasks=titles)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        _request_processor_run()
    except Exception:
        pass
    return {"id": task_id, "edited": True, "open_children": len(titles)}


@app.post("/tasks/{task_id}/breakdown/cancel", tags=["tasks"])
def cancel_manual_breakdown_http(task_id: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    result = (
        _store().client.table("tasks")
        .update({
            "breakdown_state": None,
            "breakdown_request_context": None,
            "breakdown_proposal": None,
            "breakdown_requested_at": None,
            "breakdown_completed_at": None,
            "updated_at": now,
        })
        .eq("id", task_id)
        .execute()
    )
    if not (result.data or []):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "cancelled": True}


@app.get("/tasks/{task_id}", tags=["tasks"])
def get_task_detail_http(task_id: str) -> dict:
    rows = (
        _store().client.table("tasks")
        .select(
            "id,title,context,status,due_at,defer_until,importance,urgency,parent_task_id,"
            "effort,duration,project_id,is_quick_win,is_just_do_it,"
            "is_open,is_done,is_archived,created_at,updated_at,"
            "breakdown_state,breakdown_request_context,breakdown_proposal,"
            "breakdown_requested_at,breakdown_completed_at"
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

    # Preserve breakdown context when a child task becomes the BNA.
    parent_id = str(task.get("parent_task_id") or "").strip()
    task["parent_title"] = None
    if parent_id:
        try:
            parent_rows = (_store().client.table("tasks")
                .select("id,title")
                .eq("id", parent_id).limit(1).execute().data or [])
            if parent_rows:
                task["parent_title"] = str(parent_rows[0].get("title") or "").strip() or None
        except Exception:
            task["parent_title"] = None
    task["surfaced_quick_win"] = bool(state.get("surfaced_quick_win", False))

    child_rows = (
        _store().client.table("tasks")
        .select("id,title,is_open,is_done,is_archived,step_order")
        .eq("parent_task_id", task_id)
        .eq("is_archived", False)
        .order("step_order")
        .execute()
        .data
        or []
    )
    task["has_breakdown_children"] = bool(child_rows)
    task["breakdown_children"] = [dict(row) for row in child_rows]
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
        "title", "context", "due_at", "defer_until", "importance",
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
        "context", "due_at", "defer_until", "importance",
        "urgency", "effort", "duration",
    ):
        if field in values and values[field] == "":
            values[field] = None

    for field in ("due_at", "defer_until"):
        if field in values and values[field] is not None:
            try:
                values[field] = serialize_task_datetime(values[field])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail=f"Invalid {field.replace('_', ' ')}") from exc

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
    "/projects/{project_id}/work-proposals/generate",
    tags=["projects"],
)
def request_project_work_generation_http(
    project_id: str,
    background_tasks: BackgroundTasks,
) -> dict:
    store = _store()
    rows = (
        store.client
        .table("projects")
        .select("id,is_active,outcome")
        .eq("id", project_id)
        .limit(1)
        .execute()
        .data
        or []
    )

    if not rows:
        raise HTTPException(status_code=404, detail="Project not found")

    project = dict(rows[0])
    if not project.get("is_active"):
        raise HTTPException(
            status_code=409,
            detail="Project must be active before generating project work.",
        )

    now = datetime.now(timezone.utc).isoformat()
    response = (
        store.client
        .table("projects")
        .update({
            "work_generation_requested_at": now,
            "work_generation_completed_at": None,
            "work_generation_state": "pending",
            "work_generation_question": None,
            "work_generation_answer": None,
            "work_generation_context_update": None,
            "work_generation_round": 0,
        })
        .eq("id", project_id)
        .execute()
    )

    if not (response.data or []):
        raise HTTPException(
            status_code=500,
            detail="Project-work generation request could not be saved.",
        )

    background_tasks.add_task(_request_processor_run)

    return {
        "requested": True,
        "project_id": project_id,
        "state": "pending",
    }



class ProjectWorkAnswerRequest(BaseModel):
    answer: str

class ProjectWorkContextRequest(BaseModel):
    context_update: str

@app.post("/projects/{project_id}/work-proposals/answer", tags=["projects"])
def answer_project_work_question_http(project_id: str, payload: ProjectWorkAnswerRequest, background_tasks: BackgroundTasks) -> dict:
    answer = str(payload.answer or "").strip()
    if not answer:
        raise HTTPException(status_code=400, detail="Answer is required")
    rows = (_store().client.table("projects").select("id,work_generation_state").eq("id", project_id).limit(1).execute().data or [])
    if not rows or str(rows[0].get("work_generation_state") or "") != "clarification":
        raise HTTPException(status_code=409, detail="Project is not awaiting a Project Work answer")
    _store().client.table("projects").update({"work_generation_answer": answer, "work_generation_state": "answer_pending", "work_generation_completed_at": None}).eq("id", project_id).execute()
    background_tasks.add_task(_request_processor_run)
    return {"accepted": True, "state": "answer_pending"}

@app.post("/projects/{project_id}/work-proposals/context", tags=["projects"])
def accept_project_work_context_http(project_id: str, payload: ProjectWorkContextRequest, background_tasks: BackgroundTasks) -> dict:
    update = str(payload.context_update or "").strip()
    if not update:
        raise HTTPException(status_code=400, detail="Context update is required")
    rows = (_store().client.table("projects").select("id,context,work_generation_state").eq("id", project_id).limit(1).execute().data or [])
    if not rows or str(rows[0].get("work_generation_state") or "") != "context_review":
        raise HTTPException(status_code=409, detail="Project context update is not awaiting review")
    existing = str(rows[0].get("context") or "").strip()
    merged = (existing + "\n" + update).strip() if existing else update
    _store().client.table("projects").update({"context": merged, "work_generation_state": "pending", "work_generation_requested_at": datetime.now(timezone.utc).isoformat(), "work_generation_completed_at": None, "work_generation_question": None, "work_generation_answer": None, "work_generation_context_update": None}).eq("id", project_id).execute()
    background_tasks.add_task(_request_processor_run)
    return {"accepted": True, "state": "pending", "context": merged}

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

    now = datetime.now(timezone.utc).isoformat()
    (
        store.client
        .table("projects")
        .update({
            "work_generation_requested_at": now,
            "work_generation_completed_at": None,
            "work_generation_state": "pending",
        })
        .eq("id", project_id)
        .execute()
    )

    try:
        _request_processor_run()
    except Exception:
        pass

    return {
        "retry_requested": True,
        "proposal": rejected,
    }


@app.put("/projects/{project_id}/tasks", tags=["projects"])
def update_project_task_list_http(project_id: str, request: ProjectTaskListUpdate) -> dict:
    store = _store()
    project_rows = (
        store.client.table("projects").select("id").eq("id", project_id).limit(1).execute().data or []
    )
    if not project_rows:
        raise HTTPException(status_code=404, detail="Project not found")

    current = (
        store.client.table("tasks")
        .select("id,title,is_open,is_done,is_archived")
        .eq("project_id", project_id)
        .eq("is_open", True)
        .eq("is_done", False)
        .eq("is_archived", False)
        .execute().data or []
    )
    current_ids = {str(row.get("id")) for row in current if row.get("id")}
    requested_existing: set[str] = set()
    normalized: list[tuple[str | None, str]] = []
    for item in request.tasks:
        title = str(item.title or "").strip()
        if not title:
            continue
        task_id = str(item.id or "").strip() or None
        if task_id:
            if task_id not in current_ids:
                raise HTTPException(status_code=409, detail="Project task list changed; reload and try again")
            if task_id in requested_existing:
                raise HTTPException(status_code=422, detail="Duplicate project task")
            requested_existing.add(task_id)
        normalized.append((task_id, title))

    removed_ids = current_ids - requested_existing
    now = datetime.now(timezone.utc).isoformat()
    for task_id in removed_ids:
        store.client.table("tasks").update({"is_archived": True, "is_open": False, "updated_at": now}).eq("id", task_id).execute()

    saved = []
    for order, (task_id, title) in enumerate(normalized, start=1):
        if task_id:
            result = store.client.table("tasks").update({"title": title, "project_order": order, "updated_at": now}).eq("id", task_id).execute()
            rows = result.data or []
            verify = store.client.table("tasks").select("id,title,project_order,updated_at").eq("id", task_id).limit(1).execute().data or []
            if rows:
                saved.append(dict(rows[0]))
        else:
            task = create_supabase_project_task(store, title=title, project_id=project_id)
            result = store.client.table("tasks").update({"project_order": order, "updated_at": now}).eq("id", task["id"]).execute()
            rows = result.data or []
            saved.append(dict(rows[0]) if rows else task)

    # Do not immediately run the processor after editing the project task list.
    # Legacy tasks may still have stale source titles outside Supabase; an
    # immediate processor run can race the authoritative edit and restore the
    # old title. The project-list mutation itself is authoritative in Supabase.
    return {"project_id": project_id, "tasks": saved, "removed": len(removed_ids)}


@app.get("/work-patterns", tags=["work-patterns"])
def list_work_patterns_http() -> dict:
    return {"patterns": list_work_patterns(_store())}

@app.post("/work-patterns", tags=["work-patterns"])
def create_work_pattern_http(request: WorkPatternSaveRequest) -> dict:
    try: return {"pattern": save_work_pattern(_store(), pattern_id=None, name=request.name, context=request.context, steps=[s.model_dump() for s in request.steps])}
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.get("/work-patterns/{pattern_id}", tags=["work-patterns"])
def get_work_pattern_http(pattern_id: str) -> dict:
    pattern=get_work_pattern(_store(),pattern_id)
    if not pattern: raise HTTPException(status_code=404,detail="Work pattern not found")
    return {"pattern":pattern}

@app.put("/work-patterns/{pattern_id}", tags=["work-patterns"])
def update_work_pattern_http(pattern_id: str, request: WorkPatternSaveRequest) -> dict:
    try: return {"pattern":save_work_pattern(_store(),pattern_id=pattern_id,name=request.name,context=request.context,steps=[s.model_dump() for s in request.steps])}
    except ValueError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.delete("/work-patterns/{pattern_id}", tags=["work-patterns"])
def delete_work_pattern_http(pattern_id: str) -> dict:
    try: delete_work_pattern(_store(),pattern_id); return {"deleted":True}
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@app.post("/work-patterns/{pattern_id}/duplicate", tags=["work-patterns"])
def duplicate_work_pattern_http(pattern_id: str) -> dict:
    try: return {"pattern":duplicate_work_pattern(_store(),pattern_id)}
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@app.post("/projects/{project_id}/work-patterns/{pattern_id}/instantiate", tags=["work-patterns"])
def instantiate_work_pattern_http(project_id: str, pattern_id: str, request: WorkPatternInstantiateRequest) -> dict:
    if not get_work_pattern(_store(),pattern_id): raise HTTPException(status_code=404,detail="Work pattern not found")
    try: return {"tasks":instantiate_pattern_for_project(_store(),project_id=project_id,steps=[s.model_dump() for s in request.steps])}
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc


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
            "is_open,is_done,is_archived,project_order,parent_task_id,step_order"
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
        project_order = task.get("project_order")
        rank = task.get("execution_rank")
        score = task.get("execution_score")
        return (
            project_order is None,
            int(project_order) if project_order is not None else 999999,
            rank is None,
            int(rank) if rank is not None else 999999,
            score is None,
            -(float(score) if score is not None else 0.0),
            str(task.get("title") or "").lower(),
        )

    tasks.sort(key=sort_key)
    tasks = _respect_breakdown_step_order(tasks, skip_if_project_ordered=True)

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
            "work_generation_requested_at": project_row.get("work_generation_requested_at"),
            "work_generation_completed_at": project_row.get("work_generation_completed_at"),
            "work_generation_state": project_row.get("work_generation_state"),
            "work_generation_question": project_row.get("work_generation_question"),
            "work_generation_context_update": project_row.get("work_generation_context_update"),
            "work_generation_round": project_row.get("work_generation_round"),
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
            if field in ("due_at", "defer_until"):
                try:
                    value = serialize_task_datetime(value)
                except (TypeError, ValueError) as exc:
                    raise HTTPException(status_code=422, detail=f"Invalid {field.replace('_', ' ')}") from exc
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
    store = _store()
    states = (store.client.table("task_execution_state")
        .select("task_id,execution_score,execution_rank,best_next_action")
        .not_.is_("execution_rank", "null")
        .order("execution_rank")
        .limit(25).execute().data or [])
    if not states:
        return {"focus": None}

    state = None
    task = None
    for candidate_state in states:
        candidate_id = candidate_state.get("task_id")
        if not candidate_id:
            continue
        tasks = (store.client.table("tasks")
            .select("id,title,context,status,due_at,defer_until,importance,urgency,effort,duration,project_id,parent_task_id,is_quick_win,is_just_do_it,is_open,is_done,is_archived,focus_context_help_state,focus_context_draft,focus_context_question")
            .eq("id", candidate_id).eq("is_open", True).eq("is_done", False).eq("is_archived", False)
            .limit(1).execute().data or [])
        if not tasks:
            continue
        candidate_task = dict(tasks[0])
        if _is_future_defer_value(candidate_task.get("defer_until")):
            continue
        state = dict(candidate_state)
        task = candidate_task
        break

    if not state or not task:
        return {"focus": None}
    task_id = state.get("task_id")
    task["execution_score"] = state.get("execution_score")
    task["execution_rank"] = state.get("execution_rank")
    task["best_next_action"] = bool(state.get("best_next_action", False))
    task["parent_title"] = None
    parent_id = str(task.get("parent_task_id") or "").strip()
    if parent_id:
        try:
            parent_rows = (store.client.table("tasks").select("id,title").eq("id", parent_id).limit(1).execute().data or [])
            if parent_rows:
                task["parent_title"] = str(parent_rows[0].get("title") or "").strip() or None
        except Exception:
            task["parent_title"] = None
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
            task["activation_history_exists"] = True
        else:
            activation_history = list_focus_activation_children(
                _store(),
                task_id,
            )
            # Historical activation rows are not evidence that generation is
            # still in progress.  A completed/rejected child can otherwise
            # leave the dashboard pending forever when no replacement child
            # is generated.  The web refresh loop owns the transient pending
            # presentation; this flag only describes durable state.
            task["activation_pending"] = False
            task["activation_history_exists"] = bool(activation_history)
    except Exception:
        task["activation"] = None
        task["activation_pending"] = False
        task["activation_history_exists"] = False

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
    background_tasks: BackgroundTasks,
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

    # The human decision is durable once the review payload is updated.
    # Trigger downstream creation after the response so Review does not
    # wait on Cloud Run job startup/trigger latency.
    background_tasks.add_task(_request_processor_run)

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

# === DAILY JOURNAL V1 ===
class DailyJournalUpdate(BaseModel):
    body: str = ""


def _journal_day_bounds(journal_date: str):
    from datetime import date, datetime, time, timedelta, timezone
    from zoneinfo import ZoneInfo
    try:
        day = date.fromisoformat(str(journal_date or "").strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="journal_date must be YYYY-MM-DD") from exc
    zone_name = os.getenv("AIOS_LOCAL_TIMEZONE", "America/Toronto").strip()
    try:
        zone = ZoneInfo(zone_name)
    except Exception:
        zone = ZoneInfo("America/Toronto")
    start_local = datetime.combine(day, time.min, tzinfo=zone)
    end_local = start_local + timedelta(days=1)
    return day, start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _journal_completed_work(journal_date: str) -> list[dict]:
    _day, start_utc, end_utc = _journal_day_bounds(journal_date)
    store = _store()

    rows = (
        store.client.table("tasks")
        .select(
            "id,title,project_id,parent_task_id,generated_source,"
            "task_role,completed_at"
        )
        .eq("is_done", True)
        .eq("is_archived", False)
        .gte("completed_at", start_utc.isoformat())
        .lt("completed_at", end_utc.isoformat())
        .order("completed_at")
        .execute().data
        or []
    )

    # Match the population used by Completed Today Summary:
    # activation helper children are not meaningful completed project work.
    rows = [
        dict(row)
        for row in rows
        if row.get("generated_source") != "focus_activation"
        and row.get("task_role") != "focus_activation"
    ]

    project_ids = sorted({
        str(row.get("project_id") or "").strip()
        for row in rows
        if str(row.get("project_id") or "").strip()
    })

    project_by_id = {}
    if project_ids:
        project_rows = (
            store.client.table("projects")
            .select("id,name")
            .in_("id", project_ids)
            .execute().data
            or []
        )
        project_by_id = {
            str(row.get("id")): str(row.get("name") or "").strip()
            for row in project_rows
            if row.get("id")
        }

    result = []

    for row in rows:
        item = dict(row)
        project_id = str(item.get("project_id") or "").strip()
        item["project_name"] = project_by_id.get(project_id, "")
        result.append(item)

    return result


def _journal_completion_summary(
    journal_date: str,
    completed_work: list[dict],
) -> tuple[str, str]:
    """
    Read the existing cached Completed Today Summary.

    This never calls AI. The cache is used only when its fingerprint still
    matches the authoritative completed-work set for the day.
    """
    if len(completed_work) < 2:
        return "", "empty"

    try:
        fingerprint = completion_fingerprint(completed_work)

        rows = (
            _store().client
            .table("daily_completion_summaries")
            .select("fingerprint,summary,completed_count")
            .eq("workspace_id", default_workspace_id())
            .eq("summary_date", journal_date)
            .limit(1)
            .execute().data
            or []
        )

        if rows and str(rows[0].get("fingerprint") or "") == fingerprint:
            summary = str(rows[0].get("summary") or "").strip()
            return summary, ("ready" if summary else "empty")

    except Exception as exc:
        print(
            "[Journal] Daily completion summary could not be loaded:",
            exc,
        )
        return "", "empty"

    # For today, a fingerprint mismatch normally means the existing processor
    # is still regenerating the shared Completed Today Summary.
    from datetime import datetime
    from zoneinfo import ZoneInfo

    zone_name = os.getenv(
        "AIOS_LOCAL_TIMEZONE",
        "America/Toronto",
    ).strip()

    try:
        zone = ZoneInfo(zone_name)
    except Exception:
        zone = ZoneInfo("America/Toronto")

    if journal_date == datetime.now(zone).date().isoformat():
        return "", "pending"

    return "", "empty"


@app.get("/journal/{journal_date}", tags=["journal"])
def get_daily_journal_http(journal_date: str) -> dict:
    day, _start, _end = _journal_day_bounds(journal_date)

    rows = (
        _store().client.table("daily_journal")
        .select("journal_date,body,created_at,updated_at")
        .eq("workspace_id", default_workspace_id())
        .eq("journal_date", day.isoformat())
        .limit(1)
        .execute().data
        or []
    )

    journal = (
        dict(rows[0])
        if rows
        else {
            "journal_date": day.isoformat(),
            "body": "",
            "created_at": None,
            "updated_at": None,
        }
    )

    completed_work = _journal_completed_work(day.isoformat())

    completion_summary, completion_summary_state = (
        _journal_completion_summary(
            day.isoformat(),
            completed_work,
        )
    )

    return {
        "journal": journal,
        "completion_summary": completion_summary,
        "completion_summary_state": completion_summary_state,
        "completed_count": len(completed_work),
        "completed_work": completed_work,
    }


@app.put("/journal/{journal_date}", tags=["journal"])
def save_daily_journal_http(journal_date: str, request: DailyJournalUpdate) -> dict:
    from datetime import datetime, timezone
    day, _start, _end = _journal_day_bounds(journal_date)
    body = str(request.body or "")
    if len(body) > 50000:
        raise HTTPException(status_code=400, detail="Journal entry is too long.")
    payload = {
        "workspace_id": default_workspace_id(),
        "journal_date": day.isoformat(),
        "body": body,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    rows = (
        _store().client.table("daily_journal")
        .upsert(payload, on_conflict="workspace_id,journal_date")
        .execute().data
        or []
    )
    return {"saved": True, "journal": dict(rows[0]) if rows else payload}
# === END DAILY JOURNAL V1 ===
