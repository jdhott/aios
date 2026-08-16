create table if not exists public.project_work_proposals (
    id uuid primary key default gen_random_uuid(),

    project_id uuid not null
        references public.projects(id)
        on delete cascade,

    title text not null,

    status text not null default 'proposed'
        check (status in ('proposed', 'accepted', 'dismissed')),

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    accepted_at timestamptz,
    dismissed_at timestamptz
);

create index if not exists project_work_proposals_project_idx
on public.project_work_proposals (project_id);

create index if not exists project_work_proposals_status_idx
on public.project_work_proposals (status);

create unique index if not exists project_work_proposals_open_title_idx
on public.project_work_proposals (
    project_id,
    lower(trim(title))
)
where status = 'proposed';
