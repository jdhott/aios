alter table public.tasks
add column if not exists task_role text;

create index if not exists tasks_task_role_idx
on public.tasks (task_role);
