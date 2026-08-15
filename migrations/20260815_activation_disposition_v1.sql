alter table public.tasks
add column if not exists activation_disposition text;

create index if not exists tasks_activation_disposition_idx
on public.tasks (activation_disposition);
