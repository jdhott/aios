alter table public.projects
add column if not exists work_generation_requested_at timestamptz;

alter table public.projects
add column if not exists work_generation_completed_at timestamptz;

alter table public.projects
add column if not exists work_generation_state text;

alter table public.projects
drop constraint if exists projects_work_generation_state_check;

alter table public.projects
add constraint projects_work_generation_state_check
check (
    work_generation_state is null
    or work_generation_state in ('pending', 'actionable', 'waiting', 'failed')
);
