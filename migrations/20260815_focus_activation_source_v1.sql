alter table public.tasks
add column if not exists generated_source text;

create index if not exists tasks_parent_generated_source_idx
on public.tasks (parent_task_id, generated_source);
