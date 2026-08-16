alter table public.projects
add column if not exists possible_existing_project_id uuid
    references public.projects(id)
    on delete set null;

alter table public.projects
add column if not exists possible_existing_project_confidence double precision;

alter table public.projects
drop constraint if exists projects_possible_existing_project_confidence_check;

alter table public.projects
add constraint projects_possible_existing_project_confidence_check
check (
    possible_existing_project_confidence is null
    or (
        possible_existing_project_confidence >= 0
        and possible_existing_project_confidence <= 1
    )
);
