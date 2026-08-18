alter table public.tasks
add column if not exists project_order integer;

create index if not exists tasks_project_order_idx
on public.tasks (project_id, project_order)
where is_archived = false;
