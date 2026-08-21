-- Workspace tenancy Phase 1
-- Schema foundation: workspaces, members, workspace_id on core tables,
-- backfill to a single default workspace. No RLS or auth.
-- Apply once in the Supabase SQL editor.

-- Deterministic default workspace id (also used by AIOS_DEFAULT_WORKSPACE_ID).
-- Safe to reference from application code before multi-workspace UI exists.

create table if not exists public.workspaces (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    slug text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint workspaces_slug_unique unique (slug)
);

create table if not exists public.workspace_members (
    id uuid primary key default gen_random_uuid(),
    workspace_id uuid not null
        references public.workspaces (id)
        on delete cascade,
    user_id text not null,
    role text not null default 'owner'
        check (role in ('owner', 'member')),
    created_at timestamptz not null default now(),
    constraint workspace_members_workspace_user_unique
        unique (workspace_id, user_id)
);

create index if not exists workspace_members_workspace_id_idx
    on public.workspace_members (workspace_id);

insert into public.workspaces (id, name, slug)
values (
    '00000000-0000-4000-8000-000000000001'::uuid,
    'Personal',
    'default'
)
on conflict (id) do nothing;

insert into public.workspace_members (workspace_id, user_id, role)
values (
    '00000000-0000-4000-8000-000000000001'::uuid,
    'default',
    'owner'
)
on conflict (workspace_id, user_id) do nothing;

-- Core entity tables ---------------------------------------------------------

alter table public.tasks
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.tasks
set workspace_id = '00000000-0000-4000-8000-000000000001'::uuid
where workspace_id is null;

alter table public.tasks
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.tasks
    alter column workspace_id set not null;

create index if not exists tasks_workspace_id_idx
    on public.tasks (workspace_id);

alter table public.projects
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.projects
set workspace_id = '00000000-0000-4000-8000-000000000001'::uuid
where workspace_id is null;

alter table public.projects
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.projects
    alter column workspace_id set not null;

create index if not exists projects_workspace_id_idx
    on public.projects (workspace_id);

alter table public.inbox_items
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.inbox_items
set workspace_id = '00000000-0000-4000-8000-000000000001'::uuid
where workspace_id is null;

alter table public.inbox_items
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.inbox_items
    alter column workspace_id set not null;

create index if not exists inbox_items_workspace_id_idx
    on public.inbox_items (workspace_id);

alter table public.work_patterns
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.work_patterns
set workspace_id = '00000000-0000-4000-8000-000000000001'::uuid
where workspace_id is null;

alter table public.work_patterns
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.work_patterns
    alter column workspace_id set not null;

create index if not exists work_patterns_workspace_id_idx
    on public.work_patterns (workspace_id);

-- Per-workspace daily records (composite primary keys) -----------------------

alter table public.daily_journal
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.daily_journal
set workspace_id = '00000000-0000-4000-8000-000000000001'::uuid
where workspace_id is null;

alter table public.daily_journal
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.daily_journal
    alter column workspace_id set not null;

alter table public.daily_journal
    drop constraint if exists daily_journal_pkey;

alter table public.daily_journal
    add constraint daily_journal_pkey
        primary key (workspace_id, journal_date);

alter table public.daily_completion_summaries
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.daily_completion_summaries
set workspace_id = '00000000-0000-4000-8000-000000000001'::uuid
where workspace_id is null;

alter table public.daily_completion_summaries
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.daily_completion_summaries
    alter column workspace_id set not null;

alter table public.daily_completion_summaries
    drop constraint if exists daily_completion_summaries_pkey;

alter table public.daily_completion_summaries
    add constraint daily_completion_summaries_pkey
        primary key (workspace_id, summary_date);

-- Derived / cache tables (denormalized workspace_id for future RLS) -----------

alter table public.inbox_reviews
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.inbox_reviews r
set workspace_id = i.workspace_id
from public.inbox_items i
where r.inbox_item_id = i.id
  and r.workspace_id is null;

alter table public.inbox_reviews
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.inbox_reviews
    alter column workspace_id set not null;

create index if not exists inbox_reviews_workspace_id_idx
    on public.inbox_reviews (workspace_id);

alter table public.project_work_proposals
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.project_work_proposals p
set workspace_id = pr.workspace_id
from public.projects pr
where p.project_id = pr.id
  and p.workspace_id is null;

alter table public.project_work_proposals
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.project_work_proposals
    alter column workspace_id set not null;

create index if not exists project_work_proposals_workspace_id_idx
    on public.project_work_proposals (workspace_id);

alter table public.task_focus_guidance
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.task_focus_guidance g
set workspace_id = t.workspace_id
from public.tasks t
where g.task_id = t.id
  and g.workspace_id is null;

alter table public.task_focus_guidance
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.task_focus_guidance
    alter column workspace_id set not null;

create index if not exists task_focus_guidance_workspace_id_idx
    on public.task_focus_guidance (workspace_id);

alter table public.task_execution_state
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.task_execution_state s
set workspace_id = t.workspace_id
from public.tasks t
where s.task_id = t.id
  and s.workspace_id is null;

alter table public.task_execution_state
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.task_execution_state
    alter column workspace_id set not null;

create index if not exists task_execution_state_workspace_id_idx
    on public.task_execution_state (workspace_id);

alter table public.task_evaluations
    add column if not exists workspace_id uuid
        references public.workspaces (id);

update public.task_evaluations e
set workspace_id = t.workspace_id
from public.tasks t
where e.task_id = t.id
  and e.workspace_id is null;

alter table public.task_evaluations
    alter column workspace_id set default '00000000-0000-4000-8000-000000000001'::uuid;

alter table public.task_evaluations
    alter column workspace_id set not null;

create index if not exists task_evaluations_workspace_id_idx
    on public.task_evaluations (workspace_id);
