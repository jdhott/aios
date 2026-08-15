from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Project:
    id: str
    name: str

    legacy_notion_id: Optional[str] = None
    status: Optional[str] = None
    is_active: bool = False

    legacy_metadata: dict[str, Any] = field(
        default_factory=dict
    )

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Task:
    id: str
    title: str

    legacy_notion_id: Optional[str] = None

    is_open: bool = True
    is_done: bool = False
    is_archived: bool = False

    status: Optional[str] = None

    importance: Optional[str] = None
    urgency: Optional[str] = None
    effort: Optional[str] = None
    duration: Optional[str] = None

    due_at: Optional[datetime] = None
    defer_until: Optional[datetime] = None

    is_just_do_it: bool = False
    is_quick_win: bool = False

    suggested_project: Optional[str] = None

    project_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    step_order: Optional[int] = None
    generated_source: Optional[str] = None
    task_role: Optional[str] = None
    activation_disposition: Optional[str] = None

    legacy_metadata: dict[str, Any] = field(
        default_factory=dict
    )

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None